from reciclac4.core.models import Usuario

def usuario_context(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return {"usuario": usuario}