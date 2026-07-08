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
    // Nur schließen, wenn zur Desktop-Navigation gewechselt wird (76em ~ 1216px);
    // mobile Browser feuern resize schon beim Ein-/Ausblenden der URL-Leiste
    window.addEventListener('resize', function () {
      if (window.innerWidth > 1216) { close(); }
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

  /* ---------- Produkt-Diashow (Homepage): Endlosschleife, pausiert bei Interaktion ---------- */
  function initProductMarquee() {
    var marquee = document.querySelector('[data-marquee]');
    if (!marquee) { return; }
    var track = marquee.querySelector('.product-marquee__track');
    var group = marquee.querySelector('.product-marquee__group');
    if (!track || !group || group.children.length < 2) { return; }

    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      marquee.classList.add('is-static');
      return;
    }

    // Kartengruppe klonen, bis die Schleife breiter als der Viewport ist
    // (Klone sind reine Optik: fuer Screenreader und Tastatur ausgeblendet)
    function addClone() {
      var clone = group.cloneNode(true);
      clone.setAttribute('aria-hidden', 'true');
      clone.querySelectorAll('a, button').forEach(function (el) {
        el.setAttribute('tabindex', '-1');
      });
      track.appendChild(clone);
    }
    var safety = 6;
    while (track.scrollWidth < marquee.offsetWidth * 2 && safety-- > 0) {
      addClone();
    }
    // translateX(-50%) ist nur bei gerader Gruppenanzahl nahtlos
    if (track.children.length % 2 === 1) { addClone(); }

    // Tempo an die Breite koppeln (~30 px/s), damit es immer langsam schwebt
    track.style.animationDuration = Math.round(track.scrollWidth / 2 / 30) + 's';
    marquee.classList.add('is-ready');

    // Touch: Nutzerin uebernimmt die Steuerung, Diashow wird scrollbar
    marquee.addEventListener('touchstart', function () {
      marquee.classList.remove('is-ready');
      marquee.classList.add('is-static');
    }, { passive: true, once: true });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      buildOffcanvas();
      initScrollFx();
      initProductMarquee();
    });
  } else {
    buildOffcanvas();
    initScrollFx();
    initProductMarquee();
  }
}());
