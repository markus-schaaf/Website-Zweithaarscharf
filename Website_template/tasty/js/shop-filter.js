/* Zweithaar Schaaf — Shop: Kategorie-Tabs, Filter-Chips, Sortierung (Vanilla JS) */
(function () {
  'use strict';

  var root = document.querySelector('[data-shop]');
  if (!root) { return; }

  var grid = root.querySelector('[data-shop-grid]');
  var cards = Array.prototype.slice.call(grid.querySelectorAll('.product-card'));
  if (!cards.length) { return; }

  var countEl = root.querySelector('[data-shop-count]');
  var emptyEl = root.querySelector('[data-shop-empty]');
  var resetEl = root.querySelector('[data-shop-reset]');
  var sortEl = root.querySelector('[data-shop-sort]');
  var hairGroups = ['color', 'length', 'structure'];

  // Ausgangsreihenfolge merken (Sortierung "Empfohlen")
  var initialOrder = cards.slice();

  var state = {
    cat: 'all',
    sort: 'recommended',
    filters: { color: new Set(), length: new Set(), structure: new Set(), highlight: new Set() }
  };

  function hasActiveFilters() {
    if (state.cat !== 'all') { return true; }
    return Object.keys(state.filters).some(function (g) { return state.filters[g].size > 0; });
  }

  function cardMatches(card) {
    if (state.cat !== 'all' && card.getAttribute('data-category') !== state.cat) { return false; }
    return Object.keys(state.filters).every(function (group) {
      var set = state.filters[group];
      if (!set.size) { return true; }
      var attr = group === 'highlight' ? 'data-badge' : 'data-' + group;
      return set.has(card.getAttribute(attr));
    });
  }

  function render() {
    var visible = [];
    cards.forEach(function (card) {
      var match = cardMatches(card);
      card.classList.toggle('is-hidden', !match);
      if (match) { visible.push(card); }
    });

    // Sortierung: sichtbare Karten neu anordnen
    var ordered;
    if (state.sort === 'price-asc' || state.sort === 'price-desc') {
      ordered = visible.slice().sort(function (a, b) {
        var pa = parseInt(a.getAttribute('data-price'), 10) || 0;
        var pb = parseInt(b.getAttribute('data-price'), 10) || 0;
        return state.sort === 'price-asc' ? pa - pb : pb - pa;
      });
    } else {
      ordered = initialOrder.filter(function (c) { return visible.indexOf(c) !== -1; });
    }
    ordered.forEach(function (card) { grid.appendChild(card); });

    if (countEl) { countEl.textContent = String(visible.length); }
    if (emptyEl) { emptyEl.classList.toggle('is-hidden', visible.length > 0); }
    if (resetEl) { resetEl.classList.toggle('is-hidden', !hasActiveFilters()); }
  }

  // Kategorie-Tabs
  root.querySelectorAll('[data-cat]').forEach(function (tab) {
    tab.addEventListener('click', function () {
      state.cat = tab.getAttribute('data-cat');
      root.querySelectorAll('[data-cat]').forEach(function (t) {
        var active = t === tab;
        t.classList.toggle('is-active', active);
        t.setAttribute('aria-pressed', active ? 'true' : 'false');
      });

      // Haar-Filter nur bei Kategorien mit festen Attributen zeigen
      var hasAttrs = tab.getAttribute('data-has-attrs') !== 'false' || state.cat === 'all';
      hairGroups.forEach(function (group) {
        var block = root.querySelector('[data-filter-group="' + group + '"]');
        if (!block) { return; }
        block.classList.toggle('is-hidden', !hasAttrs);
        if (!hasAttrs) {
          state.filters[group].clear();
          block.querySelectorAll('[data-group]').forEach(function (chip) {
            chip.classList.remove('is-active');
            chip.setAttribute('aria-pressed', 'false');
          });
        }
      });
      render();
    });
  });

  // Filter-Chips (Mehrfachauswahl je Gruppe)
  root.querySelectorAll('[data-group]').forEach(function (chip) {
    chip.addEventListener('click', function () {
      var group = chip.getAttribute('data-group');
      var value = chip.getAttribute('data-value');
      var set = state.filters[group];
      var active = !set.has(value);
      if (active) { set.add(value); } else { set.delete(value); }
      chip.classList.toggle('is-active', active);
      chip.setAttribute('aria-pressed', active ? 'true' : 'false');
      render();
    });
  });

  if (sortEl) {
    sortEl.addEventListener('change', function () {
      state.sort = sortEl.value;
      render();
    });
  }

  if (resetEl) {
    resetEl.addEventListener('click', function () {
      state.cat = 'all';
      Object.keys(state.filters).forEach(function (g) { state.filters[g].clear(); });
      root.querySelectorAll('[data-cat]').forEach(function (t) {
        var active = t.getAttribute('data-cat') === 'all';
        t.classList.toggle('is-active', active);
        t.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
      root.querySelectorAll('[data-group]').forEach(function (chip) {
        chip.classList.remove('is-active');
        chip.setAttribute('aria-pressed', 'false');
      });
      root.querySelectorAll('[data-filter-group]').forEach(function (block) {
        block.classList.remove('is-hidden');
      });
      render();
    });
  }

  render();
}());
