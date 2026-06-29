from django.shortcuts import render, redirect
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from reciclac4.core.models import Usuario, Jornada, Inscripcion, Notificacion, Recompensa, CanjeRecompensa, TemaSemanal
from reciclac4.core.forms import InscripcionForm
from .decorators import rol_required


def residente_cat_recompensas(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    recompensas = Recompensa.objects.filter(disponible=True).order_by('-fecha_creacion')
    return render(request, "residente/cat_recompensas.html", {"usuario": usuario, "recompensas": recompensas})


def residente_historial_canjes(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    canjes = CanjeRecompensa.objects.filter(usuario_id=usuario_id).select_related('recompensa') if usuario_id else []
    return render(request, "residente/historial_canjes.html", {"usuario": usuario, "canjes": canjes})


@csrf_exempt
def residente_canje_recompensa(request):
    from django.utils import timezone

    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Método no permitido"})

    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return JsonResponse({"success": False, "error": "Usuario no autenticado"})

    try:
        usuario = Usuario.objects.get(id_usuario=usuario_id)
        recompensa_id = request.POST.get("recompensa_id")
        recompensa = Recompensa.objects.get(id_recompensa=recompensa_id)

        if usuario.puntaje_total < recompensa.puntos_requeridos:
            return JsonResponse({"success": False, "error": "Puntos insuficientes"})

        if recompensa.cantidad_disponible <= 0:
            return JsonResponse({"success": False, "error": "Recompensa agotada"})

        CanjeRecompensa.objects.create(
            usuario=usuario,
            recompensa=recompensa,
            direccion=request.POST.get("direccion", ""),
            barrio=request.POST.get("barrio", ""),
            observaciones=request.POST.get("observaciones", "")
        )

        recompensa.cantidad_disponible -= 1
        recompensa.save(update_fields=['cantidad_disponible'])

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})


def residente_como_participar(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "residente/como_participar.html", {"usuario": usuario})


@rol_required('residente')
def residente_lista_jornadas(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    jornadas = Jornada.objects.all().order_by("-fecha")
    for j in jornadas:
        j.esta_inscrito = j.esta_inscrito(usuario_id) if usuario_id else False
    return render(request, "residente/lista_jornadas.html", {"jornadas": jornadas, "usuario": usuario})


@rol_required('residente')
def residente_inicio(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "residente/inicio.html", {"usuario": usuario})


def perfil_residente(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    from reciclac4.core.models import Puntaje, ResultadoEvaluacion
    puntajes = Puntaje.objects.filter(usuario_id=usuario_id).order_by("-fecha")
    total_puntos = usuario.puntaje_total if usuario else 0
    mayor_puntaje = max([p.puntos for p in puntajes]) if puntajes else 0
    promedio = (sum([p.puntos for p in puntajes]) / puntajes.count()) if puntajes.count() > 0 else 0
    return render(request, "residente/perfil.html", {
        "usuario": usuario,
        "total_puntos": total_puntos,
        "puntajes": puntajes,
        "mayor_puntaje": mayor_puntaje,
        "promedio": promedio
    })


def residente_inscripcion(request, id_jornada):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    jornada = get_object_or_404(Jornada, id_jornada=id_jornada)
    return render(request, "residente/inscripcion.html", {"id_jornada": id_jornada, "usuario": usuario, "jornada": jornada})


def inscribirse_jornada(request, jornada_id):
    from django.utils import timezone
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)

    if request.method == "POST":
        usuario_id = request.session.get("usuario_id")
        form = InscripcionForm(request.POST)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            inscripcion.fecha_inscripcion = timezone.now()
            inscripcion.usuario_id = usuario_id
            inscripcion.save()
            return render(request, "residente/inscripcion.html", {"inscripcion_exitosa": True, "jornada": jornada})
    else:
        form = InscripcionForm(initial={'jornada': jornada.id_jornada})

    return render(request, "residente/inscripcion.html", {"form": form, "jornada": jornada})


def residente_recoleccion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "residente/recoleccion.html", {"usuario": usuario})


def residente_publicacion_foro(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "residente/publicacion_foro.html", {"usuario": usuario})


def residente_index(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "residente/index.html", {"usuario": usuario})


@rol_required('residente')
def residente_educacion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    tema = TemaSemanal.objects.filter(activo=True, vista_destino='residente').first()
    return render(request, "residente/educacion.html", {"usuario": usuario, "tema": tema})


def residente_contacto(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "residente/contacto.html", {"usuario": usuario})


def residente_foro_publicaciones(request):
    from reciclac4.core.models import TemaForo
    publicaciones = TemaForo.objects.select_related('id_usuario').prefetch_related('comentarios__autor').all().order_by('-fecha_publicacion')
    return render(request, "residente/foro_publicaciones.html", {"publicaciones": publicaciones})


def residente_configuracion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "residente/configuracion.html", {"usuario": usuario})


def cambiar_foto(request):
    usuario_id = request.session.get("usuario_id")
    if request.method == "POST" and request.FILES.get("foto"):
        usuario = Usuario.objects.get(id_usuario=usuario_id)
        usuario.foto = request.FILES["foto"]
        usuario.save()
        messages.success(request, "Foto actualizada.")
    return redirect("perfil_residente")


def residente_notificaciones(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    notificaciones = Notificacion.objects.filter(usuario_id=usuario_id).order_by('-fecha_envio') if usuario_id else []
    return render(request, "residente/notificaciones.html", {"usuario": usuario, "notificaciones": notificaciones})


def residente_eliminar_notificacion(request, notificacion_id):
    Notificacion.objects.filter(id_notificacion=notificacion_id).delete()
    return redirect("residente_notificaciones")


def residente_eliminar_todas_notificaciones(request):
    Notificacion.objects.filter(usuario_id=request.session.get("usuario_id")).delete()
    return redirect("residente_notificaciones")


def residente_panel(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    return render(request, "residente/panel.html", {"usuario": usuario})


def residente_detalle_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    return render(request, "residente/detalle_jornada.html", {"jornada": jornada})