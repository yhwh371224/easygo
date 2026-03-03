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

  // 3. Testimonials 슬라이더 초기화 (.tiny-slider-inner)
  // theme.min.js는 .tns-carousel-wrapper만 처리하므로 여기서 별도 초기화
  document.querySelectorAll('.tiny-slider-inner').forEach(function (el) {
    if (typeof tns === 'undefined') return;
    var autoplayTimeout = parseInt(el.dataset.autoplay, 10) || 0;
    tns({
      container: el,
      items: parseInt(el.dataset.items, 10) || 1,
      autoplay: autoplayTimeout > 0,
      autoplayTimeout: autoplayTimeout,
      autoplayHoverPause: true,
      autoplayButtonOutput: false,
      controls: el.dataset.arrow !== 'false',
      nav: el.dataset.dots !== 'false',
      edgePadding: parseInt(el.dataset.edge, 10) || 0,
      mouseDrag: true,
      speed: 600,
    });
  });
});

