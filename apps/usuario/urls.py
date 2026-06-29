from django.urls import path
from . import views

urlpatterns = [
    path("", views.usuario_inicio, name="index"),
    path("usuario/como-participar/", views.usuario_como_participar, name="usuario_como_participar"),
    path("usuario/educacion/", views.usuario_educacion, name="usuario_educacion"),
    path("usuario/contacto/", views.usuario_contacto, name="usuario_contacto"),
    path("usuario/foro/publicaciones/", views.usuario_foro_publicaciones, name="usuario_foro_publicaciones"),
    path("foro/comentar/<int:tema_id>/", views.usuario_comentar, name="usuario_comentar"),
    path("foro/denunciar/<int:tema_id>/", views.usuario_denunciar, name="usuario_denunciar"),
    path("foro/reaccionar/<int:tema_id>/", views.usuario_reaccionar, name="usuario_reaccionar"),
]