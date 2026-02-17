document.addEventListener('DOMContentLoaded', function() {
    const startPointInput = document.getElementById('start-point');
    const endPointInput = document.getElementById('end-point');
  
    const suburbs = {{ suburbs|safe }};
  
    startPointInput.addEventListener('input', function() {
      filterResults(this.value, 'start-point-results');
    });
  
    endPointInput.addEventListener('input', function() {
      filterResults(this.value, 'end-point-results');
    });
  
    function filterResults(query, resultElementId) {
      const resultsElement = document.getElementById(resultElementId);
      resultsElement.innerHTML = '';
      if (query.length < 2) {
        return;
      }
  
      const filteredSuburbs = suburbs.filter(suburb => suburb.toLowerCase().includes(query.toLowerCase()));
      filteredSuburbs.forEach(suburb => {
        const item = document.createElement('a');
        item.classList.add('list-group-item', 'list-group-item-action');
        item.textContent = suburb;
        item.href = '#';
        item.addEventListener('click', function(e) {
          e.preventDefault();
          document.getElementById(resultElementId.replace('-results', '')).value = suburb;
          resultsElement.innerHTML = '';
        });
        resultsElement.appendChild(item);
      });
    }
  });