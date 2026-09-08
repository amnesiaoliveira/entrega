(() => {
  const layout = document.querySelector('.app-layout');
  const toggle = document.querySelector('#sidebar-toggle');
  if (!layout || !toggle) return;
  const key = 'baranda.sidebar.collapsed';
  const compact = window.matchMedia('(max-width: 900px)');
  let preference = null;
  try {
    const saved = localStorage.getItem(key);
    if (saved === 'true' || saved === 'false') preference = saved === 'true';
  } catch { /* O menu funciona mesmo com armazenamento bloqueado. */ }

  function render() {
    const collapsed = preference ?? compact.matches;
    layout.dataset.sidebarCollapsed = String(collapsed);
    toggle.setAttribute('aria-expanded', String(!collapsed));
    const label = collapsed ? 'Expandir menu lateral' : 'Recolher menu lateral';
    toggle.setAttribute('aria-label', label);
    toggle.title = label;
  }
  toggle.addEventListener('click', () => {
    preference = layout.dataset.sidebarCollapsed !== 'true';
    try { localStorage.setItem(key, String(preference)); } catch { /* Preferência só nesta página. */ }
    render();
  });
  compact.addEventListener('change', render);
  render();
  toggle.hidden = false;
})();
