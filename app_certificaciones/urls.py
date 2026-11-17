"""Rutas de emisión, descarga y verificación de certificados."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.certificaciones_list_view, name='certificaciones_list'),
    path('emitir/', views.certificaciones_create_view, name='certificaciones_create'),
    path(
        'verificar/',
        views.certificaciones_request_view,
        name='certificacion_verify_form',
    ),
    path(
        'verificar/<uuid:codigo>/',
        views.certificaciones_verify_view,
        name='certificacion_verify',
    ),
    path('<int:pk>/pdf/', views.certificaciones_pdf_view, name='certificacion_pdf'),
    path('<int:pk>/anular/', views.certificaciones_anular_view, name='certificacion_anular'),
]
