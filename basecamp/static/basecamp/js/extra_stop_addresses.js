(function () {
    'use strict';

    function renderAddresses(select, container) {
        var count = parseInt(select.value, 10) || 0;

        // Preserve values already typed
        var saved = [];
        container.querySelectorAll('input[type="text"]').forEach(function (inp) {
            saved.push(inp.value);
        });

        container.innerHTML = '';

        for (var i = 1; i <= count; i++) {
            var wrapper = document.createElement('div');
            wrapper.className = 'mb-3';

            var label = document.createElement('label');
            label.className = 'form-label';
            label.setAttribute('for', 'extra_stop_address_' + i);
            label.textContent = 'Stop ' + i + ' Address';

            var input = document.createElement('input');
            input.type = 'text';
            input.className = 'form-control';
            input.name = 'extra_stop_address_' + i;
            input.id = 'extra_stop_address_' + i;
            input.placeholder = 'Full address';
            if (saved[i - 1]) input.value = saved[i - 1];

            wrapper.appendChild(label);
            wrapper.appendChild(input);
            container.appendChild(wrapper);
        }
    }

    document.addEventListener('DOMContentLoaded', function () {
        var select = document.getElementById('extra_stop');
        var container = document.getElementById('extra-stop-addresses');
        if (!select || !container) return;

        select.addEventListener('change', function () {
            renderAddresses(select, container);
        });
    });
})();
