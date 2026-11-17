"""Formularios de registro y seguimiento de egresados."""

from django import forms
from django.utils import timezone

from .models import Egresado, IntentoContacto, ProgramaFormacion


class EgresadoForm(forms.ModelForm):
    """Valida elegibilidad, consentimiento y datos del egresado."""

    elegibilidad_verificada = forms.BooleanField(
        required=True,
        label='Confirmo que culminó y aprobó formación titulada',
    )
    consentimiento = forms.BooleanField(
        required=False,
        label='Autorizó el tratamiento de sus datos personales',
    )

    class Meta:
        """Define los campos permitidos en el registro."""

        model = Egresado
        fields = (
            'documento',
            'nombres',
            'apellidos',
            'correo',
            'telefono',
            'municipio',
            'programa',
            'fecha_grado',
            'elegibilidad_verificada',
            'consentimiento',
            'consentimiento_sensible',
        )
        widgets = {
            'fecha_grado': forms.DateInput(attrs={'type': 'date'}),
            'consentimiento_sensible': forms.CheckboxInput(),
        }

    def __init__(self, *args, programas=None, **kwargs):
        """Limita los programas a los autorizados para el usuario."""

        super().__init__(*args, **kwargs)
        if programas is not None:
            self.fields['programa'].queryset = programas
        self.fields['programa'].queryset = (
            self.fields['programa'].queryset.filter(activo=True)
        )

    def clean_documento(self):
        """Normaliza el documento para mantener su unicidad."""

        return self.cleaned_data['documento'].strip().replace(' ', '').upper()

    def clean(self):
        """Valida el consentimiento separado para datos sensibles."""

        cleaned_data = super().clean()
        if (
            self.instance._state.adding
            and not cleaned_data.get('consentimiento')
        ):
            self.add_error(
                'consentimiento',
                'La autorización de tratamiento es necesaria para el '
                'registro.',
            )
        if (
            cleaned_data.get('consentimiento_sensible')
            and not cleaned_data.get('consentimiento')
        ):
            self.add_error(
                'consentimiento',
                'El consentimiento sensible requiere autorización general.',
            )
        return cleaned_data

    def save(self, commit=True):
        """Registra fecha de autorización al guardar el consentimiento."""

        egresado = super().save(commit=False)
        if egresado.consentimiento:
            if not egresado.consentimiento_fecha:
                egresado.consentimiento_fecha = timezone.now()
        else:
            egresado.consentimiento_fecha = None
        if commit:
            egresado.save()
            self.save_m2m()
        return egresado


class IntentoContactoForm(forms.ModelForm):
    """Captura un intento de contacto con trazabilidad."""

    class Meta:
        """Define los datos documentables del seguimiento."""

        model = IntentoContacto
        fields = ('fecha', 'medio', 'resultado', 'observacion')
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'observacion': forms.Textarea(attrs={'rows': 3}),
        }


class CambioEstadoForm(forms.Form):
    """Solicita el nuevo estado y su justificación obligatoria."""

    estado = forms.ChoiceField(choices=Egresado.Estado.choices)
    justificacion = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        min_length=8,
    )


class MotivoForm(forms.Form):
    """Valida el motivo de una baja lógica."""

    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        min_length=8,
    )


class CargaMasivaForm(forms.Form):
    """Valida un archivo de importación antes de procesar sus filas."""

    archivo = forms.FileField(
        help_text='Archivo UTF-8 CSV de hasta 5 MB y 5.000 registros.',
    )

    def clean_archivo(self):
        """Limita tamaño y extensión del archivo de carga."""

        archivo = self.cleaned_data['archivo']
        if archivo.size > 5 * 1024 * 1024:
            raise forms.ValidationError(
                'El archivo no puede superar los 5 MB.',
            )
        if not archivo.name.lower().endswith('.csv'):
            raise forms.ValidationError(
                'El formato permitido es CSV.',
            )
        return archivo


class AutogestionEgresadoForm(forms.Form):
    """Limita la autogestión a contacto y situación laboral reportada."""

    correo = forms.EmailField()
    telefono = forms.CharField(max_length=30, required=False)
    municipio = forms.CharField(max_length=100, required=False)
    estado = forms.ChoiceField(choices=Egresado.Estado.choices)
    consentimiento = forms.BooleanField(
        required=False,
        label='Autorizo el tratamiento de mis datos personales',
    )
    consentimiento_sensible = forms.BooleanField(
        required=False,
        label='Autorizo por separado el tratamiento de datos sensibles',
    )

    def clean(self):
        """Impide autorizar datos sensibles sin consentimiento general."""

        cleaned_data = super().clean()
        if (
            cleaned_data.get('consentimiento_sensible')
            and not cleaned_data.get('consentimiento')
        ):
            self.add_error(
                'consentimiento',
                'El consentimiento sensible requiere autorización general.',
            )
        return cleaned_data
