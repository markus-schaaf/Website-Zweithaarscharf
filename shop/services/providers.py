"""Austauschbare Image-to-3D-Provider (Strategy-Pattern).

Neuer Provider: Image3DProvider implementieren, in PROVIDERS registrieren,
per Umgebungsvariable IMAGE3D_PROVIDER auswählen.
"""

import abc
import base64
import time
from dataclasses import dataclass

import requests
from django.conf import settings


class ProviderError(Exception):
    pass


@dataclass
class JobResult:
    status: str  # "processing" | "done" | "failed"
    glb_url: str = ""
    thumbnail_url: str = ""
    error: str = ""


class Image3DProvider(abc.ABC):
    name = ""

    @abc.abstractmethod
    def create_job(self, image_bytes_list):
        """Startet die Generierung aus 1-4 Bildern (PNG/JPEG-Bytes), gibt Job-ID zurück."""

    @abc.abstractmethod
    def poll_job(self, job_id):
        """Fragt den Job-Status ab, gibt JobResult zurück."""

    @abc.abstractmethod
    def download(self, url):
        """Lädt eine Ergebnis-Datei herunter, gibt Bytes zurück."""


class MeshyProvider(Image3DProvider):
    """Meshy Multi-Image-to-3D API (https://docs.meshy.ai/en/api/multi-image-to-3d).

    Bilder werden als Base64-Data-URIs übertragen, weil lokale Medien
    keine öffentlich erreichbare URL haben.
    """

    name = "meshy"
    BASE_URL = "https://api.meshy.ai/openapi/v1/multi-image-to-3d"
    MAX_RETRIES = 3

    def _headers(self):
        api_key = settings.MESHY_API_KEY
        if not api_key:
            raise ProviderError(
                "MESHY_API_KEY ist nicht gesetzt (Umgebungsvariable, siehe README.md)."
            )
        return {"Authorization": f"Bearer {api_key}"}

    def _request(self, method, url, **kwargs):
        # Kurzer Retry bei Überlastung/Serverfehlern; alles andere sofort melden
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.request(
                    method, url, headers=self._headers(), timeout=(10, 120), **kwargs
                )
            except requests.RequestException as exc:
                last_error = f"Netzwerkfehler: {exc}"
            else:
                if response.status_code < 400:
                    return response.json()
                last_error = f"HTTP {response.status_code}: {response.text[:300]}"
                if response.status_code not in (429,) and response.status_code < 500:
                    break
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(2 * (attempt + 1))
        raise ProviderError(f"Meshy-API-Fehler: {last_error}")

    def create_job(self, image_bytes_list):
        image_urls = [
            "data:image/png;base64," + base64.b64encode(data).decode("ascii")
            for data in image_bytes_list[:4]
        ]
        payload = {
            "image_urls": image_urls,
            "should_texture": True,
            "ai_model": "latest",
        }
        data = self._request("POST", self.BASE_URL, json=payload)
        job_id = data.get("result")
        if not job_id:
            raise ProviderError(f"Meshy-Antwort ohne Task-ID: {data}")
        return job_id

    def poll_job(self, job_id):
        data = self._request("GET", f"{self.BASE_URL}/{job_id}")
        status = data.get("status", "")
        if status == "SUCCEEDED":
            glb_url = (data.get("model_urls") or {}).get("glb", "")
            if not glb_url:
                return JobResult(status="failed", error="Meshy lieferte keine GLB-URL.")
            return JobResult(
                status="done",
                glb_url=glb_url,
                thumbnail_url=data.get("thumbnail_url", ""),
            )
        if status in ("FAILED", "CANCELED"):
            error = (data.get("task_error") or {}).get("message", "") or status
            return JobResult(status="failed", error=f"Meshy: {error}")
        return JobResult(status="processing")

    def download(self, url):
        # Ergebnis-URLs sind vorsignierte Asset-Links, kein Auth-Header nötig
        response = requests.get(url, timeout=(10, 300))
        if response.status_code >= 400:
            raise ProviderError(f"Download fehlgeschlagen: HTTP {response.status_code}")
        return response.content


class StableFast3DProvider(Image3DProvider):
    """Platzhalter für selbst gehostetes Stable Fast 3D
    (https://github.com/Stability-AI/stable-fast-3d) als spätere Kostenoptimierung.
    """

    name = "stablefast3d"

    def create_job(self, image_bytes_list):
        raise NotImplementedError("TODO: Stable Fast 3D Self-Hosting anbinden")

    def poll_job(self, job_id):
        raise NotImplementedError("TODO: Stable Fast 3D Self-Hosting anbinden")

    def download(self, url):
        raise NotImplementedError("TODO: Stable Fast 3D Self-Hosting anbinden")


PROVIDERS = {
    MeshyProvider.name: MeshyProvider,
    StableFast3DProvider.name: StableFast3DProvider,
}


def get_provider():
    name = settings.IMAGE3D_PROVIDER
    try:
        return PROVIDERS[name]()
    except KeyError:
        raise ProviderError(
            f"Unbekannter 3D-Provider '{name}' (verfügbar: {', '.join(PROVIDERS)})."
        )
