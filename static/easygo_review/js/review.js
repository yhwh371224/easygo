function search_post() {
  var searchValue = document.getElementById('search-input').value;
  if (searchValue.trim() === '') {
    alert('Please enter a valid search term.');
  } else {
    location.href = '/easygo_review/search/' + encodeURIComponent(searchValue) + '/';
  }
}

function wait_for_enterkey() {
  if (window.event.keyCode === 13) {
    search_post();
  }
}

document.addEventListener('DOMContentLoaded', function () {
  var newPostBtn = document.getElementById('new-post-btn');
  if (newPostBtn) {
    newPostBtn.addEventListener('click', function () {
      location.href = '/easygo_review/create/';
    });
  }

  var searchBtn = document.getElementById('search-btn');
  if (searchBtn) {
    searchBtn.addEventListener('click', search_post);
  }

  var editReviewBtn = document.getElementById('edit-review-btn');
  if (editReviewBtn) {
    editReviewBtn.addEventListener('click', function () {
      location.href = editReviewBtn.dataset.url;
    });
  }

  document.querySelectorAll('.comment-edit-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      location.href = btn.dataset.url;
    });
  });

  document.querySelectorAll('.comment-delete-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      location.href = btn.dataset.url;
    });
  });
});
