"""Formularios de configuración y respuesta de encuestas."""

import json

from django import forms
from django.forms import BaseInlineFormSet

from .models import Encuesta, Pregunta


class EncuestaForm(forms.ModelForm):
    """Valida vigencia y público objetivo de una encuesta."""

    class Meta:
        """Define los campos de configuración de la encuesta."""

        model = Encuesta
        fields = (
            'titulo',
            'descripcion',
            'programas',
            'inicia_en',
            'finaliza_en',
        )
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 3}),
            'programas': forms.CheckboxSelectMultiple(),
            'inicia_en': forms.DateInput(attrs={'type': 'date'}),
            'finaliza_en': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean(self):
        """Rechaza rangos de vigencia invertidos."""

        cleaned_data = super().clean()
        inicio = cleaned_data.get('inicia_en')
        fin = cleaned_data.get('finaliza_en')
        if inicio and fin and fin < inicio:
            self.add_error(
                'finaliza_en',
                'La fecha de cierre debe ser igual o posterior al inicio.',
            )
        return cleaned_data


class PreguntaForm(forms.ModelForm):
    """Convierte una lista de opciones legible en una lista validada."""

    opciones_texto = forms.CharField(
        required=False,
        label='Opciones (una por línea)',
        widget=forms.Textarea(attrs={'rows': 3}),
    )

    class Meta:
        """Define los campos de cada pregunta."""

        model = Pregunta
        fields = ('texto', 'tipo', 'obligatoria', 'orden')
        widgets = {
            'texto': forms.TextInput(
                attrs={'placeholder': 'Escribe la pregunta'},
            ),
        }

    def __init__(self, *args, **kwargs):
        """Crea opciones editables a partir de las opciones guardadas."""

        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['opciones_texto'].initial = '\n'.join(
                self.instance.opciones or [],
            )
        else:
            self.fields['orden'].initial = None
            self.fields['obligatoria'].initial = False

    def clean_opciones_texto(self):
        """Valida que las preguntas de selección tengan opciones distintas."""

        opciones = [
            opcion.strip()
            for opcion in self.cleaned_data['opciones_texto'].splitlines()
            if opcion.strip()
        ]
        return list(dict.fromkeys(opciones))

    def clean(self):
        """Exige dos opciones para preguntas de selección."""

        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        opciones = cleaned_data.get('opciones_texto', [])
        if tipo in (Pregunta.Tipo.OPCION, Pregunta.Tipo.MULTIPLE):
            if len(opciones) < 2:
                self.add_error(
                    'opciones_texto',
                    'Incluye al menos dos opciones diferentes.',
                )
        elif opciones:
            self.add_error(
                'opciones_texto',
                'Solo las preguntas de selección admiten opciones.',
            )
        return cleaned_data

    def save(self, commit=True):
        """Guarda opciones en formato estructurado JSON."""

        pregunta = super().save(commit=False)
        pregunta.opciones = self.cleaned_data['opciones_texto']
        if commit:
            pregunta.save()
        return pregunta


class BasePreguntaFormSet(BaseInlineFormSet):
    """Requiere que una encuesta publicada tenga al menos una pregunta."""

    def clean(self):
        """Valida el conjunto de preguntas activas."""

        super().clean()
        if any(self.errors):
            return
        preguntas = [
            form.cleaned_data
            for form in self.forms
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False)
        ]
        if not preguntas:
            raise forms.ValidationError(
                'Agrega por lo menos una pregunta a la encuesta.',
            )


def crear_formulario_respuesta(encuesta, data=None):
    """Construye campos de respuesta con opciones definidas por la encuesta."""

    class RespuestaDinamicaForm(forms.Form):
        """Valida respuestas contra el tipo y opciones configuradas."""

        pass

    for pregunta in encuesta.preguntas.all():
        name = f'pregunta_{pregunta.pk}'
        required = pregunta.obligatoria
        if pregunta.tipo == Pregunta.Tipo.TEXTO:
            field = forms.CharField(
                required=required,
                max_length=4000,
                widget=forms.Textarea(attrs={'rows': 3}),
            )
        elif pregunta.tipo == Pregunta.Tipo.NUMERO:
            field = forms.DecimalField(
                required=required,
                max_digits=12,
                decimal_places=2,
            )
        elif pregunta.tipo == Pregunta.Tipo.SI_NO:
            field = forms.ChoiceField(
                required=required,
                choices=(('', 'Selecciona'), ('si', 'Sí'), ('no', 'No')),
            )
        elif pregunta.tipo == Pregunta.Tipo.OPCION:
            field = forms.ChoiceField(
                required=required,
                choices=[('', 'Selecciona')] + [
                    (opcion, opcion) for opcion in pregunta.opciones
                ],
            )
        else:
            field = forms.MultipleChoiceField(
                required=required,
                choices=[
                    (opcion, opcion) for opcion in pregunta.opciones
                ],
                widget=forms.CheckboxSelectMultiple(),
            )
        RespuestaDinamicaForm.base_fields[name] = field
    form = RespuestaDinamicaForm(data=data)
    form.preguntas = list(encuesta.preguntas.all())
    return form


def valor_serializable(valor):
    """Convierte valores validados del formulario a JSON nativo."""

    return json.loads(json.dumps(valor, default=str))
