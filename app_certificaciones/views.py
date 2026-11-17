"""Vistas para emitir, consultar y verificar certificaciones."""

import io
from uuid import uuid4
from xml.sax.saxutils import escape

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app_auditoria.services import registrar_evento
from app_dashboard.access import ADMIN_ROLES, STAFF_ROLES
from app_egresados.models import (
    AlcanceFuncionario,
    Egresado,
    ProgramaFormacion,
)

from .forms import (
    AnulacionCertificacionForm,
    CertificacionForm,
    VerificacionCertificacionForm,
)
from .models import Certificacion


def _es_administrativo(usuario):
    """Identifica usuarios institucionales con facultades administrativas."""

    return usuario.is_superuser or usuario.groups.filter(
        name__in=ADMIN_ROLES,
    ).exists()


def _puede_emitir(usuario):
    """Autoriza al administrativo o funcionario con permiso explícito."""

    return (
        _es_administrativo(usuario)
        or (
            usuario.groups.filter(name='Funcionario').exists()
            and usuario.has_perm(
                'app_certificaciones.emitir_certificaciones',
            )
        )
    )


def _egresados_accesibles(usuario):
    """Limita la emisión a egresados activos del programa asignado."""

    egresados = Egresado.objects.filter(activo=True).select_related(
        'programa',
    )
    if _es_administrativo(usuario):
        return egresados
    try:
        programas = usuario.alcance_funcionario.programas.all()
    except AlcanceFuncionario.DoesNotExist:
        return egresados.none()
    return egresados.filter(programa__in=programas)


def _certificaciones_visibles(usuario):
    """Restringe certificados al egresado titular o al equipo con alcance."""

    if usuario.groups.filter(name='Egresado').exists():
        try:
            return Certificacion.objects.filter(
                egresado=usuario.ficha_egresado,
            ).select_related('egresado', 'egresado__programa')
        except Egresado.DoesNotExist as error:
            raise PermissionDenied from error
    return Certificacion.objects.filter(
        egresado__in=_egresados_accesibles(usuario),
    ).select_related('egresado', 'egresado__programa')


def _render_pdf(request, certificado):
    """Genera un PDF de una sola página con enlace verificable."""

    buffer = io.BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.8 * inch,
        leftMargin=0.8 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
        title=f'Certificación {certificado.numero}',
        author='Centro Industrial y de Energías Alternativas · SENA',
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'WalenaTitle',
        parent=styles['Title'],
        textColor=colors.HexColor('#A93200'),
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=26,
        spaceAfter=12,
    )
    subtitle_style = ParagraphStyle(
        'WalenaSubtitle',
        parent=styles['Normal'],
        textColor=colors.HexColor('#56585A'),
        fontSize=10,
        leading=15,
    )
    body_style = ParagraphStyle(
        'WalenaBody',
        parent=styles['BodyText'],
        fontName='Helvetica',
        fontSize=12,
        leading=19,
        alignment=1,
        spaceAfter=15,
    )
    safe_name = escape(certificado.egresado.nombre_completo)
    safe_documento = escape(certificado.egresado.documento)
    safe_program = escape(certificado.egresado.programa.nombre)
    safe_type = escape(certificado.tipo)
    safe_reason = escape(certificado.motivo)
    safe_issuer = escape(
        certificado.emitida_por.get_full_name()
        or certificado.emitida_por.get_username(),
    )
    verification_url = request.build_absolute_uri(
        reverse(
            'certificacion_verify',
            args=[certificado.codigo_verificacion],
        ),
    )
    elements = [
        Paragraph('WALENA · TALENTO Y HOSPITALIDAD', subtitle_style),
        Spacer(1, 0.6 * inch),
        Paragraph('CERTIFICACIÓN', title_style),
        Paragraph(
            'CENTRO INDUSTRIAL Y DE ENERGÍAS ALTERNATIVAS'
            '<br/>SENA · REGIONAL LA GUAJIRA',
            subtitle_style,
        ),
        Spacer(1, 0.55 * inch),
        Paragraph(
            f'El Centro certifica que <b>{safe_name}</b>, identificado(a) '
            f'con documento <b>{safe_documento}</b>, '
            f'es egresado(a) del programa <b>{safe_program}</b>.',
            body_style,
        ),
        Paragraph(
            f'<b>Tipo:</b> {safe_type}<br/>'
            f'<b>Motivo:</b> {safe_reason}',
            body_style,
        ),
    ]
    details = [
        ['Número', certificado.numero],
        [
            'Fecha de emisión',
            timezone.localtime(certificado.emitida_en).strftime('%d/%m/%Y'),
        ],
        ['Estado', certificado.get_estado_display()],
    ]
    table = Table(details, colWidths=[1.6 * inch, 4.7 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F7F5EC')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#56585A')),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E5E1D3')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 9),
    ]))
    elements.extend([
        table,
        Spacer(1, 0.45 * inch),
        Paragraph(
            'Verifica este documento en:<br/>'
            f'<link href="{escape(verification_url)}" color="#006972">'
            f'{escape(verification_url)}</link>'
            f'<br/><b>Código:</b> {certificado.codigo_verificacion}',
            subtitle_style,
        ),
        Spacer(1, 0.25 * inch),
        Paragraph(
            f'Emitido por: {safe_issuer}',
            subtitle_style,
        ),
    ])
    document.build(elements)
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="certificacion-{certificado.numero}.pdf"'
    )
    return response


@login_required
def certificaciones_list_view(request):
    """Muestra certificados propios o del alcance del equipo."""

    if not (
        request.user.groups.filter(
            name__in=STAFF_ROLES + ('Egresado', 'Visor'),
        ).exists()
        or request.user.is_superuser
    ):
        raise PermissionDenied
    return render(
        request,
        'app_certificaciones/app_certificaciones_list.html',
        {
            'certificaciones': _certificaciones_visibles(request.user),
            'puede_emitir': _puede_emitir(request.user),
            'puede_anular': (
                _es_administrativo(request.user)
                or request.user.has_perm(
                    'app_certificaciones.anular_certificaciones',
                )
            ),
        },
    )


@login_required
def certificaciones_create_view(request):
    """Emite un certificado numerado y audita la operación."""

    if not _puede_emitir(request.user):
        raise PermissionDenied
    form = CertificacionForm(
        request.POST or None,
        egresados=_egresados_accesibles(request.user),
    )
    if request.method == 'POST' and form.is_valid():
        certificado = Certificacion.objects.create(
            egresado=form.cleaned_data['egresado'],
            numero=(
                f"CIEA-{timezone.localdate():%Y}-"
                f'{uuid4().hex.upper()}'
            ),
            tipo=form.cleaned_data['tipo'],
            motivo=form.cleaned_data['motivo'],
            emitida_por=request.user,
        )
        registrar_evento(
            request,
            'EMITIR_CERTIFICACION',
            'Certificacion',
            certificado.pk,
            {
                'numero': certificado.numero,
                'egresado': certificado.egresado.documento,
                'tipo': certificado.tipo,
            },
        )
        messages.success(request, 'La certificación fue emitida.')
        return redirect('certificacion_pdf', pk=certificado.pk)
    return render(
        request,
        'app_certificaciones/app_certificaciones_form.html',
        {'form': form},
    )


@login_required
def certificaciones_pdf_view(request, pk):
    """Entrega el PDF solo al titular o a un funcionario autorizado."""

    certificado = get_object_or_404(
        _certificaciones_visibles(request.user),
        pk=pk,
    )
    registrar_evento(
        request,
        'DESCARGAR_CERTIFICACION',
        'Certificacion',
        certificado.pk,
    )
    return _render_pdf(request, certificado)


def certificaciones_verify_view(request, codigo):
    """Permite verificar un documento sin revelar datos personales."""

    form = VerificacionCertificacionForm(
        {'codigo': codigo} if codigo else None,
    )
    certificado = None
    if form.is_valid():
        certificado = Certificacion.objects.filter(
            codigo_verificacion=form.cleaned_data['codigo'],
        ).first()
    return render(
        request,
        'app_certificaciones/app_certificaciones_verify.html',
        {'certificado': certificado, 'codigo': codigo},
    )


@login_required
def certificaciones_anular_view(request, pk):
    """Anula una certificación únicamente por autorización administrativa."""

    if not (
        _es_administrativo(request.user)
        or request.user.has_perm(
            'app_certificaciones.anular_certificaciones',
        )
    ):
        raise PermissionDenied
    if request.method != 'POST':
        raise PermissionDenied
    certificado = get_object_or_404(Certificacion, pk=pk)
    form = AnulacionCertificacionForm(request.POST)
    if form.is_valid() and certificado.estado == Certificacion.Estado.VIGENTE:
        certificado.estado = Certificacion.Estado.ANULADA
        certificado.anulada_por = request.user
        certificado.anulacion_motivo = form.cleaned_data['motivo']
        certificado.anulada_en = timezone.now()
        certificado.save(
            update_fields=[
                'estado',
                'anulada_por',
                'anulacion_motivo',
                'anulada_en',
            ],
        )
        registrar_evento(
            request,
            'ANULAR_CERTIFICACION',
            'Certificacion',
            certificado.pk,
            {
                'anterior': {'estado': Certificacion.Estado.VIGENTE},
                'nuevo': {
                    'estado': Certificacion.Estado.ANULADA,
                    'motivo': certificado.anulacion_motivo,
                },
            },
        )
        messages.success(request, 'La certificación fue anulada.')
    else:
        messages.error(request, 'Indica un motivo para anular el certificado.')
    return redirect('certificaciones_list')


def certificaciones_request_view(request):
    """Muestra la consulta pública para validar un código de certificado."""

    if request.method == 'POST':
        form = VerificacionCertificacionForm(request.POST)
        if form.is_valid():
            return redirect(
                'certificacion_verify',
                codigo=form.cleaned_data['codigo'],
            )
    else:
        form = VerificacionCertificacionForm()
    return render(
        request,
        'app_certificaciones/app_certificaciones_verify.html',
        {'form': form},
    )
