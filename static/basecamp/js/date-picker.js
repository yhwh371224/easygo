/**
 * Date / time picker
 * @requires https://github.com/flatpickr/flatpickr
 */


const datePicker = (() => {
  const pickers = document.querySelectorAll('input.date-picker');
  if (pickers.length === 0) return;

  pickers.forEach(p => {
    const defaults = {
      disableMobile: true  // boolean
    };
    
    const userOptions = p.dataset.datepickerOptions ? JSON.parse(p.dataset.datepickerOptions) : {};
    
    let linkedOptions = {};
    if (p.classList.contains('date-range') && p.dataset.linkedInput) {
      linkedOptions.plugins = [new rangePlugin({ input: p.dataset.linkedInput })];
    }

    const options = {...defaults, ...linkedOptions, ...userOptions};

    // 반드시 altInput 제거!
    if (options.altInput) delete options.altInput;

    flatpickr(p, options);
  });
})();


// const datePicker = (() => {
//   let picker = document.querySelectorAll('input.date-picker');      
//   if (picker.length === 0) return;
  
//   picker.forEach(p => {
//     let defaults = { disableMobile: true };
//     let userOptions = p.dataset.datepickerOptions ? JSON.parse(p.dataset.datepickerOptions) : {};
//     flatpickr(p, {...defaults, ...userOptions});
//   });
// })();


// document.addEventListener('DOMContentLoaded', function () {
//   const pickers = document.querySelectorAll('input.date-picker');
//   if (pickers.length === 0) return;

//   pickers.forEach(p => {
//     flatpickr(p, {
//       dateFormat: "Y-m-d",   // Django가 요구하는 형식
//       allowInput: true,       // 직접 입력 가능
//     });
//   });
// });