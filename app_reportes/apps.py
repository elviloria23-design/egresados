"""Configuración de la aplicación de reportes."""

from django.apps import AppConfig


class AppReportesConfig(AppConfig):
    """Registra la aplicación de reportes."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_reportes'
