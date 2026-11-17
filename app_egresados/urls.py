"""Rutas de administración y seguimiento del padrón."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.egresados_list_view, name='egresados_list'),
    path('nuevo/', views.egresados_create_view, name='egresados_create'),
    path('importar/', views.egresados_import_view, name='egresados_import'),
    path(
        'plantilla.csv',
        views.egresados_import_template_view,
        name='egresados_import_template',
    ),
    path(
        'pendientes/',
        views.egresados_pendientes_view,
        name='egresados_pendientes',
    ),
    path(
        'pendientes/<int:pk>/verificar/',
        views.egresados_verificar_actualizacion_view,
        name='egresados_verificar',
    ),
    path(
        'mi-perfil/',
        views.egresados_self_update_view,
        name='egresados_self_update',
    ),
    path('<int:pk>/', views.egresados_detail_view, name='egresados_detail'),
    path(
        '<int:pk>/editar/',
        views.egresados_update_view,
        name='egresados_update',
    ),
    path(
        '<int:pk>/contacto/',
        views.egresados_contacto_create_view,
        name='egresados_contacto',
    ),
    path(
        '<int:pk>/estado/',
        views.egresados_estado_view,
        name='egresados_estado',
    ),
    path('<int:pk>/baja/', views.egresados_baja_view, name='egresados_baja'),
    path(
        '<int:pk>/restaurar/',
        views.egresados_restore_view,
        name='egresados_restore',
    ),
]
