"""Configuración de la aplicación de certificaciones."""

from django.apps import AppConfig


class AppCertificacionesConfig(AppConfig):
    """Registra la aplicación de certificaciones."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_certificaciones'
