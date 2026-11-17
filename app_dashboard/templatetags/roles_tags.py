"""Filtros para evaluar grupos de usuario en plantillas."""

from django import template

register = template.Library()


@register.filter
def has_any_group(user, group_names):
    """Indica si el usuario pertenece a alguno de los grupos listados."""

    if not user.is_authenticated:
        return False
    names = [name.strip() for name in group_names.split(',') if name.strip()]
    return user.is_superuser or user.groups.filter(name__in=names).exists()
