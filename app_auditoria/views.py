"""Vistas administrativas de consulta y exportación de auditoría."""

import csv
import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.dateparse import parse_date

from app_auditoria.services import registrar_evento
from app_dashboard.access import ADMIN_ROLES

from .models import RegistroAuditoria


def _verificar_administrador(usuario):
    """Exige superusuario o grupo administrativo para consultar la bitácora."""

    if not (
        usuario.is_superuser
        or usuario.groups.filter(name__in=ADMIN_ROLES).exists()
    ):
        raise PermissionDenied


def _filtrar_registros(request):
    """Aplica filtros acotados de acción, entidad y rango de fechas."""

    registros = RegistroAuditoria.objects.select_related('usuario').all()
    accion = request.GET.get('accion', '').strip()[:80]
    entidad = request.GET.get('entidad', '').strip()[:100]
    desde = parse_date(request.GET.get('desde', ''))
    hasta = parse_date(request.GET.get('hasta', ''))
    if accion:
        registros = registros.filter(accion=accion)
    if entidad:
        registros = registros.filter(entidad__icontains=entidad)
    if desde:
        registros = registros.filter(creado_en__date__gte=desde)
    if hasta:
        registros = registros.filter(creado_en__date__lte=hasta)
    filtros = {
        'accion': accion,
        'entidad': entidad,
        'desde': desde,
        'hasta': hasta,
    }
    return registros, filtros


@login_required
def auditoria_list_view(request):
    """Muestra eventos administrativos filtrados con paginación."""

    _verificar_administrador(request.user)
    registros, filtros = _filtrar_registros(request)
    registrar_evento(
        request,
        'CONSULTAR_AUDITORIA',
        'RegistroAuditoria',
        valores={
            'accion': filtros['accion'],
            'entidad': filtros['entidad'],
        },
    )
    return render(
        request,
        'app_auditoria/app_auditoria_list.html',
        {'registros': registros[:200], 'filtros': filtros},
    )


@login_required
def auditoria_export_view(request):
    """Exporta eventos de auditoría únicamente para personal administrativo."""

    _verificar_administrador(request.user)
    registros, _ = _filtrar_registros(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="auditoria.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow([
        'Fecha',
        'Usuario',
        'Acción',
        'Entidad',
        'Identificador',
        'Dirección IP',
        'Valores',
    ])
    for registro in registros.iterator():
        writer.writerow([
            registro.creado_en.isoformat(),
            _proteger_formula(
                registro.usuario.get_username()
                if registro.usuario
                else 'Sistema'
            ),
            _proteger_formula(registro.accion),
            _proteger_formula(registro.entidad),
            _proteger_formula(registro.entidad_id),
            registro.direccion_ip or '',
            _proteger_formula(
                json.dumps(registro.valores, ensure_ascii=False),
            ),
        ])
    registrar_evento(
        request,
        'EXPORTAR_AUDITORIA',
        'RegistroAuditoria',
        valores={'filtros': request.GET.dict()},
    )
    return response


def _proteger_formula(valor):
    """Evita que datos de auditoría se ejecuten como fórmulas en CSV."""

    texto = str(valor or '')
    if texto.lstrip().startswith(('=', '+', '-', '@')):
        return f"'{texto}"
    return texto
