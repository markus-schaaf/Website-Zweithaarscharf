import logging
import time

from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile

logger = logging.getLogger(__name__)


@shared_task
def generate_3d_model(asset_id):
    """Erzeugt aus den Quellbildern eines Product3DAsset ein GLB-Modell.

    Fehler werden vollständig im Asset gespeichert (status=failed +
    error_message) und niemals weitergeworfen — der auslösende Request
    bzw. Worker darf dadurch nie einen 500er/Task-Fehler produzieren.
    """
    from .models import Product3DAsset
    from .services.preprocessing import prepare_source_image
    from .services.providers import get_provider

    try:
        asset = Product3DAsset.objects.get(pk=asset_id)
    except Product3DAsset.DoesNotExist:
        logger.warning("3D-Task: Asset %s existiert nicht mehr.", asset_id)
        return

    asset.status = Product3DAsset.Status.PROCESSING
    asset.error_message = ""
    asset.save(update_fields=["status", "error_message", "updated_at"])

    try:
        composites = []
        for source in asset.source_images:
            with source.open("rb") as f:
                composites.append(
                    prepare_source_image(
                        f.read(),
                        offset_x=asset.comp_offset_x,
                        offset_y=asset.comp_offset_y,
                        scale=asset.comp_scale,
                    )
                )

        provider = get_provider()
        job_id = provider.create_job(composites)
        asset.provider = provider.name
        asset.provider_job_id = job_id
        asset.save(update_fields=["provider", "provider_job_id", "updated_at"])

        deadline = time.monotonic() + settings.IMAGE3D_POLL_TIMEOUT
        while True:
            result = provider.poll_job(job_id)
            if result.status != "processing":
                break
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Zeitüberschreitung: Provider hat nach "
                    f"{settings.IMAGE3D_POLL_TIMEOUT // 60} Minuten kein Ergebnis geliefert."
                )
            time.sleep(settings.IMAGE3D_POLL_INTERVAL)

        if result.status == "failed":
            raise RuntimeError(result.error or "Generierung beim Provider fehlgeschlagen.")

        glb_bytes = provider.download(result.glb_url)
        asset.model_file.save(f"{asset.pk}.glb", ContentFile(glb_bytes), save=False)

        if result.thumbnail_url:
            thumb_bytes = provider.download(result.thumbnail_url)
            asset.preview_thumbnail.save(
                f"{asset.pk}.png", ContentFile(thumb_bytes), save=False
            )
        elif composites:
            # Fallback-Poster: erstes vorverarbeitetes Bild
            asset.preview_thumbnail.save(
                f"{asset.pk}.png", ContentFile(composites[0]), save=False
            )

        asset.status = Product3DAsset.Status.DONE
        asset.save()
        logger.info("3D-Modell für Asset %s erfolgreich generiert.", asset_id)
    except Exception as exc:
        logger.exception("3D-Generierung für Asset %s fehlgeschlagen.", asset_id)
        asset.status = Product3DAsset.Status.FAILED
        asset.error_message = str(exc)[:2000]
        asset.save(update_fields=["status", "error_message", "updated_at"])
