"""
Django settings for reciclac4 project.
"""

from pathlib import Path
import os
import sys


# Build paths inside the project.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Añadir la carpeta raíz al path para que Python encuentre los módulos
sys.path.append(str(BASE_DIR))

SECRET_KEY = 'django-insecure-4pqo=-lc(p=_743py%&ivl(ooac2z80dsad#y&)vb6kg$708)1'
DEBUG = True
ALLOWED_HOSTS = ['recicla-c4.onrender.com', '127.0.0.1', 'localhost']

# --- INSTALLED_APPS CORREGIDO ---
# Eliminamos 'apps.core' y añadimos 'apps.organizador' que sí existe
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    'reciclac4.core',

    'apps.administrador',
    'apps.errores',
    'apps.login',
    'apps.organizador',
    'apps.residente',
    'apps.usuario',
]

SITE_ID = 1

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'reciclac4.config.urls'
WSGI_APPLICATION = 'reciclac4.config.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
'OPTIONS': {
                'context_processors': [
                    'django.template.context_processors.debug',
                    'django.template.context_processors.request',
                    'django.contrib.auth.context_processors.auth',
                    'django.contrib.messages.context_processors.messages',
                    'reciclac4.core.context_processors.usuario_context',
                ],
            },
    },
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'defaultdb',
        'USER': 'avnadmin',
        'PASSWORD': 'AVNS_c9XX9y7lqWLWI1xclKT',
        'HOST': 'mysql-2e7073e1-rc4.k.aivencloud.com',
        'PORT': 11080,
        'OPTIONS': {
            'ssl': {'ca': 'ca.pem'},
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        }
    }
}

# Test database (SQLite)
import os
if os.environ.get('DJANGO_TEST') == '1':
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

AUTHENTICATION_BACKENDS = [
    'apps.login.auth_backends.UsuarioBackend',
    'django.contrib.auth.backends.ModelBackend',
]

# Si tenías un backend personalizado, debe estar en alguna de tus apps existentes.
# Si no lo encuentras, comenta esta línea para probar el arranque.
# AUTHENTICATION_BACKENDS = ['apps.usuario.backends.UsuariosBackend'] 

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Email configuration - SMTP Gmail
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'reciclacomuna@gmail.com'
EMAIL_HOST_PASSWORD = 'tzjo ixob tlxs olwi'
DEFAULT_FROM_EMAIL = 'reciclacomuna@gmail.com'