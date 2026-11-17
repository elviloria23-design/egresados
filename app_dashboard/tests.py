"""Pruebas de autenticación y acceso al tablero."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from app_dashboard.views import fecha_limite_seguimiento

User = get_user_model()


class DashboardAccessTests(TestCase):
    """Comprueba los accesos públicos y por rol al tablero."""

    def test_inicio_es_publico_y_presenta_enlace_de_ingreso(self):
        """Permite explorar la portada sin autenticación."""

        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tu talento abre caminos.')
        self.assertContains(response, reverse('login'))

    def test_tablero_requiere_usuario_con_rol(self):
        """Redirige a autenticación y niega acceso sin grupo institucional."""

        anonymous_response = self.client.get(reverse('dashboard'))
        self.assertEqual(anonymous_response.status_code, 302)
        user = User.objects.create_user(
            username='sin-rol',
            password='test-password',
        )
        self.client.force_login(user)
        denied_response = self.client.get(reverse('dashboard'))
        self.assertEqual(denied_response.status_code, 403)

    def test_superusuario_consulta_tablero(self):
        """Concede acceso institucional al superusuario."""

        admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='Secure-test-password-2026',
        )
        self.client.force_login(admin)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Estado de seguimiento')

    def test_visor_accede_al_tablero_solo_lectura(self):
        """Permite a los visores ver indicadores agregados."""

        visor = User.objects.create_user(
            username='visor',
            password='test-password',
        )
        visor.groups.add(Group.objects.create(name='Visor'))
        self.client.force_login(visor)
        self.assertEqual(
            self.client.get(reverse('dashboard')).status_code,
            200,
        )

    def test_fecha_de_alerta_calcula_once_meses_calendario(self):
        """Respeta la duración variable de los meses al fijar alertas."""

        from datetime import date

        self.assertEqual(
            fecha_limite_seguimiento(date(2024, 3, 31)),
            date(2023, 4, 30),
        )
