"""Formularios de publicación de oportunidades."""

from django import forms
from django.utils import timezone

from .models import Oportunidad


class OportunidadForm(forms.ModelForm):
    """Valida los datos obligatorios para publicar una oferta."""

    class Meta:
        """Define los campos editables de la oferta."""

        model = Oportunidad
        fields = (
            'titulo',
            'tipo',
            'descripcion',
            'fuente',
            'enlace',
            'vigente_hasta',
        )
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 5}),
            'vigente_hasta': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_vigente_hasta(self):
        """Rechaza ofertas que ya vencieron al ser publicadas."""

        vigente_hasta = self.cleaned_data['vigente_hasta']
        if vigente_hasta < timezone.localdate():
            raise forms.ValidationError(
                'La fecha de vigencia debe ser hoy o una fecha futura.'
            )
        return vigente_hasta
