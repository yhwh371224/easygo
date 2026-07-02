document.addEventListener('DOMContentLoaded', function () {
    const regionName = document.body.dataset.regionName || 'Sydney';

    function isDropOff(dir) {
        return !!dir && dir.startsWith('Drop off to');
    }

    // Departure flights (Drop off to ...) need no hint — the traveler already
    // knows their own flight's departure time. Only arrival flights (Pickup
    // from ...) get a hint, since customers often confuse it with departure time.
    function applyHint(el, dir) {
        if (!el) return;
        if (isDropOff(dir)) {
            el.style.display = 'none';
        } else {
            el.textContent = '⚠ ' + regionName + ' arrival time';
            el.style.display = 'block';
        }
    }

    // Outbound flight_time hint.
    const directionSelect = document.getElementById('direction');
    const flightHint = document.getElementById('id_flight_time_hint');
    if (directionSelect && flightHint) {
        const update = function () { applyHint(flightHint, directionSelect.value); };
        directionSelect.addEventListener('change', update);
        update();
    }

    // Return flight_time hint — prefer a dedicated return_direction control if the
    // page has one; otherwise the return leg is the inverse of the outbound direction.
    const returnFlightHint = document.getElementById('id_return_flight_time_hint');
    if (returnFlightHint) {
        const returnDirectionSelect = document.getElementById('return_direction');
        if (returnDirectionSelect) {
            const update = function () { applyHint(returnFlightHint, returnDirectionSelect.value); };
            returnDirectionSelect.addEventListener('change', update);
            update();
        } else if (directionSelect) {
            const update = function () {
                const returnLegDirection = isDropOff(directionSelect.value) ? 'Pickup from' : 'Drop off to';
                applyHint(returnFlightHint, returnLegDirection);
            };
            directionSelect.addEventListener('change', update);
            update();
        }
    }
});
