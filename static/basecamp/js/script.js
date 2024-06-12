document.addEventListener('DOMContentLoaded', function () {
    var textElement = document.getElementById('changing-text');
    var backgroundElement = document.getElementById('changing-background');
  
    function toggleTextColor() {
      textElement.classList.toggle('text-light');
      textElement.classList.toggle('text-danger');
    }
  
    function toggleBackgroundImage() {
      var currentBackgroundImage = backgroundElement.style.backgroundImage;
      if (currentBackgroundImage.includes('sydney-airport.webp')) {
        backgroundElement.style.backgroundImage = 'url("/static/basecamp/photos/easygo-home-page3.webp")';
      } else {
        backgroundElement.style.backgroundImage = 'url("/static/basecamp/images/sydney-airport.webp")';
      }
    }
  
    // Change text color and background image every 5 seconds
    setInterval(function () {
      toggleTextColor();
      toggleBackgroundImage();
    }, 5000);
  });
  