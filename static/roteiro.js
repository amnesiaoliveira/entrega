const stops = document.querySelector('#route-stops');
function updateOrder() {
  const rows = [...stops.children];
  rows.forEach((row, index) => {
    row.querySelector('.stop-number').textContent = index + 1;
    row.querySelector('[data-move="-1"]').disabled = index === 0;
    row.querySelector('[data-move="1"]').disabled = index === rows.length - 1;
  });
}
stops?.addEventListener('click', (event) => {
  const button = event.target.closest('[data-move]');
  if (!button) return;
  const row = button.closest('.stop');
  if (button.dataset.move === '-1' && row.previousElementSibling) {
    stops.insertBefore(row, row.previousElementSibling);
  } else if (button.dataset.move === '1' && row.nextElementSibling) {
    stops.insertBefore(row.nextElementSibling, row);
  }
  updateOrder();
});
if (stops) updateOrder();
document.querySelector('#print-route')?.addEventListener('click', () => window.print());
