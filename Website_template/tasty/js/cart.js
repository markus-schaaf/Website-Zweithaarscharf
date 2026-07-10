/* Warenkorb: eingeloggt -> Server-API, anonym -> localStorage. */
(function () {
  'use strict';

  var STORAGE_KEY = 'zs_cart';
  var MAX_QTY = 99;
  var API = {
    products: '/warenkorb/api/produkte/',
    add: '/warenkorb/api/add/',
    update: '/warenkorb/api/update/',
    remove: '/warenkorb/api/remove/',
    merge: '/warenkorb/api/merge/'
  };

  var isAuth = document.body.dataset.authenticated === 'true';
  var euroFormat = new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' });

  /* ---------- localStorage ---------- */

  function readCart() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) { return { v: 1, items: {} }; }
      var cart = JSON.parse(raw);
      if (!cart || cart.v !== 1 || typeof cart.items !== 'object' || cart.items === null) {
        throw new Error('bad schema');
      }
      var items = {};
      Object.keys(cart.items).forEach(function (id) {
        var qty = parseInt(cart.items[id], 10);
        if (qty > 0) { items[id] = Math.min(qty, MAX_QTY); }
      });
      return { v: 1, items: items };
    } catch (e) {
      localStorage.removeItem(STORAGE_KEY);
      return { v: 1, items: {} };
    }
  }

  function writeCart(cart) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cart));
  }

  function cartCount(cart) {
    return Object.keys(cart.items).reduce(function (sum, id) {
      return sum + cart.items[id];
    }, 0);
  }

  /* ---------- Helpers ---------- */

  function getCookie(name) {
    var match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]+)'));
    return match ? decodeURIComponent(match[2]) : '';
  }

  function postJSON(url, data) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie('csrftoken')
      },
      body: JSON.stringify(data)
    }).then(function (res) {
      if (!res.ok) { throw res; }
      return res.json();
    });
  }

  function setBadge(count) {
    /* Header-Badge + Klone im Off-Canvas-Menue */
    document.querySelectorAll('#cart-count, [data-cart-count]').forEach(function (el) {
      el.textContent = count;
    });
    /* Header-Badge bei 0 ausblenden (nicht den Off-Canvas-Text "Warenkorb (n)") */
    var n = parseInt(count, 10) || 0;
    document.querySelectorAll('.nav-cart__badge').forEach(function (el) {
      el.classList.toggle('nav-cart__badge--empty', n === 0);
    });
  }

  /* ---------- In den Warenkorb ---------- */

  function flashButton(btn) {
    var original = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Hinzugefügt ✓';
    setTimeout(function () {
      btn.disabled = false;
      btn.textContent = original;
    }, 1200);
  }

  function addAnon(productId) {
    var cart = readCart();
    cart.items[productId] = Math.min((cart.items[productId] || 0) + 1, MAX_QTY);
    writeCart(cart);
    setBadge(cartCount(cart));
  }

  document.addEventListener('click', function (event) {
    var btn = event.target.closest('.js-add-to-cart');
    if (!btn) { return; }
    var productId = btn.dataset.productId;
    if (isAuth) {
      postJSON(API.add, { product_id: productId, quantity: 1 })
        .then(function (resp) {
          setBadge(resp.count);
          flashButton(btn);
        })
        .catch(function (err) {
          if (err && err.status === 401) {
            addAnon(productId);
            flashButton(btn);
          }
        });
    } else {
      addAnon(productId);
      flashButton(btn);
    }
  });

  /* ---------- Merge nach Login ---------- */

  function mergeIfNeeded() {
    if (!isAuth) { return; }
    var cart = readCart();
    if (cartCount(cart) === 0) { return; }
    postJSON(API.merge, cart)
      .then(function (resp) {
        localStorage.removeItem(STORAGE_KEY);
        setBadge(resp.count);
        if (document.getElementById('cart-anon-root') || document.getElementById('cart-table')) {
          window.location.reload();
        }
      })
      .catch(function () {
        /* localStorage behalten, naechster Seitenaufruf versucht es erneut */
      });
  }

  /* ---------- Warenkorb-Seite: eingeloggt ---------- */

  function bindAuthCartPage() {
    var table = document.getElementById('cart-table');
    if (!table) { return; }

    function rowQty(row) {
      return parseInt(row.querySelector('.qty-value').textContent, 10) || 0;
    }

    function applyUpdate(row, resp) {
      setBadge(resp.count);
      var total = document.getElementById('cart-total');
      if (total) { total.textContent = resp.total_display; }
      if (resp.quantity === 0 || resp.removed) {
        row.remove();
      } else if (typeof resp.quantity !== 'undefined') {
        row.querySelector('.qty-value').textContent = resp.quantity;
        row.querySelector('.js-line-total').textContent = resp.line_total_display;
      }
      if (!table.querySelector('tbody tr')) {
        table.closest('.form-card').style.display = 'none';
        var empty = document.getElementById('cart-empty');
        if (empty) { empty.style.display = ''; }
      }
    }

    table.addEventListener('click', function (event) {
      var row = event.target.closest('tr[data-product-id]');
      if (!row) { return; }
      var productId = row.dataset.productId;

      if (event.target.closest('.js-qty-plus')) {
        postJSON(API.update, { product_id: productId, quantity: rowQty(row) + 1 })
          .then(function (resp) { applyUpdate(row, resp); });
      } else if (event.target.closest('.js-qty-minus')) {
        var qty = rowQty(row);
        if (qty <= 1) { return; }
        postJSON(API.update, { product_id: productId, quantity: qty - 1 })
          .then(function (resp) { applyUpdate(row, resp); });
      } else if (event.target.closest('.js-remove')) {
        event.preventDefault();
        postJSON(API.remove, { product_id: productId })
          .then(function (resp) {
            resp.removed = true;
            applyUpdate(row, resp);
          });
      }
    });
  }

  /* ---------- Warenkorb-Seite: anonym ---------- */

  function renderAnonCartPage() {
    var root = document.getElementById('cart-anon-root');
    if (!root) { return; }

    fetch(API.products, { credentials: 'same-origin' })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        var products = data.products || {};
        var cart = readCart();

        // Produkte entfernen, die es nicht mehr gibt
        var changed = false;
        Object.keys(cart.items).forEach(function (id) {
          if (!products[id]) {
            delete cart.items[id];
            changed = true;
          }
        });
        if (changed) { writeCart(cart); }
        setBadge(cartCount(cart));
        render(root, products, cart);
      });

    function render(container, products, cart) {
      var ids = Object.keys(cart.items);
      if (ids.length === 0) {
        container.innerHTML =
          '<div class="cart-empty form-card">' +
          '<h2>Ihr Warenkorb ist leer.</h2>' +
          '<a class="btn btn-gold" href="' + container.dataset.shopUrl + '">Zum Shop</a>' +
          '</div>';
        return;
      }

      var total = 0;
      var rows = ids.map(function (id) {
        var p = products[id];
        var qty = cart.items[id];
        var line = p.price * qty;
        total += line;
        return (
          '<tr data-product-id="' + p.id + '">' +
          '<td class="cart-table__img"><a href="' + p.url + '">' +
          (p.image ? '<img src="' + p.image + '" alt="" loading="lazy">' : '') +
          '</a></td>' +
          '<td class="cart-table__name"><a href="' + p.url + '">' + p.name + '</a></td>' +
          '<td data-label="Einzelpreis">ab ' + p.price_display + ',- €</td>' +
          '<td data-label="Menge"><span class="qty-controls">' +
          '<button type="button" class="qty-btn js-qty-minus" aria-label="Menge verringern">−</button>' +
          '<span class="qty-value">' + qty + '</span>' +
          '<button type="button" class="qty-btn js-qty-plus" aria-label="Menge erhöhen">+</button>' +
          '</span></td>' +
          '<td data-label="Zwischensumme" class="js-line-total">' + euroFormat.format(line) + '</td>' +
          '<td class="cart-table__actions"><a href="#" class="cart-table__remove js-remove">Entfernen</a></td>' +
          '</tr>'
        );
      }).join('');

      container.innerHTML =
        '<div class="form-card table-scroll">' +
        '<table class="account-table cart-table" id="cart-anon-table">' +
        '<thead><tr><th></th><th>Produkt</th><th>Einzelpreis</th><th>Menge</th><th>Zwischensumme</th><th></th></tr></thead>' +
        '<tbody>' + rows + '</tbody>' +
        '<tfoot><tr><th colspan="4" style="text-align: right;">Gesamtsumme</th>' +
        '<th id="cart-total">' + euroFormat.format(total) + '</th><th></th></tr></tfoot>' +
        '</table>' +
        '<p class="text-muted" style="margin-top: 20px; margin-bottom: 0;">' +
        'Alle Preise sind „ab“-Richtwerte für die Grundausführung – ' +
        'der endgültige Preis wird im Beratungsgespräch festgelegt.</p>' +
        '</div>';

      container.querySelector('tbody').addEventListener('click', function (event) {
        var row = event.target.closest('tr[data-product-id]');
        if (!row) { return; }
        var id = row.dataset.productId;
        var current = readCart();

        if (event.target.closest('.js-qty-plus')) {
          current.items[id] = Math.min((current.items[id] || 0) + 1, MAX_QTY);
        } else if (event.target.closest('.js-qty-minus')) {
          if ((current.items[id] || 0) <= 1) { return; }
          current.items[id] -= 1;
        } else if (event.target.closest('.js-remove')) {
          event.preventDefault();
          delete current.items[id];
        } else {
          return;
        }
        writeCart(current);
        setBadge(cartCount(current));
        render(container, products, current);
      });
    }
  }

  /* ---------- Init ---------- */

  document.addEventListener('DOMContentLoaded', function () {
    if (!isAuth) {
      setBadge(cartCount(readCart()));
    }
    mergeIfNeeded();
    bindAuthCartPage();
    renderAnonCartPage();
  });
})();
