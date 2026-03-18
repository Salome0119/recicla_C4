from django.contrib.auth.hashers import check_password
from .models import Usuario

class UsuariosBackend:
    """
    Autentica contra la tabla usuarios de MySQL Workbench.
    """
    def authenticate(self, request, correo=None, contrasena=None):
        try:
            user = Usuario.objects.get(correo=correo)
        except Usuario.DoesNotExist:
            return None

        # asumiendo que contrasena está hasheada con PBKDF2 o similar:
        if check_password(contrasena, user.contrasena):
            # devolvemos el objeto Usuario para uso interno; no es un User de django.contrib.auth
            return user
        # si tus contraseñas están en texto plano (NO recomendado), usa:
        # if user.contrasena == contrasena: return user

        return None

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None
