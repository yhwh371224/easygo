document.addEventListener('DOMContentLoaded', function () {

  // 1. 품질 인증서 클릭 이벤트
  var qualityAward = document.getElementById('quality-award');
  if (qualityAward) {
    qualityAward.addEventListener('click', function () {
      location.href = 'https://easygo.s3.ap-southeast-2.amazonaws.com/panel_members.webp';
    });
  }

  // 2. Slider A11y fix
  function fixSliderA11y() {
    document.querySelectorAll('[aria-hidden="true"] a, [aria-hidden="true"] button').forEach(el => {
      el.setAttribute('tabindex', '-1');
    });
    document.querySelectorAll('.tns-item:not([aria-hidden="true"]) a, .tns-item:not([aria-hidden="true"]) button').forEach(el => {
      el.removeAttribute('tabindex');
    });
  }

  setTimeout(fixSliderA11y, 500);
  setTimeout(fixSliderA11y, 1000); 
  setTimeout(fixSliderA11y, 2000);  

  const sliderContainer = document.querySelector('.tns-carousel-wrapper');
  if (sliderContainer) {
    const observer = new MutationObserver(fixSliderA11y);
    observer.observe(sliderContainer, {
      attributes: true,
      subtree: true,
      attributeFilter: ['aria-hidden']  // aria-hidden 변경만 감지
    });
  }
  // 3. 날짜 필드 유효성 검사
  const bookingForm = document.getElementById('booking-form');
  if (bookingForm) {
    bookingForm.addEventListener('submit', function (e) {
      const pickupDate = document.querySelector('[name="pickup_date"]').value;
      if (!pickupDate) {
        e.preventDefault();
        alert('Please select a pickup date.');
      }
    });
  }
});

