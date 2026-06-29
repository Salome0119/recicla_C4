function validateField(field, rules) {
    var errors = [];
    var value = field.value.trim();
    
    if (rules.required && value === '') {
        errors.push(rules.requiredMessage || 'Este campo no puede estar vacío.');
        return errors;
    }
    
    if (value === '') {
        return errors;
    }
    
    if (rules.minLength && value.length < rules.minLength) {
        errors.push(rules.minLengthMessage || 'Mínimo ' + rules.minLength + ' caracteres.');
    }
    
    if (rules.maxLength && value.length > rules.maxLength) {
        errors.push(rules.maxLengthMessage || 'Máximo ' + rules.maxLength + ' caracteres.');
    }
    
    if (rules.pattern && !rules.pattern.test(value)) {
        errors.push(rules.patternMessage || 'Formato inválido.');
    }
    
    if (rules.letras && !/^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/.test(value)) {
        errors.push('Solo se permiten letras.');
    }
    
    if (rules.telefono && !/^\d{7,15}$/.test(value.replace(/[\s\-\(\)]/g, ''))) {
        errors.push('Teléfono inválido (7-15 dígitos).');
    }
    
    if (rules.correo && !/^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value)) {
        errors.push('Correo electrónico inválido.');
    }
    
    if (rules.barrio && !/^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s\-]+$/.test(value)) {
        errors.push('Barrio contiene caracteres inválidos.');
    }
    
    return errors;
}

function showFieldErrors(field, errors) {
    var container = field.closest('.form-group') || field.parentElement;
    var errorEl = container.querySelector('.error-message');
    
    if (errors.length > 0) {
        field.classList.add('is-invalid');
        if (!errorEl) {
            errorEl = document.createElement('div');
            errorEl.className = 'error-message text-danger small mt-1';
            container.appendChild(errorEl);
        }
        errorEl.textContent = errors[0];
        return false;
    } else {
        field.classList.remove('is-invalid');
        if (errorEl) {
            errorEl.remove();
        }
        return true;
    }
}

function validateForm(formId, fieldRules) {
    var form = document.getElementById(formId);
    if (!form) return true;
    
    var isValid = true;
    
    for (var fieldName in fieldRules) {
        var field = form.querySelector('[name="' + fieldName + '"]');
        if (field) {
            var errors = validateField(field, fieldRules[fieldName]);
            if (!showFieldErrors(field, errors)) {
                isValid = false;
            }
        }
    }
    
    return isValid;
}

document.addEventListener('DOMContentLoaded', function() {
    var forms = document.querySelectorAll('form[data-validate="true"]');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            var rules = JSON.parse(form.dataset.rules || '{}');
            if (!validateForm(form.id, rules)) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    var nombreFields = document.querySelectorAll('[name="nombre"]');
    nombreFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            showFieldErrors(this, validateField(this, {
                required: true,
                requiredMessage: 'El nombre no puede estar vacío.',
                minLength: 2,
                minLengthMessage: 'Mínimo 2 caracteres.',
                maxLength: 50,
                maxLengthMessage: 'Máximo 50 caracteres.',
                letras: true
            }));
        });
    });
    
    var apellidoFields = document.querySelectorAll('[name="apellido"]');
    apellidoFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            showFieldErrors(this, validateField(this, {
                required: true,
                requiredMessage: 'El apellido no puede estar vacío.',
                minLength: 2,
                minLengthMessage: 'Mínimo 2 caracteres.',
                maxLength: 50,
                maxLengthMessage: 'Máximo 50 caracteres.',
                letras: true
            }));
        });
    });
    
    var correoFields = document.querySelectorAll('[name="correo"]');
    correoFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            showFieldErrors(this, validateField(this, {
                required: true,
                requiredMessage: 'El correo no puede estar vacío.',
                correo: true,
                correoMessage: 'Correo electrónico inválido.'
            }));
        });
    });
    
    var tituloFields = document.querySelectorAll('[name="titulo"]');
    tituloFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            showFieldErrors(this, validateField(this, {
                required: true,
                requiredMessage: 'El título no puede estar vacío.',
                minLength: 3,
                minLengthMessage: 'Mínimo 3 caracteres.',
                maxLength: 100,
                maxLengthMessage: 'Máximo 100 caracteres.'
            }));
        });
    });
    
    var descripcionFields = document.querySelectorAll('[name="descripcion"]');
    descripcionFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            showFieldErrors(this, validateField(this, {
                required: true,
                requiredMessage: 'La descripción no puede estar vacía.',
                minLength: 10,
                minLengthMessage: 'Mínimo 10 caracteres.',
                maxLength: 500,
                maxLengthMessage: 'Máximo 500 caracteres.'
            }));
        });
    });
    
    var direccionFields = document.querySelectorAll('[name="direccion"]');
    direccionFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            showFieldErrors(this, validateField(this, {
                required: true,
                requiredMessage: 'La dirección no puede estar vacía.',
                minLength: 5,
                minLengthMessage: 'Mínimo 5 caracteres.',
                maxLength: 200,
                maxLengthMessage: 'Máximo 200 caracteres.'
            }));
        });
    });
    
    var barrioFields = document.querySelectorAll('[name="barrio"]');
    barrioFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            showFieldErrors(this, validateField(this, {
                barrio: true,
                barrioMessage: 'El barrio contiene caracteres inválidos.'
            }));
        });
    });
    
    var puntosFields = document.querySelectorAll('[name="puntos"]');
    puntosFields.forEach(function(field) {
        field.addEventListener('blur', function() {
            var value = parseInt(this.value);
            var errors = [];
            if (!this.value || this.value === '') {
                errors.push('El valor de puntos no puede estar vacío.');
            } else if (value < 1) {
                errors.push('El puntaje debe ser al menos 1.');
            } else if (value > 1000) {
                errors.push('El puntaje no puede exceder 1000.');
            }
            showFieldErrors(this, errors);
        });
    });
});