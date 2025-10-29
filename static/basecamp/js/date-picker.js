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
      allowInput: true,  // 브라우저 기본 입력 허용
      altInput: false    // altInput 제거
    };

    // userOptions에서 dateFormat 포함
    let userOptions = picker[i].dataset.datepickerOptions 
                        ? JSON.parse(picker[i].dataset.datepickerOptions) 
                        : { dateFormat: "Y-m-d" };  // 기본 YYYY-MM-DD

    let linkedInput = picker[i].classList.contains('date-range') && picker[i].dataset.linkedInput
      ? { plugins: [new rangePlugin({ input: picker[i].dataset.linkedInput })] } 
      : {};
    
    let options = { ...defaults, ...linkedInput, ...userOptions };

    flatpickr(picker[i], options);
  }
})();

export default datePicker;