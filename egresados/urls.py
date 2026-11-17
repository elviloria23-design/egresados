"""Enrutamiento principal hacia las aplicaciones del sistema."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('app_dashboard.urls')),
    path('egresados/', include('app_egresados.urls')),
    path('oportunidades/', include('app_oportunidades.urls')),
    path('encuestas/', include('app_encuestas.urls')),
    path('certificaciones/', include('app_certificaciones.urls')),
    path('reportes/', include('app_reportes.urls')),
    path('auditoria/', include('app_auditoria.urls')),
]
