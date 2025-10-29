/**
 * Date / time picker
 * @requires https://github.com/flatpickr/flatpickr
 */


// const datePicker = (() => {
//   let picker = document.querySelectorAll('input.date-picker'); // <-- only inputs      
//   if (picker.length === 0) return;
  
//   for (let i = 0; i < picker.length; i++) {

//     let defaults = {
//       disableMobile: 'true'
//     }
    
//     let userOptions;
//     if(picker[i].dataset.datepickerOptions != undefined) userOptions = JSON.parse(picker[i].dataset.datepickerOptions);
//     let linkedInput = picker[i].classList.contains('date-range') ? {"plugins": [new rangePlugin({ input: picker[i].dataset.linkedInput })]} : '{}';
//     let options = {...defaults, ...linkedInput, ...userOptions}

//     flatpickr(picker[i], options);
//   }
// })();

const datePicker = (() => {
  let picker = document.querySelectorAll('input.date-picker');      
  if (picker.length === 0) return;
  
  picker.forEach(p => {
    let defaults = { disableMobile: true };
    let userOptions = p.dataset.datepickerOptions ? JSON.parse(p.dataset.datepickerOptions) : {};
    flatpickr(p, {...defaults, ...userOptions});
  });
})();


