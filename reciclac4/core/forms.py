from django import forms
from .models import Jornada
from .models import Inscripcion
from django import forms
from .models import Usuario
from django.contrib.auth.hashers import make_password
from .models import Puntaje
from .models import Notificacion
from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator, ValidationError
import re

def validate_no_empty(value):
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValidationError('Este campo no puede estar vacío.')

def validate_letras(value):
    if value and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', str(value)):
        raise ValidationError('Este campo solo puede contener letras.')

def validate_alphanumeric(value):
    if value and not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$', str(value)):
        raise ValidationError('Este campo solo puede contener letras y números.')

def validate_telefono(value):
    if value:
        value_clean = re.sub(r'[\s\-\(\)]', '', str(value))
        if not re.match(r'^\d{7,15}$', value_clean):
            raise ValidationError('El teléfono debe tener entre 7 y 15 dígitos.')

def validate_correo(value):
    if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', str(value)):
        raise ValidationError('Ingrese un correo electrónico válido.')

def validate_barrio(value):
    if value and not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-]+$', str(value)):
        raise ValidationError('El barrio contiene caracteres inválidos.')

def clean_field_with_validators(self, field_name, validators):
    value = self.cleaned_data.get(field_name)
    if not value:
        raise ValidationError(f'Este campo no puede estar vacío.')
    for validator in validators:
        try:
            validator(value)
        except ValidationError as e:
            raise ValidationError(e.message)
    return value

class JornadaForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['titulo', 'descripcion', 'direccion', 'barrio', 'tipo_material']:
            if field_name in self.fields:
                self.fields[field_name].required = True
    
    def clean_titulo(self):
        value = self.cleaned_data.get('titulo')
        if not value or not value.strip():
            raise ValidationError('El título no puede estar vacío.')
        if len(value) < 3:
            raise ValidationError('El título debe tener al menos 3 caracteres.')
        if len(value) > 100:
            raise ValidationError('El título no puede exceder 100 caracteres.')
        return value.strip()
    
    def clean_descripcion(self):
        value = self.cleaned_data.get('descripcion')
        if not value or not value.strip():
            raise ValidationError('La descripción no puede estar vacía.')
        if len(value) < 10:
            raise ValidationError('La descripción debe tener al menos 10 caracteres.')
        if len(value) > 500:
            raise ValidationError('La descripción no puede exceder 500 caracteres.')
        return value.strip()
    
    def clean_direccion(self):
        value = self.cleaned_data.get('direccion')
        if not value or not value.strip():
            raise ValidationError('La dirección no puede estar vacía.')
        if len(value) < 5:
            raise ValidationError('La dirección debe tener al menos 5 caracteres.')
        if len(value) > 200:
            raise ValidationError('La dirección no puede exceder 200 caracteres.')
        return value.strip()
    
    def clean_barrio(self):
        value = self.cleaned_data.get('barrio')
        if value and not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-]+$', str(value)):
            raise ValidationError('El barrio contiene caracteres inválidos.')
        return value
    
    def clean_cupo_maximo(self):
        value = self.cleaned_data.get('cupo_maximo')
        if value is None:
            raise ValidationError('El cupo máximo no puede estar vacío.')
        if value < 1:
            raise ValidationError('El cupo máximo debe ser al menos 1.')
        if value > 1000:
            raise ValidationError('El cupo máximo no puede exceder 1000.')
        return value
    
    class Meta:
        model = Jornada
        fields = ['titulo', 'descripcion', 'fecha', 'hora', 'direccion', 'barrio', 'tipo_material', 'cupo_maximo', 'estado']
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'hora': forms.TimeInput(attrs={'type': 'time'}),
        }

class InscripcionForm(forms.ModelForm):
    class Meta:
        model = Inscripcion
        fields = ['usuario', 'jornada']  # ← QUITAMOS estado
        widgets = {
            'usuario': forms.HiddenInput(),
            'jornada': forms.HiddenInput(),
        }

# core/forms.py
class UsuarioForm(forms.ModelForm):
    password_plain = forms.CharField(
        label="Contraseña (si quieres cambiarla)",
        required=False,
        widget=forms.PasswordInput(render_value=False)
    )

    def clean_nombre(self):
        value = self.cleaned_data.get('nombre')
        if not value or not value.strip():
            raise ValidationError('El nombre no puede estar vacío.')
        if len(value) < 2:
            raise ValidationError('El nombre debe tener al menos 2 caracteres.')
        if len(value) > 50:
            raise ValidationError('El nombre no puede exceder 50 caracteres.')
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', value):
            raise ValidationError('El nombre solo puede contener letras.')
        return value.strip()
    
    def clean_apellido(self):
        value = self.cleaned_data.get('apellido')
        if not value or not value.strip():
            raise ValidationError('El apellido no puede estar vacío.')
        if len(value) < 2:
            raise ValidationError('El apellido debe tener al menos 2 caracteres.')
        if len(value) > 50:
            raise ValidationError('El apellido no puede exceder 50 caracteres.')
        if not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', value):
            raise ValidationError('El apellido solo puede contener letras.')
        return value.strip()
    
    def clean_correo(self):
        value = self.cleaned_data.get('correo')
        if not value or not value.strip():
            raise ValidationError('El correo no puede estar vacío.')
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise ValidationError('Ingrese un correo electrónico válido.')
        return value.strip().lower()
    
    def clean_barrio(self):
        value = self.cleaned_data.get('barrio')
        if value and not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-]+$', str(value)):
            raise ValidationError('El barrio contiene caracteres inválidos.')
        return value
    
    class Meta:
        model = Usuario
        fields = [
            'nombre',
            'apellido',
            'correo',
            'fecha_nacimiento',
            'barrio',
            'rol',
            'estado',
            'foto'
        ]

    def save(self, commit=True):
        instance = super().save(commit=False)
        pwd = self.cleaned_data.get('password_plain')
        if pwd:
            instance.contrasena = make_password(pwd)
        if commit:
            instance.save()
        return instance

    
class PuntajeForm(forms.ModelForm):
    def clean_puntos(self):
        value = self.cleaned_data.get('puntos')
        if value is None:
            raise ValidationError('El valor de puntos no puede estar vacío.')
        if value < 1:
            raise ValidationError('El puntaje debe ser al menos 1.')
        if value > 1000:
            raise ValidationError('El puntaje no puede exceder 1000.')
        return value
    
    def clean_motivo(self):
        value = self.cleaned_data.get('motivo')
        if value and not value.strip():
            raise ValidationError('El motivo no puede estar vacío.')
        if value and len(value) > 255:
            raise ValidationError('El motivo no puede exceder 255 caracteres.')
        return value.strip() if value else value
    
    class Meta:
        model = Puntaje
        exclude = ['fecha']

class AsignarPuntajeForm(forms.ModelForm):
    def clean_puntos(self):
        value = self.cleaned_data.get('puntos')
        if value is None:
            raise ValidationError('El valor de puntos no puede estar vacío.')
        if value < 1:
            raise ValidationError('El puntaje debe ser al menos 1.')
        if value > 500:
            raise ValidationError('El puntaje no puede exceder 500.')
        return value
    
    class Meta:
        model = Puntaje
        fields = ['puntos']
        
class PasswordResetRequestForm(forms.Form):
    correo = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "Ingresa tu correo"})
    )

class NotificacionForm(forms.ModelForm):
    usuario = forms.ModelChoiceField(
        queryset=Usuario.objects.all(),
        label="Enviar a:",
        widget=forms.Select(attrs={"class": "form-control"})
    )

    def clean_tipo(self):
        value = self.cleaned_data.get('tipo')
        if not value or not value.strip():
            raise ValidationError('El tipo de notificación no puede estar vacío.')
        return value.strip()
    
    def clean_mensaje(self):
        value = self.cleaned_data.get('mensaje')
        if not value or not value.strip():
            raise ValidationError('El mensaje no puede estar vacío.')
        if len(value) > 500:
            raise ValidationError('El mensaje no puede exceder 500 caracteres.')
        return value.strip()

    class Meta:
        model = Notificacion
        fields = ["usuario", "tipo", "mensaje"]
        widgets = {
            "tipo": forms.TextInput(attrs={"class": "form-control"}),
            "mensaje": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }