"""Rutas de portada, autenticación y tablero."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('ingresar/', views.login_view, name='login'),
    path('salir/', views.logout_view, name='logout'),
    path('tablero/', views.dashboard_view, name='dashboard'),
]
