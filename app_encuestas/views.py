"""Vistas para crear, responder y analizar encuestas institucionales."""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from app_auditoria.services import registrar_evento
from app_dashboard.access import ADMIN_ROLES, STAFF_ROLES, roles_required
from app_egresados.models import AlcanceFuncionario, Egresado, ProgramaFormacion

from .forms import (
    BasePreguntaFormSet,
    EncuestaForm,
    PreguntaForm,
    crear_formulario_respuesta,
    valor_serializable,
)
from .models import DetalleRespuesta, Encuesta, Pregunta, RespuestaEncuesta

PreguntaFormSet = forms.inlineformset_factory(
    Encuesta,
    Pregunta,
    form=PreguntaForm,
    formset=BasePreguntaFormSet,
    extra=3,
    can_delete=True,
    max_num=30,
    validate_max=True,
)


def _encuestas_visibles(usuario):
    """Limita la administración de encuestas por creador y programas."""

    encuestas = Encuesta.objects.all()
    if usuario.is_superuser or usuario.groups.filter(
        name__in=ADMIN_ROLES,
    ).exists():
        return encuestas
    try:
        programas = usuario.alcance_funcionario.programas.all()
    except AlcanceFuncionario.DoesNotExist:
        return encuestas.filter(creada_por=usuario)
    return encuestas.filter(
        programas__in=programas,
    ).distinct() | encuestas.filter(creada_por=usuario)


def _programas_disponibles(usuario):
    """Retorna únicamente programas que el creador puede gestionar."""

    programas = ProgramaFormacion.objects.filter(activo=True)
    if usuario.is_superuser or usuario.groups.filter(
        name__in=ADMIN_ROLES,
    ).exists():
        return programas
    try:
        return usuario.alcance_funcionario.programas.filter(activo=True)
    except AlcanceFuncionario.DoesNotExist:
        return programas.none()


def _puede_editar_encuesta(usuario, encuesta):
    """Aplica mínimo privilegio al mantenimiento de cada encuesta."""

    return (
        usuario.is_superuser
        or usuario.groups.filter(name__in=ADMIN_ROLES).exists()
        or (
            usuario.groups.filter(name='Funcionario').exists()
            and encuesta.creada_por_id == usuario.pk
        )
    )


@login_required
def encuestas_list_view(request):
    """Muestra encuestas que están vigentes o son administrables."""

    if not (
        request.user.is_superuser
        or request.user.groups.filter(
            name__in=STAFF_ROLES + ('Visor', 'Egresado'),
        ).exists()
    ):
        raise PermissionDenied
    es_egresado = request.user.groups.filter(name='Egresado').exists()
    if es_egresado:
        try:
            egresado = request.user.ficha_egresado
        except Egresado.DoesNotExist as error:
            raise PermissionDenied from error
        encuestas = Encuesta.objects.filter(
            publicada=True,
            inicia_en__lte=timezone.localdate(),
            finaliza_en__gte=timezone.localdate(),
        ).filter(
            Q(programas__isnull=True) | Q(programas=egresado.programa)
        ).distinct()
        if not egresado.consentimiento:
            encuestas = encuestas.none()
    else:
        encuestas = _encuestas_visibles(request.user)
    encuestas = list(encuestas.prefetch_related('preguntas'))
    if es_egresado:
        respuestas = set(
            RespuestaEncuesta.objects.filter(
                encuesta__in=encuestas,
                egresado=egresado,
            ).values_list('encuesta_id', flat=True)
        )
        for encuesta in encuestas:
            encuesta.respondida = encuesta.pk in respuestas
    return render(
        request,
        'app_encuestas/app_encuestas_list.html',
        {'encuestas': encuestas, 'es_egresado': es_egresado},
    )


@roles_required(*STAFF_ROLES)
def encuestas_create_view(request):
    """Crea una encuesta y sus preguntas en una transacción."""

    if (
        request.user.groups.filter(name='Funcionario').exists()
        and not request.user.is_superuser
        and not request.user.groups.filter(name__in=ADMIN_ROLES).exists()
        and not _programas_disponibles(request.user).exists()
    ):
        raise PermissionDenied
    form = EncuestaForm(request.POST or None)
    form.fields['programas'].queryset = _programas_disponibles(request.user)
    if request.user.groups.filter(name='Funcionario').exists():
        form.fields['programas'].required = True
    formset = PreguntaFormSet(
        request.POST or None,
        instance=Encuesta(creada_por=request.user),
        prefix='preguntas',
    )
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            encuesta = form.save(commit=False)
            encuesta.creada_por = request.user
            encuesta.save()
            form.save_m2m()
            formset.instance = encuesta
            formset.save()
            registrar_evento(
                request,
                'CREAR_ENCUESTA',
                'Encuesta',
                encuesta.pk,
                {'titulo': encuesta.titulo, 'publicada': encuesta.publicada},
            )
        messages.success(request, 'La encuesta fue creada correctamente.')
        return redirect('encuestas_detail', pk=encuesta.pk)
    return render(
        request,
        'app_encuestas/app_encuestas_form.html',
        {
            'form': form,
            'formset': formset,
            'titulo': 'Crear encuesta',
            'pregunta_tipos': Pregunta.Tipo.choices,
        },
    )


@roles_required(*STAFF_ROLES)
def encuestas_update_view(request, pk):
    """Actualiza una encuesta y sus preguntas si aún no tiene respuestas."""

    encuesta = get_object_or_404(_encuestas_visibles(request.user), pk=pk)
    if not _puede_editar_encuesta(request.user, encuesta):
        raise PermissionDenied
    if encuesta.respuestas.exists():
        messages.error(
            request,
            'No se puede editar una encuesta que ya recibió respuestas.',
        )
        return redirect('encuestas_detail', pk=encuesta.pk)
    form = EncuestaForm(request.POST or None, instance=encuesta)
    form.fields['programas'].queryset = _programas_disponibles(request.user)
    if request.user.groups.filter(name='Funcionario').exists():
        form.fields['programas'].required = True
    formset = PreguntaFormSet(
        request.POST or None,
        instance=encuesta,
        prefix='preguntas',
    )
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            form.save()
            formset.save()
            registrar_evento(
                request,
                'ACTUALIZAR_ENCUESTA',
                'Encuesta',
                encuesta.pk,
                {'titulo': encuesta.titulo},
            )
        messages.success(request, 'La encuesta fue actualizada.')
        return redirect('encuestas_detail', pk=encuesta.pk)
    return render(
        request,
        'app_encuestas/app_encuestas_form.html',
        {
            'form': form,
            'formset': formset,
            'titulo': 'Editar encuesta',
            'pregunta_tipos': Pregunta.Tipo.choices,
            'encuesta': encuesta,
        },
    )


@roles_required(*STAFF_ROLES)
def encuestas_detail_view(request, pk):
    """Muestra la encuesta y, según el rol, su análisis agregado."""

    encuesta = get_object_or_404(_encuestas_visibles(request.user), pk=pk)
    puede_editar = _puede_editar_encuesta(request.user, encuesta)
    respuestas = encuesta.respuestas.count()
    resultados = []
    if puede_editar:
        for pregunta in encuesta.preguntas.all():
            conteo = _contar_respuestas(pregunta)
            resultados.append({'pregunta': pregunta, 'conteo': conteo})
    return render(
        request,
        'app_encuestas/app_encuestas_detail.html',
        {
            'encuesta': encuesta,
            'puede_editar': puede_editar,
            'respuestas': respuestas,
            'resultados': resultados,
        },
    )


def _contar_respuestas(pregunta):
    """Agrupa valores JSON de una pregunta sin exponer a sus participantes."""

    import json
    from collections import Counter

    valores = DetalleRespuesta.objects.filter(
        pregunta=pregunta,
    ).values_list('valor', flat=True)
    acumulados = Counter(
        json.dumps(valor, ensure_ascii=False, sort_keys=True)
        for valor in valores
    )
    return [
        {'valor': valor, 'total': total}
        for valor, total in sorted(
            acumulados.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]


@login_required
def encuestas_answer_view(request, pk):
    """Recibe una respuesta voluntaria de un egresado con consentimiento."""

    if not request.user.groups.filter(name='Egresado').exists():
        raise PermissionDenied
    try:
        egresado = request.user.ficha_egresado
    except Egresado.DoesNotExist as error:
        raise PermissionDenied from error
    encuesta = get_object_or_404(
        Encuesta.objects.filter(
            publicada=True,
            inicia_en__lte=timezone.localdate(),
            finaliza_en__gte=timezone.localdate(),
        ).filter(
            Q(programas__isnull=True) | Q(programas=egresado.programa),
        ).distinct(),
        pk=pk,
    )
    if not egresado.consentimiento:
        messages.error(
            request,
            'Debes tener autorización vigente para participar en encuestas.',
        )
        return redirect('encuestas_list')
    if RespuestaEncuesta.objects.filter(
        encuesta=encuesta,
        egresado=egresado,
    ).exists():
        messages.info(request, 'Ya registraste una respuesta para esta encuesta.')
        return redirect('encuestas_list')

    form = crear_formulario_respuesta(
        encuesta,
        request.POST if request.method == 'POST' else None,
    )
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                respuesta = RespuestaEncuesta.objects.create(
                    encuesta=encuesta,
                    egresado=egresado,
                )
                DetalleRespuesta.objects.bulk_create(
                    [
                        DetalleRespuesta(
                            respuesta=respuesta,
                            pregunta=pregunta,
                            valor=valor_serializable(
                                form.cleaned_data[f'pregunta_{pregunta.pk}'],
                            ),
                        )
                        for pregunta in form.preguntas
                        if f'pregunta_{pregunta.pk}' in form.cleaned_data
                    ],
                )
                registrar_evento(
                    request,
                    'RESPONDER_ENCUESTA',
                    'Encuesta',
                    encuesta.pk,
                    {'respuesta': respuesta.pk},
                )
        except IntegrityError:
            messages.info(request, 'Ya registraste una respuesta para esta encuesta.')
        else:
            messages.success(request, 'Gracias por compartir tu experiencia.')
        return redirect('encuestas_list')
    return render(
        request,
        'app_encuestas/app_encuestas_answer.html',
        {'encuesta': encuesta, 'form': form},
    )


@roles_required(*STAFF_ROLES)
def encuestas_publish_view(request, pk):
    """Publica o cierra una encuesta dentro del alcance del usuario."""

    if request.method != 'POST':
        raise PermissionDenied
    encuesta = get_object_or_404(_encuestas_visibles(request.user), pk=pk)
    if not _puede_editar_encuesta(request.user, encuesta):
        raise PermissionDenied
    encuesta.publicada = not encuesta.publicada
    encuesta.save(update_fields=['publicada'])
    registrar_evento(
        request,
        'PUBLICAR_ENCUESTA' if encuesta.publicada else 'CERRAR_ENCUESTA',
        'Encuesta',
        encuesta.pk,
        {'publicada': encuesta.publicada},
    )
    messages.success(
        request,
        'La encuesta fue publicada.' if encuesta.publicada else 'La encuesta fue cerrada.',
    )
    return redirect('encuestas_detail', pk=encuesta.pk)
