/* Warenwirtschaft: Bildvorschau, Reihenfolge, Filter.
   Reihenfolge bewusst ueber Pfeiltasten statt Drag-and-drop - auf iOS
   zuverlaessig bedienbar. */
(function () {
  "use strict";

  // --- Bilder ---------------------------------------------------------------

  function tiles(grid) {
    return Array.prototype.slice.call(grid.querySelectorAll("[data-img-tile]"));
  }

  function move(grid, tile, richtung) {
    var liste = tiles(grid);
    var index = liste.indexOf(tile);
    var ziel = index + richtung;
    if (ziel < 0 || ziel >= liste.length) return;
    if (richtung < 0) {
      grid.insertBefore(tile, liste[ziel]);
    } else {
      grid.insertBefore(liste[ziel], tile);
    }
    tile.classList.add("is-moved");
    window.setTimeout(function () { tile.classList.remove("is-moved"); }, 400);
  }

  function preview(input, ziel) {
    ziel.innerHTML = "";
    var dateien = Array.prototype.slice.call(input.files || []);
    ziel.hidden = dateien.length === 0;
    dateien.forEach(function (datei) {
      if (datei.type.indexOf("image/") !== 0) return;
      var figure = document.createElement("figure");
      figure.className = "img-tile img-tile--neu";
      var bild = document.createElement("img");
      bild.alt = "";
      figure.appendChild(bild);
      var bar = document.createElement("figcaption");
      bar.className = "img-tile__bar img-tile__bar--neu";
      bar.textContent = "neu";
      figure.appendChild(bar);
      ziel.appendChild(figure);

      var leser = new FileReader();
      leser.onload = function (e) { bild.src = e.target.result; };
      leser.readAsDataURL(datei);
    });
  }

  document.querySelectorAll("[data-img-uploader]").forEach(function (box) {
    var grid = box.querySelector("[data-img-grid]");
    var input = box.querySelector("[data-img-input]");
    var vorschau = box.querySelector("[data-img-preview]");

    if (grid) {
      grid.addEventListener("click", function (event) {
        var knopf = event.target.closest("[data-img-move]");
        if (!knopf) return;
        event.preventDefault();
        move(grid, knopf.closest("[data-img-tile]"), parseInt(knopf.dataset.imgMove, 10));
      });
      grid.addEventListener("change", function (event) {
        if (event.target.type !== "checkbox") return;
        var tile = event.target.closest("[data-img-tile]");
        if (tile) tile.classList.toggle("is-deleted", event.target.checked);
      });
    }

    if (input && vorschau) {
      input.addEventListener("change", function () { preview(input, vorschau); });
    }
  });

  // --- Filterleiste ---------------------------------------------------------

  document.querySelectorAll("[data-wws-filter]").forEach(function (form) {
    form.querySelectorAll("[data-wws-submit]").forEach(function (feld) {
      feld.addEventListener("change", function () { form.submit(); });
    });
  });
})();
