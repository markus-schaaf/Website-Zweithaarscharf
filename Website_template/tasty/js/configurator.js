/* Perücken-Konfigurator: unverbindliche Preisschätzung (Rohpreis + Aufpreise). */
(function () {
  'use strict';

  var euroFormat = new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' });

  function recalc() {
    var priceEl = document.getElementById('estimated-price');
    var configurator = document.getElementById('configurator');
    if (!priceEl || !configurator) { return; }

    var total = parseFloat(priceEl.dataset.basePrice) || 0;
    var checked = configurator.querySelectorAll('input[type="radio"]:checked');
    Array.prototype.forEach.call(checked, function (input) {
      total += parseFloat(input.dataset.surcharge) || 0;
    });
    priceEl.textContent = 'ca. ' + euroFormat.format(total);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var configurator = document.getElementById('configurator');
    if (!configurator) { return; }
    configurator.addEventListener('change', recalc);
    recalc();
  });
})();
