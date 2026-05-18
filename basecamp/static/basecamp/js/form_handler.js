document.addEventListener("DOMContentLoaded", function() {
    // Once the DOM is fully loaded, we try to get the form element
    var form = document.getElementById("booking-form");
    if (form) {  // Check if the form element exists
        form.addEventListener("submit", function(event) {
            event.preventDefault(); // Prevent the default form submission
            event.stopPropagation(); // Prevent the event from propagating to parent elements

            var formData = new FormData(form);

            // Fetch API to submit form data
            fetch(form.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest', // Indicate this is an AJAX request
                },
            })
            .then(response => {
                if (!response.headers.get('content-type').includes('application/json')) {
                    throw new Error('The server response is not a JSON object.');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    window.location.href = data.redirect_url || '/inquiry_done/';
                } else {
                    var submitButton = document.getElementById("submitButton");
                    if (submitButton) {
                        submitButton.disabled = false;
                        submitButton.innerHTML = "Submit";
                    }
                    var errorMessageDiv = document.getElementById("errorMessage");
                    if (errorMessageDiv) {
                        errorMessageDiv.textContent = data.error || data.message || 'An error occurred. Please try again.';
                        errorMessageDiv.style.display = 'block';
                    } else {
                        alert(data.error || data.message || 'An error occurred. Please try again.');
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                var submitButton = document.getElementById("submitButton");
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = "Submit";
                }
                var errorMessageDiv = document.getElementById("errorMessage");
                if (errorMessageDiv) {
                    errorMessageDiv.textContent = 'There was a problem processing your request.';
                    errorMessageDiv.style.display = 'block';
                } else {
                    alert('There was a problem processing your request.');
                }
            });
        });
    } else {
        // If the form element with ID 'booking-form' was not found, log an error
        console.error('Form element not found!');
    }
});
