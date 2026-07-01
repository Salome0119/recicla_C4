# Recicla Comuna 4 - Plataforma de Gestión de Reciclaje Comunitario

[![Django](https://img.shields.io/badge/Django-5.0-green.svg)](https://www.djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://www.mysql.com/)

## 📋 Tabla de Contenidos

- [Descripción del Proyecto](#descripción-del-proyecto)
- [Características Principales](#características-principales)
- [Arquitectura del Sistema](#arquitectura-del-sistema)
- [Roles y Usuarios](#roles-y-usuarios)
- [Instalación y Configuración](#instalación-y-configuración)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [API y Endpoints](#api-y-endpoints)
- [Modelos de Datos](#modelos-de-datos)
- [Validaciones Implementadas](#validaciones-implementadas)
- [Personalización y Estilos](#personalización-y-estilos)
- [Despliegue](#despliegue)
- [Contribución](#contribución)
- [Licencia](#licencia)

---

## 📖 Descripción del Proyecto

**Recicla Comuna 4** es una plataforma web desarrollada en Django que facilita la gestión de actividades de reciclaje en la Comuna 4 de la ciudad. El sistema permite a los residentes, organizadores y administradores participar activamente en jornadas de reciclaje, canjear recompensas por puntos acumulados, participar en foros comunitarios y acceder a información educativa sobre reciclaje.

La aplicación promueve el reciclaje responsable mediante un sistema de gamificación donde los usuarios acumulan puntos por su participación en actividades, los cuales pueden canjearse por recompensas ofrecidas por el programa.

---

## ✨ Características Principales

### Para Residentes
- **Gestión de Perfil**: Visualización y actualización de información personal, foto de perfil (JPG/PNG) y configuración de notificaciones
- **Jornadas de Reciclaje**: Inscripción a jornadas, registro de recolección de materiales y seguimiento de participación
- **Sistema de Puntos**: Acumulación automática de puntos por participación y visualización de historial de puntajes
- **Recompensas**: Catálogo de recompensas canjeables con sistema de notificaciones
- **Foro Comunitario**: Publicación de temas, comentarios, respuestas anidadas y reacciones (me gusta, no me gusta, me encanta)
- **Educación Ambiental**: Acceso a contenido educativo sobre prácticas de reciclaje

### Para Organizadores
- **Gestión de Jornadas**: Creación y edición de jornadas de reciclaje con cupos limitados
- **Panel de Recompensas**: Creación, edición y eliminación de recompensas
- **Seguimiento de Canjes**: Historial de recompensas canjeadas por usuarios
- **Foro Administrado**: Gestión de publicaciones y denuncias en el foro
- **Estadísticas**: Visualización de métricas de participación

### Para Administradores
- **Panel de Control Total**: Gestión completa de usuarios, jornadas y recompensas
- **Validación de Acciones**: Aprobación de actividades destacadas
- **Gestión de Temas Semanales**: Generación automática de temas educativos con IA
- **Reportes y Estadísticas**: Tableros de analítica con datos de la comunidad

---

## 🏗️ Arquitectura del Sistema

```
recicla_C4-Mejoras-GestionUsuarios/
├── reciclac4/                    # Proyecto principal Django
│   ├── config/                   # Configuración del proyecto
│   │   ├── settings.py          # Configuración principal
│   │   ├── urls.py              # URLs principales
│   │   └── wsgi.py              # WSGI para despliegue
│   └── core/                    # Aplicación base con modelos compartidos
│       ├── models.py            # Modelos principales
│       ├── views.py             # Vistas compartidas
│       ├── forms.py             # Formularios con validaciones
│       └── context_processors/  # Procesadores de contexto
├── apps/                        # Aplicaciones por rol
│   ├── administrador/           # Panel de administrador
│   ├── organizador/             # Panel de organizador
│   ├── residente/               # Panel de residente
│   ├── login/                   # Autenticación personalizada
│   ├── usuario/                 # Vistas públicas
│   └── errores/                 # Manejo de errores
├── static/                      # Archivos estáticos (CSS, JS, imágenes)
└── media_volume/                # Archivos de usuarios (fotos, documentos)
```

---

## 👥 Roles y Usuarios

### Roles del Sistema
| Rol | Descripción | Permisos Principales |
|-----|-------------|-------------------|
| **Administrador** | Control total del sistema | Gestión de usuarios, validación de actividades, temas semanales, reportes |
| **Organizador** | Coordinador de actividades | Gestión de jornadas, recompensas, seguimiento de canjes |
| **Residente** | Usuario participante | Inscripción a jornadas, canje de recompensas, publicaciones en foro |

### Sistema de Autenticación
- Backend personalizado basado en `id_usuario` como identificador único
- Contraseñas encriptadas con `make_password` (Django)
- Sesiones gestionadas mediante `request.session`
- Decorador `@rol_required` para proteger vistas por rol

---

## 🚀 Instalación y Configuración

### Requisitos Previos
- Python 3.11+
- MySQL 8.0+
- pip y virtualenv

### Instalación

```bash
# Clonar el repositorio
git clone https://github.com/usuario/recicla-comuna4.git
cd recicla-comuna4

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con credenciales de base de datos

# Aplicar migraciones
python manage.py migrate

# Crear superusuario (opcional)
python manage.py createsuperuser

# Ejecutar servidor de desarrollo
python manage.py runserver
```

### Variables de Entorno Requeridas

```env
DB_NAME=nombre_base_datos
DB_USER=usuario_mysql
DB_PASSWORD=contraseña_mysql
DB_HOST=host_mysql
DB_PORT=puerto_mysql
DB_SSL_CA=ruta/al/certificado.pem
```

---

## 📁 Estructura del Proyecto

### Aplicación Core (`reciclac4/core/`)
Contiene los modelos principales utilizados por todas las aplicaciones:

- **Usuario**: Modelo principal con información personal, rol, puntos totales
- **Jornada**: Eventos de reciclaje con fecha, hora, dirección, cupo
- **Inscripcion**: Relación entre usuarios y jornadas
- **Recompensa**: Recompensas canjeables por puntos
- **CanjeRecompensa**: Registro de canjes realizados
- **Puntaje**: Historial de puntos acumulados
- **Notificacion**: Sistema de notificaciones
- **TemaForo**: Publicaciones en el foro comunitario
- **Comentario**: Comentarios y respuestas del foro
- **TemaSemanal**: Temas educativos generados por IA

### Apps por Rol

#### Administrador (`apps/administrador/`)
- Dashboard con estadísticas
- Gestión de usuarios
- Creación de jornadas
- Validación de acciones
- Temas semanales IA
- Historial de canjes

#### Organizador (`apps/organizador/`)
- Dashboard de organizador
- Gestión de jornadas
- Gestión de recompensas
- Seguimiento de participantes
- Foro administrado

#### Residente (`apps/residente/`)
- Perfil de usuario
- Lista y detalle de jornadas
- Inscripción a jornadas
- Registro de recolección
- Catálogo de recompensas
- Foro comunitario
- Configuración de cuenta

#### Usuario (`apps/usuario/`)
- Páginas públicas
- Inicio, educación, contacto
- Formulario de registro

---

## 🔌 API y Endpoints

### Autenticación
```
GET  /                     -> Página principal
GET  /login/               -> Formulario de login
POST /login/               -> Procesar login
GET  /logout/              -> Cerrar sesión
```

### Residente
```
GET  /residente/inicio/           -> Dashboard
GET  /residente/perfil/           -> Ver perfil
POST /residente/perfil/cambiar-foto/ -> Cambiar foto (JPG/PNG)
GET  /residente/jornadas/         -> Lista de jornadas
GET  /residente/jornadas/{id}/    -> Detalle de jornada
POST /residente/inscribirse/{id}/ -> Inscribirse a jornada
GET  /residente/recompensas/      -> Catálogo de recompensas
POST /residente/canje/             -> Canjear recompensa
GET  /residente/foro/              -> Publicaciones del foro
POST /residente/foro/              -> Crear publicación
```

### Organizador
```
GET  /organizador/inicio/          -> Dashboard
GET  /organizador/perfil/          -> Ver perfil
POST /organizador/perfil/cambiar-foto/ -> Cambiar foto
GET  /organizador/jornadas/        -> Gestión de jornadas
GET  /organizador/recompensas/     -> Gestión de recompensas
```

### Administrador
```
GET  /admi/inicio/                 -> Dashboard
GET  /admi/perfil/                 -> Ver perfil
POST /admi/perfil/cambiar-foto/    -> Cambiar foto
GET  /admi/usuarios/               -> Gestión de usuarios
GET  /admi/validar-acciones/       -> Validar actividades
```

---

## 🗃️ Modelos de Datos

### Usuario
```python
Usuario:
- id_usuario (PK)
- nombre, apellido
- correo (único)
- contrasena (hash)
- rol (admin, organizador, residente)
- estado (activo, inactivo)
- barrio
- fecha_registro
- puntaje_total
- foto (ImageField)
- recibe_notificaciones_jornadas (Boolean)
- canal_notificacion_push (Boolean)
```

### Jornada
```python
Jornada:
- id_jornada (PK)
- titulo, descripcion
- fecha, hora
- direccion, barrio
- tipo_material
- cupo_maximo
- estado (programada, activa, completada)
```

### Recompensa
```python
Recompensa:
- id_recompensa (PK)
- titulo, descripcion
- puntos_requeridos
- cantidad_disponible
- disponible (Boolean)
- fecha_creacion
- imagen
```

---

## ✅ Validaciones Implementadas

### Validaciones de Foto de Perfil
- **Formatos permitidos**: Solo JPG (`image/jpeg`) y PNG (`image/png`)
- **Mensaje de error**: "El archivo debe ser JPG o PNG."
- **Validación en frontend**: Atributo `accept="image/jpeg,image/png"` en input
- **Validación en backend**: Verificación de `content_type` en vistas

### Validaciones de Formularios
- Campos requeridos validados (nombre, apellido, correo, etc.)
- Longitudes mínimas y máximas (título: 3-100 caracteres, descripción: 10-500)
- Formato de correo electrónico válido
- Teléfono con 7-15 dígitos
- Contraseña mínimo 6 caracteres, con al menos una letra y un número

### Validaciones de Negocio
- No inscribirse dos veces en la misma jornada
- Cupo máximo de jornadas respetado
- Recompensas con stock disponible
- Permisos de edición por autor en foro

---

## 🎨 Personalización y Estilos

### Paleta de Colores
```css
--primary: #2ECC71 (Verde principal)
--secondary: #27AE60 (Verde oscuro)
--dark: #1E5631 (Verde muy oscuro)
--muted: #666666 (Gris para texto secundario)
```

### Archivos CSS Principales
- `estilos.css` - Estilos base y responsive
- `perfil.css` - Estilos del perfil de usuario
- `estilos_residentes.css` - Estilos específicos para residentes
- `publicacion_foro.css` - Estilos del foro

### Responsive Design
- Mobile-first design
- Menú lateral colapsable en móviles
- Tablas adaptables a pantallas pequeñas
- Tipografía mínima 16px en móviles

---

## ☁️ Despliegue

### Requisitos de Producción
- Base de datos MySQL con SSL
- Archivos estáticos recolectados (`python manage.py collectstatic`)
- Variables de entorno configuradas
- Servidor WSGI (Gunicorn, uWSGI)

### Comandos de Despliegue
```bash
# Recolectar archivos estáticos
python manage.py collectstatic --noinput

# Aplicar migraciones
python manage.py migrate

# Reiniciar servidor
# (depende del servicio de hosting)
```

---

## 🤝 Contribución

1. Fork del repositorio
2. Crear rama feature: `git checkout -b feature/nueva-funcionalidad`
3. Commit de cambios: `git commit -m 'Agregar nueva funcionalidad'`
4. Push a la rama: `git push origin feature/nueva-funcionalidad`
5. Abrir Pull Request

---

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver archivo `LICENSE` para más detalles.

---

## 📞 Contacto

- **Email**: reciclacomuna@gmail.com
- **Teléfono**: 315 5959444
- **Repositorio**: [GitHub - Recicla Comuna 4](https://github.com/usuario/recicla-comuna4)

---

*Desarrollado con ❤️ para la Comuna 4 - Promoviendo el reciclaje responsable*‍
