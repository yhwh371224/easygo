(function () {
  'use strict';

  /**
   * Enable sticky behaviour of navigation bar on page scroll
   * Extracted from theme.js (Around Bootstrap Template)
   */
  var stickyNavbar = function () {
    var navbar = document.querySelector('.navbar-sticky');
    if (navbar == null) return;
    var navbarClass = navbar.classList,
        navbarH = navbar.offsetHeight,
        scrollOffset = 500;

    if (navbarClass.contains('navbar-floating') && navbarClass.contains('navbar-dark')) {
      window.addEventListener('scroll', function (e) {
        if (e.currentTarget.pageYOffset > scrollOffset) {
          navbar.classList.remove('navbar-dark');
          navbar.classList.add('navbar-light', 'navbar-stuck');
        } else {
          navbar.classList.remove('navbar-light', 'navbar-stuck');
          navbar.classList.add('navbar-dark');
        }
      });
    } else if (navbarClass.contains('navbar-floating') && navbarClass.contains('navbar-light')) {
      window.addEventListener('scroll', function (e) {
        if (e.currentTarget.pageYOffset > scrollOffset) {
          navbar.classList.add('navbar-stuck');
        } else {
          navbar.classList.remove('navbar-stuck');
        }
      });
    } else {
      window.addEventListener('scroll', function (e) {
        if (e.currentTarget.pageYOffset > scrollOffset) {
          document.body.style.paddingTop = navbarH + 'px';
          navbar.classList.add('navbar-stuck');
        } else {
          document.body.style.paddingTop = '';
          navbar.classList.remove('navbar-stuck');
        }
      });
    }
  }();

  /**
   * Offcanvas toggler — navbar mobile menu open/close
   * Extracted from theme.js (Around Bootstrap Template)
   */
  var offcanvas = function () {
    var offcanvasTogglers = document.querySelectorAll('[data-bs-toggle="offcanvas"]'),
        offcanvasDismissers = document.querySelectorAll('[data-bs-dismiss="offcanvas"]'),
        offcanvasEls = document.querySelectorAll('.offcanvas'),
        docBody = document.body,
        fixedElements = document.querySelectorAll('[data-fixed-element]'),
        hasScrollbar = window.innerWidth > docBody.clientWidth;

    // Creating backdrop
    var backdrop = document.createElement('div');
    backdrop.classList.add('offcanvas-backdrop');

    // Open offcanvas
    var offcanvasOpen = function offcanvasOpen(offcanvasID) {
      var backdropContainer = document.querySelector(offcanvasID).parentNode;
      backdropContainer.appendChild(backdrop);
      setTimeout(function () {
        backdrop.classList.add('show');
      }, 20);
      document.querySelector(offcanvasID).setAttribute('data-offcanvas-show', true);

      if (hasScrollbar) {
        docBody.style.paddingRight = '15px';
        for (var i = 0; i < fixedElements.length; i++) {
          fixedElements[i].classList.add('right-15');
        }
      }
      docBody.classList.add('offcanvas-open');
    };

    // Close offcanvas
    var offcanvasClose = function offcanvasClose() {
      for (var i = 0; i < offcanvasEls.length; i++) {
        offcanvasEls[i].removeAttribute('data-offcanvas-show');
      }
      backdrop.classList.remove('show');
      setTimeout(function () {
        if (backdrop.parentNode) {
          backdrop.parentNode.removeChild(backdrop);
        }
      }, 250);

      if (hasScrollbar) {
        docBody.style.paddingRight = 0;
        for (var _i = 0; _i < fixedElements.length; _i++) {
          fixedElements[_i].classList.remove('right-15');
        }
      }
      docBody.classList.remove('offcanvas-open');
    };

    // Open on toggler click
    for (var i = 0; i < offcanvasTogglers.length; i++) {
      offcanvasTogglers[i].addEventListener('click', function (e) {
        e.preventDefault();
        offcanvasOpen(e.currentTarget.dataset.bsTarget);
      });
    }

    // Close on dismiss button click
    for (var _i2 = 0; _i2 < offcanvasDismissers.length; _i2++) {
      offcanvasDismissers[_i2].addEventListener('click', function (e) {
        e.preventDefault();
        offcanvasClose();
      });
    }

    // Close on backdrop click
    document.addEventListener('click', function (e) {
      if (e.target.classList[0] === 'offcanvas-backdrop') {
        offcanvasClose();
      }
    });
  }();

})();
