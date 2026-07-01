document.addEventListener('DOMContentLoaded', function () {
    const directionSelect = document.getElementById('direction');
    const flightHint = document.getElementById('id_flight_time_hint');
    if (!directionSelect || !flightHint) return;

    const regionName = document.body.dataset.regionName || 'Sydney';

    function updateFlightHint() {
        const dir = directionSelect.value;
        const suffix = dir.startsWith('Drop off to') ? 'departure time' : 'arrival time';
        flightHint.textContent = '⚠ ' + regionName + ' ' + suffix;
    }

    directionSelect.addEventListener('change', updateFlightHint);
    updateFlightHint();
});