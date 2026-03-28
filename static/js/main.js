document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('input:not([type="submit"]):not([type="file"]):not([type="checkbox"]):not([type="radio"]),textarea,select').forEach(el => {
    if (!el.classList.contains('form-control') && !el.classList.contains('form-select')) {
      el.classList.add(el.tagName === 'SELECT' ? 'form-select' : 'form-control');
    }
  });
  document.querySelectorAll('.alert.alert-dismissible').forEach(alert => {
    setTimeout(() => { try { bootstrap.Alert.getOrCreateInstance(alert).close(); } catch(e){} }, 5000);
  });
  const nav = document.getElementById('mainNav');
  if (nav) window.addEventListener('scroll', () => { nav.style.boxShadow = window.scrollY > 20 ? '0 2px 20px rgba(0,0,0,.25)' : 'none'; });
  const today = new Date().toISOString().split('T')[0];
  document.querySelectorAll('input[type="date"]').forEach(i => { if (!['date_of_birth','follow_up_date'].includes(i.name)) i.setAttribute('min', today); });
});
