console.log("=== form_handler.js loaded ===");

(function() {
    console.log("=== form_handler.js executing ===");
    
    var form = document.getElementById("booking-form");
    var submitButton = document.getElementById("submitButton");

    console.log("Form:", form);
    console.log("Submit button:", submitButton);

    if (!form) {
        console.error("❌ booking-form NOT FOUND!");
        return;
    }

    console.log("✅ Form found, attaching submit handler...");

    form.addEventListener("submit", function(event) {
        console.log("🔥 SUBMIT EVENT FIRED!");
        
        event.preventDefault(); 
        event.stopPropagation();

        // 1. 날짜 유효성 최종 확인
        const flightDateInput = document.getElementById("flight-date");
        if (flightDateInput && flightDateInput.classList.contains("is-invalid")) {
            console.log("❌ Invalid date");
            alert("Please select a valid date.");
            return;
        }
        console.log("✅ Date validation passed");

        // 2. reCAPTCHA 확인
        if (typeof grecaptcha !== "undefined") {
            const recaptchaResponse = grecaptcha.getResponse();
            console.log("reCAPTCHA response:", recaptchaResponse);
            if (!recaptchaResponse) {
                console.log("❌ reCAPTCHA not completed");
                alert("Please complete the reCAPTCHA verification.");
                return;
            }
        }
        console.log("✅ reCAPTCHA passed");

        // 3. 버튼 잠금
        if (submitButton) {
            submitButton.disabled = true;
            submitButton.innerHTML = "Submitting... <span class='spinner-border spinner-border-sm ms-2'></span>";
        }
        if (typeof startTitleSpinner === "function") startTitleSpinner();

        console.log("📤 Sending fetch request to:", form.action);

        var formData = new FormData(form);

        fetch(form.action, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        })
        .then(response => {
            console.log("📥 Response received:", response);
            return response.json();
        })
        .then(data => {
            console.log("📊 Response data:", data);
            if (data.success) {
                console.log("✅ Success! Redirecting...");
                window.location.href = '/inquiry_done';
            } else {
                console.log("❌ Server returned error:", data.error);
                alert(data.error || "Something went wrong.");
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = "Submit Booking";
                }
                if (typeof stopTitleSpinner === "function") stopTitleSpinner();
            }
        })
        .catch(error => {
            console.error('❌ Fetch error:', error);
            alert("Network error. Please try again.");
            if (submitButton) {
                submitButton.disabled = false;
                submitButton.innerHTML = "Submit Booking";
            }
            if (typeof stopTitleSpinner === "function") stopTitleSpinner();
        });
    });

    console.log("✅ Submit handler attached successfully");
})();