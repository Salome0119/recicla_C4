from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import re
from django.shortcuts import render, redirect
from django.contrib import messages
from reciclac4.core.models import Usuario, Jornada, Recompensa, CanjeRecompensa, Notificacion, TemaForo, Inscripcion, Asistencia, AccionDestacada, Puntaje, UserChangeLog, TemaSemanal, ResultadoEvaluacion
from reciclac4.core.forms import JornadaForm, PuntajeForm, AsignarPuntajeForm, UsuarioForm
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, Max, Q
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from django.http import HttpResponse, JsonResponse
import openpyxl
import io
from xhtml2pdf import pisa
from django.template.loader import render_to_string
from .decorators import rol_required
from django.core.mail import send_mail
import re
from django.contrib.auth.hashers import check_password, make_password
from openai import OpenAI

def _enviar_notificaciones_automaticas_foro(publicacion, usuario):
    try:
        usuarios = Usuario.objects.filter(rol__in=['residente', 'organizador', 'administrador'])
        for u in usuarios:
            Notificacion.objects.create(
                usuario=u,
                tipo='foro',
                mensaje=f'Nueva publicación en foro: {publicacion.titulo}',
            )
    except Exception:
        pass

def _enviar_notificaciones_automaticas_jornada(jornada, accion):
    try:
        usuarios = Usuario.objects.filter(rol__in=['residente', 'organizador', 'administrador'])
        for u in usuarios:
            Notificacion.objects.create(
                usuario=u,
                tipo='jornada',
                mensaje=f'Jornada {accion}: {jornada.titulo}',
            )
    except Exception:
        pass

def _porcentaje_ocupacion_jornada(jornada):
    inscritos = Inscripcion.objects.filter(jornada=jornada, estado='activa').count()
    if jornada.cupo_maximo and jornada.cupo_maximo > 0:
        return inscritos / jornada.cupo_maximo
    return 0

@rol_required('administrador')
def admin_panel(request):
    if not request.session.get("usuario_id"):
        return redirect("login")
    return render(request, "administrador/asistencia.html")

@rol_required('administrador')
def admi_inicio(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    return render(request, "administrador/inicio.html", {"usuario": usuario})

@rol_required('administrador')
def admin_users_list(request):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    try:
        user = Usuario.objects.get(id_usuario=uid)
        if user.rol != "administrador":
            messages.error(request, "No tienes permisos.")
            return redirect("admi_inicio")
    except Usuario.DoesNotExist:
        return redirect("login")

    q = request.GET.get("q", "").strip()
    rol = request.GET.get("rol", "")
    estado = request.GET.get("estado", "")
    page = int(request.GET.get("page", 1))
    per_page = int(request.GET.get("per_page", 10))

    users_qs = Usuario.objects.all().order_by('-fecha_registro')

    if q:
        users_qs = users_qs.filter(
            Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(correo__icontains=q)
        )
    if rol:
        users_qs = users_qs.filter(rol=rol)
    if estado:
        users_qs = users_qs.filter(estado=estado)

    paginator = Paginator(users_qs, per_page)
    page_obj = paginator.get_page(page)

    context = {
        "usuario": user,
        "users": page_obj,
        "q": q,
        "rol": rol,
        "estado": estado,
        "page_obj": page_obj,
        "per_page": per_page,
    }
    return render(request, "administrador/usuarios_list.html", context)

@rol_required('administrador')
def admin_users_create(request):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            nuevo = form.save(commit=False)
            pwd = request.POST.get("password_plain")
            if pwd:
                nuevo.contrasena = make_password(pwd)
            else:
                nuevo.contrasena = make_password("Cambiar123!")
            nuevo.save()
            UserChangeLog.objects.create(
                usuario=nuevo,
                quien=f"{usuario_actual.nombre} {usuario_actual.apellido}",
                accion="crear",
                detalle=f"Creado por admin id={usuario_actual.id_usuario}"
            )
            messages.success(request, "Usuario creado.")
            return redirect("admin_users_list")
    else:
        form = UsuarioForm()

    return render(request, "administrador/usuarios_form.html", {"usuario": usuario_actual, "form": form, "crear": True})

@rol_required('administrador')
def admin_users_edit(request, id_usuario):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)

    if request.method == "POST":
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            form.save()
            UserChangeLog.objects.create(
                usuario=usuario,
                quien=f"{usuario_actual.nombre} {usuario_actual.apellido}",
                accion="editar",
                detalle="Editado por admin"
            )
            messages.success(request, "Usuario actualizado.")
            return redirect("admin_users_list")
    else:
        form = UsuarioForm(instance=usuario)

    return render(request, "administrador/usuarios_form.html", {"usuario": usuario_actual, "form": form, "crear": False, "usuario_obj": usuario})

@rol_required('administrador')
def admin_users_suspend_confirm(request, id_usuario):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    if usuario.estado == "suspendido":
        messages.warning(request, "El usuario ya está suspendido.")
        return redirect("admin_users_list")
    
    return render(request, "administrador/suspender_confirm.html", {"usuario": usuario_actual, "usuario_suspend": usuario})

@rol_required('administrador')
def admin_users_suspend(request, id_usuario):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    
    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()
        if not motivo:
            messages.error(request, "Debe ingresar un motivo.")
            return render(request, "administrador/suspender_confirm.html", {"usuario": usuario_actual, "usuario_suspend": usuario})
        
        usuario.estado = "suspendido"
        usuario.save()
        UserChangeLog.objects.create(
            usuario=usuario, 
            quien=f"{usuario_actual.nombre} {usuario_actual.apellido}", 
            accion="suspender", 
            detalle=f"Suspensión: {motivo}"
        )
        messages.success(request, f"Usuario suspendido. Motivo: {motivo}")
    return redirect("admin_users_list")

def admin_users_restore(request, id_usuario):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    usuario.estado = "activo"
    usuario.save()
    UserChangeLog.objects.create(usuario=usuario, quien=f"{usuario_actual.nombre} {usuario_actual.apellido}", accion="restaurar", detalle="Restaurado por administrador")
    messages.success(request, "Usuario reactivado.")
    return redirect("admin_users_deleted")

@rol_required('administrador')
def admin_users_deleted(request):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    usuarios = Usuario.objects.filter(estado="suspendido").order_by("-fecha_registro")
    return render(request, "administrador/usuarios_deleted.html", {"usuario": usuario_actual, "usuarios": usuarios})

@rol_required('administrador')
def admin_users_export_xlsx(request):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    usuarios = Usuario.objects.all().order_by("id_usuario")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ID", "Nombre", "Apellido", "Correo", "Rol", "Estado", "Fecha registro"])
    for u in usuarios:
        ws.append([u.id_usuario, u.nombre, u.apellido, u.correo, u.rol, u.estado, u.fecha_registro])

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    response = HttpResponse(stream.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response['Content-Disposition'] = 'attachment; filename=usuarios.xlsx'
    return response

@rol_required('administrador')
def admin_users_export_pdf(request):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    usuarios = Usuario.objects.all().order_by("id_usuario")
    html = render_to_string("administrador/usuarios_pdf.html", {"usuarios": usuarios})
    result = io.BytesIO()
    pdf = pisa.pisaDocument(io.BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return HttpResponse(result.getvalue(), content_type='application/pdf')
    else:
        messages.error(request, "Error generando PDF")
        return redirect("admin_users_list")

@rol_required('administrador')
def admin_users_api_search(request):
    q = request.GET.get("q", "").strip()
    rol = request.GET.get("rol", "")
    estado = request.GET.get("estado", "")
    qs = Usuario.objects.all().order_by('-fecha_registro')
    if q:
        qs = qs.filter(Q(nombre__icontains=q) | Q(apellido__icontains=q) | Q(correo__icontains=q))
    if rol:
        qs = qs.filter(rol=rol)
    if estado:
        qs = qs.filter(estado=estado)

    data = []
    for u in qs[:200]:
        data.append({
            "id": u.id_usuario,
            "nombre": u.nombre,
            "apellido": u.apellido,
            "correo": u.correo,
            "rol": u.rol,
            "estado": u.estado,
        })
    from django.http import JsonResponse
    return JsonResponse({"results": data})

@rol_required('administrador')
def panel_usuarios(request):
    busqueda = request.GET.get('q', '')
    estado_filtro = request.GET.get('estado', '')
    page_number = request.GET.get('page', 1)
    per_page = 10

    uid = request.session.get("usuario_id")
    usuario_actual = Usuario.objects.filter(id_usuario=uid).first() if uid else None

    usuarios_qs = Usuario.objects.exclude(estado='suspendido')

    if busqueda:
        usuarios_qs = usuarios_qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(correo__icontains=busqueda)
        )

    if estado_filtro:
        usuarios_qs = usuarios_qs.filter(estado=estado_filtro)

    paginator = Paginator(usuarios_qs, per_page)
    usuarios = paginator.get_page(page_number)

    suspendidos_qs = Usuario.objects.filter(estado='suspendido')
    paginator_sus = Paginator(suspendidos_qs, per_page)
    suspendidos = paginator_sus.get_page(page_number)

    if request.method == 'POST':
        form = PuntajeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('panel_usuarios')
    else:
        form = PuntajeForm()

    return render(request, 'administrador/usuarios.html', {
        'usuario': usuario_actual,
        'usuarios': usuarios,
        'suspendidos': suspendidos,
        'busqueda': busqueda,
        'estado_filtro': estado_filtro,
        'form': form
    })

@rol_required('administrador')
def agregar_usuario(request):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        apellido = request.POST.get("apellido", "").strip()
        correo = request.POST.get("correo", "").strip()
        contrasena = request.POST.get("contrasena", "").strip()
        rol = request.POST.get("rol")
        estado = request.POST.get("estado")

        errors = []
        
        if not nombre:
            errors.append("El nombre no puede estar vacío.")
        elif len(nombre) < 2:
            errors.append("El nombre debe tener al menos 2 caracteres.")
        elif len(nombre) > 50:
            errors.append("El nombre no puede exceder 50 caracteres.")
        elif not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', nombre):
            errors.append("El nombre solo puede contener letras.")
        
        if not apellido:
            errors.append("El apellido no puede estar vacío.")
        elif len(apellido) < 2:
            errors.append("El apellido debe tener al menos 2 caracteres.")
        elif len(apellido) > 50:
            errors.append("El apellido no puede exceder 50 caracteres.")
        elif not re.match(r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$', apellido):
            errors.append("El apellido solo puede contener letras.")
        
        if not correo:
            errors.append("El correo no puede estar vacío.")
        elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', correo):
            errors.append("Ingrese un correo electrónico válido.")
        elif Usuario.objects.filter(correo=correo).exists():
            messages.error(request, "El correo ya está registrado.")
            return redirect("agregar_usuario")
        
        if not contrasena:
            errors.append("La contraseña no puede estar vacía.")
        elif len(contrasena) < 8:
            errors.append("La contraseña debe tener al menos 8 caracteres.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return render(request, "administrador/usuarios_agregar.html", {"usuario": usuario_actual})

        nuevo = Usuario.objects.create(
            nombre=nombre,
            apellido=apellido,
            correo=correo,
            contrasena=make_password(contrasena),
            rol=rol,
            estado=estado
        )

        UserChangeLog.objects.create(
            usuario=nuevo,
            quien=f"{usuario_actual.nombre} {usuario_actual.apellido}",
            accion="crear",
            detalle=f"Creado por admin id={usuario_actual.id_usuario}"
        )

        messages.success(request, "Usuario creado correctamente.")
        return redirect("panel_usuarios")

    return render(request, "administrador/usuarios_agregar.html", {"usuario": usuario_actual})

@rol_required('administrador')
def editar_usuario(request, id):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")
    usuario = get_object_or_404(Usuario, id_usuario=id)
    if request.method == "POST":
        usuario.nombre = request.POST.get("nombre", usuario.nombre)
        usuario.apellido = request.POST.get("apellido", usuario.apellido)
        usuario.correo = request.POST.get("correo", usuario.correo)
        usuario.rol = request.POST.get("rol", usuario.rol)
        usuario.estado = request.POST.get("estado", usuario.estado)
        usuario.save()
        messages.success(request, "Usuario actualizado.")
        return redirect("admin_users_list")
    return render(request, "administrador/usuarios_editar.html", {"usuario": usuario_actual, "usuario_obj": usuario})

@rol_required('administrador')
def suspender_usuario(request, id):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")
    usuario = get_object_or_404(Usuario, id_usuario=id)
    if request.method == "POST":
        motivo = request.POST.get("motivo", "").strip()
        usuario.estado = "suspendido"
        usuario.save()
        UserChangeLog.objects.create(usuario=usuario, quien=f"{usuario_actual.nombre}", accion="suspender", detalle=motivo)
        messages.success(request, "Usuario suspendido.")
        return redirect("admin_users_list")
    return render(request, "administrador/suspender_confirm.html", {"usuario": usuario_actual, "usuario_suspend": usuario})

@rol_required('administrador')
def eliminar_usuario(request, id_usuario):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    usuario.estado = "suspendido"
    usuario.save()
    UserChangeLog.objects.create(
        usuario=usuario,
        quien=f"{usuario_actual.nombre} {usuario_actual.apellido}",
        accion="eliminar",
        detalle="Usuario eliminado/suspendido"
    )
    messages.success(request, "Usuario eliminado.")
    return redirect("admin_users_list")

def reactivar_usuario(request, id):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")

    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    usuario = get_object_or_404(Usuario, id_usuario=id)
    usuario.estado = "activo"
    usuario.save()

    UserChangeLog.objects.create(
        usuario=usuario,
        quien=f"{usuario_actual.nombre} {usuario_actual.apellido}",
        accion="reactivar",
        detalle="Usuario reactivado"
    )

    messages.success(request, "Usuario reactivado correctamente.")
    return redirect("panel_usuarios")

@rol_required('administrador')
def perfil_admin(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    return render(request, "administrador/perfil.html", {"usuario": usuario})

@rol_required('administrador')
def cambiar_foto_admin(request):
    usuario_id = request.session.get("usuario_id")
    if request.method == "POST" and request.FILES.get("foto"):
        usuario = Usuario.objects.get(id_usuario=usuario_id)
        usuario.foto = request.FILES["foto"]
        usuario.save()
        messages.success(request, "Foto actualizada.")
    return redirect("perfil_admin")

def admi_notificaciones(request):
    usuario_id = request.session.get("usuario_id")
    uid = request.session.get("usuario_id")
    usuario_actual = Usuario.objects.filter(id_usuario=uid).first() if uid else None

    if not uid:
        return redirect("login")
    
    usuarios = Usuario.objects.all()
    barrios = Usuario.objects.values_list('barrio', flat=True).distinct()
    roles = [choice[0] for choice in Usuario.ROL_CHOICES]

    query = request.GET.get('buscar', '')
    tipo_filtro = request.GET.get('tipo', '')
    usuario_filtro = request.GET.get('usuario', '')
    barrio_filtro = request.GET.get('barrio', '')
    rol_filtro = request.GET.get('rol', '')
    page_number = request.GET.get('page', 1)

    notificaciones_qs = Notificacion.objects.select_related('usuario').all().order_by('-fecha_envio')

    if query:
        notificaciones_qs = notificaciones_qs.filter(
            Q(usuario__nombre__icontains=query) |
            Q(usuario__apellido__icontains=query) |
            Q(mensaje__icontains=query)
        )
    if tipo_filtro:
        notificaciones_qs = notificaciones_qs.filter(tipo=tipo_filtro)
    if usuario_filtro:
        notificaciones_qs = notificaciones_qs.filter(usuario_id=usuario_filtro)
    if barrio_filtro:
        notificaciones_qs = notificaciones_qs.filter(usuario__barrio=barrio_filtro)
    if rol_filtro:
        notificaciones_qs = notificaciones_qs.filter(usuario__rol=rol_filtro)

    paginator = Paginator(notificaciones_qs, 20)
    page_obj = paginator.get_page(page_number)

    if request.method == "POST":
        destino = request.POST.get("destino")
        tipo = request.POST.get("tipo")
        mensaje = request.POST.get("mensaje")

        usuarios_a_notificar = Usuario.objects.none()

        if destino == "usuario":
            usuario_id_envio = request.POST.get("usuario_id")
            if usuario_id_envio:
                usuarios_a_notificar = Usuario.objects.filter(id_usuario=usuario_id_envio)
        elif destino == "barrio":
            barrio_envio = request.POST.get("barrio_envio")
            if barrio_envio:
                usuarios_a_notificar = Usuario.objects.filter(barrio=barrio_envio)
        elif destino == "todos_barrios":
            usuarios_a_notificar = Usuario.objects.all()
        elif destino == "rol":
            rol_envio = request.POST.get("rol_envio")
            if rol_envio:
                usuarios_a_notificar = Usuario.objects.filter(rol=rol_envio)

        for u in usuarios_a_notificar:
            Notificacion.objects.create(
                usuario=u,
                tipo=tipo,
                mensaje=mensaje,
                canal='web'
            )

        messages.success(request, "Notificaciones enviadas correctamente.")
        return redirect('admi_notificaciones')

    return render(request, "administrador/notificaciones.html", {
        "usuario": usuario_actual,
        "usuarios": usuarios,
        "barrios": barrios,
        "roles": roles,
        "notificaciones": page_obj,
        "page_obj": page_obj,
        "query": query,
        "tipo_filtro": tipo_filtro,
        "usuario_filtro": usuario_filtro,
        "barrio_filtro": barrio_filtro,
        "rol_filtro": rol_filtro,
    })

@rol_required('administrador')
def historial_puntaje(request, id_usuario):
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)
    puntajes = Puntaje.objects.filter(usuario=usuario).order_by('-fecha')
    return render(request, "administrador/historial_puntaje.html", {"usuario": usuario, "puntajes": puntajes})

@rol_required('administrador')
def asignar_puntaje(request):
    if request.method == "POST":
        form = AsignarPuntajeForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Puntaje asignado.")
            return redirect("panel_usuarios")
    else:
        form = AsignarPuntajeForm()
    return render(request, "administrador/asignar_puntaje.html", {"usuario": Usuario.objects.filter(id_usuario=request.session.get("usuario_id")).first(), "form": form})

@rol_required('administrador')
def admi_detalle_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    return render(request, "administrador/detalle_jornada.html", {"usuario": Usuario.objects.filter(id_usuario=request.session.get("usuario_id")).first(), "jornada": jornada})

@rol_required('administrador')
def admi_creacion_jornadas(request):
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

        return redirect("admi_creacion_jornadas")

    jornadas = Jornada.objects.all().order_by("-fecha")

    return render(request, "administrador/creacionjornadas.html", {
        "usuario": usuario,
        "jornadas": jornadas
    })

@rol_required('administrador')
def admi_publicacion_foro(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None

    if request.method == "POST":
        titulo = request.POST.get("titulo")
        contenido = request.POST.get("contenido")

        if not usuario_id:
            messages.error(request, "Debe iniciar sesión para publicar.")
            return redirect("login")

        try:
            usuario = Usuario.objects.get(id_usuario=usuario_id)

            publicacion = TemaForo.objects.create(
                titulo=titulo,
                contenido=contenido,
                id_usuario=usuario,
                fecha_publicacion=timezone.now()
            )
            _enviar_notificaciones_automaticas_foro(publicacion, usuario)

            messages.success(request, "¡Publicación creada exitosamente! 🎉")
            return redirect("admi_foro_publicaciones")

        except Exception as e:
            messages.error(request, f"Error al guardar la publicación: {e}")

    return render(request, "administrador/publicacion_foro.html", {"usuario": usuario})

@rol_required('administrador')
def admi_foro_publicaciones(request):
    FECHA_CORTE = timezone.datetime(2025, 11, 23, tzinfo=timezone.get_current_timezone())

    publicaciones = TemaForo.objects.filter(
        fecha_publicacion__gte=FECHA_CORTE
    ).order_by("-fecha_publicacion")
    
    return render(request, "administrador/foro_publicaciones.html", {
        "publicaciones": publicaciones
    })

@rol_required('administrador')
def admi_editar_publicacion(request, publicacion_id):
    publicacion = get_object_or_404(TemaForo, id_tema=publicacion_id)
    
    if request.method == "POST":
        titulo = request.POST.get("titulo")
        contenido = request.POST.get("contenido")
        
        if titulo and contenido:
            publicacion.titulo = titulo
            publicacion.contenido = contenido
            publicacion.save()
            messages.success(request, "✅ Publicación actualizada correctamente.")
            return redirect('admi_foro_publicaciones')
        else:
            messages.error(request, "El título y el contenido son obligatorios.")
    
    return render(request, "administrador/editar_publicacion.html", {
        "publicacion": publicacion
    })

@rol_required('administrador')
def admi_eliminar_publicacion(request, publicacion_id):
    publicacion = get_object_or_404(TemaForo, id_tema=publicacion_id)
    
    if request.method == "POST":
        titulo = publicacion.titulo
        publicacion.delete()
        messages.success(request, f"✅ Publicación '{titulo}' eliminada correctamente.")
        return redirect('admi_foro_publicaciones')
    
    return redirect('admi_foro_publicaciones')

@rol_required('administrador')
def admi_recoleccion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    return render(request, "administrador/recoleccion.html", {"usuario": usuario})

@rol_required('administrador')
def admi_recompensa(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None

    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        descripcion = request.POST.get('descripcion')
        puntos_requeridos = request.POST.get('puntos_requeridos')
        cantidad_disponible = request.POST.get('cantidad_disponible')
        imagen = request.FILES.get('imagen')
        
        if titulo and descripcion and puntos_requeridos and cantidad_disponible:
            Recompensa.objects.create(
                titulo=titulo,
                descripcion=descripcion,
                puntos_requeridos=int(puntos_requeridos),
                cantidad_disponible=int(cantidad_disponible),
                imagen=imagen,
                disponible=True
            )
            messages.success(request, 'Recompensa creada correctamente.')
        else:
            messages.error(request, 'Todos los campos son requeridos.')
        
        return redirect('admi_recompensa')
    
    recompensas = Recompensa.objects.all().order_by('-fecha_creacion')
    return render(request, "administrador/recompensa.html", {"usuario": usuario, "recompensas": recompensas})

@rol_required('administrador')
def admi_recompensa_canjes(request, recompensa_id):
    recompensa = get_object_or_404(Recompensa, id_recompensa=recompensa_id)
    canjes = CanjeRecompensa.objects.filter(recompensa=recompensa).select_related('usuario')
    return render(request, "administrador/recompensa_canjes.html", {"recompensa": recompensa, "canjes": canjes})

@rol_required('administrador')
def admi_historial_canjes(request):
    canjes_list = CanjeRecompensa.objects.select_related('usuario', 'recompensa').order_by('-fecha_canje')
    paginator = Paginator(canjes_list, 10)
    page = request.GET.get('page', 1)
    try:
        canjes = paginator.page(page)
    except:
        canjes = paginator.page(1)
    
    return render(request, "administrador/historial_canjes.html", {
        'canjes': canjes,
        'total': canjes_list.count()
    })

@rol_required('administrador')
def admi_educacion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    tema_residente = TemaSemanal.objects.filter(activo=True, vista_destino='residente').first()
    tema_organizador = TemaSemanal.objects.filter(activo=True, vista_destino='organizador').first()
    return render(request, "administrador/educacion.html", {
        "usuario": usuario,
        "tema_residente": tema_residente,
        "tema_organizador": tema_organizador,
    })

@rol_required('administrador')
def admi_contacto(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first() if usuario_id else None
    
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        correo = request.POST.get('correo', '').strip()
        mensaje = request.POST.get('mensaje', '').strip()
        
        errors = []
        if not nombre or len(nombre) < 2:
            errors.append('El nombre debe tener al menos 2 caracteres.')
        if not correo or '@' not in correo:
            errors.append('Ingresa un correo electrónico válido.')
        if not mensaje or len(mensaje) < 10:
            errors.append('El mensaje debe tener al menos 10 caracteres.')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            messages.success(request, 'Mensaje enviado correctamente. Te hemos enviado una confirmación a tu correo.')
        
        return redirect('admi_contacto')
    
    return render(request, "administrador/contacto.html", {"usuario": usuario})

@rol_required('administrador')
def admi_asistencia(request):
    from datetime import timedelta, datetime

    filtro_estado = request.GET.get('estado', '')
    jornadas_query = Jornada.objects.exclude(estado='cancelada').order_by('-fecha')
    
    if filtro_estado:
        jornadas_query = jornadas_query.filter(estado=filtro_estado)
    
    jornada_id = request.GET.get('jornada_id') or request.POST.get('jornada_id')
    jornada = None
    inscripciones = []

    if jornada_id:
        jornada = get_object_or_404(Jornada, id_jornada=jornada_id)

        if jornada.fecha:
            if jornada.hora:
                fecha_hora_jornada = datetime.combine(jornada.fecha, jornada.hora)
                fecha_hora_jornada = timezone.make_aware(fecha_hora_jornada)
            else:
                fecha_hora_jornada = datetime.combine(jornada.fecha, datetime.min.time())
                fecha_hora_jornada = timezone.make_aware(fecha_hora_jornada)

            limite = fecha_hora_jornada + timedelta(hours=48)
            if timezone.now() > limite:
                messages.error(request, "Ya pasaron las 48 horas limite para asignar puntos a esta jornada.")
                return redirect("admi_asistencia")

        puntos_residente = 10
        puntos_organizador = 20
        
        try:
            inscripciones = Inscripcion.objects.filter(
                jornada=jornada,
                estado='activa'
            ).select_related('usuario')
            
            for inscripcion in inscripciones:
                asistencia = Asistencia.objects.filter(inscripcion=inscripcion).first()
                if asistencia and asistencia.presente:
                    usuario = inscripcion.usuario
                    puntos = puntos_organizador if usuario.rol == "organizador" else puntos_residente
                    
                    asistencia.puntos_asignados = puntos
                    asistencia.save(update_fields=['puntos_asignados'])
                    
                    ya_tiene = Puntaje.objects.filter(
                        usuario=usuario,
                        jornada=jornada
                    ).exists()
                    
                    if not ya_tiene:
                        Puntaje.objects.create(
                            usuario=usuario,
                            puntos=puntos,
                            motivo=f"Asistencia validada a jornada: {jornada.titulo}",
                            jornada=jornada
                        )
            
            messages.success(request, "Asistencia validada y puntos asignados correctamente.")
        except Exception as e:
            messages.error(request, f"Error al validar asistencia: {str(e)}")
        
        return redirect("admi_asistencia")

    return render(request, "administrador/asistencia.html", {
        'jornadas': jornadas_query,
        'jornada': jornada,
        'inscripciones': inscripciones
    })

@rol_required('administrador')
def admi_eliminar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    if jornada.estado != "pendiente":
        messages.error(request, "Solo se pueden cancelar jornadas con estado pendiente.")
        return redirect("admi_creacion_jornadas")

    confirmacion = request.POST.get("confirmar") == "1"
    if _porcentaje_ocupacion_jornada(jornada) > 0.5 and not confirmacion:
        messages.error(request, "Esta jornada ya supera el 50% del cupo inscrito. Debes confirmar la cancelacion para continuar.")
        return redirect("admi_creacion_jornadas")

    jornada.estado = "cancelada"
    jornada.save(update_fields=["estado", "last_update"])
    messages.success(request, "Jornada cancelada correctamente.")
    return redirect("admi_creacion_jornadas")

@rol_required('administrador')
def admi_modificar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    if jornada.estado != "pendiente":
        messages.error(request, "Solo se pueden editar jornadas con estado pendiente.")
        return redirect("admi_creacion_jornadas")

    if request.method == "POST":
        form = JornadaForm(request.POST, instance=jornada)
        if form.is_valid():
            jornada = form.save(commit=False)
            if not jornada.id_organizador:
                jornada.id_organizador = Usuario.objects.filter(id_usuario=request.session.get("usuario_id")).first()
            jornada.save()
            messages.success(request, "Jornada modificada correctamente.")
            return redirect("admi_creacion_jornadas")
    else:
        form = JornadaForm(instance=jornada)

    return render(request, "administrador/modificar_jornada.html", {"form": form, "jornada": jornada})

@rol_required('administrador')
def admi_validar_acciones(request):
    acciones_pendientes = AccionDestacada.objects.filter(
        validada=False
    ).select_related('inscripcion__usuario', 'inscripcion__jornada')

    if request.method == "POST":
        accion_id = request.POST.get("accion_id")
        accion = get_object_or_404(AccionDestacada, id=accion_id)

        accion.validada = True
        accion.save()

        Puntaje.objects.create(
            usuario=accion.inscripcion.usuario,
            puntos=accion.puntos_sugeridos,
            motivo=f"Accion destacada: {accion.descripcion}",
            jornada=accion.inscripcion.jornada
        )

        messages.success(request, f"Accion validada y {accion.puntos_sugeridos} puntos asignados a {accion.inscripcion.usuario.nombre}.")
        return redirect("admi_validar_acciones")

    return render(request, "administrador/validar_acciones.html", {
        "acciones_pendientes": acciones_pendientes
    })

@rol_required('administrador')
def admi_validar_asistencia(request):
    from datetime import timedelta

    jornada_id = request.GET.get('jornada_id') or request.POST.get('jornada_id')

    if not jornada_id:
        messages.error(request, "No se especificó la jornada.")
        return redirect("admi_asistencia")

    try:
        jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    except Exception as e:
        messages.error(request, f"Error al obtener la jornada: {str(e)}")
        return redirect("admi_asistencia")

    if jornada.fecha:
        from datetime import datetime
        if jornada.hora:
            fecha_hora_jornada = datetime.combine(jornada.fecha, jornada.hora)
            fecha_hora_jornada = timezone.make_aware(fecha_hora_jornada)
        else:
            fecha_hora_jornada = datetime.combine(jornada.fecha, datetime.min.time())
            fecha_hora_jornada = timezone.make_aware(fecha_hora_jornada)

        limite = fecha_hora_jornada + timedelta(hours=48)
        if timezone.now() > limite:
            messages.error(request, "Ya pasaron las 48 horas limite para asignar puntos a esta jornada.")
            return redirect("admi_asistencia")

    return redirect("admi_asistencia")

@rol_required('administrador')
def admi_configuracion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    
    if not usuario_id:
        return redirect("login")
    
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return redirect("login")
    
    if request.method == "POST":
        password_actual = request.POST.get("password_actual")
        password_nueva = request.POST.get("password_nueva")
        password_confirmacion = request.POST.get("password_confirmacion")
        
        if password_actual and password_nueva and password_confirmacion:
            if not check_password(password_actual, usuario.contrasena):
                messages.error(request, "La contraseña actual es incorrecta.")
                return redirect("admi_configuracion")
            
            if password_nueva != password_confirmacion:
                messages.error(request, "Las nuevas contraseñas no coinciden.")
                return redirect("admi_configuracion")
            
            usuario.contrasena = make_password(password_nueva)
            usuario.save()
            
            messages.success(request, "Contraseña actualizada. Inicia sesión nuevamente.")
            return redirect("login")
    
    return render(request, "administrador/configuracion.html", {"usuario": usuario})

import requests
import json
import os

GEMINI_API_KEY = os.environ.get('GROQ_API_KEY', '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')

def admin_generar_tema(request):
    usuario_id = request.session.get("usuario_id")
    admin = Usuario.objects.filter(id_usuario=usuario_id, rol='administrador').first()
    if not admin:
        return redirect("login")

    modo = request.GET.get('modo', 'generar')
    result = None
    vista_destino = 'residente'
    tema_titulo = ''

    if request.method == "POST":
        tema_titulo = request.POST.get("titulo", "").strip()
        vista_destino = (request.POST.get("vista_destino", "residente") or "residente").strip().lower()
        if not tema_titulo:
            messages.error(request, "El título del tema es requerido.")
            return redirect("admin_tema_semanal")

        # Si ya se está guardando, usar datos de sesión o contenido editado directamente
        if request.POST.get("guardar") == "1":
            contenido_editado = request.POST.get("contenido_editado", "").strip()
            preguntas_editadas_raw = request.POST.get("preguntas_editadas", "").strip()

            if contenido_editado and preguntas_editadas_raw:
                # El usuario editó el contenido antes de guardar
                try:
                    preguntas_editadas = json.loads(preguntas_editadas_raw)
                except Exception:
                    preguntas_editadas = []
                contenido_final = contenido_editado
                preguntas_final = preguntas_editadas
            else:
                # Usar datos de la sesión (generados sin edición)
                preview_key = f"preview_data_{tema_titulo}"
                session_data = request.session.get(preview_key, {})
                if not session_data:
                    messages.error(request, "No hay contenido generado para guardar. Genere el tema primero.")
                    return redirect("admin_tema_semanal")
                contenido_final = str(session_data['contenido'])
                preguntas_final = session_data['preguntas']

            # Solo desactivar el tema activo del mismo rol destino
            TemaSemanal.objects.filter(activo=True, vista_destino=vista_destino).update(activo=False)
            TemaSemanal.objects.create(
                titulo=tema_titulo,
                contenido_educativo=contenido_final,
                preguntas_json=json.dumps(preguntas_final),
                vista_destino=vista_destino,
                activo=True,
                creado_por=admin
            )
            messages.success(request, f"Tema '{tema_titulo}' guardado como tema activo para {vista_destino}.")
            return redirect("admin_tema_semanal")

        result = None

        try:
            
            client = OpenAI(
                base_url='https://api.groq.com/openai/v1',
                api_key=GEMINI_API_KEY
            )
            prompt = (
                'Eres un experto en educación ambiental para Colombia. '
                'Genera ÚNICAMENTE JSON válido en ESPAÑOL con caracteres acentuados (áéíóúñ). '
                'Tema: ' + tema_titulo + '. '
                'El campo "contenido" debe tener MÁS DE 800 PALABRAS usando etiquetas HTML: '
                '<h2> para títulos principales (mínimo 4 secciones), '
                '<h3> para subtítulos, <p> para párrafos extensos, <ul><li> para listas. '
                'Las secciones OBLIGATORIAS son: '
                '1) Introducción detallada al tema con contexto en Colombia, '
                '2) ¿Por qué es importante? con estadísticas reales de Colombia, '
                '3) Causas y consecuencias, '
                '4) Acciones prácticas que pueden hacer los ciudadanos colombianos, '
                '5) Normativa y contexto legal en Colombia, '
                '6) Conclusión motivadora. '
                'Genera EXACTAMENTE 5 preguntas de opción múltiple, cada una con 4 opciones (A, B, C, D), '
                'directamente relacionadas con el contenido del tema ' + tema_titulo + '. '
                'Las preguntas deben evaluar comprensión, no memoria trivial. '
                'Formato JSON estricto: '
                '{"contenido": "<h2>...</h2><p>...</p>...", '
                '"preguntas": ['
                '{"pregunta": "...", "opciones": ["A) ...","B) ...","C) ...","D) ..."], "respuesta_correcta": 0, "explicacion": "..."},'
                '{"pregunta": "...", "opciones": ["A) ...","B) ...","C) ...","D) ..."], "respuesta_correcta": 1, "explicacion": "..."},'
                '{"pregunta": "...", "opciones": ["A) ...","B) ...","C) ...","D) ..."], "respuesta_correcta": 2, "explicacion": "..."},'
                '{"pregunta": "...", "opciones": ["A) ...","B) ...","C) ...","D) ..."], "respuesta_correcta": 0, "explicacion": "..."},'
                '{"pregunta": "...", "opciones": ["A) ...","B) ...","C) ...","D) ..."], "respuesta_correcta": 3, "explicacion": "..."}'
                ']}'
            )
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=4000
            )
            content = completion.choices[0].message.content
            if content:
                import re
                # Limpiar markdown y caracteres de control
                content_clean = content.replace('```json', '').replace('```', '').replace('`', '').strip()
                content_clean = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', content_clean)
                # Busca JSON completo
                match = re.search(r'\{[\s\S]*\}', content_clean)
                if match:
                    content_clean = match.group(0)
                try:
                    data = json.loads(content_clean)
                    contenido = data.get('contenido', '')
                    preguntas = data.get('preguntas', [])
                    # Si contenido es dict, convertir a HTML
                    if isinstance(contenido, dict):
                        html_parts = []
                        for k, v in contenido.items():
                            if isinstance(v, str):
                                html_parts.append(f"<h2>{k.replace('_', ' ').title()}</h2><p>{v.strip()}</p>")
                            elif isinstance(v, dict):
                                if 'elemento1' in v or 'elemento2' in v:
                                    items = ''.join([f'<li>{v.get(f"elemento{i}","")}</li>' for i in range(1,6) if v.get(f'elemento{i}')])
                                    if items:
                                        html_parts.append(f"<ul>{items}</ul>")
                                else:
                                    if v.get('titulo'):
                                        html_parts.append(f"<h2>{v.get('titulo')}</h2>")
                                    if v.get('texto'):
                                        html_parts.append(f"<p>{v.get('texto')}</p>")
                        contenido = ''.join(html_parts) if html_parts else str(contenido)
                    for i, pregunta in enumerate(preguntas):
                        if 'respuesta_correcta' in pregunta:
                            pregunta['respuesta_correcta'] = int(pregunta['respuesta_correcta'])
                    result = {"contenido": contenido, "preguntas": preguntas}
                    request.session[f"preview_data_{tema_titulo}"] = {"contenido": contenido, "preguntas": preguntas}
                except json.JSONDecodeError as je:
                    result = {"contenido": "El reciclaje reduce la contaminación y genera empleos. En Colombia solo 17% residuos se reciclan adecuadamente. Separa papel, cartón, vidrio, plástico y metales en origen. Deposita en puntos verdes amarillos (plástico), azules (papel), verdes (vidrio). Medellín lidera con 45% recolección. Decreto 1072/2015 fomenta gestión integral.", "preguntas": [{"pregunta": "¿Qué es el reciclaje?", "opciones": ["Proceso de reutilizar materiales", "Quema de basura", "Enterrar residuos", "Ninguna de las anteriores"], "respuesta_correcta": 0, "explicacion": "Reduce residuos y genera empleo."}]}
                except Exception as je:
                    result = {"contenido": "<h2>Error</h2><p>Ocurrió un error procesando la respuesta.</p>", "preguntas": []}
            else:
                messages.warning(request, "Respuesta vacía de IA")
        except Exception as e:
            import traceback
            print(f"GROQ ERROR: {traceback.format_exc()}")
            messages.error(request, f"Error Groq API: {str(e)}")

        if result is None:
            messages.error(request, "No se recibió respuesta de IA. Verifica conexión y API key.")

        return render(request, "administrador/tema_semanal.html", {
            "usuario": admin,
            "preview": result,
            "tema_titulo": tema_titulo,
            "vista_destino": vista_destino
        })

    if modo == 'vista_previa':
        titulo_prev = request.GET.get("titulo", "")
        vista_prev = request.GET.get("vista", "")
        preview_key = f"preview_data_{titulo_prev}"
        preview = request.session.get(preview_key, {})
        preguntas_json = json.dumps(preview.get("preguntas", []))
        return render(request, "administrador/tema_semanal.html", {
            "usuario": admin,
            "preview": preview,
            "preview_preguntas_json": preguntas_json,
            "tema_titulo": titulo_prev,
            "vista_destino": vista_prev,
            "modo": "vista_previa"
        })

    if modo == 'editar':
        titulo_ed = request.GET.get("titulo", "")
        vista_ed = request.GET.get("vista", "")
        preview_key = f"preview_data_{titulo_ed}"
        preview = request.session.get(preview_key, {})
        preguntas_json = json.dumps(preview.get("preguntas", []))
        return render(request, "administrador/tema_semanal.html", {
            "usuario": admin,
            "preview": preview,
            "preview_preguntas_json": preguntas_json,
            "tema_titulo": titulo_ed,
            "vista_destino": vista_ed,
            "modo": "editar"
        })

    if modo == 'historial':
        page_number = request.GET.get('page', 1)
        temas_qs = TemaSemanal.objects.all().order_by('-fecha_creacion')
        paginator = Paginator(temas_qs, 10)
        temas = paginator.get_page(page_number)
        return render(request, "administrador/tema_semanal.html", {
            "usuario": admin,
            "modo": "historial",
            "temas": temas
        })

    return render(request, "administrador/tema_semanal.html", {"usuario": admin})

def educacion_api(request):
    """API pública para que residente y organizador carguen su tema semanal según su rol."""
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()

    if not usuario:
        return JsonResponse({"error": "No autenticado"}, status=401)

    # Cada rol ve solo su tema: residente → 'residente', organizador → 'organizador'
    rol = (usuario.rol or '').strip().lower()
    if rol == 'administrador':
        # El admin puede ver cualquier tema activo (primer resultado)
        tema_activo = TemaSemanal.objects.filter(activo=True).first()
    else:
        tema_activo = TemaSemanal.objects.filter(activo=True, vista_destino=rol).first()

    if not tema_activo:
        return JsonResponse({"error": "No hay tema activo para tu rol"}, status=404)

    evaluacion_realizada = ResultadoEvaluacion.objects.filter(usuario=usuario, tema=tema_activo).exists()
    resultado = ResultadoEvaluacion.objects.filter(usuario=usuario, tema=tema_activo).first() if evaluacion_realizada else None

    return JsonResponse({
        "titulo": tema_activo.titulo,
        "contenido": tema_activo.contenido_educativo,
        "preguntas": json.loads(tema_activo.preguntas_json) if isinstance(tema_activo.preguntas_json, str) else tema_activo.preguntas_json,
        "evaluacion_realizada": evaluacion_realizada,
        "retroalimentacion_guardada": resultado.retroalimentacion if hasattr(resultado, 'retroalimentacion') else "",
        "puntos_guardados": resultado.puntos_obtenidos if resultado else 0,
        "max_puntos": len(json.loads(tema_activo.preguntas_json) if isinstance(tema_activo.preguntas_json, str) else tema_activo.preguntas_json) * 20
    })

@require_POST
@csrf_exempt
def guardar_evaluacion(request):
    """Permite a residente y organizador enviar respuestas de su evaluación del tema semanal."""
    usuario_id = request.session.get('usuario_id')
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return JsonResponse({"error": "No autenticado"}, status=401)
    if usuario.rol not in ['residente', 'organizador', 'administrador']:
        return JsonResponse({"error": "No autorizado"}, status=403)

    try:
        data = json.loads(request.body)
        respuestas = data.get('respuestas', {})

        # Buscar el tema activo correspondiente al rol del usuario
        rol = (usuario.rol or '').strip().lower()
        if rol == 'administrador':
            tema = TemaSemanal.objects.filter(activo=True).first()
        else:
            tema = TemaSemanal.objects.filter(activo=True, vista_destino=rol).first()

        if not tema:
            return JsonResponse({"error": "No hay tema activo para tu rol"}, status=400)

        # Verificar si ya completó la evaluación
        if ResultadoEvaluacion.objects.filter(usuario=usuario, tema=tema).exists():
            return JsonResponse({"error": "Ya completaste esta evaluación"}, status=400)

        preguntas = json.loads(tema.preguntas_json) if isinstance(tema.preguntas_json, str) else tema.preguntas_json
        puntos = 0
        preguntas_correctas = 0
        retroalimentaciones = []

        for i, pregunta in enumerate(preguntas):
            opcion_seleccionada = respuestas.get(f'p{i}')
            correcta = pregunta.get('respuesta_correcta')
            if opcion_seleccionada is not None and int(opcion_seleccionada) == correcta:
                puntos += 20
                preguntas_correctas += 1
                retroalimentaciones.append(f"✓ Pregunta {i+1}: Correcta (+20 pts)")
            else:
                explicacion = pregunta.get('explicacion', '').strip()
                if not explicacion:
                    explicacion = 'Revisa el contenido educativo del tema para mejorar.'
                retroalimentaciones.append(f"✗ Pregunta {i+1}: Incorrecta. {explicacion}")

        ResultadoEvaluacion.objects.update_or_create(
            usuario=usuario, tema=tema,
            defaults={
                'puntos_obtenidos': puntos,
                'total_preguntas': len(preguntas),
                'retroalimentacion': '<br>'.join(retroalimentaciones)
            }
        )
        Puntaje.objects.create(usuario=usuario, puntos=puntos, motivo=f"Evaluación: {tema.titulo}")
        return JsonResponse({
            "puntos": puntos,
            "correctas": preguntas_correctas,
            "max_puntos": len(preguntas) * 20,
            "retroalimentacion": '<br>'.join(retroalimentaciones)
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)