document.addEventListener('DOMContentLoaded', function () {
  // 1. 품질 인증서 클릭 이벤트 (기존 코드)
  var qualityAward = document.getElementById('quality-award');
  if (qualityAward) {
    qualityAward.addEventListener('click', function () {
      location.href = 'https://easygo.s3.ap-southeast-2.amazonaws.com/panel_members.webp';
    });
  }

  // 2. CSP 대응: CSS 비동기 로드 (onload="this.media='all'" 대체)
  const lazyCss = document.querySelectorAll('.lazy-load-css');
  lazyCss.forEach(link => {
    link.media = 'all';
  });
});
