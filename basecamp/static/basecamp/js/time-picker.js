import flatpickr from "https://cdn.jsdelivr.net/npm/flatpickr";


document.addEventListener('DOMContentLoaded', function() {
  const timePickers = document.querySelectorAll('.time-picker');

  timePickers.forEach(input => {
    flatpickr(input, {
      enableTime: true,
      noCalendar: true,
      time_24hr: false,     // 12시간제
      dateFormat: "h:i K",  // 12시간제 표시 + AM/PM
      minuteIncrement: 1,
      defaultHour: 12,
      onReady: function(selectedDates, dateStr, instance) {
        // 시간 범위 제한 (0~12)
        const hoursInput = instance.hourElement;
        hoursInput.setAttribute('min', 0);
        hoursInput.setAttribute('max', 12);
      }
    });
  });
});
