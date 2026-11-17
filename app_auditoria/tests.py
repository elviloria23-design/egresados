"""Pruebas de acceso a la bitácora administrativa."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from .models import RegistroAuditoria

User = get_user_model()


class AuditoriaTests(TestCase):
    """Comprueba autorización y exportación filtrada de eventos."""

    def setUp(self):
        """Crea el evento de ejemplo y el usuario administrador."""

        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='Secure-test-password-2026',
        )
        self.evento = RegistroAuditoria.objects.create(
            usuario=self.admin,
            accion='CAMBIAR_ESTADO',
            entidad='Egresado',
            entidad_id='12',
            valores={'anterior': 'ACTIVO', 'nuevo': 'EMPRENDEDOR'},
            direccion_ip='127.0.0.1',
        )

    def test_bitacora_requiere_rol_administrativo(self):
        """Deniega a usuarios sin rol de administrador."""

        user = User.objects.create_user(
            username='funcionario',
            password='test-password',
        )
        user.groups.add(Group.objects.create(name='Funcionario'))
        self.client.force_login(user)
        response = self.client.get(reverse('auditoria_list'))
        self.assertEqual(response.status_code, 403)

    def test_administrador_filtra_y_exporta_eventos(self):
        """Presenta la bitácora y ofrece exportación delimitada por filtros."""

        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('auditoria_export'),
            {'accion': 'CAMBIAR_ESTADO'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'CAMBIAR_ESTADO',
            response.content.decode('utf-8-sig'),
        )
        self.assertEqual(
            self.client.get(reverse('auditoria_list')).status_code,
            200,
        )
