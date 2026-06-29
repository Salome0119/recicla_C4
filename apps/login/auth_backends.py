from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.hashers import check_password
from reciclac4.core.models import Usuario


class UsuarioBackend(ModelBackend):
    def authenticate(self, request, correo=None, password=None, **kwargs):
        if correo is None or password is None:
            return None
        
        try:
            usuario = Usuario.objects.get(correo=correo)
        except Usuario.DoesNotExist:
            return None
        
        if check_password(password, usuario.contrasena):
            return usuario
        return None

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(id_usuario=user_id)
        except Usuario.DoesNotExist:
            return None

    def get_user_permissions(self, user_obj, obj=None):
        return set()

    def has_perm(self, user_obj, perm, obj=None):
        return True

    def has_module_perms(self, user_obj, app_label):
        return True
    
    def user_can_authenticate(self, user):
        return True
    
    def _update_last_login(self, request, user):
        pass