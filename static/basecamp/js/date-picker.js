document.addEventListener('DOMContentLoaded', () => {
  const form = document.querySelector('form'); // or use specific ID if you have one, e.g. #booking-form
  const dateInput = document.querySelector('input[name="pickup_date"]');
  const errorMsg = document.getElementById('date-error');

  if (!form || !dateInput) return;

  form.addEventListener('submit', (e) => {
    const today = new Date().toISOString().split('T')[0];
    const selected = dateInput.value;

    if (!selected || selected <= today) {
      e.preventDefault();
      errorMsg.style.display = 'block';
      dateInput.classList.add('is-invalid');
    } else {
      errorMsg.style.display = 'none';
      dateInput.classList.remove('is-invalid');
    }
  });
});