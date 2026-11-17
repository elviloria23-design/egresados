"""Configuración de la aplicación de auditoría."""

from django.apps import AppConfig


class AppAuditoriaConfig(AppConfig):
    """Registra la aplicación de auditoría."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_auditoria'
