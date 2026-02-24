document.addEventListener('DOMContentLoaded', function () {
  // 1. 품질 인증서 클릭 이벤트
  var qualityAward = document.getElementById('quality-award');
  if (qualityAward) {
    qualityAward.addEventListener('click', function () {
      location.href = 'https://easygo.s3.ap-southeast-2.amazonaws.com/panel_members.webp';
    });
  }

  // 2. 폼 위치 자동 조정
  // function adjustFormPosition() {
  //   const jarallax = document.querySelector('section.jarallax');
  //   const form = document.querySelector('.booking-form-top');
  //   if (!jarallax || !form) return;

  //   if (window.innerWidth > 768) {
  //     jarallax.style.paddingBottom = '';
  //     form.style.marginBottom = '-98px';
  //   } else {
  //     const formHeight = form.offsetHeight;
  //     jarallax.style.paddingBottom = formHeight + 'px';
  //     form.style.marginBottom = '-' + (formHeight +25) + 'px';
  //   }
  // }

  // window.addEventListener('load', adjustFormPosition);
  // window.addEventListener('resize', adjustFormPosition);
  // adjustFormPosition(); // 페이지 로드시 즉시 실행
});
