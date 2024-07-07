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
                    window.location.href = '/inquiry_done'; // Redirect to the desired URL
                } else {
                    var errorMessageDiv = document.getElementById("errorMessage");
                    if (errorMessageDiv) { // Check if the errorMessage element exists
                        errorMessageDiv.textContent = data.error;
                        errorMessageDiv.style.display = 'block';
                    } else {
                        console.error('Error message div not found on the page.');
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                var errorMessageDiv = document.getElementById("errorMessage");
                if (errorMessageDiv) { // Check if the errorMessage element exists
                    window.location.href = '/date_error';
                    // errorMessageDiv.textContent = 'There was a problem processing your request.';
                    // errorMessageDiv.style.display = 'block';
                } else {
                    console.error('Error message div not found on the page.');
                }
            });
        });
    } else {
        // If the form element with ID 'booking-form' was not found, log an error
        console.error('Form element not found!');
    }
});

