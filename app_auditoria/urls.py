"""Rutas de consulta de la bitácora."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.auditoria_list_view, name='auditoria_list'),
    path('exportar/', views.auditoria_export_view, name='auditoria_export'),
]
