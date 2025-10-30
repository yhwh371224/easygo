/**
 * Date / time picker
 * @requires https://github.com/flatpickr/flatpickr
 */


const datePicker = (() => {
  let picker = document.querySelectorAll('.date-picker');
      
  if (picker.length === 0) return;
  
  for (let i = 0; i < picker.length; i++) {

    let defaults = {
      disableMobile: true,
    }
    
    let userOptions;
    if(picker[i].dataset.datepickerOptions != undefined) userOptions = JSON.parse(picker[i].dataset.datepickerOptions);
    let linkedInput = picker[i].classList.contains('date-range') && picker[i].dataset.linkedInput ? 
                  { plugins: [new rangePlugin({ input: picker[i].dataset.linkedInput })] } : {};
    let options = {...defaults, ...linkedInput, ...userOptions};

    // altInput 제거
    if (options.altInput) delete options.altInput;

    flatpickr(picker[i], options);
  }
})();

export default datePicker;
