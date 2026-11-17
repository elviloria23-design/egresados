"""Formularios de emisión y anulación de certificaciones."""

from django import forms

from app_egresados.models import Egresado


class CertificacionForm(forms.Form):
    """Valida egresado, tipo de documento y motivo de emisión."""

    egresado = forms.ModelChoiceField(queryset=Egresado.objects.none())
    tipo = forms.CharField(max_length=120)
    motivo = forms.CharField(
        max_length=300,
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    def __init__(self, *args, egresados=None, **kwargs):
        """Limita la selección de egresados al alcance autorizado."""

        super().__init__(*args, **kwargs)
        if egresados is not None:
            self.fields['egresado'].queryset = egresados


class AnulacionCertificacionForm(forms.Form):
    """Exige motivo para anular una certificación."""

    motivo = forms.CharField(
        max_length=500,
        min_length=8,
        widget=forms.Textarea(attrs={'rows': 3}),
    )


class VerificacionCertificacionForm(forms.Form):
    """Valida formato de UUID antes de consultar la certificación."""

    codigo = forms.UUIDField()
