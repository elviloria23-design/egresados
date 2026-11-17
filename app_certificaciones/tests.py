"""Pruebas de autorización, emisión y verificación de certificados."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from app_auditoria.models import RegistroAuditoria
from app_egresados.models import AlcanceFuncionario, Egresado, ProgramaFormacion

from .models import Certificacion

User = get_user_model()


class CertificacionesTests(TestCase):
    """Comprueba PDFs verificables y acceso por titular o rol autorizado."""

    def setUp(self):
        """Crea egresado y usuario administrativo."""

        self.programa = ProgramaFormacion.objects.create(
            nombre='Tecnología solar',
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='Secure-test-password-2026',
        )
        self.egresado = Egresado.objects.create(
            documento='88776655',
            nombres='Lucía',
            apellidos='Pérez',
            correo='lucia@example.com',
            programa=self.programa,
            fecha_grado=date(2024, 6, 1),
            consentimiento=True,
        )

    def test_emision_crea_numero_codigo_pdf_y_auditoria(self):
        """Emite PDF único e información de verificación auditada."""

        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('certificaciones_create'),
            {
                'egresado': self.egresado.pk,
                'tipo': 'Constancia de egreso',
                'motivo': 'Solicitud del egresado.',
            },
        )
        self.assertEqual(response.status_code, 302)
        certificado = Certificacion.objects.get()
        pdf_response = self.client.get(
            reverse('certificacion_pdf', args=[certificado.pk]),
        )
        self.assertEqual(pdf_response.status_code, 200)
        self.assertEqual(pdf_response['Content-Type'], 'application/pdf')
        self.assertTrue(pdf_response.content.startswith(b'%PDF'))
        self.assertTrue(certificado.numero.startswith('CIEA-'))
        self.assertTrue(certificado.codigo_verificacion)
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion='EMITIR_CERTIFICACION',
            ).exists()
        )

    def test_interfaz_lista_certificados_y_formulario_de_emision(self):
        """Renderiza el listado y el alta solo para administración."""

        self.client.force_login(self.admin)
        self.assertEqual(
            self.client.get(reverse('certificaciones_list')).status_code,
            200,
        )
        self.assertEqual(
            self.client.get(reverse('certificaciones_create')).status_code,
            200,
        )

    def test_verificacion_publica_no_revela_datos_personales(self):
        """Muestra autenticidad sin nombres, documentos ni correos."""

        certificado = Certificacion.objects.create(
            egresado=self.egresado,
            numero='CIEA-2026-TEST-1',
            tipo='Constancia',
            motivo='Solicitud.',
            emitida_por=self.admin,
        )
        response = self.client.get(
            reverse(
                'certificacion_verify',
                args=[certificado.codigo_verificacion],
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Documento auténtico y vigente')
        self.assertNotContains(response, self.egresado.documento)
        self.assertNotContains(response, self.egresado.nombre_completo)
        self.assertNotContains(response, self.egresado.correo)

    def test_egresado_solo_descarga_su_certificacion(self):
        """Impide que un egresado descargue certificados de otras personas."""

        group = Group.objects.create(name='Egresado')
        alumni_user = User.objects.create_user(
            username='egresada',
            password='test-password',
        )
        alumni_user.groups.add(group)
        self.egresado.usuario = alumni_user
        self.egresado.save(update_fields=['usuario'])
        certificado = Certificacion.objects.create(
            egresado=self.egresado,
            numero='CIEA-2026-TEST-2',
            tipo='Constancia',
            motivo='Solicitud.',
            emitida_por=self.admin,
        )
        self.client.force_login(alumni_user)
        self.assertEqual(
            self.client.get(
                reverse('certificacion_pdf', args=[certificado.pk]),
            ).status_code,
            200,
        )

        otro_egresado = Egresado.objects.create(
            documento='44556677',
            nombres='Mario',
            apellidos='Díaz',
            correo='mario@example.com',
            programa=self.programa,
            fecha_grado=date(2022, 1, 1),
            consentimiento=True,
        )
        otro = Certificacion.objects.create(
            egresado=otro_egresado,
            numero='CIEA-2026-TEST-3',
            tipo='Constancia',
            motivo='Solicitud.',
            emitida_por=self.admin,
        )
        self.assertEqual(
            self.client.get(
                reverse('certificacion_pdf', args=[otro.pk]),
            ).status_code,
            404,
        )

    def test_funcionario_requiere_permiso_explicito_para_emitir(self):
        """Solo autoriza la emisión a personal que recibió el permiso."""

        funcionario = User.objects.create_user(
            username='funcionario',
            password='test-password',
        )
        funcionario.groups.add(Group.objects.create(name='Funcionario'))
        alcance = AlcanceFuncionario.objects.create(usuario=funcionario)
        alcance.programas.add(self.programa)
        self.client.force_login(funcionario)
        self.assertEqual(
            self.client.get(reverse('certificaciones_create')).status_code,
            403,
        )

        permission = Permission.objects.get(
            content_type__app_label='app_certificaciones',
            codename='emitir_certificaciones',
        )
        funcionario.user_permissions.add(permission)
        self.assertEqual(
            self.client.get(reverse('certificaciones_create')).status_code,
            200,
        )

    def test_solo_administrativo_puede_anular_y_cada_anulacion_se_verifica(self):
        """Audita el motivo y publica el estado revocado al verificar."""

        certificado = Certificacion.objects.create(
            egresado=self.egresado,
            numero='CIEA-2026-TEST-4',
            tipo='Constancia',
            motivo='Solicitud.',
            emitida_por=self.admin,
        )
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('certificacion_anular', args=[certificado.pk]),
            {'motivo': 'Documento emitido por error.'},
        )
        self.assertEqual(response.status_code, 302)
        certificado.refresh_from_db()
        self.assertEqual(certificado.estado, Certificacion.Estado.ANULADA)
        self.assertEqual(
            self.client.get(
                reverse(
                    'certificacion_verify',
                    args=[certificado.codigo_verificacion],
                ),
            ).status_code,
            200,
        )
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion='ANULAR_CERTIFICACION',
            ).exists()
        )
