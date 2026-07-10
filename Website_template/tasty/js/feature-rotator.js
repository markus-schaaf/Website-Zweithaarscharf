/* Zweithaar Schaaf — Startseite: Crossfade-Rotator "Qualität & Handwerk" (Vanilla JS) */
(function () {
  'use strict';

  var root = document.querySelector('[data-rotator]');
  if (!root) { return; }

  var slides = Array.prototype.slice.call(root.querySelectorAll('.feature-rotator__slide'));
  if (slides.length < 2) { return; }

  var dotsWrap = root.querySelector('.feature-rotator__dots');
  var current = 0;
  var timer = null;

  var dots = slides.map(function (_, i) {
    var dot = document.createElement('button');
    dot.type = 'button';
    dot.className = 'feature-rotator__dot' + (i === 0 ? ' is-active' : '');
    dot.setAttribute('aria-label', 'Beitrag ' + (i + 1) + ' anzeigen');
    dot.addEventListener('click', function () { show(i); restart(); });
    dotsWrap.appendChild(dot);
    return dot;
  });

  function show(i) {
    slides[current].classList.remove('is-active');
    dots[current].classList.remove('is-active');
    current = i;
    slides[current].classList.add('is-active');
    dots[current].classList.add('is-active');
  }

  function stop() {
    if (timer) { clearInterval(timer); timer = null; }
  }

  function restart() {
    stop();
    timer = setInterval(function () { show((current + 1) % slides.length); }, 6500);
  }

  root.addEventListener('mouseenter', stop);
  root.addEventListener('mouseleave', restart);

  restart();
}());
