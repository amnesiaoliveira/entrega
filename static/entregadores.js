(() => {
  const $ = (selector) => document.querySelector(selector);
  const escape = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[char]));
  let items = [], editing = null, busy = false, toastTimer;
  async function api(url, options = {}) {
    const token = document.cookie.split('; ').find((entry) => entry.startsWith('csrftoken='))?.slice(10);
    const response = await fetch(url, {...options, signal: AbortSignal.timeout(15000), headers: {'Content-Type': 'application/json', 'X-CSRFToken': token || ''}});
    if (response.status === 401) { location.href = '/entrar/'; throw new Error('Entre novamente.'); }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.erro || (data.erros && Object.values(data.erros).flat().join('\n')) || 'Não foi possível concluir a operação.');
    return data;
  }
  function toast(message) {
    clearTimeout(toastTimer); $('#courier-toast').textContent = message; $('#courier-toast').hidden = false;
    toastTimer = setTimeout(() => { $('#courier-toast').hidden = true; }, 4000);
  }
  function render() {
    const query = $('#courier-search').value.toLocaleLowerCase('pt-BR');
    const status = $('#courier-filter').value;
    const filtered = items.filter((item) => `${item.nome} ${item.telefone}`.toLocaleLowerCase('pt-BR').includes(query) && (!status || item.ativo === (status === 'active')));
    $('#courier-list').innerHTML = filtered.map((item) => `<tr><td><strong>${escape(item.nome)}</strong></td><td>${escape(item.telefone || 'Não informado')}</td><td><span class="badge ${item.ativo ? 'entregue' : 'cancelada'}">${item.ativo ? 'Ativo' : 'Inativo'}</span></td><td><div class="table-actions"><button class="button secondary" data-edit="${item.id}">Editar</button><button class="button secondary" data-toggle="${item.id}">${item.ativo ? 'Inativar' : 'Reativar'}</button></div></td></tr>`).join('');
    $('#courier-empty').hidden = filtered.length > 0;
    $('#courier-empty').textContent = 'Nenhum entregador encontrado. Use “Novo entregador” para cadastrar.';
    $('#courier-count').textContent = `${filtered.length} entregador(es) · ${items.filter((item) => item.ativo).length} ativo(s)`;
  }
  async function load() {
    try { items = (await api('/api/entregadores/')).entregadores; $('#courier-error').hidden = true; render(); }
    catch (error) { $('#courier-error').textContent = `${error.message} Verifique a conexão e atualize a tabela.`; $('#courier-error').hidden = false; $('#courier-empty').hidden = true; }
  }
  function open(item = null) {
    editing = item; $('#courier-form').reset(); $('#courier-form-error').hidden = true;
    $('#courier-title').textContent = item ? 'Editar entregador' : 'Novo entregador';
    for (const [key, value] of Object.entries(item || {ativo: true})) {
      if ($('#courier-form').elements.namedItem(key)) $('#courier-form').elements.namedItem(key).value = String(value);
    }
    $('#courier-dialog').showModal();
  }
  $('#new-courier').addEventListener('click', () => open());
  $('#courier-list').addEventListener('click', async (event) => {
    const button = event.target.closest('[data-edit], [data-toggle]');
    if (!button || busy) return;
    const item = items.find((entry) => entry.id === Number(button.dataset.edit || button.dataset.toggle));
    if (button.dataset.edit) { open(item); return; }
    busy = true; button.disabled = true;
    try { await api(`/api/entregadores/${item.id}/`, {method: 'PATCH', body: JSON.stringify({...item, ativo: !item.ativo})}); toast(item.ativo ? 'Entregador inativado.' : 'Entregador reativado.'); await load(); }
    catch (error) { $('#courier-error').textContent = error.message; $('#courier-error').hidden = false; }
    finally { busy = false; button.disabled = false; }
  });
  $('#courier-form').addEventListener('submit', async (event) => {
    event.preventDefault(); if (busy) return;
    const data = Object.fromEntries(new FormData(event.target)); data.ativo = data.ativo === 'true';
    if (editing) data.versao = editing.versao;
    busy = true; for (const element of event.target.elements) element.disabled = true;
    try {
      await api(editing ? `/api/entregadores/${editing.id}/` : '/api/entregadores/', {method: editing ? 'PATCH' : 'POST', body: JSON.stringify(data)});
      $('#courier-dialog').close(); toast('Entregador salvo.'); await load();
    } catch (error) { $('#courier-form-error').textContent = error.message; $('#courier-form-error').hidden = false; }
    finally { busy = false; for (const element of event.target.elements) element.disabled = false; }
  });
  $('#courier-dialog').addEventListener('cancel', (event) => { if (busy) event.preventDefault(); });
  $('#courier-search').addEventListener('input', render);
  $('#courier-filter').addEventListener('change', render);
  $('#courier-refresh').addEventListener('click', load);
  const phone = $('#courier-form').elements.namedItem('telefone');
  phone.addEventListener('input', () => {
    const position = phone.selectionStart ?? phone.value.length;
    const before = phone.value.slice(0, position).replace(/\D/g, '').length;
    const digits = phone.value.replace(/\D/g, '');
    if (phone.value.trim().startsWith('+') || digits.length > 11) return;
    const rest = digits.slice(2), split = digits.length === 11 ? 5 : 4;
    phone.value = !digits ? '' : digits.length <= 2 ? `(${digits}` : `(${digits.slice(0, 2)}) ${rest.slice(0, split)}${rest.length > split ? '-' + rest.slice(split) : ''}`;
    let cursor = 0, count = 0;
    while (cursor < phone.value.length && count < before) { if (/\d/.test(phone.value[cursor])) count++; cursor++; }
    phone.setSelectionRange(cursor, cursor);
  });
  load();
})();
