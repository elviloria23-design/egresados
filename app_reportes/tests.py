"""Pruebas de alcance, privacidad y exportación de indicadores."""

from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from app_auditoria.models import RegistroAuditoria
from app_egresados.models import AlcanceFuncionario, Egresado, ProgramaFormacion

User = get_user_model()


class ReportesTests(TestCase):
    """Asegura que cada rol solo reciba la información que le corresponde."""

    def setUp(self):
        """Crea datos para dos programas institucionales."""

        self.programa = ProgramaFormacion.objects.create(nombre='Energía solar')
        self.otro_programa = ProgramaFormacion.objects.create(
            nombre='Mantenimiento industrial',
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='Secure-test-password-2026',
        )
        self.egresado = Egresado.objects.create(
            documento='11223344',
            nombres='Laura',
            apellidos='García',
            correo='laura@example.com',
            programa=self.programa,
            fecha_grado=date(2024, 6, 1),
            consentimiento=True,
        )

    def test_visor_solo_exporta_datos_agregados_de_su_alcance(self):
        """No incluye identificadores, nombre ni contacto en CSV del visor."""

        visor = User.objects.create_user(
            username='visor',
            password='test-password',
        )
        visor.groups.add(Group.objects.create(name='Visor'))
        AlcanceFuncionario.objects.create(usuario=visor).programas.add(
            self.programa,
        )
        self.client.force_login(visor)
        response = self.client.get(reverse('reportes_export'))
        contenido = response.content.decode('utf-8-sig')
        self.assertIn('Programa,Estado,Cantidad', contenido)
        self.assertIn('Energía solar', contenido)
        self.assertNotIn(self.egresado.documento, contenido)
        self.assertNotIn(self.egresado.nombre_completo, contenido)
        self.assertNotIn(self.egresado.correo, contenido)

    def test_administrativo_exporta_detalle_dentro_de_su_rol(self):
        """Permite informe detallado únicamente a personal autorizado."""

        self.client.force_login(self.admin)
        response = self.client.get(reverse('reportes_export'))
        contenido = response.content.decode('utf-8-sig')
        self.assertIn(self.egresado.documento, contenido)
        self.assertIn(self.egresado.correo, contenido)
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion='EXPORTAR_REPORTE',
            ).exists()
        )

    def test_panel_de_indicadores_se_renderiza(self):
        """Muestra indicadores y filtros para usuarios autorizados."""

        self.client.force_login(self.admin)
        response = self.client.get(reverse('reportes_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Distribución por estado')
        self.assertContains(response, 'Energía solar')

    def test_celda_csv_con_formula_se_sanea(self):
        """Evita interpretar valores de programas como fórmulas ejecutables."""

        ProgramaFormacion.objects.filter(pk=self.programa.pk).update(
            nombre='=HYPERLINK("https://example.invalid")',
        )
        self.client.force_login(self.admin)
        response = self.client.get(reverse('reportes_export'))
        contenido = response.content.decode('utf-8-sig')
        self.assertIn("'=HYPERLINK", contenido)
        self.assertNotIn('\n=HYPERLINK', contenido)
