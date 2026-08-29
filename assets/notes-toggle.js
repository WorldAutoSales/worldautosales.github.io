document.querySelectorAll('.notes-card').forEach(card => {
  const toggle = card.querySelector('.notes-toggle');
  if(!toggle) return;
  toggle.addEventListener('click', () => {
    const collapsed = card.classList.toggle('is-collapsed');
    toggle.setAttribute('aria-expanded', String(!collapsed));
  });
});
