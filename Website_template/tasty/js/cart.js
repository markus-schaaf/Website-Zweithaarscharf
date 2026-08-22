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

  /* ---------- Rueckmeldung ---------- */

  // Eine Live-Region fuer alle Warenkorb-Aktionen. Sichtbar wird nichts,
  // aber Screenreader sagen an, was passiert ist.
  function announce(text) {
    var region = document.getElementById('cart-status');
    if (!region) {
      region = document.createElement('p');
      region.id = 'cart-status';
      region.className = 'visually-hidden';
      region.setAttribute('role', 'status');
      region.setAttribute('aria-live', 'polite');
      document.body.appendChild(region);
    }
    region.textContent = text;
  }

  // Sichtbarer Fehler mit Weg zurueck statt stiller Fehlschlag.
  function showError(anchor, text, retry) {
    if (!anchor) { return; }
    var box = anchor.parentElement.querySelector('.action-error');
    if (!box) {
      box = document.createElement('p');
      box.className = 'action-error';
      box.setAttribute('role', 'alert');
      anchor.parentElement.insertBefore(box, anchor.nextSibling);
    }
    box.textContent = text + ' ';
    if (retry) {
      var again = document.createElement('button');
      again.type = 'button';
      again.className = 'action-error__retry';
      again.textContent = 'Erneut versuchen';
      again.addEventListener('click', function () {
        box.remove();
        retry();
      });
      box.appendChild(again);
    }
    announce(text);
  }

  function clearError(anchor) {
    if (!anchor || !anchor.parentElement) { return; }
    var box = anchor.parentElement.querySelector('.action-error');
    if (box) { box.remove(); }
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

  function itemsLabel(n) {
    return n + (n === 1 ? ' Modell' : ' Modelle') + ' im Warenkorb';
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

  function addToCart(btn) {
    var productId = btn.dataset.productId;
    clearError(btn);
    if (!isAuth) {
      addAnon(productId);
      flashButton(btn);
      announce('Zum Warenkorb hinzugefügt.');
      return;
    }
    btn.disabled = true;
    postJSON(API.add, { product_id: productId, quantity: 1 })
      .then(function (resp) {
        btn.disabled = false;
        setBadge(resp.count);
        flashButton(btn);
        announce('Zum Warenkorb hinzugefügt. ' + resp.count + ' Artikel im Warenkorb.');
      })
      .catch(function (err) {
        btn.disabled = false;
        // Sitzung abgelaufen: still auf den lokalen Warenkorb ausweichen.
        // 401 kommt vom View, 403 von der CSRF-Pruefung davor - beides heisst,
        // dass die Anmeldung nicht mehr traegt.
        if (err && (err.status === 401 || err.status === 403)) {
          addAnon(productId);
          flashButton(btn);
          announce('Zum Warenkorb hinzugefügt.');
          return;
        }
        showError(btn, 'Konnte nicht in den Warenkorb gelegt werden.', function () {
          addToCart(btn);
        });
      });
  }

  document.addEventListener('click', function (event) {
    var btn = event.target.closest('.js-add-to-cart');
    if (!btn) { return; }
    addToCart(btn);
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
        if (document.getElementById('cart-anon-root') || document.getElementById('cart-items')) {
          window.location.reload();
        }
      })
      .catch(function () {
        /* localStorage behalten, naechster Seitenaufruf versucht es erneut */
      });
  }

  /* ---------- Warenkorb-Seite: eingeloggt ---------- */

  function bindAuthCartPage() {
    var list = document.getElementById('cart-items');
    if (!list) { return; }

    function rowQty(row) {
      return parseInt(row.querySelector('.qty-value').textContent, 10) || 0;
    }

    function applyUpdate(row, resp) {
      setBadge(resp.count);
      var total = document.getElementById('cart-total');
      if (total) { total.textContent = resp.total_display; }
      // Zwischensumme entspricht der Gesamtsumme - es gibt keine Zuschlaege
      var subtotal = document.getElementById('cart-subtotal');
      if (subtotal) { subtotal.textContent = resp.total_display; }
      if (resp.quantity === 0 || resp.removed) {
        row.remove();
      } else if (typeof resp.quantity !== 'undefined') {
        row.querySelector('.qty-value').textContent = resp.quantity;
        row.querySelector('.js-line-total').textContent = resp.line_total_display;
      }
      var label = document.getElementById('cart-count-label');
      if (label) { label.textContent = itemsLabel(list.querySelectorAll('.cart-item').length); }
      if (!list.querySelector('.cart-item')) {
        var box = document.getElementById('cart-box');
        if (box) { box.style.display = 'none'; }
        var empty = document.getElementById('cart-empty');
        if (empty) { empty.style.display = ''; }
      }
    }

    // Eine Stelle fuer alle drei Aktionen: Erfolg meldet, Fehler laesst die
    // Zeile unveraendert und bietet einen zweiten Versuch an.
    function run(row, request, erfolgstext, entfernen) {
      var controls = row.querySelector('.qty-controls');
      clearError(controls);
      row.setAttribute('aria-busy', 'true');
      request()
        .then(function (resp) {
          row.removeAttribute('aria-busy');
          if (entfernen) { resp.removed = true; }
          applyUpdate(row, resp);
          announce(erfolgstext);
        })
        .catch(function () {
          row.removeAttribute('aria-busy');
          showError(controls, 'Änderung nicht gespeichert.', function () {
            run(row, request, erfolgstext, entfernen);
          });
        });
    }

    list.addEventListener('click', function (event) {
      var row = event.target.closest('.cart-item[data-product-id]');
      if (!row) { return; }
      var productId = row.dataset.productId;

      if (event.target.closest('.js-qty-plus')) {
        var mehr = rowQty(row) + 1;
        run(row, function () {
          return postJSON(API.update, { product_id: productId, quantity: mehr });
        }, 'Menge auf ' + mehr + ' geändert.', false);
      } else if (event.target.closest('.js-qty-minus')) {
        var qty = rowQty(row);
        if (qty <= 1) { return; }
        run(row, function () {
          return postJSON(API.update, { product_id: productId, quantity: qty - 1 });
        }, 'Menge auf ' + (qty - 1) + ' geändert.', false);
      } else if (event.target.closest('.js-remove')) {
        event.preventDefault();
        run(row, function () {
          return postJSON(API.remove, { product_id: productId });
        }, 'Artikel aus dem Warenkorb entfernt.', true);
      }
    });
  }

  /* ---------- Warenkorb-Seite: anonym ---------- */

  function renderAnonCartPage() {
    var root = document.getElementById('cart-anon-root');
    if (!root) { return; }

    function load() {
      fetch(API.products, { credentials: 'same-origin' })
        .then(function (res) {
          if (!res.ok) { throw res; }
          return res.json();
        })
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
        })
        .catch(function () {
          // Ohne Fehlerzustand bliebe hier dauerhaft "wird geladen" stehen
          root.innerHTML =
            '<div class="cart-empty form-card">' +
            '<h2>Der Warenkorb konnte nicht geladen werden.</h2>' +
            '<p class="text-muted">Bitte prüfen Sie Ihre Verbindung.</p>' +
            '</div>';
          var again = document.createElement('button');
          again.type = 'button';
          again.className = 'btn btn-gold';
          again.textContent = 'Erneut versuchen';
          again.addEventListener('click', function () {
            root.innerHTML = '<div class="cart-empty form-card"><h2>Ihr Warenkorb wird geladen …</h2></div>';
            load();
          });
          root.querySelector('.cart-empty').appendChild(again);
          announce('Der Warenkorb konnte nicht geladen werden.');
        });
    }
    load();

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
      var shopUrl = container.dataset.shopUrl;
      var cards = ids.map(function (id) {
        var p = products[id];
        var qty = cart.items[id];
        var line = p.price * qty;
        total += line;
        var chips =
          (p.category_label ? '<span class="cart-chip">' + p.category_label + '</span>' : '') +
          (p.stock_label ? '<span class="cart-chip">' + p.stock_label + '</span>' : '');
        var notice = p.sold_out
          ? '<div class="cart-notice">' +
            '<span class="cart-notice__icon" aria-hidden="true">!</span>' +
            '<div>' +
            '<p class="cart-notice__title">Inzwischen verkauft</p>' +
            '<p>Dieses Einzelstück ist nicht mehr verfügbar. ' +
            'Wir finden gern ein vergleichbares Modell für Sie.</p>' +
            '<div class="cart-notice__links">' +
            '<a href="#" class="js-remove">Aus dem Warenkorb entfernen</a>' +
            '<a href="' + shopUrl + '">Ähnliche Modelle zeigen</a>' +
            '</div></div></div>'
          : '';
        return (
          '<article class="cart-item" data-product-id="' + p.id + '">' +
          '<a class="cart-item__img" href="' + p.url + '">' +
          (p.image ? '<img src="' + p.image + '" alt="" loading="lazy">' : '') +
          '</a>' +
          '<div class="cart-item__body">' +
          '<a class="cart-item__name" href="' + p.url + '">' + p.name + '</a>' +
          '<div class="cart-item__chips">' + chips + '</div>' +
          '<p class="cart-item__meta">Einzelpreis: ab ' + p.price_display + ',- €</p>' +
          notice +
          '<div class="cart-item__actions">' +
          '<span class="qty-controls">' +
          '<button type="button" class="qty-btn js-qty-minus" aria-label="Menge verringern">−</button>' +
          '<span class="qty-value">' + qty + '</span>' +
          '<button type="button" class="qty-btn js-qty-plus" aria-label="Menge erhöhen">+</button>' +
          '</span>' +
          '<a href="#" class="cart-item__remove js-remove">Entfernen</a>' +
          '</div></div>' +
          '<div class="cart-item__side">' +
          '<span class="cart-item__total js-line-total">' + euroFormat.format(line) + '</span>' +
          '</div></article>'
        );
      }).join('');

      var summe = euroFormat.format(total);

      container.innerHTML =
        '<div class="cart-layout" id="cart-box">' +
        '<div class="cart-items-col">' +
        '<div class="cart-list-head"><span id="cart-count-label">' +
        itemsLabel(ids.length) + '</span></div>' +
        '<div class="cart-items" id="cart-items">' + cards + '</div>' +
        '<div class="cart-list-foot">' +
        '<a class="cart-back" href="' + shopUrl + '">← Weiter stöbern</a>' +
        '<span>Fragen zu einem Modell? ' +
        '<a href="tel:+4912345678">Rufen Sie uns an: +49 123 456 78</a></span>' +
        '</div></div>' +
        '<aside class="cart-summary">' +
        '<div class="cart-summary__rule" aria-hidden="true"></div>' +
        '<div class="cart-summary__inner">' +
        '<h2 class="cart-summary__title">Zusammenfassung</h2>' +
        '<div class="cart-summary__row"><span>Zwischensumme</span>' +
        '<span id="cart-subtotal">' + summe + '</span></div>' +
        '<div class="cart-summary__row"><span>Beratung im Studio</span>' +
        '<span class="cart-summary__free">kostenlos</span></div>' +
        '<div class="cart-summary__total"><span>Gesamtsumme</span>' +
        '<strong id="cart-total">' + summe + '</strong></div>' +
        '<p class="cart-summary__hint text-muted">' +
        'Alle Preise sind „ab“-Richtwerte für die Grundausführung – ' +
        'der endgültige Preis wird im Beratungsgespräch festgelegt.</p>' +
        (container.dataset.reservationUrl
          ? '<a class="btn btn-gold" href="' + container.dataset.reservationUrl + '">Beratungstermin vereinbaren</a>'
          : '') +
        (container.dataset.contactUrl
          ? '<a class="btn btn-outline" href="' + container.dataset.contactUrl + '">Unverbindlich anfragen</a>'
          : '') +
        '<ul class="cart-trust">' +
        '<li><span class="cart-trust__check" aria-hidden="true">✓</span>' +
        '<span>Kostenlose Erstberatung, telefonisch oder im Studio</span></li>' +
        '<li><span class="cart-trust__check" aria-hidden="true">✓</span>' +
        '<span>Der Warenkorb ist eine Merkliste – es entsteht keine Zahlungspflicht</span></li>' +
        '<li><span class="cart-trust__check" aria-hidden="true">✓</span>' +
        '<span>Anpassung und Schnitt durch Meisterhand inklusive</span></li>' +
        '</ul></div></aside></div>';

      container.querySelector('.cart-items').addEventListener('click', function (event) {
        var row = event.target.closest('.cart-item[data-product-id]');
        if (!row) { return; }
        var id = row.dataset.productId;
        var current = readCart();

        var meldung;
        if (event.target.closest('.js-qty-plus')) {
          current.items[id] = Math.min((current.items[id] || 0) + 1, MAX_QTY);
          meldung = 'Menge auf ' + current.items[id] + ' geändert.';
        } else if (event.target.closest('.js-qty-minus')) {
          if ((current.items[id] || 0) <= 1) { return; }
          current.items[id] -= 1;
          meldung = 'Menge auf ' + current.items[id] + ' geändert.';
        } else if (event.target.closest('.js-remove')) {
          event.preventDefault();
          delete current.items[id];
          meldung = 'Artikel aus dem Warenkorb entfernt.';
        } else {
          return;
        }
        writeCart(current);
        setBadge(cartCount(current));
        render(container, products, current);
        announce(meldung);
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
