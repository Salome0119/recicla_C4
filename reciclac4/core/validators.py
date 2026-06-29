from django.core.validators import RegexValidator, MinLengthValidator, MaxLengthValidator, ValidationError
import re

def validate_no_empty(value):
    if not value or (isinstance(value, str) and not value.strip()):
        raise ValidationError('Este campo no puede estar vacío.')

def validate_letras(value):
    if value and not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', value):
        raise ValidationError('Este campo solo puede contener letras.')

def validate_alphanumeric(value):
    if value and not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$', value):
        raise ValidationError('Este campo solo puede contener letras y números.')

def validate_telefono(value):
    if value:
        value_clean = re.sub(r'[\s\-\(\)]', '', value)
        if not re.match(r'^\d{7,15}$', value_clean):
            raise ValidationError('El teléfono debe tener entre 7 y 15 dígitos.')

def validate_correo(value):
    if value and not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
        raise ValidationError('Ingrese un correo electrónico válido.')

def validate_barrio(value):
    if value and not re.match(r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-]+$', value):
        raise ValidationError('El barrio contiene caracteres inválidos.')

validate_nombre = [
    MinLengthValidator(2, message='El nombre debe tener al menos 2 caracteres.'),
    MaxLengthValidator(50, message='El nombre no puede exceder 50 caracteres.')
]

validate_apellido = [
    MinLengthValidator(2, message='El apellido debe tener al menos 2 caracteres.'),
    MaxLengthValidator(50, message='El apellido no puede exceder 50 caracteres.')
]

validate_titulo = [
    MinLengthValidator(3, message='El título debe tener al menos 3 caracteres.'),
    MaxLengthValidator(100, message='El título no puede exceder 100 caracteres.')
]

validate_descripcion = [
    MinLengthValidator(10, message='La descripción debe tener al menos 10 caracteres.'),
    MaxLengthValidator(500, message='La descripción no puede exceder 500 caracteres.')
]

validate_direccion = [
    MinLengthValidator(5, message='La dirección debe tener al menos 5 caracteres.'),
    MaxLengthValidator(200, message='La dirección no puede exceder 200 caracteres.')
]

validate_puntos = [
    MinLengthValidator(1, message='El valor de puntos no puede estar vacío.'),
]

validate_cantidad = [
    MinLengthValidator(1, message='La cantidad no puede estar vacía.'),
]