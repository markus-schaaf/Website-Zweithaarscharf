"""Demo-Produktdaten (Platzhalter, kein echtes Sortiment).

Wird nicht mehr direkt gerendert, sondern per `manage.py seed_products`
in die Datenbank uebernommen (shop.Product).

Optionale Attributfelder je Eintrag: hair_length, hair_size, hair_structure,
hair_color, hair_density, cap_type (Peruecken) bzw. content_amount, usage_notes
(Pflege, Zubehoer, Top Holder).
"""

# Konfigurierbare Echthaarperücken: Preis = Rohpreis (Grundausführung).
# Nicht bestellbar — Kauf nur nach persönlichem Beratungstermin.
# Attributwerte sind Beispiele der Grundausführung (frei konfigurierbar).
KONFIG_PRODUCTS = [
    {"display_name": 'Maßperücke „Klassik“', "label": "MASS KLASSIK", "price": "1.290", "badge": "popular",
     "desc": "Unser Einstieg in die Maßanfertigung: Echthaarperücke auf bewährter "
             "Tressenmontur, individuell konfigurierbar in Länge, Farbe, Haardicke und Schnitt. "
             "Der angezeigte Preis ist der Rohpreis der Grundausführung.",
     "hair_length": "Grundausführung 40 cm", "hair_size": "54-56 cm", "hair_structure": "glatt",
     "hair_color": "Naturbraun", "hair_density": "mittel",
     "cap_type": "Tressenmontur (konfigurierbar)"},
    {"display_name": 'Maßperücke „Pur“', "label": "MASS PUR", "price": "1.490", "badge": None,
     "desc": "Federleichte Maßanfertigung mit besonders natürlichem Ansatz. Monofilament-Oberkopf "
             "serienmäßig, alle weiteren Merkmale frei konfigurierbar. Rohpreis der Grundausführung.",
     "hair_length": "Grundausführung 45 cm", "hair_size": "54-56 cm", "hair_structure": "glatt",
     "hair_color": "Naturbraun", "hair_density": "mittel",
     "cap_type": "Monofilament-Oberkopf (konfigurierbar)"},
    {"display_name": 'Maßperücke „Premium handgeknüpft“', "label": "MASS PREMIUM", "price": "1.890", "badge": "new",
     "desc": "Vollständig handgeknüpfte Echthaarperücke in Manufakturqualität — jede Strähne einzeln "
             "verarbeitet, unsichtbarer Filmansatz möglich. Rohpreis der Grundausführung.",
     "hair_length": "Grundausführung 50 cm", "hair_size": "56-58 cm", "hair_structure": "leicht gewellt",
     "hair_color": "Dunkelbraun", "hair_density": "voll",
     "cap_type": "Vollmontur handgeknüpft (konfigurierbar)"},
    {"display_name": 'Maßhaarteil „Volumen“', "label": "MASS HAARTEIL", "price": "890", "badge": None,
     "desc": "Individuell gefertigtes Echthaar-Haarteil zur Verdichtung von Oberkopf und Scheitel. "
             "Größe, Farbe und Haardicke werden exakt auf Ihr Eigenhaar abgestimmt. Rohpreis der Grundausführung.",
     "hair_length": "Grundausführung 35 cm", "hair_size": "Oberkopf/Scheitel", "hair_structure": "glatt",
     "hair_color": "Naturbraun", "hair_density": "mittel",
     "cap_type": "Integrationsmontur (konfigurierbar)"},
]

# Fertig konfigurierte Echthaarperücken im Bestand — sofort bestellbar.
BESTAND_PRODUCTS = [
    {"display_name": 'Perücke „Classic“', "label": "CLASSIC", "price": "890", "badge": "popular",
     "desc": "Zeitloses, schulterlanges Modell mit natürlichem Ansatz und glattem Haar.",
     "hair_length": "ca. 40 cm", "hair_size": "54-56 cm", "hair_structure": "glatt",
     "hair_color": "Naturbraun", "hair_density": "mittel",
     "cap_type": "Tressenmontur mit Monofilament-Scheitel"},
    {"display_name": 'Perücke „Long Layers“', "label": "LONG LAYERS", "price": "1.190", "badge": "new",
     "desc": "Voluminöses Langhaarmodell mit fein gestuften Strähnen.",
     "hair_length": "ca. 55 cm", "hair_size": "56-58 cm", "hair_structure": "glatt, gestuft",
     "hair_color": "Dunkelbraun", "hair_density": "voll",
     "cap_type": "Monofilament mit Filmansatz"},
    {"display_name": 'Perücke „Bob Chic“', "label": "BOB CHIC", "price": "950", "badge": None,
     "desc": "Kinnlanger, glatter Bob mit klarer Kontur.",
     "hair_length": "ca. 25 cm", "hair_size": "52-54 cm", "hair_structure": "glatt",
     "hair_color": "Dunkelbraun", "hair_density": "mittel",
     "cap_type": "Tressenmontur"},
    {"display_name": 'Perücke „Curly Volume“', "label": "CURLY VOLUME", "price": "1.290", "badge": None,
     "desc": "Lebendige Locken in warmem Rotbraun für besonders viel Fülle.",
     "hair_length": "ca. 45 cm", "hair_size": "54-56 cm", "hair_structure": "lockig",
     "hair_color": "Rotbraun", "hair_density": "voll",
     "cap_type": "Monofilament-Oberkopf"},
    {"display_name": 'Perücke „Soft Waves“', "label": "SOFT WAVES", "price": "990", "badge": None,
     "desc": "Aschblonde, mittellange Wellen für einen weichen, natürlichen Look.",
     "hair_length": "ca. 35 cm", "hair_size": "54-56 cm", "hair_structure": "gewellt",
     "hair_color": "Aschblond", "hair_density": "mittel",
     "cap_type": "Tressenmontur mit Monofilament-Scheitel"},
    {"display_name": 'Perücke „Silver Elegance“', "label": "SILVER ELEGANCE", "price": "1.050", "badge": None,
     "desc": "Elegantes silbergraues Modell, schulterlang und glatt.",
     "hair_length": "ca. 40 cm", "hair_size": "54-56 cm", "hair_structure": "glatt",
     "hair_color": "Silbergrau", "hair_density": "mittel",
     "cap_type": "Monofilament mit Filmansatz"},
    {"display_name": 'Perücke „Honey Blonde“', "label": "HONEY BLONDE", "price": "1.150", "badge": None,
     "desc": "Honigblondes, langes Modell mit seidigem Glanz.",
     "hair_length": "ca. 50 cm", "hair_size": "56-58 cm", "hair_structure": "glatt",
     "hair_color": "Honigblond", "hair_density": "voll",
     "cap_type": "Monofilament-Oberkopf"},
    {"display_name": 'Perücke „Chestnut Layers“', "label": "CHESTNUT LAYERS", "price": "980", "badge": None,
     "desc": "Kastanienbraune, gestufte Längen für natürliche Bewegung.",
     "hair_length": "ca. 40 cm", "hair_size": "54-56 cm", "hair_structure": "glatt, gestuft",
     "hair_color": "Kastanienbraun", "hair_density": "mittel",
     "cap_type": "Tressenmontur"},
    {"display_name": 'Perücke „Platinum Pixie“', "label": "PLATINUM PIXIE", "price": "720", "badge": "new",
     "desc": "Kurzes platinblondes Modell für einen mutigen, modernen Auftritt.",
     "hair_length": "ca. 15 cm", "hair_size": "52-54 cm", "hair_structure": "glatt, texturiert",
     "hair_color": "Platinblond", "hair_density": "leicht",
     "cap_type": "Tressenmontur mit Filmansatz"},
    {"display_name": 'Perücke „Mahogany Waves“', "label": "MAHOGANY WAVES", "price": "1.020", "badge": None,
     "desc": "Mahagonifarbene Wellen mit warmem Rotschimmer.",
     "hair_length": "ca. 40 cm", "hair_size": "54-56 cm", "hair_structure": "gewellt",
     "hair_color": "Mahagoni", "hair_density": "mittel",
     "cap_type": "Monofilament-Scheitel"},
    {"display_name": 'Perücke „Copper Curls“', "label": "COPPER CURLS", "price": "1.080", "badge": None,
     "desc": "Kupferrote Locken, mittellang, für einen lebendigen Auftritt.",
     "hair_length": "ca. 35 cm", "hair_size": "54-56 cm", "hair_structure": "lockig",
     "hair_color": "Kupferrot", "hair_density": "voll",
     "cap_type": "Tressenmontur"},
    {"display_name": 'Perücke „Ash Bob“', "label": "ASH BOB", "price": "940", "badge": None,
     "desc": "Aschbrauner Bob mit klarer, pflegeleichter Form.",
     "hair_length": "ca. 25 cm", "hair_size": "52-54 cm", "hair_structure": "glatt",
     "hair_color": "Aschbraun", "hair_density": "mittel",
     "cap_type": "Tressenmontur"},
    {"display_name": 'Perücke „Golden Layers“', "label": "GOLDEN LAYERS", "price": "1.220", "badge": None,
     "desc": "Goldblonde, lange Strähnen mit feinen Stufen.",
     "hair_length": "ca. 50 cm", "hair_size": "56-58 cm", "hair_structure": "glatt, gestuft",
     "hair_color": "Goldblond", "hair_density": "voll",
     "cap_type": "Monofilament mit Filmansatz"},
    {"display_name": 'Perücke „Espresso Straight“', "label": "ESPRESSO STRAIGHT", "price": "1.010", "badge": None,
     "desc": "Tiefbraunes, glattes Langhaarmodell mit intensivem Glanz.",
     "hair_length": "ca. 50 cm", "hair_size": "56-58 cm", "hair_structure": "glatt",
     "hair_color": "Tiefbraun", "hair_density": "voll",
     "cap_type": "Monofilament-Oberkopf"},
    {"display_name": 'Perücke „Rose Gold Waves“', "label": "ROSE GOLD WAVES", "price": "1.140", "badge": "new",
     "desc": "Rosegüldene Wellen für einen besonders femininen Look.",
     "hair_length": "ca. 40 cm", "hair_size": "54-56 cm", "hair_structure": "gewellt",
     "hair_color": "Roségold", "hair_density": "mittel",
     "cap_type": "Monofilament-Scheitel"},
    {"display_name": 'Perücke „Caramel Balayage“', "label": "CARAMEL BALAYAGE", "price": "1.090", "badge": None,
     "desc": "Karamellfarbenes Balayage, mittellang mit sanftem Verlauf.",
     "hair_length": "ca. 35 cm", "hair_size": "54-56 cm", "hair_structure": "leicht gewellt",
     "hair_color": "Karamell-Balayage", "hair_density": "mittel",
     "cap_type": "Monofilament mit Filmansatz"},
    {"display_name": 'Perücke „Midnight Black“', "label": "MIDNIGHT BLACK", "price": "1.030", "badge": None,
     "desc": "Tiefschwarzes, glattes Modell in voller Länge.",
     "hair_length": "ca. 55 cm", "hair_size": "56-58 cm", "hair_structure": "glatt",
     "hair_color": "Tiefschwarz", "hair_density": "voll",
     "cap_type": "Tressenmontur mit Monofilament-Scheitel"},
    {"display_name": 'Perücke „Champagne Blonde“', "label": "CHAMPAGNE BLONDE", "price": "1.060", "badge": None,
     "desc": "Champagnerblondes, schulterlanges Modell mit feinem Schimmer.",
     "hair_length": "ca. 40 cm", "hair_size": "54-56 cm", "hair_structure": "glatt",
     "hair_color": "Champagnerblond", "hair_density": "mittel",
     "cap_type": "Monofilament-Scheitel"},
]

PFLEGE_PRODUCTS = [
    {"display_name": "Perücken-Shampoo mild", "label": "SHAMPOO MILD", "price": "19", "badge": "popular",
     "desc": "Mildes Spezialshampoo für Echthaarperücken, reinigt schonend und erhält den Glanz.",
     "content_amount": "250 ml",
     "usage_notes": "Perücke in lauwarmem Wasser mit einer kleinen Menge Shampoo sanft bewegen, "
                    "nicht reiben. Gründlich ausspülen und auf dem Ständer trocknen lassen."},
    {"display_name": "Conditioner & Intensivkur", "label": "CONDITIONER", "price": "24", "badge": None,
     "desc": "Pflegende Kur für geschmeidiges Echthaar, beugt Austrocknung und Knotenbildung vor.",
     "content_amount": "200 ml",
     "usage_notes": "Nach der Wäsche in die Längen einarbeiten, 5–10 Minuten einwirken lassen "
                    "und lauwarm ausspülen. Den Ansatzbereich aussparen."},
    {"display_name": "Pflegespray Echthaar", "label": "PFLEGESPRAY", "price": "21", "badge": "new",
     "desc": "Leichtes Sprühspray für Feuchtigkeit und Kämmbarkeit zwischen den Wäschen.",
     "content_amount": "150 ml",
     "usage_notes": "Aus ca. 20 cm Entfernung auf das trockene oder handtuchfeuchte Haar sprühen "
                    "und mit einer Perückenbürste durchkämmen. Nicht ausspülen."},
]

# Perücken Zubehör (kein Pflegemittel) — sofort bestellbar.
ZUBEHOER_PRODUCTS = [
    {"display_name": "Perückenständer Holz", "label": "STAENDER", "price": "29", "badge": "popular",
     "desc": "Formstabiler Holzständer zur schonenden Aufbewahrung und Trocknung Ihrer Perücke.",
     "content_amount": "1 Stück, Höhe ca. 36 cm",
     "usage_notes": "Perücke nach dem Tragen oder Waschen locker über den Ständer legen — "
                    "so behalten Montur und Frisur ihre Form."},
    {"display_name": "Perückenbürste antistatisch", "label": "BUERSTE", "price": "15", "badge": None,
     "desc": "Spezialbürste mit abgerundeten Borsten, schont Ansatz und Tressen.",
     "content_amount": "1 Stück",
     "usage_notes": "Haar von den Spitzen zum Ansatz hin strähnenweise entwirren, "
                    "am Ansatz nur mit leichtem Druck arbeiten."},
    {"display_name": "Antirutsch-Halteband", "label": "HALTEBAND", "price": "12", "badge": None,
     "desc": "Elastisches Halteband für sicheren, komfortablen Sitz der Perücke den ganzen Tag.",
     "content_amount": "1 Stück, längenverstellbar",
     "usage_notes": "Unter der Perücke am Hinterkopf anlegen und auf angenehme Spannung einstellen."},
    {"display_name": "Aufbewahrungsnetz", "label": "HAARNETZ", "price": "8", "badge": None,
     "desc": "Feines Netz zum Schutz der Frisur bei Aufbewahrung und Transport.",
     "content_amount": "2 Stück",
     "usage_notes": "Perücke locker über den Kopf des Ständers ziehen und mit dem Netz umschließen."},
]

# Top Holder — Halterungen und Montageköpfe für Präsentation und Lagerung.
TOPHOLDER_PRODUCTS = [
    {"display_name": "Top Holder Basic", "label": "HOLDER BASIC", "price": "34", "badge": "popular",
     "desc": "Standfeste Tischhalterung für die sichere Präsentation und Lagerung einer Perücke.",
     "content_amount": "1 Stück, Standfuß Ø ca. 14 cm",
     "usage_notes": "Halterung auf eine ebene Fläche stellen und die Perücke faltenfrei aufsetzen."},
    {"display_name": "Top Holder Deluxe", "label": "HOLDER DELUXE", "price": "49", "badge": "new",
     "desc": "Hochwertige Halterung mit gepolstertem Kopf für formschonende Langzeitlagerung.",
     "content_amount": "1 Stück, höhenverstellbar",
     "usage_notes": "Höhe einstellen, Perücke aufsetzen und Ansatzkontur leicht andrücken."},
    {"display_name": "Top Holder Reise", "label": "HOLDER REISE", "price": "27", "badge": None,
     "desc": "Zusammenklappbare Reisehalterung — leicht und platzsparend für unterwegs.",
     "content_amount": "1 Stück, faltbar",
     "usage_notes": "Vor Gebrauch aufklappen und einrasten; nach Gebrauch flach zusammenlegen."},
]

# Nur fuer B2B-Kunden sichtbar (audience "b2b")
ROHLING_PRODUCTS = [
    {"display_name": "Echthaar-Rohling 30 cm, naturbraun", "label": "ROHLING 30 BRAUN", "price": "240", "badge": None,
     "audience": "b2b",
     "desc": "Unbehandeltes europäisches Echthaar auf Tresse, ideal für Konfektion und Maßanfertigung.",
     "hair_length": "30 cm", "hair_size": "Tresse ca. 90 cm", "hair_structure": "glatt",
     "hair_color": "Naturbraun", "hair_density": "mittel", "cap_type": "Tresse"},
    {"display_name": "Echthaar-Rohling 40 cm, hellblond", "label": "ROHLING 40 BLOND", "price": "320", "badge": "popular",
     "audience": "b2b",
     "desc": "Unbehandelte, sortenreine Knüpfware in Hellblond, geeignet zum Färben und Tönen.",
     "hair_length": "40 cm", "hair_size": "Tresse ca. 100 cm", "hair_structure": "glatt",
     "hair_color": "Hellblond", "hair_density": "mittel", "cap_type": "Tresse"},
    {"display_name": "Echthaar-Rohling 50 cm, dunkelbraun", "label": "ROHLING 50 DUNKEL", "price": "410", "badge": None,
     "audience": "b2b",
     "desc": "Lange, gleichmäßig gezogene Strähnen für hochwertige Vollperücken und Haarteile.",
     "hair_length": "50 cm", "hair_size": "Tresse ca. 110 cm", "hair_structure": "glatt",
     "hair_color": "Dunkelbraun", "hair_density": "voll", "cap_type": "Tresse"},
    {"display_name": "Echthaar-Rohling 55 cm, grau meliert", "label": "ROHLING 55 GRAU", "price": "460", "badge": None,
     "audience": "b2b",
     "desc": "Natürlich grau meliertes Echthaar, unbehandelt, für authentische Grauverläufe.",
     "hair_length": "55 cm", "hair_size": "Tresse ca. 110 cm", "hair_structure": "glatt",
     "hair_color": "Grau meliert", "hair_density": "mittel", "cap_type": "Tresse"},
    {"display_name": "Echthaar-Rohling 60 cm, schwarz", "label": "ROHLING 60 SCHWARZ", "price": "520", "badge": "new",
     "audience": "b2b",
     "desc": "Doppelt gezogene Premium-Qualität in Tiefschwarz für anspruchsvolle Maßanfertigungen.",
     "hair_length": "60 cm", "hair_size": "Tresse ca. 120 cm", "hair_structure": "glatt",
     "hair_color": "Tiefschwarz", "hair_density": "voll", "cap_type": "Tresse"},
]

# Konfigurator-Katalog: gilt global fuer alle konfigurierbaren Peruecken.
# Erste Option je Gruppe = Grundausfuehrung (Aufpreis 0), wird vorausgewaehlt.
CONFIGURATOR_GROUPS = [
    {"name": "Haarlänge", "options": [
        ("30 cm", "0"), ("40 cm", "150"), ("50 cm", "290"), ("60 cm", "450"),
    ]},
    {"name": "Haarfarbe", "options": [
        ("Naturton (braun/schwarz)", "0"), ("Grau meliert", "90"),
        ("Blondton", "120"), ("Balayage / Wunschfarbe", "180"),
    ]},
    {"name": "Haardicke", "options": [
        ("Standard", "0"), ("Dicht", "160"), ("Extra dicht", "290"),
    ]},
    {"name": "Haarstruktur", "options": [
        ("Glatt", "0"), ("Gewellt", "80"), ("Lockig", "150"),
    ]},
    {"name": "Montur / Cap", "options": [
        ("Tresse", "0"), ("Filmansatz", "120"), ("Monofilament", "180"),
        ("Vollmontur handgeknüpft", "350"),
    ]},
]
