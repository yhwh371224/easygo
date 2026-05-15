(function () {
    'use strict';

    var MAX = 30;

    // Remove native browser spinners (all devices) + stepper sizing (desktop only)
    var style = document.createElement('style');
    style.textContent =
        'input.baggage-qty::-webkit-outer-spin-button,' +
        'input.baggage-qty::-webkit-inner-spin-button{-webkit-appearance:none;margin:0}' +
        'input.baggage-qty{-moz-appearance:textfield;appearance:textfield}' +
        '@media(min-width:768px){' +
        '.baggage-stepper .btn{width:2.25rem;padding:0;font-size:1.1rem;line-height:1}' +
        '.baggage-stepper input.baggage-qty{text-align:center}' +
        '}';
    document.head.appendChild(style);

    function sanitize(val) {
        var n = parseInt(val, 10);
        return (isNaN(n) || n < 0) ? 0 : Math.min(n, MAX);
    }

    function makeBtn(label, text) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'btn btn-outline-secondary';
        btn.setAttribute('aria-label', label);
        btn.textContent = text;
        return btn;
    }

    function buildStepper(input) {
        var wrapper = document.createElement('div');
        wrapper.className = 'input-group baggage-stepper';

        var btnMinus = makeBtn('decrease', '−'); // −
        var btnPlus  = makeBtn('increase', '+');

        input.parentNode.insertBefore(wrapper, input);
        wrapper.appendChild(btnMinus);
        wrapper.appendChild(input);
        wrapper.appendChild(btnPlus);

        if (!input.value) input.value = '0';

        btnMinus.addEventListener('click', function () {
            input.value = Math.max(sanitize(input.value) - 1, 0);
        });
        btnPlus.addEventListener('click', function () {
            input.value = Math.min(sanitize(input.value) + 1, MAX);
        });
    }

    function initValidation(input, desktop) {
        input.addEventListener('focus', function () {
            if (this.value === '0') this.value = '';
        });
        input.addEventListener('blur', function () {
            var val = parseInt(this.value, 10);
            if (this.value === '' || isNaN(val) || val < 0) {
                this.value = desktop ? '0' : '';
            } else if (val > MAX) {
                this.value = String(MAX);
            }
        });
        input.addEventListener('keydown', function (e) {
            var allow = ['Backspace','Delete','Tab','Escape','Enter',
                         'ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Home','End'];
            if (allow.includes(e.key) || e.ctrlKey || e.metaKey) return;
            if (!/^\d$/.test(e.key)) { e.preventDefault(); return; }
            if (parseInt(this.value + e.key, 10) > MAX) e.preventDefault();
        });
        input.addEventListener('input', function () {
            this.value = this.value.replace(/\D/g, '');
            if (this.value !== '' && parseInt(this.value, 10) > MAX) this.value = String(MAX);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        var desktop = window.matchMedia('(min-width: 768px)').matches;
        document.querySelectorAll('.baggage-qty').forEach(function (input) {
            if (desktop) buildStepper(input);
            initValidation(input, desktop);
        });
    });
})();
