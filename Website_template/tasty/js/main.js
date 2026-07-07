/* Zweithaar Schaaf — Navigation & Scroll-Verhalten (Vanilla JS, ohne jQuery) */
(function () {
  'use strict';

  /* ---------- Off-Canvas-Navigation (mobil) ---------- */
  function buildOffcanvas() {
    var page = document.getElementById('page');
    if (!page || document.getElementById('fh5co-offcanvas')) { return; }

    var toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'fh5co-nav-toggle js-fh5co-nav-toggle';
    toggle.setAttribute('aria-label', 'Menü öffnen oder schließen');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-controls', 'fh5co-offcanvas');
    toggle.innerHTML = '<i></i>';

    var panel = document.createElement('nav');
    panel.id = 'fh5co-offcanvas';
    panel.setAttribute('aria-label', 'Mobile Navigation');

    ['.menu-1 > ul', '.menu-2 > ul'].forEach(function (selector) {
      var source = document.querySelector(selector);
      if (!source) { return; }
      var clone = source.cloneNode(true);
      clone.querySelectorAll('li').forEach(function (li) {
        li.classList.remove('has-dropdown');
      });
      // Unterpunkte im Off-Canvas immer ausgeklappt anzeigen
      clone.querySelectorAll('li > ul').forEach(function (ul) {
        ul.parentElement.classList.add('offcanvas-has-dropdown', 'active');
      });
      panel.appendChild(clone);
    });

    page.prepend(panel);
    page.prepend(toggle);

    function close() {
      document.body.classList.remove('offcanvas', 'overflow');
      toggle.classList.remove('active');
      toggle.setAttribute('aria-expanded', 'false');
    }
    function open() {
      document.body.classList.add('offcanvas', 'overflow');
      toggle.classList.add('active');
      toggle.setAttribute('aria-expanded', 'true');
    }

    toggle.addEventListener('click', function () {
      if (document.body.classList.contains('offcanvas')) { close(); } else { open(); }
    });
    document.addEventListener('click', function (event) {
      if (!document.body.classList.contains('offcanvas')) { return; }
      if (!panel.contains(event.target) && !toggle.contains(event.target)) { close(); }
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { close(); }
    });
    // Nur schließen, wenn zur Desktop-Navigation gewechselt wird (66em ~ 1056px);
    // mobile Browser feuern resize schon beim Ein-/Ausblenden der URL-Leiste
    window.addEventListener('resize', function () {
      if (window.innerWidth > 1056) { close(); }
    });
  }

  /* ---------- Scroll-Effekte: Header-Schatten + Go-to-top ---------- */
  function initScrollFx() {
    var header = document.querySelector('.fh5co-nav');
    var topWrap = document.querySelector('.js-top');

    window.addEventListener('scroll', function () {
      var y = window.scrollY;
      if (topWrap) { topWrap.classList.toggle('active', y > 200); }
      if (header) { header.classList.toggle('scrolled', y > 100); }
    }, { passive: true });

    var goTop = document.querySelector('.js-gotop');
    if (goTop) {
      goTop.addEventListener('click', function (event) {
        event.preventDefault();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      buildOffcanvas();
      initScrollFx();
    });
  } else {
    buildOffcanvas();
    initScrollFx();
  }
}());
