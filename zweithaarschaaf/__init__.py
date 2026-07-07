# Celery-App beim Django-Start laden, damit @shared_task sie findet
from .celery import app as celery_app

__all__ = ("celery_app",)
