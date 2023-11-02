document.getElementById("booking-form").addEventListener("submit", function(event) {
    event.preventDefault();  // Prevent the default form submission

    var form = this;
    var formData = new FormData(form);

    fetch(form.action, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest', // Indicate AJAX request
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Handle successful submission (e.g., redirect or update UI)
        } else {
            // Display error message
            var errorMessageDiv = document.getElementById("errorMessage");
            errorMessageDiv.textContent = data.error;
            errorMessageDiv.style.display = 'block';
        }
    })
    .catch(error => console.error('Error:', error));
});