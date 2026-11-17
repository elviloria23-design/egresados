"""Rutas de consulta y exportación de indicadores."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.reportes_dashboard_view, name='reportes_dashboard'),
    path('exportar/', views.reportes_export_view, name='reportes_export'),
]
