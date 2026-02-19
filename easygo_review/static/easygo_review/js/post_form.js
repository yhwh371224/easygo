function setRating(rating) {
  var stars = document.querySelectorAll('.star-rating .star');
  stars.forEach(function (star, index) {
    star.style.color = index < rating ? 'gold' : '#ccc';
  });
  document.getElementById('rating').value = rating;
}

document.addEventListener('DOMContentLoaded', function () {
  document.querySelectorAll('.star-rating .star').forEach(function (star, index) {
    star.addEventListener('click', function () {
      setRating(index + 1);
    });
  });
});
