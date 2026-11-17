"""Configuración de la aplicación de egresados."""

from django.apps import AppConfig


class AppEgresadosConfig(AppConfig):
    """Registra la aplicación de egresados."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_egresados'
