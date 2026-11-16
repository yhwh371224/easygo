// Show the "Child age(s)" field only while at least one baby/booster seat is selected.
// The +/- stepper buttons change the value without firing input events, so we
// re-check on any click/input/change in the document.
(function () {
    'use strict';

    function count(id) {
        var el = document.getElementById(id);
        var n = el ? parseInt(el.value, 10) : 0;
        return isNaN(n) ? 0 : n;
    }

    function update() {
        var field = document.getElementById('child-ages-field');
        if (!field) return;
        field.hidden = count('baggage_baby') + count('baggage_booster') <= 0;
    }

    ['click', 'input', 'change'].forEach(function (type) {
        document.addEventListener(type, update);
    });
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', update);
    } else {
        update();
    }
})();
