from django.urls import path
from . import views

urlpatterns = [
    path("organizador/asistencia/", views.organizador_asistencia, name="organizador_asistencia"),
    path("organizador/creacionjornadas/", views.organizador_creacion_jornadas, name="organizador_creacion_jornadas"),
    path("organizador/foro/", views.organizador_publicacion_foro, name="organizador_publicacion_foro"),
    path("organizador/recoleccion/", views.organizador_recoleccion, name="organizador_recoleccion"),
    path("organizador/recompensa/", views.organizador_recompensa, name="organizador_recompensa"),
    path("organizador/recompensa/<int:recompensa_id>/canjes/", views.organizador_recompensa_canjes, name="organizador_recompensa_canjes"),
    path("organizador/historial-canjes/", views.organizador_historial_canjes, name="organizador_historial_canjes"),
    path("organizador/inicio/", views.organizador_inicio, name="organizador_inicio"),
    path("organizador/educacion/", views.organizador_educacion, name="organizador_educacion"),
    path("organizador/contacto/", views.organizador_contacto, name="organizador_contacto"),
    path("organizador/foro/publicaciones/", views.organizador_foro_publicaciones, name="organizador_foro_publicaciones"),
    path("organizador/configuracion/", views.organizador_configuracion, name="organizador_configuracion"),
    path("organizador/perfil/", views.perfil_organizador, name="perfil_organizador"),
    path("organizador/perfil/cambiar-foto/", views.cambiar_foto_organizador, name="cambiar_foto_organizador"),
    path("organizador/notificaciones/", views.organizador_notificaciones, name="organizador_notificaciones"),
    path("organizador/jornadas/modificar/<int:jornada_id>/", views.organizador_modificar_jornada, name="organizador_modificar_jornada"),
    path("organizador/jornadas/eliminar/<int:jornada_id>/", views.organizador_eliminar_jornada, name="organizador_eliminar_jornada"),
    path("organizador/jornadas/detalle/<int:jornada_id>/", views.organizador_detalle_jornada, name="organizador_detalle_jornada"),
]