"""Pruebas de publicación, consentimiento y respuestas de encuestas."""

from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from app_egresados.models import Egresado, ProgramaFormacion

from .models import (
    DetalleRespuesta,
    Encuesta,
    Pregunta,
    RespuestaEncuesta,
)

User = get_user_model()


class EncuestasTests(TestCase):
    """Comprueba respuestas de egresados y gestión por usuarios autorizados."""

    def setUp(self):
        """Crea un egresado consentido y una encuesta vigente."""

        self.programa = ProgramaFormacion.objects.create(
            nombre='Energías renovables',
        )
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='Secure-test-password-2026',
        )
        self.alumni_user = User.objects.create_user(
            username='egresada',
            password='test-password',
        )
        self.alumni_user.groups.add(Group.objects.create(name='Egresado'))
        self.egresado = Egresado.objects.create(
            usuario=self.alumni_user,
            documento='22334455',
            nombres='Ana',
            apellidos='Gómez',
            correo='ana@example.com',
            programa=self.programa,
            fecha_grado=date(2023, 1, 15),
            consentimiento=True,
        )
        self.encuesta = Encuesta.objects.create(
            titulo='Seguimiento anual',
            descripcion='Cuéntanos sobre tu trayectoria.',
            creada_por=self.admin,
            publicada=True,
            inicia_en=timezone.localdate() - timedelta(days=1),
            finaliza_en=timezone.localdate() + timedelta(days=10),
        )
        self.encuesta.programas.add(self.programa)
        self.pregunta = Pregunta.objects.create(
            encuesta=self.encuesta,
            texto='¿Cuál es tu situación?',
            tipo=Pregunta.Tipo.OPCION,
            opciones=['Empleo', 'Emprendimiento'],
            orden=1,
        )

    def test_egresado_con_consentimiento_responde_una_vez(self):
        """Almacena respuesta y previene nuevos envíos del mismo usuario."""

        self.client.force_login(self.alumni_user)
        response = self.client.post(
            reverse('encuestas_answer', args=[self.encuesta.pk]),
            {f'pregunta_{self.pregunta.pk}': 'Empleo'},
        )
        self.assertRedirects(response, reverse('encuestas_list'))
        self.assertEqual(RespuestaEncuesta.objects.count(), 1)
        detalle = DetalleRespuesta.objects.get()
        self.assertEqual(detalle.valor, 'Empleo')

        self.client.post(
            reverse('encuestas_answer', args=[self.encuesta.pk]),
            {f'pregunta_{self.pregunta.pk}': 'Emprendimiento'},
        )
        self.assertEqual(RespuestaEncuesta.objects.count(), 1)
        self.assertEqual(DetalleRespuesta.objects.get().valor, 'Empleo')

    def test_sin_consentimiento_no_ve_ni_responde_encuestas(self):
        """Excluye egresados sin autorización de encuestas vigentes."""

        self.egresado.consentimiento = False
        self.egresado.save(update_fields=['consentimiento'])
        self.client.force_login(self.alumni_user)
        list_response = self.client.get(reverse('encuestas_list'))
        answer_response = self.client.get(
            reverse('encuestas_answer', args=[self.encuesta.pk]),
        )
        self.assertNotContains(list_response, self.encuesta.titulo)
        self.assertEqual(answer_response.status_code, 302)

    def test_solo_publicadas_y_vigentes_se_muestran_a_egresados(self):
        """Oculta borradores y encuestas fuera de la vigencia configurada."""

        self.encuesta.publicada = False
        self.encuesta.save(update_fields=['publicada'])
        self.client.force_login(self.alumni_user)
        response = self.client.get(reverse('encuestas_list'))
        self.assertNotContains(response, self.encuesta.titulo)

    def test_resultados_son_agregados_y_no_exponen_participantes(self):
        """El equipo ve recuentos por pregunta y no datos personales."""

        RespuestaEncuesta.objects.create(
            encuesta=self.encuesta,
            egresado=self.egresado,
        )
        DetalleRespuesta.objects.create(
            respuesta=self.encuesta.respuestas.get(),
            pregunta=self.pregunta,
            valor='Empleo',
        )
        self.client.force_login(self.admin)
        response = self.client.get(
            reverse('encuestas_detail', args=[self.encuesta.pk]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Empleo')
        self.assertNotContains(response, self.egresado.documento)
        self.assertNotContains(response, self.egresado.correo)

    def test_funcionario_solo_publica_para_programas_de_su_alcance(self):
        """Restringe público objetivo al programa de alcance asignado."""

        from app_egresados.models import AlcanceFuncionario

        grupo = Group.objects.create(name='Funcionario')
        funcionario = User.objects.create_user(
            username='funcionario',
            password='test-password',
        )
        funcionario.groups.add(grupo)
        alcance = AlcanceFuncionario.objects.create(usuario=funcionario)
        alcance.programas.add(self.programa)
        self.client.force_login(funcionario)

        response = self.client.get(reverse('encuestas_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.programa.nombre)

    def test_crear_encuesta_y_preguntas_desde_interfaz(self):
        """Guarda preguntas tipadas y las publica mediante la acción autorizada."""

        self.client.force_login(self.admin)
        page = self.client.get(reverse('encuestas_create'))
        self.assertEqual(page.status_code, 200)
        response = self.client.post(
            reverse('encuestas_create'),
            {
                'titulo': 'Actualización de perfil',
                'descripcion': 'Cuéntanos qué ha cambiado.',
                'programas': [str(self.programa.pk)],
                'inicia_en': timezone.localdate().isoformat(),
                'finaliza_en': (
                    timezone.localdate() + timedelta(days=14)
                ).isoformat(),
                'preguntas-TOTAL_FORMS': '3',
                'preguntas-INITIAL_FORMS': '0',
                'preguntas-MIN_NUM_FORMS': '0',
                'preguntas-MAX_NUM_FORMS': '30',
                'preguntas-0-texto': '¿Trabajas actualmente?',
                'preguntas-0-tipo': Pregunta.Tipo.OPCION,
                'preguntas-0-opciones_texto': 'Sí\nNo',
                'preguntas-0-obligatoria': 'on',
                'preguntas-0-orden': '1',
                'preguntas-1-texto': '',
                'preguntas-2-texto': '',
            },
        )
        self.assertEqual(response.status_code, 302)
        encuesta = Encuesta.objects.get(titulo='Actualización de perfil')
        self.assertEqual(encuesta.preguntas.count(), 1)
        self.assertEqual(
            encuesta.preguntas.get().opciones,
            ['Sí', 'No'],
        )

        publish_response = self.client.post(
            reverse('encuestas_publish', args=[encuesta.pk]),
        )
        self.assertEqual(publish_response.status_code, 302)
        encuesta.refresh_from_db()
        self.assertTrue(encuesta.publicada)
