python manage.py makemigrations shop inventory# Warenwirtschaft - Konzept fuer Zweithaar Schaaf / feinhaarmaedchen.de

Planungsdokument. Grundlage: bestehendes Django-Projekt (Katalog, Warenkorb,
Konfigurator, 3D-Vorschau). Ziel: Bestandsfuehrung, Bestellabwicklung, Einkauf
und komfortable Produktpflege im Web-Admin - fuer **Einzelstuecke und
Mengenartikel** bei **geteiltem Bestand zwischen Online-Shop und Studio**.

---

## 1. Systemgrenze (Scope) - was dazu gehoert und was nicht

**Teil dieses Projekts:**
- Produktpflege ueber ein Admin-Konto auf der Website (alle Produkte:
  Peruecken als Einzelstuecke **und** Mengenartikel wie Pflegeprodukte)
- Bestandsfuehrung (verfuegbar / reserviert / verkauft)
- Bestellabwicklung (Warenkorb -> Bestellung erfassen)
- Einkauf/Lieferanten (Wareneingang, Einkaufspreis)
- **Uebergabe der Bestelldaten an ein externes System**

**NICHT Teil dieses Projekts** (liegt im externen System):
- Zahlungsabwicklung / Bezahlwesen
- Rechnungen
- Buchhaltung
- Kasse / TSE

Die Grenze ist also klar: Unser System fuehrt den Bestand und nimmt die
Bestellung auf. Sobald eine Bestellung steht, **uebergeben wir die Daten** an das
externe System, das sich um Zahlung, Rechnung und Buchhaltung kuemmert.

---

## 2. Ausgangslage

**Vorhanden:** `Product` (mit Peruecken-Attributen), `ProductImage`,
`Product3DAsset`, `ConfiguratorGroup/Option`, `Cart/CartItem`.

**Fehlt fuer Warenwirtschaft:**
- Bestand/Lager (Einzelstueck- und Mengenfuehrung)
- Bestellungen (persistente Orders inkl. Status)
- Einkauf: Lieferanten, Einkaufspreise, Wareneingang
- Uebergabe-Schnittstelle zum externen System

---

## 3. Zwei Produktarten sauber abbilden

Damit du **alle** Produkte ueber den Web-Admin pflegen kannst, unterscheidet das
Modell zwei Bestandsarten - eingestellt pro Produkt ueber ein Feld `stock_mode`:

- **Einzelstueck (serialisiert):** z. B. Echthaarperuecken. Jedes physische
  Stueck ist ein eigener Datensatz (`StockItem`) mit Inventarnummer, Einkaufspreis
  und Status. Verfuegbarkeit = Anzahl der Stuecke mit Status "verfuegbar".
- **Mengenartikel:** z. B. Pflegeprodukte. Ein Zaehlfeld `stock_quantity` am
  Produkt, das beim Verkauf reduziert wird. Kein Einzeldatensatz noetig.

So deckt ein einziges Admin beide Welten ab, ohne dass du bei Pflegeprodukten
kuenstlich Einzelstuecke anlegen musst.

---

## 4. Das Kernproblem: geteilter Bestand Online + Studio

Da du **online und im Studio aus demselben Bestand** verkaufst, braucht es
**eine einzige Quelle der Wahrheit** fuer die Verfuegbarkeit. Sonst passiert der
klassische Fehler: Kundin kauft online eine Peruecke, die kurz vorher im Studio
verkauft wurde.

Bei Einzelstuecken ist der **Status des `StockItem`** diese Quelle der Wahrheit:

```
verfuegbar  ->  reserviert  ->  verkauft
                    |
                    -> (Reservierung laeuft ab) -> verfuegbar
```

- **Online-Verkauf:** Beim Checkout wird das Stueck kurz **reserviert**
  (z. B. 30 Min.), nach Abschluss **verkauft**.
- **Studio-Verkauf:** Die Mitarbeiterin markiert das Stueck im **Web-Admin** als
  verkauft. Damit verschwindet es sofort aus dem Online-Shop.

Praktische Konsequenz: **Das Studio muss den Verkauf im System eintragen.** Das
ist der Preis fuer korrekten geteilten Bestand. Bei Mengenartikeln gilt dasselbe
ueber das Zaehlfeld (Studio-Verkauf reduziert die Menge).

---

## 5. Vorgeschlagenes Datenmodell (neue App `inventory`)

Anschlussfaehig an dein bestehendes `Product`:

```python
# shop/models.py - Ergaenzung an Product
class Product(models.Model):
    ...
    STOCK_MODE = [("einzelstueck", "Einzelstueck"), ("menge", "Mengenartikel")]
    stock_mode = models.CharField(max_length=12, choices=STOCK_MODE,
                                  default="einzelstueck")
    stock_quantity = models.PositiveIntegerField("Bestand (Mengenartikel)",
                                                 default=0)  # nur bei "menge"

# inventory/models.py
class Supplier(models.Model):            # Lieferant
    name = models.CharField(max_length=120)
    contact = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)

class StockItem(models.Model):           # ein physisches Einzelstueck
    product = models.ForeignKey("shop.Product", on_delete=models.PROTECT,
                                related_name="stock_items")
    inventory_no = models.CharField("Inventarnummer", max_length=40, unique=True)
    supplier = models.ForeignKey(Supplier, null=True, blank=True,
                                 on_delete=models.SET_NULL)
    purchase_price = models.DecimalField("Einkaufspreis", max_digits=8,
                                         decimal_places=2, null=True, blank=True)
    received_at = models.DateField("Wareneingang", null=True, blank=True)
    # Dimension 1: kaufmaennischer Verfuegbarkeits-Status
    STATUS = [("verfuegbar","Verfuegbar"), ("reserviert","Reserviert"),
              ("verkauft","Verkauft"), ("ausgemustert","Ausgemustert")]
    status = models.CharField(max_length=12, choices=STATUS, default="verfuegbar")
    reserved_for = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="reserved_items")
    reserved_until = models.DateTimeField(null=True, blank=True)
    sold_at = models.DateTimeField(null=True, blank=True)
    sold_channel = models.CharField(max_length=10, blank=True,
                                    choices=[("online","Online"),("studio","Studio")])
    # Dimension 2: handwerkliche Fertigungsphase (eigener Bearbeitungsprozess)
    current_phase = models.ForeignKey("ProductionPhase", null=True, blank=True,
                                      on_delete=models.SET_NULL)

class ProductionPhase(models.Model):     # Katalog der Fertigungsschritte (im Admin pflegbar)
    name = models.CharField("Phase", max_length=60, unique=True)  # z. B. Rohling, Knuepfen, Schnitt, Finish
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

class StockItemEvent(models.Model):      # Historie / Audit-Trail (wer/wann)
    stock_item = models.ForeignKey(StockItem, on_delete=models.CASCADE,
                                   related_name="events")
    kind = models.CharField(max_length=10,
        choices=[("phase","Phase"), ("status","Status")])
    from_value = models.CharField(max_length=60, blank=True)
    to_value = models.CharField(max_length=60, blank=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                   on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

class Order(models.Model):               # aufgenommene Bestellung
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                             on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    STATUS = [("aufgenommen","Aufgenommen"), ("uebergeben","An Fremdsystem uebergeben"),
              ("storniert","Storniert")]
    status = models.CharField(max_length=12, choices=STATUS, default="aufgenommen")
    total = models.DecimalField(max_digits=10, decimal_places=2)
    # + Liefer-/Kontaktdaten (aus accounts.User uebernehmbar)
    export_status = models.CharField(max_length=10, default="pending",
        choices=[("pending","Offen"),("sent","Gesendet"),("failed","Fehlgeschlagen")])
    export_ref = models.CharField(max_length=100, blank=True)  # ID im Fremdsystem

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("shop.Product", on_delete=models.PROTECT)
    stock_item = models.ForeignKey(StockItem, null=True, blank=True,
                                   on_delete=models.PROTECT)  # nur bei Einzelstueck
    quantity = models.PositiveIntegerField(default=1)         # bei Mengenartikel
    price = models.DecimalField(max_digits=8, decimal_places=2)  # Verkaufspreis
```

Kernpunkte:
- `on_delete=PROTECT`: verkaufte Stuecke / Bestellpositionen bleiben als Historie
  erhalten (wichtig, weil das Fremdsystem darauf aufsetzt).
- `OrderItem` deckt beide Faelle ab: Einzelstueck ueber `stock_item`,
  Mengenartikel ueber `product` + `quantity`.
- Der Shop zeigt ein Produkt nur, wenn es verfuegbar ist (Einzelstueck: min. ein
  `StockItem` "verfuegbar"; Mengenartikel: `stock_quantity > 0`).
- **Zwei getrennte Dimensionen** am Stueck: `status` (kaufmaennisch:
  verfuegbar/reserviert/verkauft) und `current_phase` (handwerklich: deine
  Fertigungsschritte). Beide unabhaengig - ein Stueck kann "in Fertigung: Schnitt"
  **und** "reserviert" sein.
- `ProductionPhase` ist ein **im Admin pflegbarer Katalog** deiner Arbeitsschritte -
  du legst die Phasen selbst an und aenderst sie, ohne Code.
- `StockItemEvent` schreibt **jede** Phasen- und Statusaenderung mit (alter Wert,
  neuer Wert, wer, wann) - der lueckenlose Verlauf je Stueck.

---

## 6. Die Uebergabe an das externe System

Das ist die wichtigste neue Schnittstelle. Prinzip: **entkoppelt und
wiederholbar**, damit ein kurzer Ausfall des Fremdsystems keine Bestellung
verliert.

Ablauf:
1. Bestellung wird aufgenommen (Status `aufgenommen`, `export_status=pending`).
2. Ein Hintergrund-Task (Celery, hast du schon) baut die **Uebergabe-Nutzlast**
   und schickt sie ans Fremdsystem.
3. Erfolg -> `export_status=sent`, `export_ref` = ID im Fremdsystem,
   Order-Status `uebergeben`. Fehler -> `failed`, automatischer Wiederholversuch.

Die Uebergabe kapseln wir hinter einer klaren Schnittstelle, damit die konkrete
Technik austauschbar bleibt:

```python
# inventory/services/handover.py
class OrderHandover(abc.ABC):
    @abc.abstractmethod
    def send(self, order) -> str:   # gibt Referenz-ID zurueck
        ...
```

Beispiel-Nutzlast (an das Fremdsystem):

```json
{
  "bestellnummer": "2026-000123",
  "datum": "2026-07-30T14:05:00+02:00",
  "kunde": {"name": "...", "email": "...", "adresse": {...}},
  "positionen": [
    {"artikel": "Echthaarperuecke Bob", "inventarnummer": "P-0042",
     "menge": 1, "einzelpreis": 890.00}
  ],
  "summe": 890.00
}
```

> **Das muss noch geklaert werden (siehe Abschnitt 9):** Wie nimmt dein externes
> System Daten entgegen? REST-API/Webhook, Datei-Export (CSV/JSON), oder E-Mail?
> Danach richtet sich die konkrete `send()`-Implementierung. Bis das feststeht,
> bauen wir gegen die abstrakte Schnittstelle - der Rest funktioniert unabhaengig
> davon.

---

## 7. Produktpflege im Web-Admin

Ziel: Ein Admin-Konto auf der Website, mit dem du **alle** Produkte pflegst. Das
ist ueber Djangos eingebauten Admin bereits weitgehend moeglich (du hast schon
`admin.py` in `shop`). Ergaenzt wird:
- `Product` mit `stock_mode` und (bei Menge) `stock_quantity` direkt editierbar.
- Bei Einzelstuecken: `StockItem` als Inline unter dem Produkt - neue Stuecke
  erfassen (Inventarnummer, Einkaufspreis, Lieferant) mit wenigen Klicks.
- Bestell-Uebersicht mit Status und Uebergabe-Status.

Falls du fuer die Mitarbeiterinnen eine einfachere Oberflaeche als den
Django-Admin willst (z. B. eine schlanke "Verkauf im Studio"-Seite), laesst sich
das aufsetzen - im ersten Schritt reicht aber der Admin.

---

## 8. Empfohlener Phasenplan (MVP zuerst)

**Phase 1 - Bestand (Fundament):** `inventory`-App, `Supplier` + `StockItem`,
`stock_mode`/`stock_quantity` an `Product`, Admin-Pflege inkl. StockItem-Inline.
Shop zeigt nur Verfuegbares. Studio kann Stuecke/Mengen als verkauft buchen.
-> Geteilter Bestand ist damit schon korrekt.

**Phase 2 - Bestellung + Uebergabe:** `Order`/`OrderItem`, Checkout aus dem
Warenkorb, Reservierungslogik (30 Min.), Bestaetigungsmail, Uebergabe ans
Fremdsystem ueber die abstrakte Schnittstelle (konkrete Technik sobald geklaert).

**Phase 3 - Einkauf/Lieferanten:** Wareneingang komfortabel buchen (mehrere
Stuecke auf einmal), Lieferanten-Ansicht, einfache Auswertung (Bestandswert,
Lagerdauer).

---

## 9. Offene Punkte / naechste Entscheidungen

- **Schnittstelle des Fremdsystems:** Wie werden Bestelldaten uebergeben
  (REST/Webhook, Datei-Export, E-Mail)? Gibt es dort eine API oder ein
  Import-Format? Das ist der einzige echte Blocker fuer Phase 2.
- **Reservierungsdauer** online (Vorschlag: 30 Minuten) - passt das?
- **Studio-Oberflaeche:** reicht der Django-Admin, oder braucht es eine
  vereinfachte Verkaufsseite fuer die Mitarbeiterinnen?
- **Fertigungsphasen:** Welche konkreten Arbeitsschritte durchlaeuft eine
  Peruecke bei dir? (z. B. Rohling, Knuepfen, Schnitt, Faerben, Finish,
  Qualitaetskontrolle) - daraus wird der Start-Katalog `ProductionPhase`.

Sobald die Schnittstelle des Fremdsystems geklaert ist, kann ich Phase 1 direkt
als Code (die `inventory`-App mit Modellen, Migrationen und Admin) umsetzen -
Phase 1 haengt nicht von der Schnittstelle ab und koennte sogar sofort starten.
```
