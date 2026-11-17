"""Configuración de la aplicación de tablero."""

from django.apps import AppConfig


class AppDashboardConfig(AppConfig):
    """Registra la aplicación del tablero."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app_dashboard'
