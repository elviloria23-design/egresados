"""Vistas públicas, autenticación y tablero de indicadores."""

from calendar import monthrange
from datetime import date
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from app_egresados.models import Egresado
from app_oportunidades.models import Oportunidad
from app_auditoria.services import registrar_evento

from .access import ADMIN_ROLES


def fecha_limite_seguimiento(hoy=None):
    """Devuelve el día equivalente de hace once meses calendario."""

    hoy = hoy or timezone.localdate()
    indice_mes = hoy.year * 12 + hoy.month - 1 - 11
    anio, mes_cero = divmod(indice_mes, 12)
    mes = mes_cero + 1
    dia = min(hoy.day, monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def home_view(request):
    """Muestra la portada pública o dirige usuarios autenticados al tablero."""

    if request.user.is_authenticated:
        return redirect('dashboard')
    oportunidades = Oportunidad.objects.filter(
        publicada=True,
        vigente_hasta__gte=timezone.localdate(),
    )[:3]
    return render(
        request,
        'app_dashboard/home.html',
        {'oportunidades': oportunidades},
    )


def login_view(request):
    """Autentica al usuario y registra el inicio de sesión."""

    if request.user.is_authenticated:
        return redirect('dashboard')
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        username = form.cleaned_data.get('username')
        password = form.cleaned_data.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            registrar_evento(request, 'INICIO_SESION', 'Usuario', user.pk)
            next_url = request.POST.get('next') or request.GET.get('next', '')
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect('dashboard')
        form.add_error(None, 'No fue posible validar las credenciales.')
    return render(
        request,
        'app_dashboard/login.html',
        {'form': form, 'next': request.GET.get('next', '')},
    )


@login_required
def logout_view(request):
    """Cierra la sesión únicamente mediante una solicitud POST protegida."""

    if request.method != 'POST':
        raise PermissionDenied
    usuario_id = request.user.pk
    registrar_evento(request, 'CIERRE_SESION', 'Usuario', usuario_id)
    logout(request)
    messages.success(request, 'Has cerrado tu sesión de forma segura.')
    return redirect('home')


@login_required
def dashboard_view(request):
    """Calcula indicadores institucionales sin exponer datos individuales."""

    is_admin = (
        request.user.is_superuser
        or request.user.groups.filter(name__in=ADMIN_ROLES).exists()
    )
    is_viewer = is_admin or request.user.groups.filter(
        name__in=('Visor', 'Funcionario'),
    ).exists()
    if not is_viewer:
        raise PermissionDenied

    egresados = Egresado.objects.filter(activo=True)
    if not is_admin:
        alcance = getattr(request.user, 'alcance_funcionario', None)
        programas = alcance.programas.all() if alcance else []
        egresados = egresados.filter(programa__in=programas)

    total = egresados.count()
    seguimiento_vencido = egresados.filter(
        ultima_actualizacion__lte=fecha_limite_seguimiento(),
    ).count()
    estados = [
        {
            'codigo': estado,
            'nombre': nombre,
            'cantidad': egresados.filter(estado=estado).count(),
            'porcentaje': round(
                egresados.filter(estado=estado).count() * 100 / total
            ) if total else 0,
        }
        for estado, nombre in Egresado.Estado.choices
    ]
    return render(
        request,
        'app_dashboard/dashboard.html',
        {
            'total_egresados': total,
            'vinculados': egresados.filter(
                estado=Egresado.Estado.VINCULADO_LABORAL,
            ).count(),
            'emprendedores': egresados.filter(
                estado=Egresado.Estado.EMPRENDEDOR,
            ).count(),
            'seguimiento_vencido': seguimiento_vencido,
            'estados': estados,
            'oportunidades_activas': Oportunidad.objects.filter(
                publicada=True,
                vigente_hasta__gte=timezone.localdate(),
            ).count(),
            'egresados_recientes': (
                egresados.select_related('programa').order_by('-creado_en')[:5]
            ),
        },
    )
