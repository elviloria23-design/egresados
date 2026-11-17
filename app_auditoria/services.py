"""Funciones reutilizables para registrar operaciones."""

from .models import RegistroAuditoria


def registrar_evento(request, accion, entidad, entidad_id='', valores=None):
    """Guarda el actor, IP y valores asociados a una operación crítica."""

    direccion_ip = request.META.get('REMOTE_ADDR')
    return RegistroAuditoria.objects.create(
        usuario=request.user if request.user.is_authenticated else None,
        accion=accion,
        entidad=entidad,
        entidad_id=str(entidad_id),
        valores=valores or {},
        direccion_ip=direccion_ip,
    )
