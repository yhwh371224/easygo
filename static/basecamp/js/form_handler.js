document.addEventListener("DOMContentLoaded", function() {
    var form = document.getElementById("booking-form");
    var submitButton = document.getElementById("submitButton");

    if (form) {
        form.addEventListener("submit", function(event) {
            event.preventDefault(); 
            event.stopPropagation();

            // 1. 날짜 유효성 최종 확인 (is-invalid 클래스가 있으면 중단)
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
                    // 4. 실패 시 버튼 다시 살리기
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
                window.location.href = '/date_error';
            });
        });
    }
});