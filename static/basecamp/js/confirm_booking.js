function toggleAdminFields() {
  var hiddenField = document.getElementById('index');
  var adminFields = document.getElementById('admin-fields');
  var indexInput = document.querySelector('input[name="index_visible"]');

  if (adminFields.classList.contains('d-none')) {
    adminFields.classList.remove('d-none');
    indexInput.value = hiddenField.value;
  } else {
    hiddenField.value = indexInput.value;
    adminFields.classList.add('d-none');
  }
}

document.addEventListener('DOMContentLoaded', function () {
  var adminBtn = document.getElementById('admin-access-btn');
  if (adminBtn) {
    adminBtn.addEventListener('click', toggleAdminFields);
  }
});
