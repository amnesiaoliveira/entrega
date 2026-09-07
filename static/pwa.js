if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      const indicator = document.querySelector('#connection');
      if (indicator) indicator.title = 'Modo offline indisponível neste navegador.';
    });
  });
}
let installPrompt;
window.addEventListener('beforeinstallprompt', (event) => {
  event.preventDefault();
  installPrompt = event;
});
document.querySelector('#install')?.addEventListener('click', async () => {
  if (installPrompt) {
    await installPrompt.prompt();
    await installPrompt.userChoice;
    installPrompt = null;
  } else {
    document.querySelector('#install-dialog').showModal();
  }
});
document.querySelectorAll('[data-close]').forEach((button) => {
  button.addEventListener('click', () => button.closest('dialog').close());
});
document.querySelector('#logout-form')?.addEventListener('submit', () => {
  try {
    localStorage.removeItem('baranda.offline');
    localStorage.removeItem('baranda.user');
    Object.keys(localStorage).filter((key) => key.startsWith('baranda.draft.'))
      .forEach((key) => localStorage.removeItem(key));
  } catch { /* Logout must continue when storage is unavailable. */ }
});
if (location.pathname === '/entrar/') {
  try {
    localStorage.removeItem('baranda.offline');
    localStorage.removeItem('baranda.user');
  } catch { /* Storage may be disabled. */ }
}
