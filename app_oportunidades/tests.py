"""Pruebas para publicación y expiración de oportunidades."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app_oportunidades.models import Oportunidad

User = get_user_model()


class OportunidadesTests(TestCase):
    """Comprueba publicación pública, expiración y permisos de gestión."""

    def setUp(self):
        """Crea una oportunidad vigente y otra expirada."""

        self.usuario = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='Secure-test-password-2026',
        )
        self.vigente = Oportunidad.objects.create(
            titulo='Técnico de mantenimiento solar',
            tipo=Oportunidad.Tipo.LABORAL,
            descripcion='Vacante en La Guajira.',
            fuente='Empresa regional',
            vigente_hasta=timezone.localdate() + timedelta(days=5),
            responsable=self.usuario,
        )
        self.expirada = Oportunidad.objects.create(
            titulo='Convocatoria vencida',
            tipo=Oportunidad.Tipo.FORMACION,
            descripcion='Ya finalizó.',
            fuente='SENA',
            vigente_hasta=timezone.localdate() - timedelta(days=1),
            responsable=self.usuario,
        )

    def test_solo_muestra_oportunidades_vigentes(self):
        """Oculta las ofertas vencidas de portada y listado público."""

        response = self.client.get(reverse('oportunidades_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.vigente.titulo)
        self.assertNotContains(response, self.expirada.titulo)

    def test_comando_despublica_oportunidades_vencidas(self):
        """El comando programable retira las ofertas vencidas."""

        from django.core.management import call_command

        call_command('expire_opportunities', stdout=None)
        self.expirada.refresh_from_db()
        self.assertFalse(self.expirada.publicada)
        self.assertTrue(self.vigente.publicada)

    def test_publicar_oportunidad_exige_rol(self):
        """Impide que un usuario no autorizado publique ofertas."""

        user = User.objects.create_user(
            username='sin-rol',
            password='test-password',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('oportunidades_create'))
        self.assertEqual(response.status_code, 403)
