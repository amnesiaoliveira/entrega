(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const icons = {
    grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
    box: '<path d="m12 3 9 5v9l-9 5-9-5V8zM3 8l9 5 9-5M12 13v9M7.5 5.5l9 5v4"/>',
    truck: '<path d="M3 5h11v12H3zM14 9h4l3 4v4h-7"/><circle cx="7" cy="18" r="2"/><circle cx="18" cy="18" r="2"/>',
    clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    check: '<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>',
    plus: '<path d="M12 5v14M5 12h14"/>',
    search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 4 4"/>',
    calendar: '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M7 3v4M17 3v4M3 11h18M7 15h3M14 15h3"/>',
    download: '<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
    refresh: '<path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 6M4 12l2 6a7 7 0 0 0 12-1"/>',
    phone: '<rect x="6" y="2" width="12" height="20" rx="2"/><path d="M10 18h4M10 5h4"/>',
    store: '<path d="M4 10v11h16V10M2 10l2-7h16l2 7M2 10c0 4 5 4 5 0 0 4 5 4 5 0 0 4 5 4 5 0 0 4 5 4 5 0M9 21v-6h6v6"/>',
    logout: '<path d="M10 4H4v16h6M9 12h12m-5-5 5 5-5 5"/>',
  };
  const icon = (name) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[name] || ''}</svg>`;
  document.querySelectorAll('[data-icon]').forEach((node) => { node.innerHTML = icon(node.dataset.icon); });
  const escape = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
  const labels = {pendente: 'Pendente', em_rota: 'Em rota', entregue: 'Entregue', cancelada: 'Cancelada'};
  const user = $('.app-layout').dataset.user;
  let today = $('.app-layout').dataset.hoje;
  const storeTimezone = $('.app-layout').dataset.fuso;
  let followToday = true;
  let serverOffset = 0;
  const draftKey = `baranda.draft.${user}`;
  const state = {items: [], status: '', page: 1, request: 0, online: navigator.onLine, editing: null, detail: null, saving: false};
  const selectedDeliveries = new Set();
  let couriers = [];
  function courierOptions(selected = null, allowInactive = false) {
    return '<option value="">A definir</option>' + couriers.filter((item) => item.ativo || (allowInactive && item.id === Number(selected))).map((item) => `<option value="${item.id}">${escape(item.nome)}${item.ativo ? '' : ' (inativo)'}</option>`).join('');
  }
  let timer;
  let confirmTask;
  const form = $('#delivery-form');
  const storage = {
    get(key) { try { return localStorage.getItem(key); } catch { return null; } },
    set(key, value) { try { localStorage.setItem(key, value); return true; } catch { return false; } },
    remove(key) { try { localStorage.removeItem(key); } catch { /* Storage disabled. */ } },
  };
  if (storage.get('baranda.user') !== user) storage.remove('baranda.offline');
  storage.set('baranda.user', user);
  function showDay() {
    $('#today-label').textContent = new Date(`${today}T12:00:00`).toLocaleDateString('pt-BR', {weekday: 'long', day: 'numeric', month: 'long', year: 'numeric'}).toUpperCase();
  }
  function updateDay(day) {
    if (!day || day === today) return false;
    today = day;
    showDay();
    if (!followToday) return false;
    $('#date').value = today;
    selectedDeliveries.clear();
    state.items = [];
    state.page = 1;
    render();
    return true;
  }
  function checkDay() {
    const parts = Object.fromEntries(new Intl.DateTimeFormat('en', {timeZone: storeTimezone, year: 'numeric', month: '2-digit', day: '2-digit'}).formatToParts(new Date(Date.now() + serverOffset)).map((part) => [part.type, part.value]));
    if (updateDay(`${parts.year}-${parts.month}-${parts.day}`)) load();
  }
  showDay();

  function toast(message) {
    clearTimeout(timer);
    $('#toast').textContent = message;
    $('#toast').hidden = false;
    timer = setTimeout(() => { $('#toast').hidden = true; }, 4500);
  }
  function connection(online) {
    state.online = online;
    $('#connection').classList.toggle('offline', !online);
    $('#connection').innerHTML = `<i></i>${online ? 'Conectado' : 'Sem conexão'}`;
    $('#offline-banner').hidden = online;
    $('#export').disabled = !online;
    $('#save-delivery').disabled = !online || state.saving;
    $('#emit-route').disabled = !online || selectedDeliveries.size === 0;
    document.querySelectorAll('[data-online-action]').forEach((button) => { button.disabled = !online; });
  }
  async function api(url, options = {}) {
    const csrf = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))?.slice(10);
    let response;
    try {
      response = await fetch(url, {
        ...options,
        signal: AbortSignal.timeout(15000),
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': csrf || '', ...options.headers},
      });
    } catch {
      connection(false);
      throw new Error('Não foi possível acessar o servidor. Seu formulário foi preservado.');
    }
    if (response.status === 401) {
      storage.remove('baranda.offline');
      storage.remove('baranda.user');
      location.href = '/entrar/';
      throw new Error('Sua sessão expirou. Entre novamente.');
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const messages = data.erros ? Object.entries(data.erros).map(([field, errors]) => `${field}: ${errors.join(' ')}`).join('\n') : '';
      throw new Error(data.erro || messages || `Não foi possível concluir a operação (${response.status}).`);
    }
    connection(true);
    return data;
  }
  function params() {
    return new URLSearchParams({data: $('#date').value, busca: $('#search').value.trim()});
  }
  async function load() {
    const request = ++state.request;
    $('.deliveries-panel').setAttribute('aria-busy', 'true');
    $('#refresh').disabled = true;
    $('#list-error').hidden = true;
    $('#loading').hidden = state.items.length > 0;
    try {
      const result = await api(`/api/entregas/?${params()}`);
      if (request !== state.request) return;
      serverOffset = new Date(result.consultado_em).getTime() - Date.now();
      if (updateDay(result.hoje)) { await load(); return; }
      state.items = result.entregas;
      couriers = result.entregadores || [];
      const saved = storage.set('baranda.offline', JSON.stringify({user, at: result.consultado_em, items: state.items, query: params().toString()}));
      $('#last-updated').textContent = `Atualizado às ${new Date(result.consultado_em).toLocaleTimeString('pt-BR', {hour: '2-digit', minute: '2-digit'})}${saved ? '' : ' · Cópia offline indisponível'}`;
    } catch (error) {
      if (request !== state.request) return;
      let snapshot;
      try { snapshot = JSON.parse(storage.get('baranda.offline')); } catch { snapshot = null; }
      if (!state.online && snapshot?.user === user) {
        const query = $('#search').value.trim().toLocaleLowerCase('pt-BR');
        state.items = snapshot.items.filter((item) => (!$('#date').value || item.data === $('#date').value) && [item.nome, item.cpf, formatCpf(item.cpf), item.endereco, item.cupom, item.sequencia, item.responsavel].join(' ').toLocaleLowerCase('pt-BR').includes(query));
        $('#last-updated').textContent = `Cópia de ${new Date(snapshot.at).toLocaleString('pt-BR')}`;
        $('#offline-banner').textContent = 'Sem conexão. Exibindo somente entregas da última consulta salva neste dispositivo. Alterações precisam de conexão.';
      } else {
        state.items = [];
        $('#list-error').textContent = error.message;
        $('#list-error').hidden = false;
      }
    } finally {
      if (request === state.request) {
        $('#loading').hidden = true;
        $('.deliveries-panel').setAttribute('aria-busy', 'false');
        $('#refresh').disabled = false;
        render();
      }
    }
  }
  function badge(status) { return `<span class="badge ${escape(status)}">${escape(labels[status])}</span>`; }
  function render() {
    const counts = {pendente: 0, em_rota: 0, entregue: 0, cancelada: 0};
    for (const item of state.items) counts[item.status]++;
    $('#stat-total').textContent = state.items.length;
    $('#tab-total').textContent = state.items.length;
    for (const [key, value] of Object.entries(counts)) {
      if ($(`#stat-${key}`)) $(`#stat-${key}`).textContent = value;
      $(`#tab-${key}`).textContent = value;
    }
    const filtered = state.items.filter((item) => !state.status || item.status === state.status);
    const pages = Math.max(1, Math.ceil(filtered.length / 8));
    state.page = Math.min(state.page, pages);
    const start = (state.page - 1) * 8;
    const visible = filtered.slice(start, start + 8);
    $('#list-count').textContent = filtered.length;
    $('#delivery-list').innerHTML = visible.map((item) => {
      const initials = item.nome.trim().split(/\s+/).slice(0, 2).map((word) => word[0]).join('').toUpperCase();
      return `<tr><td><div class="client-cell"><span class="client-avatar">${escape(initials)}</span><div><span class="client-name">${escape(item.nome)}</span><span class="cell-sub">#${item.sequencia} <span aria-hidden="true">·</span> Cupom ${escape(item.cupom)}</span></div></div></td><td class="address-cell"><span class="address-text" title="${escape(item.endereco)}">${escape(item.endereco)}</span><span class="cell-sub">${item.data.split('-').reverse().join('/')} ${item.horario ? `· ${item.horario}` : '· Sem horário'}</span></td><td><span class="volumes">${icon('box')} ${item.volumes} ${item.volumes === 1 ? 'volume' : 'volumes'}</span></td><td><span class="courier">${item.responsavel ? '<i class="dot"></i>' : ''}${escape(item.responsavel || 'A definir')}</span></td><td>${badge(item.status)}</td><td><button class="icon-button row-open" data-id="${item.id}" aria-label="Abrir entrega ${item.sequencia}" title="Ver detalhes">↗</button></td></tr>`;
    }).join('');
    $('#delivery-list').querySelectorAll('.client-cell').forEach((cell, index) => {
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.className = 'delivery-select';
      checkbox.dataset.selectionId = visible[index].id;
      checkbox.setAttribute('aria-label', `Selecionar entrega ${visible[index].sequencia}`);
      cell.prepend(checkbox);
      const actions = cell.closest('tr').lastElementChild;
      actions.className = 'delivery-actions';
      actions.innerHTML = deliveryActions(visible[index]);
    });
    updateSelection();
    $('#empty-state').hidden = filtered.length !== 0;
    $('#empty-description').textContent = state.status || $('#search').value ? 'Tente outro status, data ou termo de busca.' : 'Cadastre a primeira entrega e comece a organizar o dia.';
    $('#showing').textContent = filtered.length ? `Mostrando ${start + 1}–${start + visible.length} de ${filtered.length} entregas` : 'Nenhuma entrega encontrada';
    $('#page-info').textContent = `${state.page} / ${pages}`;
    $('#previous').disabled = state.page === 1;
    $('#next').disabled = state.page === pages;
    const defaultDate = followToday ? today : '';
    $('#clear-filters').hidden = !($('#search').value || state.status || $('#date').value !== defaultDate);
    document.querySelectorAll('.status-tabs [data-status]').forEach((button) => button.setAttribute('aria-pressed', String(button.dataset.status === state.status)));
  }
  function deliveryActions(item) {
    const button = (action, label) => `<button type="button" class="row-action" data-online-action data-action="${action}" data-id="${item.id}" ${state.online ? '' : 'disabled'}>${label}</button>`;
    let actions = `<button type="button" class="row-action row-open" data-action="details" data-id="${item.id}" aria-label="Abrir entrega ${item.sequencia}">Detalhes</button>`;
    if (item.status === 'pendente') actions += button('start', 'Iniciar rota →');
    if (item.status === 'em_rota') actions += button('print', 'Imprimir ficha') + button('edit', 'Editar') + button('cancel', 'Cancelar') + button('complete', 'Confirmar entrega ✓');
    return `<div class="row-actions">${actions}</div>`;
  }
  function updateSelection() {
    const boxes = [...document.querySelectorAll('.delivery-select')];
    for (const checkbox of boxes) {
      checkbox.checked = selectedDeliveries.has(Number(checkbox.dataset.selectionId));
      checkbox.closest('tr').classList.toggle('selected-delivery', checkbox.checked);
    }
    const checked = boxes.filter((checkbox) => checkbox.checked).length;
    $('#select-page').checked = boxes.length > 0 && checked === boxes.length;
    $('#select-page').indeterminate = checked > 0 && checked < boxes.length;
    $('#select-page').disabled = boxes.length === 0;
    $('#selection-count').textContent = selectedDeliveries.size ? `${selectedDeliveries.size} selecionada(s), incluindo outras páginas e filtros. O roteiro incluirá apenas pendentes.` : 'Nenhuma selecionada';
    $('#clear-selection').disabled = selectedDeliveries.size === 0;
    $('#emit-route').disabled = !state.online || selectedDeliveries.size === 0;
  }
  $('#delivery-list').addEventListener('change', (event) => {
    const checkbox = event.target.closest('.delivery-select');
    if (!checkbox) return;
    const id = Number(checkbox.dataset.selectionId);
    if (checkbox.checked && selectedDeliveries.size >= 100) {
      toast('Selecione no máximo 100 entregas por roteiro.');
    } else if (checkbox.checked) selectedDeliveries.add(id);
    else selectedDeliveries.delete(id);
    updateSelection();
  });
  $('#select-page').addEventListener('change', (event) => {
    const ids = [...document.querySelectorAll('.delivery-select')].map((checkbox) => Number(checkbox.dataset.selectionId));
    if (event.target.checked && new Set([...selectedDeliveries, ...ids]).size > 100) {
      toast('Selecione no máximo 100 entregas por roteiro.');
    } else {
      for (const id of ids) {
        if (event.target.checked) selectedDeliveries.add(id);
        else selectedDeliveries.delete(id);
      }
    }
    updateSelection();
  });
  $('#clear-selection').addEventListener('click', () => { selectedDeliveries.clear(); updateSelection(); });
  $('#emit-route').addEventListener('click', () => {
    if (!state.online || selectedDeliveries.size === 0) return;
    window.open(`/roteiro/?${new URLSearchParams({ids: [...selectedDeliveries].join(',')})}`, '_blank', 'noopener,noreferrer');
  });
  function formatCpf(value = '') {
    return value.replace(/\D/g, '').slice(0, 11)
      .replace(/^(\d{3})(\d)/, '$1.$2')
      .replace(/^(\d{3}\.\d{3})(\d)/, '$1.$2')
      .replace(/^(\d{3}\.\d{3}\.\d{3})(\d)/, '$1-$2');
  }
  const cpfInput = form.elements.namedItem('cpf');
  const customerFields = ['nome', 'telefone', 'endereco'];
  let cpfTimer;
  let cpfRequest = 0;
  let filledCpf = '';
  function cpfMessage(message = '') {
    $('#cpf-status').textContent = message;
    $('#cpf-status').hidden = !message;
  }
  async function lookupCustomer(cpf, request) {
    if (state.editing || state.saving || !$('#delivery-dialog').open) return;
    if (!state.online) {
      cpfMessage('Sem conexão para consultar o CPF. Você pode preencher os dados manualmente.');
      return;
    }
    const previous = Object.fromEntries(customerFields.map((key) => [key, form.elements.namedItem(key).value]));
    cpfMessage('Buscando cliente…');
    try {
      const result = await api('/api/clientes/por-cpf/', {method: 'POST', body: JSON.stringify({cpf})});
      if (request !== cpfRequest || state.saving || state.editing || !$('#delivery-dialog').open || cpfInput.value.replace(/\D/g, '') !== cpf) return;
      if (!result.cliente) {
        cpfMessage('CPF ainda não encontrado. Preencha os dados para a primeira entrega.');
        return;
      }
      for (const key of customerFields) {
        const input = form.elements.namedItem(key);
        // Uma resposta atrasada não sobrescreve o que o operador acabou de digitar.
        if (input.value === previous[key]) input.value = key === 'telefone' ? formatPhone(result.cliente[key]) : result.cliente[key];
      }
      filledCpf = cpf;
      saveDraft();
      cpfMessage('Cliente encontrado. Revise nome, telefone e endereço antes de salvar.');
    } catch (error) {
      if (request === cpfRequest && $('#delivery-dialog').open && !state.saving) cpfMessage(error.message);
    }
  }
  cpfInput.addEventListener('input', () => {
    const before = cpfInput.value.slice(0, cpfInput.selectionStart ?? cpfInput.value.length).replace(/\D/g, '').length;
    cpfInput.value = formatCpf(cpfInput.value);
    let cursor = 0;
    let digits = 0;
    while (cursor < cpfInput.value.length && digits < before) {
      if (/\d/.test(cpfInput.value[cursor])) digits++;
      cursor++;
    }
    cpfInput.setSelectionRange(cursor, cursor);
    clearTimeout(cpfTimer);
    const request = ++cpfRequest;
    if (state.editing) return;
    const cpf = cpfInput.value.replace(/\D/g, '');
    if (filledCpf && filledCpf !== cpf) {
      for (const key of customerFields) form.elements.namedItem(key).value = '';
      filledCpf = '';
    }
    cpfMessage();
    if (cpf.length === 11) cpfTimer = setTimeout(() => lookupCustomer(cpf, request), 250);
  });
  function formatPhone(value) {
    const digits = value.replace(/\D/g, '');
    if (!digits) return '';
    // Preserve international numbers already accepted by the application.
    if (value.trim().startsWith('+') || digits.length > 11) {
      return `${value.trim().startsWith('+') ? '+' : ''}${digits}`;
    }
    if (digits.length <= 2) return `(${digits}`;
    const subscriber = digits.slice(2);
    const split = digits.length === 11 ? 5 : 4;
    return `(${digits.slice(0, 2)}) ${subscriber.slice(0, split)}${subscriber.length > split ? `-${subscriber.slice(split)}` : ''}`;
  }
  const phoneInput = form.elements.namedItem('telefone');
  phoneInput.placeholder = '(00) 00000-0000';
  phoneInput.addEventListener('input', () => {
    const position = phoneInput.selectionStart ?? phoneInput.value.length;
    const digitsBeforeCursor = phoneInput.value.slice(0, position).replace(/\D/g, '').length;
    const formatted = formatPhone(phoneInput.value);
    phoneInput.value = formatted;
    let cursor = 0;
    let digitsSeen = 0;
    while (cursor < formatted.length && digitsSeen < digitsBeforeCursor) {
      if (/\d/.test(formatted[cursor])) digitsSeen++;
      cursor++;
    }
    phoneInput.setSelectionRange(cursor, cursor);
  });
  function newRequestId() {
    if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
    // getRandomValues também funciona no HTTP da rede local. UUID v4 (RFC 9562).
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  function openForm(item = null) {
    clearTimeout(cpfTimer);
    cpfRequest++;
    filledCpf = '';
    cpfMessage();
    state.editing = item;
    form.reset();
    $('#form-errors').hidden = true;
    $('#dialog-title').textContent = item ? `Editar entrega #${item.sequencia}` : 'Nova entrega';
    $('#form-description').textContent = item ? 'Atualize os dados e salve as alterações.' : 'Preencha os dados. A sequência será gerada ao salvar.';
    let values = item || {data: $('#date').value || today, volumes: 1};
    if (!item) {
      try {
        const draft = JSON.parse(storage.get(draftKey));
        if (draft) {
          values = draft;
          $('#form-description').textContent = 'Seu rascunho foi recuperado. Revise os dados antes de salvar.';
        }
      } catch { /* Ignore invalid local drafts. */ }
    }
    if (!values.entregador && values.responsavel) values = {...values, entregador: couriers.find((entry) => entry.nome === values.responsavel)?.id || ''};
    form.elements.namedItem('entregador').innerHTML = courierOptions(values.entregador, Boolean(item));
    for (const [key, value] of Object.entries(values)) {
      if (form.elements.namedItem(key)) form.elements.namedItem(key).value = value ?? '';
    }
    phoneInput.value = formatPhone(phoneInput.value);
    cpfInput.value = formatCpf(cpfInput.value);
    form.dataset.requisicao = values.requisicao || newRequestId();
    $('#delivery-dialog').showModal();
    if (!item) cpfInput.focus();
  }
  function saveDraft() {
    if (!state.editing) {
      storage.set(draftKey, JSON.stringify({...Object.fromEntries(new FormData(form)), requisicao: form.dataset.requisicao}));
    }
  }
  form.addEventListener('input', saveDraft);
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (state.saving) return;
    clearTimeout(cpfTimer);
    cpfRequest++;
    state.saving = true;
    $('#save-delivery').disabled = true;
    $('#save-delivery').textContent = 'Salvando…';
    $('#form-errors').hidden = true;
    const editing = state.editing;
    const data = {...Object.fromEntries(new FormData(form)), requisicao: form.dataset.requisicao};
    if (editing) data.versao = editing.versao;
    saveDraft();
    for (const element of form.elements) element.disabled = true;
    try {
      const result = await api(editing ? `/api/entregas/${editing.id}/` : '/api/entregas/', {method: editing ? 'PATCH' : 'POST', body: JSON.stringify(data)});
      if (!editing) storage.remove(draftKey);
      $('#delivery-dialog').close();
      $('#detail-dialog').close();
      $('#date').value = result.entrega.data;
      followToday = $('#date').value === today && $('[data-view="operacao"]').classList.contains('active');
      $('#search').value = '';
      chooseStatus('');
      state.page = 1;
      toast(editing ? 'Entrega atualizada.' : `Entrega #${result.entrega.sequencia} cadastrada com sucesso.`);
      await load();
    } catch (error) {
      $('#form-errors').textContent = error.message;
      $('#form-errors').hidden = false;
    } finally {
      state.saving = false;
      for (const element of form.elements) element.disabled = false;
      $('#save-delivery').disabled = !state.online;
      $('#save-delivery').textContent = 'Salvar entrega';
    }
  });
  $('#delivery-dialog').addEventListener('cancel', (event) => { if (state.saving) event.preventDefault(); });
  async function showDetail(id) {
    try {
      let result;
      if (state.online) result = await api(`/api/entregas/${id}/`);
      else result = {entrega: state.items.find((item) => item.id === id), eventos: []};
      const item = result.entrega;
      if (!item) return;
      state.detail = item;
      $('#detail-title').textContent = `Entrega #${item.sequencia}`;
      const field = (name, value, full = false) => `<div class="${full ? 'full' : ''}"><dt>${name}</dt><dd>${escape(value || 'Não informado')}</dd></div>`;
      const digits = item.telefone.replace(/[^\d+]/g, '');
      $('#detail-content').innerHTML = `${badge(item.status)}<h3 class="detail-name">${escape(item.nome)}</h3><div class="detail-links"><a href="tel:${escape(digits)}">Ligar para o cliente</a><a href="https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(item.endereco)}" target="_blank" rel="noopener noreferrer">Abrir endereço no mapa ↗</a></div><dl class="detail-grid">${field('Endereço completo', item.endereco, true)}${field('Telefone', item.telefone)}${field('CPF', formatCpf(item.cpf))}${field('Número do cupom', item.cupom)}${field('Volumes', item.volumes)}${field('Entregador', item.responsavel)}${field('Data da entrega', item.data.split('-').reverse().join('/'))}${field('Horário previsto', item.horario)}${field('Observações', item.observacoes, true)}</dl><h3 class="form-section">Histórico da entrega</h3><ol class="timeline">${result.eventos.map((entry) => `<li>${escape(entry.descricao)}<small>${escape(entry.usuario)} · ${new Date(entry.criado_em).toLocaleString('pt-BR')}</small></li>`).join('') || '<li>Histórico disponível com conexão.</li>'}</ol>`;
      $('#detail-actions').innerHTML = '<button type="button" class="button secondary" id="close-details">Fechar</button>';
      $('#close-details').addEventListener('click', () => $('#detail-dialog').close());
      if (!$('#detail-dialog').open) $('#detail-dialog').showModal();
    } catch (error) { toast(error.message); }
  }
  function confirmStatus(item, status) {
    $('#confirm-title').textContent = status === 'cancelada' ? 'Cancelar esta entrega?' : status === 'em_rota' ? 'Tudo pronto para sair?' : 'Confirmar recebimento?';
    $('#confirm-message').textContent = status === 'cancelada' ? `A entrega #${item.sequencia} será encerrada como cancelada. O registro será mantido no histórico.` : status === 'em_rota' ? `Confirme o endereço, os ${item.volumes} volume(s) e o entregador antes de iniciar a rota.` : `Confirme que ${item.nome} recebeu os ${item.volumes} volume(s). Esta ação finaliza a entrega.`;
    $('#confirm-error').hidden = true;
    $('#route-courier-field').hidden = status !== 'em_rota';
    $('#route-courier').innerHTML = courierOptions();
    $('#route-courier').value = item.entregador || '';
    $('#confirm-action').classList.toggle('danger', status === 'cancelada');
    confirmTask = async () => {
      const payload = {status, versao: item.versao};
      if (status === 'em_rota') payload.entregador = $('#route-courier').value;
      await api(`/api/entregas/${item.id}/`, {method: 'PATCH', body: JSON.stringify(payload)});
      $('#confirm-dialog').close();
      $('#detail-dialog').close();
      toast(`Entrega #${item.sequencia}: ${labels[status].toLowerCase()}.`);
      await load();
    };
    $('#confirm-dialog').showModal();
  }
  $('#confirm-action').addEventListener('click', async () => {
    $('#confirm-action').disabled = true;
    try { await confirmTask(); }
    catch (error) { $('#confirm-error').textContent = error.message; $('#confirm-error').hidden = false; }
    finally { $('#confirm-action').disabled = false; }
  });
  function chooseStatus(status) {
    state.status = status;
    state.page = 1;
    document.querySelectorAll('.status-tabs [data-status]').forEach((button) => {
      const active = button.dataset.status === status;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    render();
  }
  document.querySelectorAll('[data-status]').forEach((button) => button.addEventListener('click', () => chooseStatus(button.dataset.status)));
  $('#new-delivery').addEventListener('click', () => openForm());
  $('#empty-new').addEventListener('click', () => openForm());
  $('#delivery-list').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-id]');
    if (!button) return;
    const id = Number(button.dataset.id);
    const action = button.dataset.action;
    if (action === 'details') { showDetail(id); return; }
    if (!state.online) return;
    if (action === 'print') {
      window.open(`/entregas/${id}/ficha/`, '_blank', 'noopener,noreferrer');
      return;
    }
    button.disabled = true;
    try {
      const {entrega: item} = await api(`/api/entregas/${id}/`);
      if (item.status !== (action === 'start' ? 'pendente' : 'em_rota')) {
        toast('O status desta entrega mudou. A lista será atualizada.');
        await load();
        return;
      }
      if (action === 'edit') openForm(item);
      else confirmStatus(item, {start: 'em_rota', cancel: 'cancelada', complete: 'entregue'}[action]);
    } catch (error) { toast(error.message); }
    finally { button.disabled = !state.online; }
  });
  $('#previous').addEventListener('click', () => { state.page--; render(); });
  $('#next').addEventListener('click', () => { state.page++; render(); });
  $('#refresh').addEventListener('click', load);
  $('#date').addEventListener('change', () => { followToday = $('#date').value === today && $('[data-view="operacao"]').classList.contains('active'); state.page = 1; load(); });
  let searchTimer;
  $('#search').addEventListener('input', () => { clearTimeout(searchTimer); searchTimer = setTimeout(() => { state.page = 1; load(); }, 300); });
  $('#clear-filters').addEventListener('click', () => {
    $('#search').value = '';
    $('#date').value = followToday ? today : '';
    chooseStatus('');
    state.page = 1;
    load();
    $('#search').focus();
  });
  $('#export').addEventListener('click', async () => {
    const query = params();
    query.set('status', state.status);
    $('#export').disabled = true;
    try {
      const response = await fetch(`/exportar/?${query}`, {signal: AbortSignal.timeout(15000)});
      if (!response.ok) throw new Error('Não foi possível exportar. Atualize a página e tente novamente.');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `entregas-baranda-${$('#date').value || 'historico'}.csv`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      toast('Arquivo de entregas exportado.');
    } catch (error) { toast(error.message); }
    finally { $('#export').disabled = !state.online; }
  });
  function selectView(view, updateUrl = true) {
    const historyView = view === 'historico';
    followToday = !historyView;
    document.querySelectorAll('[data-view]').forEach((node) => {
      const active = node.dataset.view === view;
      node.classList.toggle('active', active);
      if (active) node.setAttribute('aria-current', 'page');
      else node.removeAttribute('aria-current');
    });
    $('#breadcrumb-title').textContent = historyView ? 'Todas as entregas' : 'Visão geral';
    $('#page-title').innerHTML = historyView ? 'O histórico da sua operação<span>.</span>' : 'Entregas sob controle<span>.</span>';
    $('#page-description').textContent = historyView ? 'Consulte entregas de qualquer data, em um só lugar.' : 'Da separação à porta do cliente, acompanhe cada etapa.';
    $('#date').value = historyView ? '' : today;
    $('#search').value = '';
    chooseStatus('');
    const currentView = new URLSearchParams(location.search).get('view') === 'historico' ? 'historico' : 'operacao';
    if (updateUrl && currentView !== view) window.history.pushState({view}, '', `/?view=${view}`);
    load();
  }
  document.querySelectorAll('[data-view]').forEach((link) => link.addEventListener('click', (event) => {
    event.preventDefault();
    selectView(link.dataset.view);
  }));
  window.addEventListener('popstate', () => selectView(new URLSearchParams(location.search).get('view') === 'historico' ? 'historico' : 'operacao', false));
  document.addEventListener('keydown', (event) => {
    if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !document.querySelector('dialog[open]') && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName)) {
      event.preventDefault();
      $('#search').focus();
    }
  });
  window.addEventListener('offline', () => connection(false));
  window.addEventListener('online', load);
  window.addEventListener('focus', checkDay);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) checkDay(); });
  setInterval(() => { if (!document.hidden) checkDay(); }, 30000);
  connection(navigator.onLine);
  selectView(new URLSearchParams(location.search).get('view') === 'historico' ? 'historico' : 'operacao', false);
})();
