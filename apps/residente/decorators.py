from functools import wraps
from django.shortcuts import render, redirect
from reciclac4.core.models import Usuario


def rol_required(roles):
    if isinstance(roles, str):
        roles = [roles]
    roles = [r.strip().lower() for r in roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            usuario_id = request.session.get("usuario_id")
            session_role = request.session.get("usuario_rol")

            if not usuario_id:
                return render(request, "errores/no_sesion.html")

            if session_role:
                if session_role.strip().lower() in roles:
                    return view_func(request, *args, **kwargs)

            try:
                usuario = Usuario.objects.get(id_usuario=usuario_id)
            except Usuario.DoesNotExist:
                return render(request, "errores/no_sesion.html")

            db_role = (usuario.rol or "").strip().lower()
            if db_role in roles:
                request.session['usuario_rol'] = usuario.rol
                return view_func(request, *args, **kwargs)

            return render(request, "errores/no_permiso.html")
        return _wrapped_view
    return decorator