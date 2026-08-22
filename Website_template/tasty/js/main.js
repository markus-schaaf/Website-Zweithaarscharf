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

    function isOpen() {
      return document.body.classList.contains('offcanvas');
    }
    // Geschlossen darf das Panel weder fokussierbar noch vorlesbar sein.
    // inert deckt beides ab; aria-hidden ist der Rueckfall fuer aeltere Browser.
    function setInert(inert) {
      panel.inert = inert;
      if (inert) {
        panel.setAttribute('aria-hidden', 'true');
      } else {
        panel.removeAttribute('aria-hidden');
      }
    }
    function close(returnFocus) {
      if (!isOpen()) { return; }
      document.body.classList.remove('offcanvas', 'overflow');
      toggle.classList.remove('active');
      toggle.setAttribute('aria-expanded', 'false');
      setInert(true);
      if (returnFocus) { toggle.focus(); }
    }
    function open() {
      document.body.classList.add('offcanvas', 'overflow');
      toggle.classList.add('active');
      toggle.setAttribute('aria-expanded', 'true');
      setInert(false);
      var first = panel.querySelector('a, button');
      if (first) { first.focus(); }
    }
    setInert(true);

    toggle.addEventListener('click', function () {
      if (isOpen()) { close(true); } else { open(); }
    });
    document.addEventListener('click', function (event) {
      if (!isOpen()) { return; }
      if (!panel.contains(event.target) && !toggle.contains(event.target)) { close(false); }
    });
    // Klick auf einen Menuepunkt: Seite wechselt, Menue soll nicht offen bleiben
    panel.addEventListener('click', function (event) {
      if (event.target.closest('a')) { close(false); }
    });
    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape') { close(true); }
    });
    // Nur schließen, wenn zur Desktop-Navigation gewechselt wird (76em ~ 1216px);
    // mobile Browser feuern resize schon beim Ein-/Ausblenden der URL-Leiste
    window.addEventListener('resize', function () {
      if (window.innerWidth > 1216) { close(false); }
    });
  }

  /* ---------- Scroll-Effekte: Header-Schatten + Go-to-top ---------- */
  function initScrollFx() {
    var header = document.querySelector('.fh5co-nav');
    var topWrap = document.querySelector('.js-top');
    var toggle = document.querySelector('.js-fh5co-nav-toggle');
    var announce = document.querySelector('.announce-bar');

    // Banner scrollt im normalen Fluss weg; der fixierte Burger wandert um genau
    // die weggescrollte Bannerhoehe mit nach oben, damit er auf der Markenzeile bleibt.
    var barH = announce ? announce.offsetHeight : 0;
    window.addEventListener('resize', function () {
      if (announce) { barH = announce.offsetHeight; }
    });

    window.addEventListener('scroll', function () {
      var y = window.scrollY;
      if (topWrap) { topWrap.classList.toggle('active', y > 200); }
      if (header) { header.classList.toggle('scrolled', y > 100); }
      if (toggle) {
        toggle.style.transform = 'translateY(-' + Math.min(y, barH) + 'px)';
      }
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

  /* ---------- Formulare: Doppel-Absenden verhindern, Zustand zeigen ---------- */
  function initFormFeedback() {
    document.querySelectorAll('form[method="post"], form[method="POST"]').forEach(function (form) {
      if (form.hasAttribute('data-no-busy')) { return; }
      form.addEventListener('submit', function () {
        // Ungueltige Felder: der Browser bricht ab, dann darf nichts sperren
        if (typeof form.checkValidity === 'function' && !form.checkValidity()) { return; }
        if (form.dataset.busy === '1') { return; }
        form.dataset.busy = '1';
        form.setAttribute('aria-busy', 'true');
        // Erst nach dem Serialisieren sperren, sonst faellt ein benannter
        // Absende-Knopf aus den uebertragenen Daten heraus.
        window.setTimeout(function () {
          form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach(function (btn) {
            if (btn.tagName === 'BUTTON') {
              btn.dataset.labelOriginal = btn.textContent;
              btn.textContent = 'Wird gesendet …';
            }
            btn.disabled = true;
          });
        }, 0);
      });
    });
  }

  /* ---------- Meldungen und Fehler sichtbar machen ---------- */
  // Nach einem POST-Redirect steht die Erfolgsmeldung oft unterhalb des
  // sichtbaren Bereichs. Sie wird angesteuert und fokussiert, damit sie
  // ankommt - visuell wie akustisch.
  function focusFeedback() {
    var target = document.querySelector('.messages li')
      || document.querySelector('.form-errors')
      || document.querySelector('[aria-invalid="true"]');
    if (!target) { return; }

    // focus() scrollt selbst und beachtet dabei scroll-padding-top,
    // bleibt also nicht unter dem Sticky-Header haengen.
    var invalid = document.querySelector('[aria-invalid="true"]');
    if (invalid) {
      invalid.focus();
      return;
    }
    var box = target.closest('.messages, .form-errors') || target;
    if (!box.hasAttribute('tabindex')) { box.setAttribute('tabindex', '-1'); }
    box.focus();
  }

  /* ---------- Galerie: Vorher-Nachher-Regler ---------- */

  function initGalleryCompare() {
    var box = document.getElementById('gal-compare');
    if (!box) { return; }
    var range = box.querySelector('.gal-compare__range');
    if (!range) { return; }

    // Der Input liefert Ziehen, Tippen und Pfeiltasten - hier wird nur der
    // Wert an die CSS-Variable durchgereicht, die den Zuschnitt steuert.
    function apply() {
      box.style.setProperty('--split', range.value);
    }
    range.addEventListener('input', apply);
    apply();
  }

  function init() {
    buildOffcanvas();
    initScrollFx();
    initProductMarquee();
    initGalleryCompare();
    initFormFeedback();
    focusFeedback();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
