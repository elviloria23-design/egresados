"""Configuración de la aplicación de encuestas."""

from django.apps import AppConfig


class AppEncuestasConfig(AppConfig):
    """Registra la aplicación de encuestas."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_encuestas'
