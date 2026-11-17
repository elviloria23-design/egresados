"""Vistas públicas y administrativas de oportunidades."""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from app_auditoria.services import registrar_evento
from app_dashboard.access import STAFF_ROLES, roles_required

from .forms import OportunidadForm
from .models import Oportunidad


def oportunidades_list_view(request):
    """Lista oportunidades cuya vigencia no ha expirado."""

    oportunidades = Oportunidad.objects.filter(
        publicada=True,
        vigente_hasta__gte=timezone.localdate(),
    )
    tipo = request.GET.get('tipo', '')
    if tipo in Oportunidad.Tipo.values:
        oportunidades = oportunidades.filter(tipo=tipo)
    return render(
        request,
        'app_oportunidades/app_oportunidades_list.html',
        {
            'oportunidades': oportunidades,
            'tipos': Oportunidad.Tipo.choices,
            'tipo_seleccionado': tipo,
            'puede_gestionar': (
                request.user.is_authenticated
                and (
                    request.user.is_superuser
                    or request.user.groups.filter(
                        name__in=STAFF_ROLES,
                    ).exists()
                )
            ),
        },
    )


def oportunidades_detail_view(request, pk):
    """Muestra el detalle únicamente si la oferta sigue vigente."""

    oportunidad = get_object_or_404(
        Oportunidad,
        pk=pk,
        publicada=True,
        vigente_hasta__gte=timezone.localdate(),
    )
    return render(
        request,
        'app_oportunidades/app_oportunidades_detail.html',
        {'oportunidad': oportunidad},
    )


@roles_required(*STAFF_ROLES)
def oportunidades_create_view(request):
    """Publica una oportunidad con responsable, fuente y vigencia."""

    form = OportunidadForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        oportunidad = form.save(commit=False)
        oportunidad.responsable = request.user
        oportunidad.save()
        registrar_evento(
            request,
            'PUBLICAR',
            'Oportunidad',
            oportunidad.pk,
            {
                'titulo': oportunidad.titulo,
                'tipo': oportunidad.tipo,
                'fuente': oportunidad.fuente,
                'vigente_hasta': oportunidad.vigente_hasta.isoformat(),
            },
        )
        messages.success(request, 'La oportunidad fue publicada.')
        return redirect('oportunidades_detail', pk=oportunidad.pk)
    return render(
        request,
        'app_oportunidades/app_oportunidades_form.html',
        {'form': form, 'titulo': 'Publicar oportunidad'},
    )


@roles_required(*STAFF_ROLES)
def oportunidades_update_view(request, pk):
    """Actualiza una oportunidad manteniendo su trazabilidad."""

    oportunidad = get_object_or_404(Oportunidad, pk=pk)
    if (
        not request.user.is_superuser
        and not request.user.groups.filter(
            name__in=('Administrador', 'Administrativo'),
        ).exists()
        and oportunidad.responsable_id != request.user.pk
    ):
        raise PermissionDenied
    form = OportunidadForm(request.POST or None, instance=oportunidad)
    if request.method == 'POST' and form.is_valid():
        anterior = {
            'titulo': oportunidad.titulo,
            'tipo': oportunidad.tipo,
            'fuente': oportunidad.fuente,
            'vigente_hasta': oportunidad.vigente_hasta.isoformat(),
        }
        oportunidad = form.save()
        nuevo = {
            'titulo': oportunidad.titulo,
            'tipo': oportunidad.tipo,
            'fuente': oportunidad.fuente,
            'vigente_hasta': oportunidad.vigente_hasta.isoformat(),
        }
        registrar_evento(
            request,
            'ACTUALIZAR',
            'Oportunidad',
            oportunidad.pk,
            {'anterior': anterior, 'nuevo': nuevo},
        )
        messages.success(request, 'La oportunidad fue actualizada.')
        return redirect('oportunidades_detail', pk=oportunidad.pk)
    return render(
        request,
        'app_oportunidades/app_oportunidades_form.html',
        {'form': form, 'titulo': 'Editar oportunidad'},
    )


@roles_required(*STAFF_ROLES)
def oportunidades_unpublish_view(request, pk):
    """Despublica una oferta sin eliminar el registro."""

    if request.method != 'POST':
        raise PermissionDenied
    oportunidad = get_object_or_404(Oportunidad, pk=pk)
    if (
        not request.user.is_superuser
        and not request.user.groups.filter(
            name__in=('Administrador', 'Administrativo'),
        ).exists()
        and oportunidad.responsable_id != request.user.pk
    ):
        raise PermissionDenied
    oportunidad.publicada = False
    oportunidad.save(update_fields=['publicada'])
    registrar_evento(
        request,
        'DESPUBLICAR',
        'Oportunidad',
        oportunidad.pk,
        {'anterior': {'publicada': True}, 'nuevo': {'publicada': False}},
    )
    messages.success(request, 'La oportunidad fue despublicada.')
    return redirect('oportunidades_list')
