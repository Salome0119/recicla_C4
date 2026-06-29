from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from reciclac4.core.models import Usuario, Jornada, Recompensa, CanjeRecompensa, Notificacion, TemaSemanal
from reciclac4.core.forms import JornadaForm
from .decorators import rol_required


@rol_required('organizador')
def organizador_asistencia(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "organizador/asistencia.html", {"usuario": usuario})


def organizador_creacion_jornadas(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    if request.method == "POST":
        titulo = request.POST.get("titulo")
        descripcion = request.POST.get("descripcion")
        fecha = request.POST.get("fecha")
        hora = request.POST.get("hora")
        barrio = request.POST.get("barrio")
        direccion = request.POST.get("direccion")
        tipo_material = request.POST.get("tipo_material")
        cupo_maximo = request.POST.get("cupo_maximo")
        estado = request.POST.get("estado")

        Jornada.objects.create(
            titulo=titulo,
            descripcion=descripcion,
            fecha=fecha,
            hora=hora,
            barrio=barrio,
            direccion=direccion,
            tipo_material=tipo_material,
            cupo_maximo=cupo_maximo,
            estado=estado
        )

        return redirect("organizador_creacion_jornadas")

    jornadas = Jornada.objects.all().order_by("-fecha")

    return render(request, "organizador/creacionjornadas.html", {
        "jornadas": jornadas,
        "usuario": usuario
    })


@rol_required('organizador')
def organizador_publicacion_foro(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "organizador/publicacion_foro.html", {"usuario": usuario})


@rol_required('organizador')
def organizador_recoleccion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "organizador/recoleccion.html", {"usuario": usuario})


def organizador_recompensa(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "organizador/recompensa.html", {"usuario": usuario})


def organizador_recompensa_canjes(request, recompensa_id):
    from reciclac4.core.models import Recompensa, CanjeRecompensa
    recompensa = get_object_or_404(Recompensa, id_recompensa=recompensa_id)
    canjes = CanjeRecompensa.objects.filter(recompensa=recompensa).select_related('usuario')
    return render(request, "organizador/recompensa_canjes.html", {"recompensa": recompensa, "canjes": canjes})


def organizador_historial_canjes(request):
    return render(request, "organizador/historial_canjes.html")


@rol_required('organizador')
def organizador_inicio(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "organizador/inicio.html", {"usuario": usuario})


@rol_required('organizador')
def organizador_educacion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    tema = TemaSemanal.objects.filter(activo=True, vista_destino='organizador').first()
    return render(request, "organizador/educacion.html", {"usuario": usuario, "tema": tema})


@rol_required('organizador')
def organizador_contacto(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "organizador/contacto.html", {"usuario": usuario})


@rol_required('organizador')
def organizador_foro_publicaciones(request):
    from reciclac4.core.models import TemaForo
    publicaciones = TemaForo.objects.select_related('id_usuario').all().order_by('-fecha_publicacion')
    return render(request, "organizador/foro_publicaciones.html", {"publicaciones": publicaciones})


@rol_required('organizador')
def organizador_configuracion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "organizador/configuracion.html", {"usuario": usuario})


@rol_required('organizador')
def perfil_organizador(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    from reciclac4.core.models import Puntaje
    puntajes = Puntaje.objects.filter(usuario_id=usuario_id).order_by("-fecha")
    total_puntos = usuario.puntaje_total if usuario else 0
    mayor_puntaje = max([p.puntos for p in puntajes]) if puntajes else 0
    promedio = (sum([p.puntos for p in puntajes]) / puntajes.count()) if puntajes.count() > 0 else 0
    return render(request, "organizador/perfil.html", {
        "usuario": usuario,
        "total_puntos": total_puntos,
        "puntajes": puntajes,
        "mayor_puntaje": mayor_puntaje,
        "promedio": promedio
    })


def cambiar_foto_organizador(request):
    usuario_id = request.session.get("usuario_id")
    if request.method == "POST" and request.FILES.get("foto"):
        usuario = Usuario.objects.get(id_usuario=usuario_id)
        usuario.foto = request.FILES["foto"]
        usuario.save()
        messages.success(request, "Foto actualizada.")
    return redirect("perfil_organizador")


def organizador_notificaciones(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    notificaciones = Notificacion.objects.filter(usuario_id=usuario_id).order_by('-fecha_envio') if usuario_id else []
    return render(request, "organizador/notificaciones.html", {"usuario": usuario, "notificaciones": notificaciones})


@rol_required('organizador')
def organizador_eliminar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    if jornada.estado != "pendiente":
        messages.error(request, "Solo se pueden cancelar jornadas con estado pendiente.")
        return redirect("organizador_creacion_jornadas")
    jornada.estado = "cancelada"
    jornada.save()
    messages.success(request, "Jornada cancelada correctamente.")
    return redirect("organizador_creacion_jornadas")


@rol_required('organizador')
def organizador_modificar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    if jornada.estado != "pendiente":
        messages.error(request, "Solo se pueden editar jornadas con estado pendiente.")
        return redirect("organizador_creacion_jornadas")
    if request.method == "POST":
        form = JornadaForm(request.POST, instance=jornada)
        if form.is_valid():
            form.save()
            messages.success(request, "Jornada modificada correctamente.")
            return redirect("organizador_creacion_jornadas")
    else:
        form = JornadaForm(instance=jornada)
    return render(request, "organizador/modificar_jornada.html", {"form": form, "jornada": jornada})


@rol_required('organizador')
def organizador_detalle_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    return render(request, "organizador/detalle_jornada.html", {"jornada": jornada})