from django.urls import path
from . import views

urlpatterns = [
    path("residente/cat_recompensas/", views.residente_cat_recompensas, name="residente_cat_recompensas"),
    path("residente/historial-canjes/", views.residente_historial_canjes, name="residente_historial_canjes"),
    path("residente/canje/recompensa/", views.residente_canje_recompensa, name="residente_canje_recompensa"),
    path("residente/como-participar/", views.residente_como_participar, name="residente_como_participar"),
    path("residente/lista-jornadas/", views.residente_lista_jornadas, name="residente_lista_jornadas"),
    path("residente/inscripcion/<int:id_jornada>/", views.residente_inscripcion, name="residente_inscripcion"),
    path("residente/inscribirse/<int:jornada_id>/", views.inscribirse_jornada, name="inscribirse_jornada"),
    path("residente/inicio/", views.residente_inicio, name="residente_inicio"),
    path("residente/panel/", views.residente_panel, name="residente_panel"),
    path("residente/puntaje/", views.perfil_residente, name="perfil_residente"),
    path("residente/recoleccion/", views.residente_recoleccion, name="residente_recoleccion"),
    path("residente/foro/", views.residente_publicacion_foro, name="residente_publicacion_foro"),
    path("residente/index/", views.residente_index, name="residente_index"),
    path("residente/educacion/", views.residente_educacion, name="residente_educacion"),
    path("residente/contacto/", views.residente_contacto, name="residente_contacto"),
    path("residente/foro/publicaciones/", views.residente_foro_publicaciones, name="residente_foro_publicaciones"),
    path("residente/configuracion/", views.residente_configuracion, name="residente_configuracion"),
    path("residente/cambiar-foto/", views.cambiar_foto, name="cambiar_foto"),
    path("residente/notificaciones/", views.residente_notificaciones, name="residente_notificaciones"),
    path("residente/notificaciones/eliminar/<int:notificacion_id>/", views.residente_eliminar_notificacion, name="residente_eliminar_notificacion"),
    path("residente/notificaciones/eliminar-todas/", views.residente_eliminar_todas_notificaciones, name="residente_eliminar_todas_notificaciones"),
    path("residente/jornadas/detalle/<int:jornada_id>/", views.residente_detalle_jornada, name="residente_detalle_jornada"),
]