// Hamburger menu: buka/tutup navbar di layar kecil (< 900px)
document.addEventListener('click', function (event) {
  var button = event.target.closest('.nav-toggle');
  if (!button) return;
  var shell = button.closest('.nav-shell');
  var isOpen = shell.classList.toggle('is-open');
  button.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
  button.setAttribute('aria-label', isOpen ? 'Tutup menu' : 'Buka menu');
});