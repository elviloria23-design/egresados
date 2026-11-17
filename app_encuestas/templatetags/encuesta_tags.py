"""Filtros para acceder a campos de respuesta por nombre dinámico."""

from django import template

register = template.Library()


@register.filter
def campo(formulario, nombre):
    """Devuelve el campo de respuesta identificado por su clave."""

    return formulario[nombre]


@register.filter
def campo_pregunta(formulario, pregunta_id):
    """Obtiene el campo dinámico asociado al identificador de una pregunta."""

    return formulario[f'pregunta_{pregunta_id}']
