// DOMContentLoaded 제거 - defer로 로드되므로 DOM은 이미 준비됨
(function() {
    var form = document.getElementById("booking-form");
    var submitButton = document.getElementById("submitButton");

    if (!form) {
        console.error("booking-form not found");
        return;
    }

    form.addEventListener("submit", function(event) {
        event.preventDefault(); 
        event.stopPropagation();

        // 1. 날짜 유효성 최종 확인
        const flightDateInput = document.getElementById("flight-date");
        if (flightDateInput && flightDateInput.classList.contains("is-invalid")) {
            alert("Please select a valid date.");
            return;
        }

        // 2. reCAPTCHA 확인
        if (typeof grecaptcha !== "undefined") {
            const recaptchaResponse = grecaptcha.getResponse();
            if (!recaptchaResponse) {
                alert("Please complete the reCAPTCHA verification.");
                return;
            }
        }

        // 3. 버튼 잠금
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = "Submitting... <span class='spinner-border spinner-border-sm ms-2'></span>";
        }
        if (typeof startTitleSpinner === "function") startTitleSpinner();

        var formData = new FormData(form);

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = '/inquiry_done';
            } else {
                alert(data.error || "Something went wrong.");
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = "Submit Booking";
                }
                if (typeof stopTitleSpinner === "function") stopTitleSpinner();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert("Network error. Please try again.");
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = "Submit Booking";
            }
            if (typeof stopTitleSpinner === "function") stopTitleSpinner();
        });
    });

    console.log("Form handler attached successfully");
})();