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
      attributeFilter: ['aria-hidden']
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

  // 4. 탭 전환 (mobile touch 포함)
  function switchBookingTab(btn, tabId) {
    document.querySelectorAll('.booking-tab-btn').forEach(b => b.classList.remove('active', 'active-green'));
    document.querySelectorAll('.booking-tab-pane').forEach(p => p.classList.remove('active', 'active-green'));
    const isRebook = tabId === 'quick-rebook';
    btn.classList.add(isRebook ? 'active-green' : 'active');
    const pane = document.getElementById('tab-' + tabId);
    if (pane) pane.classList.add(isRebook ? 'active-green' : 'active');
  }

  document.querySelectorAll('.booking-tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      switchBookingTab(btn, btn.dataset.tab);
    });
  });

  // rebook_error 있으면 자동으로 Book Again 탭 열기
  const bookingTabs = document.getElementById('booking-tabs');
  if (bookingTabs && bookingTabs.dataset.rebookError === 'true') {
    var rebookBtn = document.querySelector('[data-tab="quick-rebook"]');
    if (rebookBtn) switchBookingTab(rebookBtn, 'quick-rebook');
  }

});
