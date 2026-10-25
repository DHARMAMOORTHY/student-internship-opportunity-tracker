document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('[data-dismiss]').forEach(btn => btn.addEventListener('click', () => btn.closest('.flash')?.remove()));
  document.querySelectorAll('form[data-confirm]').forEach(form => form.addEventListener('submit', e => {
    if (!window.confirm(form.dataset.confirm || 'Are you sure?')) e.preventDefault();
  }));
  const toggle = document.querySelector('[data-menu-toggle]');
  const sidebar = document.getElementById('sidebar');
  if (toggle && sidebar) toggle.addEventListener('click', () => sidebar.classList.toggle('sidebar-open'));
  document.querySelectorAll('input[type="date"]').forEach(input => {
    input.addEventListener('keydown', e => { if (e.key === 'Escape') input.blur(); });
  });
});
