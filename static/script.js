// Auto-dismiss alerts
document.querySelectorAll('.alert').forEach(el => {
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity 0.4s'; }, 4000);
});

// Mark active nav item
const path = window.location.pathname;
document.querySelectorAll('.nav-item').forEach(a => {
  if (a.getAttribute('href') === path) a.classList.add('active');
});

// Confirm dangerous actions
document.querySelectorAll('[data-confirm]').forEach(el => {
  el.addEventListener('click', e => {
    if (!confirm(el.dataset.confirm)) e.preventDefault();
  });
});

// Number input: block negative
document.querySelectorAll('input[type=number]').forEach(el => {
  el.addEventListener('input', () => {
    if (parseFloat(el.value) < 0) el.value = '';
  });
});
