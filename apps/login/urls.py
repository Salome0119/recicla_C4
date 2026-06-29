from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("register/", views.register_view, name="registro"),
    path("logout/", views.logout_view, name="logout"),
    path("password_reset/", views.password_reset_request, name="password_reset_request"),
    path("reset_password/<str:token>/", views.password_reset_confirm, name="password_reset_confirm"),
    path("aprobar/<int:id_usuario>/", views.aprobar_usuario, name="aprobar_usuario"),
    path("rechazar/<int:id_usuario>/", views.rechazar_usuario, name="rechazar_usuario"),
    path("aprobar-todos/", views.aprobar_todos_organizadores, name="aprobar_todos"),
]