"""Rutas de administración y respuesta de encuestas."""

from django.urls import path

from . import views

urlpatterns = [
    path('', views.encuestas_list_view, name='encuestas_list'),
    path('nueva/', views.encuestas_create_view, name='encuestas_create'),
    path('<int:pk>/', views.encuestas_detail_view, name='encuestas_detail'),
    path('<int:pk>/editar/', views.encuestas_update_view, name='encuestas_update'),
    path('<int:pk>/responder/', views.encuestas_answer_view, name='encuestas_answer'),
    path('<int:pk>/publicar/', views.encuestas_publish_view, name='encuestas_publish'),
]
