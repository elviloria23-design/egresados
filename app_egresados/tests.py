"""Pruebas del padrón, reglas de negocio y autorización."""

from datetime import date, timedelta
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app_auditoria.models import RegistroAuditoria
from app_egresados.forms import EgresadoForm
from app_egresados.models import (
    AlcanceFuncionario,
    ActualizacionPendiente,
    Egresado,
    HistorialConsentimiento,
    HistorialDatos,
    HistorialEstado,
    IntentoContacto,
    ProgramaFormacion,
)
from app_egresados.views import ENCABEZADOS_CSV

User = get_user_model()


class EgresadoRulesTests(TestCase):
    """Comprueba unicidad, captura de consentimiento y seguimiento."""

    def setUp(self):
        """Crea un programa y un usuario administrativo para las pruebas."""

        self.programa = ProgramaFormacion.objects.create(
            nombre='Tecnología en energías renovables',
        )
        self.usuario = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='Secure-test-password-2026',
        )
        self.egresado = Egresado.objects.create(
            documento='123456789',
            nombres='Ana',
            apellidos='Gómez',
            correo='ana@example.com',
            programa=self.programa,
            fecha_grado=date(2023, 6, 1),
            elegibilidad_verificada=True,
            consentimiento=True,
            consentimiento_fecha=timezone.now(),
        )

    def test_documento_unico_para_registros_activos(self):
        """Impide documentos duplicados en registros activos."""

        with self.assertRaises(IntegrityError), transaction.atomic():
            Egresado.objects.create(
                documento=self.egresado.documento,
                nombres='Otro',
                apellidos='Egresado',
                correo='otro@example.com',
                programa=self.programa,
                fecha_grado=date(2024, 1, 1),
                consentimiento=True,
            )

    def test_documento_puede_reutilizarse_tras_baja_logica(self):
        """Permite un nuevo registro después de una baja lógica."""

        self.egresado.activo = False
        self.egresado.save(update_fields=['activo'])
        duplicado = Egresado.objects.create(
            documento=self.egresado.documento,
            nombres='Otro',
            apellidos='Egresado',
            correo='otro@example.com',
            programa=self.programa,
            fecha_grado=date(2024, 1, 1),
            consentimiento=True,
        )
        self.assertTrue(duplicado.activo)

    def test_formulario_exige_autorizacion_y_elegibilidad(self):
        """Rechaza el alta si falta una de las dos confirmaciones."""

        form = EgresadoForm(
            data={
                'documento': '99887766',
                'nombres': 'Luis',
                'apellidos': 'Pérez',
                'correo': 'luis@example.com',
                'telefono': '',
                'municipio': '',
                'programa': self.programa.pk,
                'fecha_grado': '2024-01-01',
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn('consentimiento', form.errors)
        self.assertIn('elegibilidad_verificada', form.errors)

    def test_creacion_web_registra_estado_consentimiento_y_auditoria(self):
        """Crea ficha e historial inicial de estado y autorización."""

        self.client.force_login(self.usuario)
        response = self.client.post(
            reverse('egresados_create'),
            {
                'documento': '99887766',
                'nombres': 'Luis',
                'apellidos': 'Pérez',
                'correo': 'luis@example.com',
                'telefono': '3001234567',
                'municipio': 'Riohacha',
                'programa': self.programa.pk,
                'fecha_grado': '2024-01-01',
                'elegibilidad_verificada': 'on',
                'consentimiento': 'on',
            },
        )
        self.assertEqual(response.status_code, 302)
        nuevo = Egresado.objects.get(documento='99887766')
        self.assertTrue(nuevo.consentimiento_fecha)
        self.assertEqual(nuevo.historial_estados.count(), 1)
        self.assertTrue(
            HistorialConsentimiento.objects.filter(
                egresado=nuevo,
                autorizado=True,
                origen='REGISTRO',
            ).exists()
        )
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion='CREAR',
                entidad_id=str(nuevo.pk),
            ).exists()
        )

    def test_dos_intentos_fallidos_marcan_inactivo_y_auditan(self):
        """Aplica RN-05 y registra cada contacto y cambio de estado."""

        self.client.force_login(self.usuario)
        fechas = (
            timezone.localdate(),
            timezone.localdate() - timedelta(days=1),
        )
        for day in fechas:
            response = self.client.post(
                reverse('egresados_contacto', args=[self.egresado.pk]),
                {
                    'fecha': day.isoformat(),
                    'medio': 'Teléfono',
                    'resultado': IntentoContacto.Resultado.SIN_RESPUESTA,
                    'observacion': 'No contestó.',
                },
            )
            self.assertEqual(response.status_code, 302)

        self.egresado.refresh_from_db()
        self.assertEqual(self.egresado.estado, Egresado.Estado.INACTIVO)
        self.assertEqual(self.egresado.historial_estados.count(), 1)
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion='CAMBIAR_ESTADO',
                entidad_id=str(self.egresado.pk),
            ).exists()
        )

    def test_cambio_estado_requiere_justificacion_y_crea_historial(self):
        """Registra estado anterior, estado nuevo, actor y razón."""

        self.client.force_login(self.usuario)
        response = self.client.post(
            reverse('egresados_estado', args=[self.egresado.pk]),
            {
                'estado': Egresado.Estado.EMPRENDEDOR,
                'justificacion': 'Inició un emprendimiento local.',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.egresado.refresh_from_db()
        cambio = HistorialEstado.objects.get(egresado=self.egresado)
        self.assertEqual(self.egresado.estado, Egresado.Estado.EMPRENDEDOR)
        self.assertEqual(cambio.estado_anterior, Egresado.Estado.ACTIVO)
        self.assertEqual(cambio.usuario, self.usuario)
        self.assertEqual(
            cambio.justificacion,
            'Inició un emprendimiento local.',
        )

    def test_funcionario_solo_consulta_programas_asignados(self):
        """Deniega registros fuera del programa asignado al funcionario."""

        grupo = Group.objects.create(name='Funcionario')
        funcionario = User.objects.create_user(
            username='funcionario',
            password='test-password',
        )
        funcionario.groups.add(grupo)
        otro_programa = ProgramaFormacion.objects.create(
            nombre='Mecánica industrial',
        )
        otro_egresado = Egresado.objects.create(
            documento='44556677',
            nombres='Mario',
            apellidos='Díaz',
            correo='mario@example.com',
            programa=otro_programa,
            fecha_grado=date(2022, 1, 1),
            consentimiento=True,
        )
        AlcanceFuncionario.objects.create(usuario=funcionario).programas.add(
            self.programa,
        )
        self.client.force_login(funcionario)

        own_response = self.client.get(
            reverse('egresados_detail', args=[self.egresado.pk]),
        )
        denied_response = self.client.get(
            reverse('egresados_detail', args=[otro_egresado.pk]),
        )
        self.assertEqual(own_response.status_code, 200)
        self.assertEqual(denied_response.status_code, 404)

    def test_usuario_sin_rol_no_consulta_el_padron(self):
        """Aplica denegación por defecto a usuarios autenticados sin grupo."""

        user = User.objects.create_user(
            username='sin-rol',
            password='test-password',
        )
        self.client.force_login(user)
        response = self.client.get(reverse('egresados_list'))
        self.assertEqual(response.status_code, 403)

    def test_autogestion_actualiza_contacto_y_deja_estado_pendiente(self):
        """Aplica datos de contacto y versiona la situación para revisión."""

        grupo = Group.objects.create(name='Egresado')
        egresado_user = User.objects.create_user(
            username='ana-egresada',
            password='test-password',
        )
        egresado_user.groups.add(grupo)
        self.egresado.usuario = egresado_user
        self.egresado.save(update_fields=['usuario'])
        self.client.force_login(egresado_user)

        page_response = self.client.get(reverse('egresados_self_update'))
        self.assertEqual(page_response.status_code, 200)
        response = self.client.post(
            reverse('egresados_self_update'),
            {
                'correo': 'ana.nuevo@example.com',
                'telefono': '3001234567',
                'municipio': 'Maicao',
                'estado': Egresado.Estado.EMPRENDEDOR,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.egresado.refresh_from_db()
        pendiente = ActualizacionPendiente.objects.get(egresado=self.egresado)
        self.assertEqual(self.egresado.correo, 'ana.nuevo@example.com')
        self.assertEqual(self.egresado.estado, Egresado.Estado.ACTIVO)
        self.assertEqual(
            pendiente.valores['estado'],
            Egresado.Estado.EMPRENDEDOR,
        )
        self.assertFalse(pendiente.verificada)
        self.assertEqual(
            HistorialDatos.objects.get(egresado=self.egresado).origen,
            'AUTOGESTION',
        )
        self.assertFalse(self.egresado.consentimiento)
        revocacion = HistorialConsentimiento.objects.get(
            egresado=self.egresado,
        )
        self.assertFalse(revocacion.autorizado)
        self.assertEqual(revocacion.origen, 'AUTOGESTION')

    def test_importacion_csv_registra_validas_y_rechaza_fila_invalida(self):
        """Importa por fila y reporta errores de elegibilidad o consentimiento."""

        self.client.force_login(self.usuario)
        lineas = [
            ','.join(ENCABEZADOS_CSV),
            (
                '55667788,María,Ramírez,maria@example.com,3001234567,'
                'Maicao,Tecnología en energías renovables,2024-06-01,si,si,no'
            ),
            (
                '66778899,Pedro,López,pedro@example.com,3007654321,'
                'Uribia,Tecnología en energías renovables,2024-06-01,si,no,no'
            ),
            (
                '55667788,Otro,Duplicado,otro@example.com,3000000000,'
                'Riohacha,Tecnología en energías renovables,2024-06-01,si,si,no'
            ),
        ]
        archivo = SimpleUploadedFile(
            'egresados.csv',
            '\n'.join(lineas).encode('utf-8'),
            content_type='text/csv',
        )
        response = self.client.post(
            reverse('egresados_import'),
            {'archivo': archivo},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['resultado']['creados'], 1)
        self.assertEqual(len(response.context['resultado']['errores']), 2)
        nuevo = Egresado.objects.get(documento='55667788')
        self.assertTrue(nuevo.consentimiento)
        self.assertTrue(nuevo.historial_estados.exists())
        self.assertTrue(
            RegistroAuditoria.objects.filter(
                accion='CARGAR_CSV',
                valores__creados=1,
                valores__rechazados=2,
            ).exists()
        )

    def test_importacion_rechaza_encabezados_incorrectos(self):
        """No procesa archivos que omiten columnas de la plantilla."""

        self.client.force_login(self.usuario)
        archivo = SimpleUploadedFile(
            'incompleto.csv',
            b'documento,nombres\n123,Ana',
            content_type='text/csv',
        )
        response = self.client.post(
            reverse('egresados_import'),
            {'archivo': archivo},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Faltan columnas requeridas')
        self.assertEqual(Egresado.objects.count(), 1)
