# Zweithaar Schaaf — Online-Shop

Django-Shop für Perücken, Haarteile und Pflegeprodukte.

## Lokale Entwicklung

```
venv\Scripts\pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## 3D-Produktvorschau

Staff-Nutzer (Rolle "All Power" oder "Administrator") können unter
`Konto → Produktverwaltung → 3D` pro Produkt 1-4 Fotos hochladen. Die Pipeline:

1. Hintergrund entfernen (rembg, lokal)
2. Freisteller auf neutralen Dummy-Kopf setzen (Pillow;
   Bild: `Website_template/tasty/images/3d/dummy-head.png`, austauschbar)
3. Image-to-3D beim externen Provider (Standard: Meshy), GLB-Download
4. Freigabe-Schalter: erst danach sehen Kunden das drehbare Modell
   (`<model-viewer>`, lokal eingebunden) auf der Produktdetailseite

### Umgebungsvariablen

| Variable | Bedeutung |
|---|---|
| `MESHY_API_KEY` | API-Key von https://www.meshy.ai (Pflicht für Generierung) |
| `IMAGE3D_PROVIDER` | 3D-Dienst, Standard `meshy`; `stablefast3d` ist als Stub vorbereitet |
| `CELERY_TASK_ALWAYS_EAGER` | `1` (Standard) = Tasks laufen synchron im Request, kein Redis nötig. In Produktion `0` setzen |
| `CELERY_BROKER_URL` | Redis-URL für Produktion, z. B. `redis://localhost:6379/0` |

### Provider wechseln

Neuen Adapter in `shop/services/providers.py` implementieren
(Interface `Image3DProvider`), in `PROVIDERS` registrieren und per
`IMAGE3D_PROVIDER` auswählen. `StableFast3DProvider` ist als Platzhalter für
selbst gehostetes Stable Fast 3D (Kostenoptimierung) angelegt.

### Celery/Redis lokal (Windows)

Für die Entwicklung nicht nötig (Eager-Modus, siehe oben) — der Upload-Request
blockiert dann allerdings, bis die Generierung fertig ist (Minuten).

Echtes Hintergrund-Setup:

1. Redis starten, z. B. Docker Desktop: `docker run -p 6379:6379 redis`
   (oder Memurai als nativer Windows-Dienst)
2. `CELERY_TASK_ALWAYS_EAGER=0` setzen
3. Worker starten (Windows braucht `--pool=solo`):
   `venv\Scripts\celery -A zweithaarschaaf worker --pool=solo -l info`

### Hinweise

- Beim ersten rembg-Lauf wird das ML-Modell (~170 MB) nach
  `%USERPROFILE%\.u2net` heruntergeladen.
- GLB-Dateien landen im normalen Media-Storage (`media/products/3d/`). Der
  Code nutzt nur die Django-Storage-API — für S3 später `django-storages`
  installieren und `STORAGES["default"]` umstellen, kein Codeumbau nötig.
- In Produktion muss der Webserver `/media/` ausliefern (Whitenoise bedient
  nur `/static/`).
