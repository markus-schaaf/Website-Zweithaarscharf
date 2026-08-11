# Deployment-Anleitung — Zweithaar Schaaf Online-Shop

Schritt-für-Schritt-Anleitung, um den Django-Shop auf einem **STRATO VPS M**
(Ubuntu, 4 vCores, 4 GB RAM) produktiv zu betreiben.

Stack: **Ubuntu 24.04 LTS · PostgreSQL · Gunicorn · Nginx · Redis + Celery · Let's Encrypt (TLS)**

> Diese Anleitung ist auf dein konkretes Projekt zugeschnitten
> (Repo `markus-schaaf/Website-Zweithaarscharf`, Settings-Modul
> `zweithaarschaaf.settings`, WSGI `zweithaarschaaf.wsgi`).

---

## Übersicht der Phasen

| Phase | Was | Wo |
|-------|-----|-----|
| 0 | Code für Produktion vorbereiten (PostgreSQL, gunicorn) | **lokal** |
| 1 | Server-Grundeinrichtung, Sicherheit | SSH auf VPS |
| 2 | System-Pakete, PostgreSQL, Redis | SSH auf VPS |
| 3 | Projekt deployen, `.env`, Datenbank migrieren | SSH auf VPS |
| 4 | Gunicorn + Celery als systemd-Dienste | SSH auf VPS |
| 5 | Nginx als Reverse Proxy | SSH auf VPS |
| 6 | TLS-Zertifikat (HTTPS) | SSH auf VPS |
| 7 | Strato-Domain auf den Server zeigen | Strato-Login |
| 8 | Backups einrichten | SSH auf VPS |

---

## Phase 0 — Code lokal für Produktion vorbereiten

Diese drei Änderungen machst du **auf deinem PC**, testest kurz und pushst zu GitHub.
Der Server holt sich den Code dann per `git clone`.

### 0.1 PostgreSQL in `settings.py` ergänzen

Aktuell ist die Datenbank fest auf SQLite verdrahtet. Ersetze in
`zweithaarschaaf/settings.py` den `DATABASES`-Block durch eine env-basierte
Variante — so bleibt SQLite lokal, PostgreSQL greift nur, wenn die Variablen
gesetzt sind:

```python
# Database
if os.environ.get("DJANGO_DB_NAME"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ["DJANGO_DB_NAME"],
            "USER": os.environ["DJANGO_DB_USER"],
            "PASSWORD": os.environ["DJANGO_DB_PASSWORD"],
            "HOST": os.environ.get("DJANGO_DB_HOST", "127.0.0.1"),
            "PORT": os.environ.get("DJANGO_DB_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
```

### 0.2 `requirements.txt` ergänzen

Füge die zwei fehlenden Produktions-Pakete hinzu:

```
gunicorn==23.0.0
psycopg[binary]==3.2.9
```

### 0.3 `.env.example` ergänzen

Trag die neuen DB-Variablen als Vorlage ein (Werte kommen später auf dem Server):

```
# PostgreSQL (Produktion)
DJANGO_DB_NAME=zweithaar
DJANGO_DB_USER=zweithaar
DJANGO_DB_PASSWORD=hier-ein-starkes-passwort
DJANGO_DB_HOST=127.0.0.1
DJANGO_DB_PORT=5432
```

### 0.4 Committen und pushen

```
git add zweithaarschaaf/settings.py requirements.txt .env.example
git commit -m "Produktion: PostgreSQL-Konfiguration und Gunicorn"
git push
```

---

## Phase 1 — Server-Grundeinrichtung

### 1.1 Als root per SSH einloggen

Die Zugangsdaten (IP-Adresse, root-Passwort) stehen in deinem STRATO-Login unter
*Server → Zugangsdaten*. Betriebssystem: falls noch nicht geschehen, im
STRATO-Panel **Ubuntu 24.04 LTS** installieren.

```
ssh root@DEINE-SERVER-IP
```

### 1.2 System aktualisieren

```
apt update && apt upgrade -y
```

### 1.3 Nicht-root-Benutzer mit sudo anlegen

Aus Sicherheitsgründen arbeitest du nicht als root:

```
adduser deploy
usermod -aG sudo deploy
```

Danach ausloggen und als `deploy` neu einloggen:

```
ssh deploy@DEINE-SERVER-IP
```

### 1.4 Firewall aktivieren

```
sudo apt install -y ufw
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
```

---

## Phase 2 — System-Pakete, PostgreSQL, Redis

### 2.1 Benötigte Pakete installieren

```
sudo apt install -y python3-venv python3-dev build-essential \
    libpq-dev git nginx postgresql redis-server \
    libgl1 libglib2.0-0
```

> `libgl1` / `libglib2.0-0` werden von **onnxruntime/rembg** (3D-Vorschau)
> gebraucht. `libpq-dev` ist für den PostgreSQL-Treiber.

### 2.2 PostgreSQL-Datenbank und Benutzer anlegen

```
sudo -u postgres psql
```

Im psql-Prompt (Passwort durch ein starkes ersetzen):

```sql
CREATE DATABASE zweithaar;
CREATE USER zweithaar WITH PASSWORD 'DEIN-STARKES-PASSWORT';
ALTER ROLE zweithaar SET client_encoding TO 'utf8';
ALTER ROLE zweithaar SET default_transaction_isolation TO 'read committed';
ALTER ROLE zweithaar SET timezone TO 'Europe/Berlin';
GRANT ALL PRIVILEGES ON DATABASE zweithaar TO zweithaar;
\q
```

### 2.3 Redis und PostgreSQL laufen als Dienst

Beide starten automatisch. Kurz prüfen:

```
sudo systemctl status postgresql --no-pager
sudo systemctl status redis-server --no-pager
```

---

## Phase 3 — Projekt deployen

### 3.1 Code klonen

```
cd /home/deploy
git clone https://github.com/markus-schaaf/Website-Zweithaarscharf.git app
cd app
```

### 3.2 Virtuelle Umgebung und Abhängigkeiten

```
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> Der erste Start der 3D-Funktion lädt zusätzlich das rembg-ML-Modell
> (~170 MB) nach `~/.u2net` herunter.

### 3.3 `.env`-Datei auf dem Server anlegen

```
nano .env
```

Inhalt (Werte anpassen — SECRET_KEY neu erzeugen, siehe unten):

```
DJANGO_SECRET_KEY=LANGER-ZUFALLSSTRING
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=www.feinhaarmaedchen.de,feinhaarmaedchen.de

DJANGO_DB_NAME=zweithaar
DJANGO_DB_USER=zweithaar
DJANGO_DB_PASSWORD=DEIN-STARKES-PASSWORT
DJANGO_DB_HOST=127.0.0.1
DJANGO_DB_PORT=5432

DJANGO_EMAIL_HOST=smtp.strato.de
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_HOST_USER=noreply@feinhaarmaedchen.de
DJANGO_EMAIL_HOST_PASSWORD=DEIN-MAIL-PASSWORT
DJANGO_EMAIL_USE_TLS=1
DJANGO_DEFAULT_FROM_EMAIL=noreply@feinhaarmaedchen.de
ZS_CONTACT_EMAIL=info@feinhaarmaedchen.de

# 3D-Vorschau in Produktion: echter Hintergrund-Worker
CELERY_TASK_ALWAYS_EAGER=0
CELERY_BROKER_URL=redis://localhost:6379/0
MESHY_API_KEY=DEIN-MESHY-KEY
IMAGE3D_PROVIDER=meshy
```

Einen sicheren SECRET_KEY erzeugst du so:

```
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Damit die App die Variablen liest, exportierst du sie beim Start. Am saubersten
über die systemd-Dienste (Phase 4) mit `EnvironmentFile=`. Zum manuellen Testen:

```
set -a; source .env; set +a
```

### 3.4 Datenbank migrieren, Static sammeln, Admin anlegen

```
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 3.5 Produktbilder (`media/`) übertragen

Deine Produktbilder in `media/` (~21 MB) liegen **nicht** im Git-Repo
(per `.gitignore` ausgeschlossen). Übertrage sie von deinem PC aus per `rsync`
(im Projektordner ausführen, Windows: Git Bash oder WSL):

```
rsync -avz media/ deploy@DEINE-SERVER-IP:/home/deploy/app/media/
```

> Alternativ mit `scp -r media/ deploy@IP:/home/deploy/app/media/`.
> Die Datenbank (SQLite, nur 240 KB) muss **nicht** übertragen werden — du hast
> oben ja frisch nach PostgreSQL migriert. Produkte pflegst du danach im Admin
> bzw. über deinen bestehenden Import ein.

### 3.6 Kurztest

```
python manage.py runserver 0.0.0.0:8000
```

Im Browser `http://DEINE-SERVER-IP:8000` — läuft die Seite, mit `Strg+C`
beenden. (Für den Dauerbetrieb kommt jetzt Gunicorn.)

---

## Phase 4 — Gunicorn + Celery als Dienste

### 4.1 Gunicorn-Dienst

```
sudo nano /etc/systemd/system/gunicorn.service
```

```ini
[Unit]
Description=Gunicorn für Zweithaar Schaaf
After=network.target postgresql.service

[Service]
User=deploy
Group=www-data
WorkingDirectory=/home/deploy/app
EnvironmentFile=/home/deploy/app/.env
ExecStart=/home/deploy/app/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/home/deploy/app/gunicorn.sock \
    zweithaarschaaf.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

> **3 Worker** sind für VPS M (4 GB) ein guter Startwert. Nicht höher drehen —
> jeder Worker kostet RAM, und PostgreSQL + Redis + Celery brauchen auch welches.

### 4.2 Celery-Dienst (für die 3D-Vorschau)

```
sudo nano /etc/systemd/system/celery.service
```

```ini
[Unit]
Description=Celery Worker für Zweithaar Schaaf
After=network.target redis-server.service

[Service]
User=deploy
Group=www-data
WorkingDirectory=/home/deploy/app
EnvironmentFile=/home/deploy/app/.env
ExecStart=/home/deploy/app/venv/bin/celery -A zweithaarschaaf worker \
    --concurrency=1 -l info
Restart=always

[Install]
WantedBy=multi-user.target
```

> **`--concurrency=1`** ist Absicht: Die 3D-Generierung (rembg + onnxruntime)
> ist speicherhungrig. Auf 4 GB RAM willst du nur einen solchen Job gleichzeitig.
> Unter Linux ist der Standard-Pool korrekt — das `--pool=solo` aus der README
> gilt nur für Windows.

### 4.3 Dienste starten

```
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn celery
sudo systemctl status gunicorn --no-pager
sudo systemctl status celery --no-pager
```

Nach jedem Code-Update (`git pull`) die Dienste neu laden:

```
cd /home/deploy/app && source venv/bin/activate
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn celery
```

---

## Phase 5 — Nginx als Reverse Proxy

```
sudo nano /etc/nginx/sites-available/zweithaar
```

```nginx
server {
    listen 80;
    server_name www.feinhaarmaedchen.de feinhaarmaedchen.de;

    client_max_body_size 25M;   # Foto-Uploads für die 3D-Vorschau

    location /media/ {
        alias /home/deploy/app/media/;
        expires 30d;
    }

    # /static/ liefert WhiteNoise direkt aus der App — kein alias nötig.

    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/home/deploy/app/gunicorn.sock;
    }
}
```

> Der Header `X-Forwarded-Proto` ist wichtig: dein `settings.py` wertet ihn über
> `SECURE_PROXY_SSL_HEADER` aus, damit Django HTTPS korrekt erkennt.

Aktivieren und Nginx neu laden:

```
sudo ln -s /etc/nginx/sites-available/zweithaar /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

---

## Phase 6 — TLS-Zertifikat (HTTPS)

**Erst nachdem die Domain auf den Server zeigt (Phase 7).** Danach:

```
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d feinhaarmaedchen.de -d www.feinhaarmaedchen.de
```

Certbot passt die Nginx-Config automatisch an und richtet die Auto-Verlängerung
ein. Ab jetzt greifen auch die HTTPS-Sicherheitseinstellungen aus deiner
`settings.py` (SSL-Redirect, HSTS, sichere Cookies).

---

## Phase 7 — Strato-Domain auf den Server zeigen

Im **STRATO-Login → Domainverwaltung → feinhaarmaedchen.de → DNS-Einstellungen**:

| Typ | Name | Wert |
|-----|------|------|
| A | `@` (bzw. leer) | DEINE-SERVER-IP |
| A | `www` | DEINE-SERVER-IP |

Speichern. Die Umstellung (DNS-Propagation) kann einige Minuten bis Stunden
dauern. Prüfen mit `ping feinhaarmaedchen.de` — sobald deine Server-IP erscheint,
ist es aktiv, und du kannst Phase 6 (TLS) ausführen.

---

## Phase 8 — Backups einrichten

Backups sind bei STRATO **nicht** enthalten — gerade bei Bestelldaten wichtig.
Tägliches PostgreSQL-Backup per Cronjob:

```
crontab -e
```

Zeile hinzufügen (Backup jede Nacht um 3 Uhr, 14 Tage Aufbewahrung):

```
0 3 * * * pg_dump -U zweithaar zweithaar | gzip > /home/deploy/backups/db-$(date +\%F).sql.gz && find /home/deploy/backups -name 'db-*.sql.gz' -mtime +14 -delete
```

Vorher Ordner anlegen: `mkdir -p /home/deploy/backups`. Die `media/`-Bilder
sicherst du am besten zusätzlich regelmäßig auf einen externen Speicher
(z. B. STRATO HiDrive) per `rsync`.

---

## Schnell-Checkliste

- [ ] Phase 0: PostgreSQL-Config + gunicorn/psycopg lokal ergänzt, gepusht
- [ ] VPS mit Ubuntu 24.04, `deploy`-User, Firewall aktiv
- [ ] PostgreSQL-DB + Redis laufen
- [ ] Code geklont, venv, `.env` gesetzt, `migrate` + `collectstatic` ok
- [ ] `media/` per rsync übertragen
- [ ] Gunicorn + Celery als Dienst aktiv
- [ ] Nginx läuft, Seite über IP erreichbar
- [ ] Strato-DNS auf Server-IP
- [ ] TLS via certbot, HTTPS erzwungen
- [ ] Backup-Cronjob aktiv

---

## Häufige Stolpersteine

- **500-Fehler nach Deploy:** Meist fehlende/falsche `.env`-Variable oder
  `DJANGO_ALLOWED_HOSTS` passt nicht zur Domain. Log ansehen:
  `sudo journalctl -u gunicorn -n 50`.
- **Statische Dateien fehlen (kein CSS):** `collectstatic` vergessen oder
  `DEBUG=0` ohne WhiteNoise-Manifest — nach jedem Deploy `collectstatic` laufen
  lassen.
- **3D-Generierung hängt/scheitert:** Celery-Dienst prüfen
  (`sudo systemctl status celery`), `MESHY_API_KEY` gesetzt? Beim allerersten
  Lauf lädt rembg das 170-MB-Modell — das dauert.
- **RAM wird knapp:** `htop` installieren und beobachten. Wenn die 3D-Funktion
  den Server ausbremst, ist sie der Kandidat zum Auslagern — sonst reicht VPS M
  für deinen Shop gut aus.
```

