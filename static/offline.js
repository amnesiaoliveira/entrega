const labels = {pendente: 'Pendente', em_rota: 'Em rota', entregue: 'Entregue', cancelada: 'Cancelada'};
let snapshot;
try {
  snapshot = JSON.parse(localStorage.getItem('baranda.offline'));
  if (snapshot?.user !== localStorage.getItem('baranda.user')) snapshot = null;
} catch { snapshot = null; }
const saved = document.querySelector('#saved-at');
saved.textContent = snapshot ? `Última consulta: ${new Date(snapshot.at).toLocaleString('pt-BR')}. Apenas as entregas dessa consulta estão disponíveis.` : 'Nenhuma consulta salva neste dispositivo.';
function renderOffline() {
  const list = document.querySelector('#offline-list');
  list.replaceChildren();
  const query = document.querySelector('#offline-search').value.toLocaleLowerCase('pt-BR');
  const items = (snapshot?.items || []).filter((item) => [item.nome, item.endereco, item.cupom, item.sequencia, item.responsavel].join(' ').toLocaleLowerCase('pt-BR').includes(query));
  for (const item of items) {
    const card = document.createElement('article');
    card.className = 'offline-card';
    const title = document.createElement('h3');
    title.textContent = `#${item.sequencia} · ${item.nome}`;
    const badge = document.createElement('span');
    badge.className = `badge ${Object.hasOwn(labels, item.status) ? item.status : ''}`;
    badge.textContent = labels[item.status] || item.status;
    const info = document.createElement('p');
    info.textContent = `${item.endereco}\nTelefone: ${item.telefone}\nCupom: ${item.cupom} · ${item.volumes} volume(s)\nData: ${item.data.split('-').reverse().join('/')} ${item.horario}\nEntregador: ${item.responsavel || 'Não definido'}\n${item.observacoes || ''}`;
    card.append(title, badge, info);
    list.append(card);
  }
  if (!items.length) list.textContent = 'Nenhuma entrega disponível para esta busca.';
}
document.querySelector('#offline-search').addEventListener('input', renderOffline);
document.querySelector('#clear-offline').addEventListener('click', () => {
  try {
    localStorage.removeItem('baranda.offline');
    localStorage.removeItem('baranda.user');
  } catch { /* The in-memory snapshot is cleared even if storage is unavailable. */ }
  snapshot = null;
  saved.textContent = 'Cópia offline apagada.';
  renderOffline();
});
renderOffline();
