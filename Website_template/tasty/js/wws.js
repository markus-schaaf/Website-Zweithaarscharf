/* Warenwirtschaft: Bildvorschau, Reihenfolge, Filter.
   Reihenfolge bewusst ueber Pfeiltasten statt Drag-and-drop - auf iOS
   zuverlaessig bedienbar. */
(function () {
  "use strict";

  // --- Bilder ---------------------------------------------------------------

  // Ansagen fuer Vorgaenge, die man sonst nur sieht
  function melde(text) {
    var region = document.getElementById("wws-status");
    if (!region) {
      region = document.createElement("p");
      region.id = "wws-status";
      region.className = "visually-hidden";
      region.setAttribute("role", "status");
      region.setAttribute("aria-live", "polite");
      document.body.appendChild(region);
    }
    region.textContent = text;
  }

  function tiles(grid) {
    return Array.prototype.slice.call(grid.querySelectorAll("[data-wws-img]"));
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
    melde("Bild an Position " + (ziel + 1) + " von " + liste.length + ".");
  }

  function kuerzen(name) {
    return name.length > 22 ? name.slice(0, 19) + "…" : name;
  }

  function preview(input, ziel) {
    ziel.innerHTML = "";
    var dateien = Array.prototype.slice.call(input.files || []);
    ziel.hidden = dateien.length === 0;
    dateien.forEach(function (datei) {
      var figure = document.createElement("figure");
      figure.className = "wws-img wws-img--neu";
      var bild = document.createElement("img");
      bild.alt = "";
      figure.appendChild(bild);
      var bar = document.createElement("figcaption");
      bar.className = "wws-img__bar wws-img__bar--neu";
      bar.textContent = "neu";
      figure.appendChild(bar);
      ziel.appendChild(figure);

      // HEIC von der iPhone-Kamera kann der Browser nicht darstellen. Die
      // Datei ist trotzdem in Ordnung - sie wird beim Speichern umgewandelt.
      // Deshalb statt eines kaputten Bilds ein ruhiger Hinweis.
      function ohneVorschau() {
        figure.classList.add("wws-img--ohne-vorschau");
        bild.remove();
        var text = document.createElement("span");
        text.className = "wws-img__name";
        text.textContent = kuerzen(datei.name);
        figure.insertBefore(text, bar);
        bar.textContent = "wird umgewandelt";
      }

      bild.onerror = ohneVorschau;
      var leser = new FileReader();
      leser.onload = function (e) { bild.src = e.target.result; };
      leser.onerror = ohneVorschau;
      leser.readAsDataURL(datei);
    });
  }

  // Gespeicherte Bilder, deren Datei nicht mehr ausgeliefert wird, sollen
  // sagen was los ist statt ein kaputtes Bildsymbol zu zeigen.
  document.querySelectorAll("[data-wws-img] img").forEach(function (bild) {
    bild.addEventListener("error", function () {
      var kachel = bild.closest("[data-wws-img]");
      if (!kachel) return;
      kachel.classList.add("wws-img--ohne-vorschau", "wws-img--fehlt");
      var text = document.createElement("span");
      text.className = "wws-img__name";
      text.textContent = "Bild fehlt";
      bild.replaceWith(text);
    });
  });

  document.querySelectorAll("[data-wws-uploader]").forEach(function (box) {
    var grid = box.querySelector("[data-wwsimg-grid]");
    var input = box.querySelector("[data-wwsimg-input]");
    var vorschau = box.querySelector("[data-wwsimg-preview]");

    if (grid) {
      grid.addEventListener("click", function (event) {
        var knopf = event.target.closest("[data-wwsimg-move]");
        if (!knopf) return;
        event.preventDefault();
        move(grid, knopf.closest("[data-wws-img]"), parseInt(knopf.dataset.wwsimgMove, 10));
      });
      grid.addEventListener("change", function (event) {
        if (event.target.type !== "checkbox") return;
        var tile = event.target.closest("[data-wws-img]");
        if (tile) tile.classList.toggle("is-deleted", event.target.checked);
      });
    }

    if (input && vorschau) {
      input.addEventListener("change", function () { preview(input, vorschau); });
    }
  });

  // --- Kundensuche ----------------------------------------------------------
  // Ersetzt die Auswahlliste, sobald JavaScript laeuft. Ohne JavaScript bleibt
  // das urspruengliche <select> sichtbar und bedienbar.

  function hinweis(liste, text) {
    var eintrag = document.createElement("li");
    eintrag.className = "wws-treffer__hinweis";
    eintrag.textContent = text;
    liste.appendChild(eintrag);
  }

  document.querySelectorAll("[data-wws-kundensuche]").forEach(function (box) {
    var feld = box.querySelector("[data-wws-kundenfeld]");
    var liste = box.querySelector("[data-wws-treffer]");
    var gewaehlt = box.querySelector("[data-wws-gewaehlt]");
    var select = box.querySelector("select");
    if (!feld || !liste || !select) return;

    select.hidden = true;
    feld.hidden = false;

    function zeigeGewaehlt() {
      var option = select.options[select.selectedIndex];
      var hatKunden = select.value !== "";
      gewaehlt.hidden = !hatKunden;
      if (hatKunden) {
        gewaehlt.textContent = "Gewählt: " + option.textContent;
        var loesen = document.createElement("button");
        loesen.type = "button";
        loesen.className = "wws-btn wws-btn--quiet";
        loesen.textContent = "entfernen";
        loesen.addEventListener("click", function () {
          select.value = "";
          feld.value = "";
          zeigeGewaehlt();
        });
        gewaehlt.appendChild(loesen);
      }
    }
    zeigeGewaehlt();

    var laeuft = null;
    feld.addEventListener("input", function () {
      var suche = feld.value.trim();
      window.clearTimeout(laeuft);
      if (suche.length < 2) {
        liste.hidden = true;
        liste.innerHTML = "";
        return;
      }
      laeuft = window.setTimeout(function () {
        fetch(box.dataset.url + "?q=" + encodeURIComponent(suche))
          .then(function (r) { return r.json(); })
          .then(function (daten) {
            liste.innerHTML = "";
            liste.hidden = false;
            if (daten.treffer.length === 0) {
              // Ohne Hinweis waere nicht unterscheidbar, ob nichts gefunden
              // wurde oder ob die Suche gar nicht gelaufen ist.
              hinweis(liste, "Keine Kundin und kein Kunde gefunden.");
              melde("Keine Treffer.");
              return;
            }
            melde(daten.treffer.length + " Treffer.");
            daten.treffer.forEach(function (kunde) {
              var eintrag = document.createElement("li");
              var knopf = document.createElement("button");
              knopf.type = "button";
              knopf.className = "wws-treffer__eintrag";
              knopf.innerHTML =
                "<strong></strong><span></span>" +
                (kunde.b2b ? "<em class='wws-badge wws-badge--b2b'>B2B</em>" : "");
              knopf.querySelector("strong").textContent = kunde.name;
              knopf.querySelector("span").textContent = kunde.detail;
              knopf.addEventListener("click", function () {
                select.value = String(kunde.id);
                feld.value = "";
                liste.hidden = true;
                liste.innerHTML = "";
                zeigeGewaehlt();
              });
              eintrag.appendChild(knopf);
              liste.appendChild(eintrag);
            });
          })
          .catch(function () {
            liste.innerHTML = "";
            liste.hidden = false;
            hinweis(liste, "Suche gerade nicht möglich. Bitte noch einmal versuchen.");
            melde("Suche fehlgeschlagen.");
          });
      }, 250);
    });
  });

  // --- Filterleiste ---------------------------------------------------------

  document.querySelectorAll("[data-wws-filter]").forEach(function (form) {
    form.querySelectorAll("[data-wws-submit]").forEach(function (feld) {
      feld.addEventListener("change", function () {
        // Die Seite laedt neu - das darf man merken.
        form.setAttribute("aria-busy", "true");
        melde("Liste wird aktualisiert …");
        form.submit();
      });
    });
  });
})();
