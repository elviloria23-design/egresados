"""Decoradores de acceso basados en grupos y permisos."""

from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def roles_required(*roles):
    """Permite vistas a superusuarios o usuarios con los roles indicados."""

    def decorator(view_func):
        """Aplica autenticación y validación de grupo a la vista."""

        @login_required
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            """Deniega el acceso sin un rol institucional permitido."""

            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            if request.user.groups.filter(name__in=roles).exists():
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return wrapped_view

    return decorator


ADMIN_ROLES = ('Administrador', 'Administrativo')
STAFF_ROLES = ADMIN_ROLES + ('Funcionario',)
VIEWER_ROLES = STAFF_ROLES + ('Visor',)
