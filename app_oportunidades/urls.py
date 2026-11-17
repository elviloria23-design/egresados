"""Rutas públicas y de gestión de oportunidades."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.oportunidades_list_view, name='oportunidades_list'),
    path(
        'nueva/',
        views.oportunidades_create_view,
        name='oportunidades_create',
    ),
    path(
        '<int:pk>/',
        views.oportunidades_detail_view,
        name='oportunidades_detail',
    ),
    path(
        '<int:pk>/editar/',
        views.oportunidades_update_view,
        name='oportunidades_update',
    ),
    path(
        '<int:pk>/despublicar/',
        views.oportunidades_unpublish_view,
        name='oportunidades_unpublish',
    ),
]
