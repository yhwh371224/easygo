function toggleExtraLuggage() {
  var extraFields = document.getElementById('extraLuggageFields');
  var checkbox = document.getElementById('extraLuggageCheck');
  extraFields.style.display = checkbox.checked ? 'block' : 'none';
}

document.addEventListener('DOMContentLoaded', function () {
  var checkbox = document.getElementById('extraLuggageCheck');
  if (checkbox) {
    checkbox.addEventListener('click', toggleExtraLuggage);
  }
});
