// const datePicker = (() => {
//   let picker = document.querySelectorAll('.date-picker');
//   if (picker.length === 0) return;

//   for (let i = 0; i < picker.length; i++) {
//     let defaults = {
//       disableMobile: true,
//       allowInput: true,  
//       altInput: false    
//     };

//     let userOptions = picker[i].dataset.datepickerOptions 
//                         ? JSON.parse(picker[i].dataset.datepickerOptions) 
//                         : { dateFormat: "Y-m-d" }; 

//     let linkedInput = picker[i].classList.contains('date-range') && picker[i].dataset.linkedInput
//       ? { plugins: [new rangePlugin({ input: picker[i].dataset.linkedInput })] } 
//       : {};
    
//     let options = { ...defaults, ...linkedInput, ...userOptions };

//     flatpickr(picker[i], options);
//   }
// })();

// export default datePicker;

/**
 * Basic Date Validation (for native <input type="date">)
 * Validates that pickup_date is not in the past.
 */

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

