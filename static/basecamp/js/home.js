(function () {
  'use strict';

  /**
   * Fix aria-hidden focusable descendants in tns (tiny-slider) carousels.
   *
   * tiny-slider sets aria-hidden="true" on inactive .tns-item slides and
   * tabindex="-1" on the slide element itself, but does NOT propagate
   * tabindex="-1" to focusable descendants (links, buttons, etc.).  This
   * means keyboard users can still Tab into content that is hidden from
   * screen readers — a WCAG 2.1 SC 1.3.1 / 4.1.2 violation.
   *
   * This fix uses a MutationObserver to detect aria-hidden changes on slide
   * items and mirrors tabindex="-1" / removal onto all focusable descendants.
   */
  var carouselA11yFix = function () {
    var FOCUSABLE = [
      'a[href]',
      'area[href]',
      'button:not([disabled])',
      'input:not([disabled])',
      'select:not([disabled])',
      'textarea:not([disabled])',
      '[tabindex]:not([tabindex="-1"])'
    ].join(',');

    function syncSlideTabbing(slide) {
      var isHidden = slide.getAttribute('aria-hidden') === 'true';
      var focusables = slide.querySelectorAll(FOCUSABLE);
      for (var i = 0; i < focusables.length; i++) {
        if (isHidden) {
          focusables[i].setAttribute('tabindex', '-1');
        } else {
          focusables[i].removeAttribute('tabindex');
        }
      }
    }

    function watchSlide(slide) {
      syncSlideTabbing(slide);
      new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
          if (mutations[i].attributeName === 'aria-hidden') {
            syncSlideTabbing(mutations[i].target);
          }
        }
      }).observe(slide, { attributes: true, attributeFilter: ['aria-hidden'] });
    }

    function initSlider(slider) {
      var slides = slider.querySelectorAll('.tns-item');
      for (var i = 0; i < slides.length; i++) {
        watchSlide(slides[i]);
      }
    }

    // Watch for tns creating .tns-slider wrappers dynamically (tns injects
    // a new inner wrapper element with this class during initialisation).
    var domObserver = new MutationObserver(function (mutations) {
      for (var i = 0; i < mutations.length; i++) {
        var added = mutations[i].addedNodes;
        for (var j = 0; j < added.length; j++) {
          if (added[j].nodeType === 1 && added[j].classList.contains('tns-slider')) {
            initSlider(added[j]);
          }
        }
      }
    });
    domObserver.observe(document.documentElement, { childList: true, subtree: true });

    // Also handle any sliders already present when this script runs.
    document.addEventListener('DOMContentLoaded', function () {
      var existing = document.querySelectorAll('.tns-slider');
      for (var i = 0; i < existing.length; i++) {
        initSlider(existing[i]);
      }
    });
  }();

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
