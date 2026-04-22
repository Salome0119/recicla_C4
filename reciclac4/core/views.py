from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.messages import get_messages
from django.conf import settings
from .models import Usuario
from .forms import JornadaForm
from django.shortcuts import get_object_or_404, render
from .models import Jornada, Inscripcion
from .forms import InscripcionForm
from django.utils import timezone
from .models import Jornada, Usuario
from django.core.mail import send_mail
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from .models import TemaForo, Usuario
from django.utils import timezone
from .models import Jornada
from datetime import datetime
from django.contrib.auth.hashers import check_password, make_password
from django.db.models import Sum

from functools import wraps
from .models import Notificacion
from django.db import models
from .decorators import rol_required
from django.db.models import Sum, Max
from .models import Usuario, Puntaje
from .forms import JornadaForm, AsignarPuntajeForm  # <-- Asegúrate de importar aquí
from .forms import PuntajeForm
import openpyxl
from django.core.paginator import Paginator
from django.db import IntegrityError
from xhtml2pdf import pisa
from django.template.loader import render_to_string
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from django.db.models.functions import Trim
from django.utils import timezone
from .models import Usuario, UserChangeLog
from .forms import UsuarioForm
from django.urls import reverse
from django.core.mail import send_mail
from django.utils.crypto import get_random_string
from .forms import PasswordResetRequestForm
from .models import Notificacion


# ---------------------------
# INICIO DE SESION Y REGISTRO
# ---------------------------

# LOGIN
def login_view(request):
    if request.method == "POST":
        correo = request.POST.get("correo")
        contrasena = request.POST.get("contrasena")

        try:
            usuario = Usuario.objects.get(correo=correo)

            # validar la contraseña encriptada
            if not check_password(contrasena, usuario.contrasena):
                messages.error(request, "Correo o contraseña incorrectos")
                return redirect("login")

            # Verificar estado
            if not usuario.puede_acceder():
                if usuario.estado == 'pendiente':
                    messages.error(request, "Tu cuenta está pendiente de aprobación.")
                elif usuario.estado == 'rechazado':
                    messages.error(request, "Tu solicitud fue rechazada.")
                return redirect("login")

        except Usuario.DoesNotExist:
            messages.error(request, "Correo o contraseña incorrectos")
            return redirect("login")

        # Normalizar rol y guardar sesión
        rol_normalizado = (usuario.rol or "").strip().lower()

        request.session["usuario_id"] = usuario.id_usuario
        request.session["usuario_nombre"] = usuario.nombre
        request.session["usuario_rol"] = rol_normalizado

        # Redirección por rol
        if rol_normalizado == "administrador":
            return redirect("admi_inicio")
        elif rol_normalizado == "organizador":
            return redirect("organizador_inicio")
        else:
            return redirect("residente_inicio")

    return render(request, "login/login.html")



# REGISTRO
def register_view(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        apellido = request.POST.get("apellido")
        correo = request.POST.get("correo")
        contrasena = request.POST.get("contrasena")
        fecha_nacimiento = request.POST.get("fecha_nacimiento")
        barrio = request.POST.get("barrio")
        rol = request.POST.get("rol")

        # Validar correo único
        if Usuario.objects.filter(correo=correo).exists():
            messages.error(request, "El correo ya está registrado.")
            return redirect("register")

        # NUEVA LÓGICA DE ESTADO
        if rol == "residente":
            estado_inicial = "activo"  # Residentes activos inmediatamente
            mensaje_exito = "🎉 Registro exitoso. Ya puedes iniciar sesión."
        else:
            estado_inicial = "pendiente"  # Organizadores/Administradores requieren aprobación
            mensaje_exito = "⏳ Registro exitoso. Tu cuenta está pendiente de aprobación. Recibirás un correo cuando sea revisada."

        nuevo_usuario = Usuario.objects.create(
            nombre=nombre,
            apellido=apellido,
            correo=correo,
            contrasena=make_password(contrasena),
            fecha_nacimiento=fecha_nacimiento,
            barrio=barrio,
            rol=rol,
            estado=estado_inicial
        )

        # Enviar correo de aprobación SOLO para organizadores y administradores
        if rol in ["organizador", "administrador"]:
            dominio = get_current_site(request).domain
            aprobar_url = f"http://{dominio}/aprobar/{nuevo_usuario.id_usuario}/"
            rechazar_url = f"http://{dominio}/rechazar/{nuevo_usuario.id_usuario}/"

            mensaje_admin = f"""
NUEVA SOLICITUD DE USUARIO QUE REQUIERE APROBACIÓN:

📋 Información del usuario:
• Nombre: {nombre} {apellido}
• Correo: {correo}
• Rol solicitado: {rol.upper()}
• Barrio: {barrio}
• Fecha de registro: {nuevo_usuario.fecha_registro}

⚡ Acciones disponibles:

✅ Aprobar usuario: {aprobar_url}
❌ Rechazar usuario: {rechazar_url}
"""

            send_mail(
                subject=f"🔔 Nueva solicitud de {rol} - Recicla Comuna 4",
                message=mensaje_admin,
                from_email="reciclacomuna@gmail.com",
                recipient_list=["reciclacomuna@gmail.com"],
                fail_silently=False,
            )

        messages.success(request, mensaje_exito)
        return redirect("login")

    return render(request, "login/register.html")
# views.py - AGREGA esta vista
def solicitudes_pendientes(request):
    """Vista para ver usuarios pendientes de aprobación"""
    if not request.session.get("usuario_id"):
        return redirect("login")
    
    # Solo administradores pueden ver esto
    usuario_actual = Usuario.objects.get(id_usuario=request.session["usuario_id"])
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos para ver esta página.")
        return redirect("admi_inicio")
    
    pendientes = Usuario.objects.filter(estado='pendiente')
    return render(request, "administrador/solicitudes_pendientes.html", {
        'solicitudes': pendientes
    })

def aprobar_usuario(request, id_usuario):
    usuario = Usuario.objects.get(id_usuario=id_usuario)
    
    if usuario.estado == 'pendiente':
        usuario.estado = 'aprobado'
        usuario.save()
        
        # Enviar correo de notificación al usuario
        send_mail(
            subject="✅ Tu cuenta ha sido aprobada - Recicla Comuna 4",
            message=f"""
¡Felicidades {usuario.nombre}!

Tu solicitud para el rol de {usuario.rol} ha sido aprobada.

Ahora puedes iniciar sesión en: http://{get_current_site(request).domain}

Saludos,
Equipo Recicla Comuna 4
            """,
            from_email="salohenao19@gmail.com",
            recipient_list=[usuario.correo],
            fail_silently=False,
        )
        
        return HttpResponse(f"""
        <div style="text-align: center; padding: 50px; font-family: Arial;">
            <h2 style="color: #27AE60;">✅ Usuario Aprobado</h2>
            <p>El usuario <strong>{usuario.nombre}</strong> ha sido aprobado exitosamente.</p>
            <p>Se ha enviado una notificación por correo.</p>
            <a href="/" style="color: #2e7d32;">Volver al inicio</a>
        </div>
        """)
    else:
        return HttpResponse("Este usuario ya fue procesado anteriormente.")

def rechazar_usuario(request, id_usuario):
    usuario = Usuario.objects.get(id_usuario=id_usuario)
    
    if usuario.estado == 'pendiente':
        usuario.estado = 'rechazado'
        usuario.save()
        
        # Enviar correo de notificación al usuario
        send_mail(
            subject="❌ Solicitud de cuenta rechazada - Recicla Comuna 4",
            message=f"""
Hola {usuario.nombre},

Lamentamos informarte que tu solicitud para el rol de {usuario.rol} ha sido rechazada.

Si crees que esto es un error, por favor contacta al administrador del sistema.

Saludos,
Equipo Recicla Comuna 4
            """,
            from_email="salohenao19@gmail.com",
            recipient_list=[usuario.correo],
            fail_silently=False,
        )
        
        return HttpResponse(f"""
        <div style="text-align: center; padding: 50px; font-family: Arial;">
            <h2 style="color: #e74c3c;">❌ Usuario Rechazado</h2>
            <p>El usuario <strong>{usuario.nombre}</strong> ha sido rechazado.</p>
            <p>Se ha enviado una notificación por correo.</p>
            <a href="/" style="color: #2e7d32;">Volver al inicio</a>
        </div>
        """)
    else:
        return HttpResponse("Este usuario ya fue procesado anteriormente.")



def password_reset_request(request):
    if request.method == "POST":
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            correo = form.cleaned_data['correo']
            try:
                usuario = Usuario.objects.get(correo=correo)
                token = get_random_string(64)
                usuario.reset_token = token
                usuario.save()

                print(f"TOKEN GUARDADO: {usuario.reset_token}")  # 👈 para verificar
                # Generar token temporal
                token = get_random_string(64)
                
                usuario.reset_token = token
                usuario.save()
                

                dominio = get_current_site(request).domain
                reset_url = f"http://{dominio}/reset_password/{token}/"

                mensaje = f"""
Hola {usuario.nombre},

Recibimos una solicitud para restablecer tu contraseña.

Haz clic en el siguiente enlace para crear una nueva contraseña:

{reset_url}

Si no solicitaste esto, puedes ignorar este mensaje.

Saludos,
Equipo Recicla Comuna 4
                """

                send_mail(
                    subject="🔑 Restablecer contraseña - RC4",
                    message=mensaje,
                    from_email="salohenao19@gmail.com",
                    recipient_list=[correo],
                    fail_silently=False,
                )

                messages.success(request, "Se ha enviado un enlace a tu correo para restablecer tu contraseña.")
                return redirect("login")

            except Usuario.DoesNotExist:
                messages.error(request, "No existe un usuario con ese correo.")
    else:
        form = PasswordResetRequestForm()

    return render(request, "login/password_reset_request.html", {"form": form})
def password_reset_confirm(request, token):
    try:
        usuario = Usuario.objects.get(reset_token=token)
    except Usuario.DoesNotExist:
        messages.error(request, "Token inválido o expirado.")
        return redirect("login")

    if request.method == "POST":
        nueva_contrasena = request.POST.get("nueva_contrasena")
        confirmar_contrasena = request.POST.get("confirmar_contrasena")

        if nueva_contrasena != confirmar_contrasena:
            messages.error(request, "Las contraseñas no coinciden.")
            return redirect(request.path)

        usuario.contrasena = make_password(nueva_contrasena)
        usuario.reset_token = ""  # limpiar token
        usuario.save()

        messages.success(request, "Contraseña actualizada correctamente. Puedes iniciar sesión.")
        return redirect("login")

    return render(request, "login/password_reset_confirm.html")
















# -------------------------
#  ADMINISTRADOR
# -------------------------

#LISTADO PRINCIPAL
@rol_required('administrador')
def admin_users_list(request):
    # seguridad: permitir solo administradores de sesión
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
        "users": page_obj,
        "q": q,
        "rol": rol,
        "estado": estado,
        "page_obj": page_obj,
        "per_page": per_page,
    }
    return render(request, "administrador/usuarios_list.html", context)

#CREAR USUARIO
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
            # Si no mandaron contraseña, generamos una por defecto (mejor pedirla)
            pwd = request.POST.get("password_plain")
            from django.contrib.auth.hashers import make_password
            if pwd:
                nuevo.contrasena = make_password(pwd)
            else:
                nuevo.contrasena = make_password("Cambiar123!")
            nuevo.save()
            # guardar en historial
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

    return render(request, "administrador/usuarios_form.html", {"form": form, "crear": True})

# EDITAR USUARIO
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
            viejo = { "nombre": usuario.nombre, "apellido": usuario.apellido, "correo": usuario.correo, "rol": usuario.rol, "estado": usuario.estado }
            form.save()
            # registrar cambios
            UserChangeLog.objects.create(
                usuario=usuario,
                quien=f"{usuario_actual.nombre} {usuario_actual.apellido}",
                accion="editar",
                detalle=f"Antes: {viejo}"
            )
            messages.success(request, "Usuario actualizado.")
            return redirect("admin_users_list")
    else:
        form = UsuarioForm(instance=usuario)

    return render(request, "administrador/usuarios_form.html", {"form": form, "crear": False, "usuario_obj": usuario})

# SUSPENDER USUARIO
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
    usuario.estado = "suspendido"
    usuario.save()
    UserChangeLog.objects.create(usuario=usuario, quien=f"{usuario_actual.nombre} {usuario_actual.apellido}", accion="suspender", detalle="Suspensión por administrador")
    messages.success(request, "Usuario suspendido (no eliminado).")
    return redirect("admin_users_list")

# RESTAURAR USUARIO
@rol_required('administrador')
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

# LISTADO DE SUSPENDIDOS
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
    return render(request, "administrador/usuarios_deleted.html", {"usuarios": usuarios})

# EXPORTAR A 
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

# EXPORTAR A PDF
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

# BUSQUEDA 
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
    for u in qs[:200]:  # limit
        data.append({
            "id": u.id_usuario,
            "nombre": u.nombre,
            "apellido": u.apellido,
            "correo": u.correo,
            "rol": u.rol,
            "estado": u.estado,
        })
    return JsonResponse({"results": data})
def inscribirse_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id=jornada_id)

    if request.method == 'POST':
        form = InscripcionForm(request.POST)
        if form.is_valid():
            inscripcion = form.save(commit=False)
            inscripcion.fecha_inscripcion = timezone.now()
            inscripcion.save()
            return redirect('detalle_jornada', jornada_id=jornada.id)
    else:
        form = InscripcionForm(initial={'jornada': jornada.id, 'usuario': request.user.id})

    return render(request, 'residente/inscripcion.html', {'form': form, 'jornada': jornada})

# CREAR JORNADA
@rol_required('administrador')
def admi_creacion_jornadas(request):
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

    # 🔥 Obtener todas las jornadas
    jornadas = Jornada.objects.all().order_by("-fecha")

    return render(request, "administrador/creacionjornadas.html", {
        "jornadas": jornadas
    })

# PANEL
@rol_required('administrador')
def admin_panel(request):
    if not request.session.get("usuario_id"):
        return redirect("login")
    return render(request, "administrador/asistencia.html")

# FORO
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
def admi_publicacion_foro(request):

    if request.method == "POST":

        titulo = request.POST.get("titulo")
        contenido = request.POST.get("contenido")

        # Recoger correctamente el usuario logueado
        usuario_id = request.session.get("usuario_id")

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

    return render(request, "administrador/publicacion_foro.html")
@rol_required('administrador')
def admi_recoleccion(request):
    return render(request, "administrador/recoleccion.html")

@rol_required('administrador')
def admi_recompensa(request):
    from .models import Recompensa
    
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
    return render(request, "administrador/recompensa.html", {'recompensas': recompensas})

@rol_required('administrador')
def admi_recompensa_canjes(request, recompensa_id):
    from .models import CanjeRecompensa, Recompensa
    
    recompensa = get_object_or_404(Recompensa, id_recompensa=recompensa_id)
    canjes = CanjeRecompensa.objects.filter(recompensa=recompensa).select_related('usuario')
    
    return render(request, "administrador/recompensa_canjes.html", {
        'recompensa': recompensa,
        'canjes': canjes
    })

@rol_required('administrador')
def admi_educacion(request):
    return render(request, "administrador/educacion.html")

@rol_required('administrador')
def admi_contacto(request):
    return render(request, "administrador/contacto.html")
@rol_required('administrador')
def admi_inicio(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    _avisar_notificaciones_nuevas(request, usuario)
    return render(request, "administrador/inicio.html")

@rol_required('administrador')
def admi_asistencia(request):
    from datetime import timedelta, datetime
    from django.utils import timezone
    from .models import Asistencia

    # Obtener filtro de estado
    filtro_estado = request.GET.get('estado', '')
    
    # Mostrar todas las jornadas excepto las canceladas
    jornadas_query = Jornada.objects.exclude(estado='cancelada').order_by('-fecha')
    
    if filtro_estado:
        jornadas_query = jornadas_query.filter(estado=filtro_estado)
    
    jornadas_finalizadas = jornadas_query

    jornada_id = request.GET.get('jornada_id') or request.POST.get('jornada_id')
    jornada = None
    inscripciones = []

    if jornada_id:
        jornada = get_object_or_404(Jornada, id_jornada=jornada_id)

        # Verificar que no hayan pasado más de 48 horas desde la fecha y hora de la jornada
        if jornada.fecha:
            from datetime import datetime
            if jornada.hora:
                fecha_hora_jornada = datetime.combine(jornada.fecha, jornada.hora)
            else:
                fecha_hora_jornada = datetime.combine(jornada.fecha, datetime.min.time())
            fecha_hora_jornada = timezone.make_aware(fecha_hora_jornada)
            limite = fecha_hora_jornada + timedelta(hours=48)
            if timezone.now() > limite:
                messages.error(request, "Ya pasaron las 48 horas limite para asignar puntos a esta jornada.")
                return redirect("admi_asistencia")

        inscripciones = Inscripcion.objects.filter(
            jornada=jornada,
            estado='activa'
        ).select_related('usuario')

    if request.method == "POST" and jornada:
        # Guardar asistencia solo (sin puntos)
        for inscripcion in inscripciones:
            presente = request.POST.get(f"presente_{inscripcion.id_inscripcion}") == "1"
            observaciones = request.POST.get(f"obs_{inscripcion.id_inscripcion}", "")
            nombre_usuario = f"{inscripcion.usuario.nombre} {inscripcion.usuario.apellido}"

            # Guardar asistencia
            Asistencia.objects.update_or_create(
                inscripcion=inscripcion,
                defaults={
                    "presente": presente,
                    "observaciones": observaciones,
                    "nombre_usuario": nombre_usuario
                }
            )

        messages.success(request, "Asistencia registrada correctamente. Los puntos se asignarán al validar.")
        return redirect("admi_asistencia")

    # Agregar informacion de puntos a las inscripciones
    for ins in inscripciones:
        # Buscar asistencia
        asistencia = Asistencia.objects.filter(inscripcion=ins).first()
        ins.asistencia_obj = asistencia
        
        # Usar puntos de la tabla asistencia si existen
        if asistencia and asistencia.puntos_asignados:
            ins.puntaje_asignado = asistencia.puntos_asignados
        else:
            # Buscar en la tabla de puntajes si ya tiene puntos
            puntaje = Puntaje.objects.filter(
                usuario=ins.usuario,
                jornada=jornada
            ).first()
            ins.puntaje_asignado = puntaje.puntos if puntaje else None

    return render(request, "administrador/asistencia.html", {
        "jornadas_finalizadas": jornadas_finalizadas,
        "jornada": jornada,
        "inscripciones": inscripciones,
        "filtro_estado": filtro_estado
    })

# CONFIGURACION
@rol_required('administrador')
def admi_configuracion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)

    if request.method == "POST":

        password_actual = request.POST.get("password_actual")
        password_nueva = request.POST.get("password_nueva")
        password_confirmacion = request.POST.get("password_confirmacion")

        # Verifica que sea este formulario
        if password_actual and password_nueva and password_confirmacion:

            # 1. Validar contraseña actual ENCRIPTADA
            if not check_password(password_actual, usuario.contrasena):
                messages.error(request, "❌ La contraseña actual es incorrecta.")
                return redirect("admi_configuracion")

            # 2. Validar coincidencia
            if password_nueva != password_confirmacion:
                messages.error(request, "❌ Las nuevas contraseñas no coinciden.")
                return redirect("admi_configuracion")

            # 3. Guardar nueva contraseña encriptada
            usuario.contrasena = make_password(password_nueva)
            usuario.save()

            messages.success(request, "✔ Contraseña actualizada. Inicia sesión nuevamente.")
            return redirect("login")

    return render(request, "administrador/configuracion.html", {"usuario": usuario})

# PANEL USUARIOS
@rol_required('administrador')
def panel_usuarios(request):
    busqueda = request.GET.get('q', '')
    estado_filtro = request.GET.get('estado', '')
    page_number = request.GET.get('page', 1)  # Página actual
    per_page = 10  # Usuarios por página

    # Tabla principal: excluir suspendidos
    usuarios_qs = Usuario.objects.exclude(estado='suspendido')

    if busqueda:
        usuarios_qs = usuarios_qs.filter(
            Q(nombre__icontains=busqueda) |
            Q(apellido__icontains=busqueda) |
            Q(correo__icontains=busqueda)
        )

    if estado_filtro:
        usuarios_qs = usuarios_qs.filter(estado=estado_filtro)

    # Paginador para usuarios activos
    paginator = Paginator(usuarios_qs, per_page)
    usuarios = paginator.get_page(page_number)

    # Tabla de suspendidos (también paginada si quieres)
    suspendidos_qs = Usuario.objects.filter(estado='suspendido')
    paginator_sus = Paginator(suspendidos_qs, per_page)
    suspendidos = paginator_sus.get_page(page_number)

    # Manejar asignación de puntaje
    if request.method == 'POST':
        form = PuntajeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('panel_usuarios')
    else:
        form = PuntajeForm()

    return render(request, 'administrador/usuarios.html', {
        'usuarios': usuarios,
        'suspendidos': suspendidos,
        'busqueda': busqueda,
        'estado_filtro': estado_filtro,
        'form': form
    })
# AGREGAR DEL PANEL USUARIOS
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
        nombre = request.POST.get("nombre")
        apellido = request.POST.get("apellido")
        correo = request.POST.get("correo")
        contrasena = request.POST.get("contrasena")
        rol = request.POST.get("rol")
        estado = request.POST.get("estado")

        if Usuario.objects.filter(correo=correo).exists():
            messages.error(request, "El correo ya está registrado.")
            return redirect("agregar_usuario")

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

    return render(request, "administrador/usuarios_agregar.html")

# REACTIVAR DEL PANEL USUARIOS
@rol_required('administrador')
def reactivar_usuario(request, id):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")

    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    usuario = get_object_or_404(Usuario, id_usuario=id)
    usuario.estado = "activo"  # Cambia el estado a activo
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
            if not _validar_publicacion_jornada(jornada):
                messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
                return redirect("admi_creacion_jornadas")
            jornada.save()
            _enviar_notificaciones_automaticas_jornada(jornada, "edicion")
            messages.success(request, "Jornada modificada correctamente.")
            return redirect("admi_creacion_jornadas")
    else:
        form = JornadaForm(instance=jornada)

    return render(request, "administrador/modificar_jornada.html", {"form": form, "jornada": jornada})


@rol_required('administrador')
def admi_validar_acciones(request):
    from .models import AccionDestacada

    acciones_pendientes = AccionDestacada.objects.filter(
        validada=False
    ).select_related('inscripcion__usuario', 'inscripcion__jornada')

    if request.method == "POST":
        accion_id = request.POST.get("accion_id")
        accion = get_object_or_404(AccionDestacada, id=accion_id)

        # Validar y asignar puntos
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
    from django.utils import timezone
    from .models import Asistencia
    
    jornada_id = request.GET.get('jornada_id') or request.POST.get('jornada_id')
    
    if not jornada_id:
        messages.error(request, "No se especificó la jornada.")
        return redirect("admi_asistencia")
    
    try:
        jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    except Exception as e:
        messages.error(request, f"Error al obtener la jornada: {str(e)}")
        return redirect("admi_asistencia")
    
    # Usar fecha de la jornada como referencia
    if jornada.fecha:
        # Combinar fecha y hora de la jornada para calcular el límite
        fecha_hora_jornada = jornada.fecha
        if jornada.hora:
            from datetime import datetime
            fecha_hora_jornada = datetime.combine(jornada.fecha, jornada.hora)
            fecha_hora_jornada = timezone.make_aware(fecha_hora_jornada)
        else:
            from datetime import datetime
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
                
                # Actualizar puntos en la tabla asistencia
                asistencia.puntos_asignados = puntos
                asistencia.save(update_fields=['puntos_asignados'])
                
                # Verificar que no tenga ya puntos por esta jornada
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


@rol_required('organizador')
def organizador_eliminar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    if jornada.estado != "pendiente":
        messages.error(request, "Solo se pueden cancelar jornadas con estado pendiente.")
        return redirect("organizador_creacion_jornadas")

    confirmacion = request.POST.get("confirmar") == "1"
    if _porcentaje_ocupacion_jornada(jornada) > 0.5 and not confirmacion:
        messages.error(request, "Esta jornada ya supera el 50% del cupo inscrito. Debes confirmar la cancelacion para continuar.")
        return redirect("organizador_creacion_jornadas")

    jornada.estado = "cancelada"
    jornada.save(update_fields=["estado", "last_update"])
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
            jornada = form.save(commit=False)
            if not jornada.id_organizador:
                jornada.id_organizador = Usuario.objects.filter(id_usuario=request.session.get("usuario_id")).first()
            if not _validar_publicacion_jornada(jornada):
                messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
                return redirect("organizador_creacion_jornadas")
            jornada.save()
            _enviar_notificaciones_automaticas_jornada(jornada, "edicion")
            messages.success(request, "Jornada modificada correctamente.")
            return redirect("organizador_creacion_jornadas")
    else:
        form = JornadaForm(instance=jornada)

    return render(request, "organizador/modificar_jornada.html", {"form": form, "jornada": jornada})


def _validar_publicacion_jornada(jornada):
    return not (jornada.estado == "activa" and not jornada.id_organizador)


def _validar_datos_jornada(request, datos, organizador):
    campos_requeridos = {
        "titulo": "El titulo es obligatorio.",
        "descripcion": "La descripcion es obligatoria.",
        "fecha": "La fecha es obligatoria.",
        "hora": "La hora es obligatoria.",
        "direccion": "El punto de encuentro es obligatorio.",
        "barrio": "El barrio es obligatorio.",
        "tipo_material": "El tipo de material es obligatorio.",
        "cupo_maximo": "El cupo maximo es obligatorio.",
        "estado": "El estado es obligatorio.",
    }

    for campo, mensaje in campos_requeridos.items():
        if not str(datos.get(campo, "")).strip():
            messages.error(request, mensaje)
            return False

    try:
        cupo = int(datos.get("cupo_maximo", 0))
        if cupo < 5 or cupo > 50:
            messages.error(request, "El cupo maximo debe estar entre 5 y 50 participantes.")
            return False
    except ValueError:
        messages.error(request, "El cupo maximo debe ser un numero valido.")
        return False

    if not organizador:
        messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
        return False

    try:
        fecha_valor = datos.get("fecha")
        if hasattr(fecha_valor, "strftime"):
            fecha_obj = fecha_valor
        else:
            fecha_obj = datetime.strptime(str(fecha_valor), "%Y-%m-%d").date()

        hora_valor = datos.get("hora")
        if hasattr(hora_valor, "strftime"):
            hora_obj = hora_valor
        else:
            hora_texto = str(hora_valor)
            try:
                hora_obj = datetime.strptime(hora_texto, "%H:%M").time()
            except ValueError:
                hora_obj = datetime.strptime(hora_texto, "%H:%M:%S").time()

        fecha_hora_jornada = timezone.make_aware(datetime.combine(fecha_obj, hora_obj))
    except ValueError:
        messages.error(request, "La fecha o la hora ingresadas no tienen un formato valido.")
        return False

    if fecha_hora_jornada <= timezone.now():
        messages.error(request, "La fecha y hora de la jornada deben ser futuras.")
        return False

    return True


def _obtener_barrios_disponibles():
    return (
        Usuario.objects.exclude(barrio__isnull=True)
        .exclude(barrio__exact="")
        .values_list("barrio", flat=True)
        .distinct()
        .order_by("barrio")
    )


def _alerta_y_redireccion(request, url):
    almacenamiento = list(get_messages(request))
    mensaje = almacenamiento[0].message if almacenamiento else "No se pudo completar la operacion."
    mensaje = (
        str(mensaje)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return HttpResponse(f"""
        <html>
        <head>
            <meta charset="utf-8">
            <title>Aviso</title>
            <style>
                body {{
                    margin: 0;
                    font-family: Arial, sans-serif;
                    background: rgba(0, 0, 0, 0.45);
                }}
                .overlay {{
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 24px;
                }}
                .modal {{
                    width: min(520px, 100%);
                    background: #fff;
                    border-radius: 16px;
                    padding: 24px;
                    box-shadow: 0 18px 60px rgba(0, 0, 0, 0.2);
                    text-align: center;
                }}
                .modal h2 {{
                    margin: 0 0 12px;
                    color: #1f4d3a;
                }}
                .modal p {{
                    margin: 0 0 18px;
                    color: #31453d;
                    line-height: 1.5;
                }}
                .btn {{
                    display: inline-block;
                    background: #2e7d5a;
                    color: #fff;
                    border: 0;
                    border-radius: 10px;
                    padding: 10px 18px;
                    font-weight: 700;
                    cursor: pointer;
                }}
            </style>
        </head>
        <body>
            <div class="overlay">
                <div class="modal">
                    <h2>Aviso</h2>
                    <p>{mensaje}</p>
                    <button class="btn" onclick="window.history.back()">Aceptar</button>
                </div>
            </div>
        </body>
        </html>
    """)


def _hay_conflicto_jornada_activa(fecha, hora, barrio, jornada_actual=None):
    conflicto = Jornada.objects.filter(
        estado="activa",
        fecha=fecha,
        hora=hora,
        barrio__iexact=barrio,
    )

    if jornada_actual and getattr(jornada_actual, "id_jornada", None):
        conflicto = conflicto.exclude(id_jornada=jornada_actual.id_jornada)

    return conflicto.exists()


def _validar_datos_jornada(request, datos, organizador, jornada_actual=None):
    campos_requeridos = {
        "titulo": "El titulo es obligatorio.",
        "descripcion": "La descripcion es obligatoria.",
        "fecha": "La fecha es obligatoria.",
        "hora": "La hora es obligatoria.",
        "direccion": "El punto de encuentro es obligatorio.",
        "barrio": "El barrio es obligatorio.",
        "tipo_material": "El tipo de material es obligatorio.",
        "cupo_maximo": "El cupo maximo es obligatorio.",
        "estado": "El estado es obligatorio.",
    }

    for campo, mensaje in campos_requeridos.items():
        if not str(datos.get(campo, "")).strip():
            messages.error(request, mensaje)
            return False

    descripcion = str(datos.get("descripcion", "")).strip()
    if len(descripcion) < 10:
        messages.error(request, "La descripcion debe contener minimo 10 caracteres.")
        return False

    try:
        cupo_maximo = int(datos.get("cupo_maximo"))
    except (TypeError, ValueError):
        messages.error(request, "El cupo maximo debe ser un numero valido.")
        return False

    if cupo_maximo < 5 or cupo_maximo > 50:
        messages.error(request, "El cupo maximo debe estar entre 5 y 50 participantes.")
        return False

    if not organizador:
        messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
        return False

    try:
        fecha_valor = datos.get("fecha")
        if hasattr(fecha_valor, "strftime"):
            fecha_obj = fecha_valor
        else:
            fecha_obj = datetime.strptime(str(fecha_valor), "%Y-%m-%d").date()

        hora_valor = datos.get("hora")
        if hasattr(hora_valor, "strftime"):
            hora_obj = hora_valor
        else:
            hora_texto = str(hora_valor)
            try:
                hora_obj = datetime.strptime(hora_texto, "%H:%M").time()
            except ValueError:
                hora_obj = datetime.strptime(hora_texto, "%H:%M:%S").time()

        fecha_hora_jornada = timezone.make_aware(datetime.combine(fecha_obj, hora_obj))
    except ValueError:
        messages.error(request, "La fecha o la hora ingresadas no tienen un formato valido.")
        return False

    if fecha_hora_jornada <= timezone.now():
        messages.error(request, "La fecha y hora de la jornada deben ser futuras.")
        return False

    barrio = str(datos.get("barrio", "")).strip()
    if _hay_conflicto_jornada_activa(fecha_obj, hora_obj, barrio, jornada_actual):
        messages.error(request, "No se puede guardar la jornada porque ya existe otra jornada activa en el mismo barrio y horario.")
        return False

    return True


@rol_required('administrador')
def admi_creacion_jornadas(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario_actual = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario_actual or usuario_actual.rol != "administrador":
        messages.error(request, "Solo los administradores pueden acceder al formulario de creacion de jornadas.")
        return redirect("login")

    barrios = _obtener_barrios_disponibles()

    if request.method == "POST":
        datos_jornada = {
            "titulo": request.POST.get("titulo"),
            "descripcion": request.POST.get("descripcion"),
            "fecha": request.POST.get("fecha"),
            "hora": request.POST.get("hora"),
            "direccion": request.POST.get("direccion"),
            "barrio": request.POST.get("barrio"),
            "tipo_material": request.POST.get("tipo_material"),
            "cupo_maximo": request.POST.get("cupo_maximo"),
            "estado": request.POST.get("estado"),
        }

        if not _validar_datos_jornada(request, datos_jornada, usuario_actual):
            return _alerta_y_redireccion(request, "/admi/creacionjornadas/")

        jornada = Jornada(
            titulo=request.POST.get("titulo"),
            descripcion=request.POST.get("descripcion"),
            fecha=request.POST.get("fecha"),
            hora=request.POST.get("hora"),
            barrio=request.POST.get("barrio"),
            direccion=request.POST.get("direccion"),
            tipo_material=request.POST.get("tipo_material"),
            cupo_maximo=request.POST.get("cupo_maximo"),
            estado=request.POST.get("estado"),
            id_organizador=usuario_actual,
        )

        if not _validar_publicacion_jornada(jornada):
            messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
            return _alerta_y_redireccion(request, "/admi/creacionjornadas/")

        jornada.save()
        _enviar_notificaciones_automaticas_jornada(jornada, "creacion")
        return HttpResponse("""
            <script>
                alert('El formulario de jornada se envio correctamente y la jornada fue creada.');
                window.location.href = '/admi/creacionjornadas/';
            </script>
        """)

    jornadas = Jornada.objects.all().order_by("-fecha")
    return render(request, "administrador/creacionjornadas.html", {
        "jornadas": jornadas,
        "barrios": barrios,
    })


@rol_required('organizador')
def organizador_creacion_jornadas(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario_actual = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario_actual or usuario_actual.rol != "organizador":
        messages.error(request, "Solo los organizadores pueden acceder al formulario de creacion de jornadas.")
        return redirect("login")

    barrios = _obtener_barrios_disponibles()

    if request.method == "POST":
        datos_jornada = {
            "titulo": request.POST.get("titulo"),
            "descripcion": request.POST.get("descripcion"),
            "fecha": request.POST.get("fecha"),
            "hora": request.POST.get("hora"),
            "direccion": request.POST.get("direccion"),
            "barrio": request.POST.get("barrio"),
            "tipo_material": request.POST.get("tipo_material"),
            "cupo_maximo": request.POST.get("cupo_maximo"),
            "estado": request.POST.get("estado"),
        }

        if not _validar_datos_jornada(request, datos_jornada, usuario_actual):
            return _alerta_y_redireccion(request, "/organizador/creacionjornadas/")

        jornada = Jornada(
            titulo=request.POST.get("titulo"),
            descripcion=request.POST.get("descripcion"),
            fecha=request.POST.get("fecha"),
            hora=request.POST.get("hora"),
            barrio=request.POST.get("barrio"),
            direccion=request.POST.get("direccion"),
            tipo_material=request.POST.get("tipo_material"),
            cupo_maximo=request.POST.get("cupo_maximo"),
            estado=request.POST.get("estado"),
            id_organizador=usuario_actual,
        )

        if not _validar_publicacion_jornada(jornada):
            messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
            return _alerta_y_redireccion(request, "/organizador/creacionjornadas/")

        jornada.save()
        _enviar_notificaciones_automaticas_jornada(jornada, "creacion")
        return HttpResponse("""
            <script>
                alert('El formulario de jornada se envio correctamente y la jornada fue creada.');
                window.location.href = '/organizador/creacionjornadas/';
            </script>
        """)

    jornadas = Jornada.objects.all().order_by("-fecha")
    return render(request, "organizador/creacionjornadas.html", {
        "jornadas": jornadas,
        "barrios": barrios,
    })

# EDITAR DEL PANEL USUARIOS
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
        viejo = {
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "correo": usuario.correo,
            "rol": usuario.rol,
            "estado": usuario.estado
        }

        usuario.nombre = request.POST.get("nombre")
        usuario.apellido = request.POST.get("apellido")
        usuario.correo = request.POST.get("correo")
        usuario.rol = request.POST.get("rol")
        usuario.estado = request.POST.get("estado")

        nueva_contra = request.POST.get("nueva_contrasena")
        if nueva_contra.strip() != "":
            usuario.contrasena = make_password(nueva_contra)

        usuario.save()

        UserChangeLog.objects.create(
            usuario=usuario,
            quien=f"{usuario_actual.nombre} {usuario_actual.apellido}",
            accion="editar",
            detalle=f"Antes: {viejo}"
        )

        messages.success(request, "Usuario actualizado correctamente.")
        return redirect("panel_usuarios")

    return render(request, "administrador/usuarios_editar.html", {"usuario": usuario})

# SUSPENDER DEL PANEL USUARIOS
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
    usuario.estado = "suspendido"
    usuario.save()

    UserChangeLog.objects.create(
        usuario=usuario,
        quien=f"{usuario_actual.nombre} {usuario_actual.apellido}",
        accion="suspender",
        detalle="Usuario suspendido"
    )

    messages.success(request, "Usuario suspendido correctamente.")
    return redirect("panel_usuarios")

@rol_required('administrador')
def eliminar_usuario(request, id_usuario):
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)

    try:
        usuario.delete()
    except IntegrityError:
        # Si no se puede eliminar, marcar como suspendido
        usuario.estado = 'suspendido'
        usuario.save()

    return redirect('panel_usuarios')


@rol_required('administrador')
def panel_puntajes(request):
    uid = request.session.get("usuario_id")
    if not uid:
        return redirect("login")
    
    usuario_actual = Usuario.objects.get(id_usuario=uid)
    if usuario_actual.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    # Obtener todos los puntajes
    puntajes_qs = Puntaje.objects.select_related('usuario', 'jornada').order_by('-fecha')

    # Paginación
    page = request.GET.get('page', 1)
    per_page = 10
    paginator = Paginator(puntajes_qs, per_page)
    page_obj = paginator.get_page(page)

    return render(request, "administrador/asignar_puntaje.html", {
        "puntajes": page_obj,
        "page_obj": page_obj
    })

@rol_required('administrador')
def perfil_admin(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")
    
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)
    
    # Solo administradores
    if usuario.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")
    
    # Puntajes del administrador (si aplica)
    puntajes = Puntaje.objects.filter(usuario=usuario).order_by('-fecha')
    total_puntos = puntajes.aggregate(total=Sum('puntos'))['total'] or 0
    mayor_puntaje = puntajes.aggregate(mayor=Max('puntos'))['mayor'] or 0
    count = puntajes.count()
    promedio = (total_puntos / count) if count > 0 else 0
    promedio = round(promedio, 2)
    
    return render(request, "administrador/perfil.html", {
        "usuario": usuario,
        "puntajes": puntajes,
        "total_puntos": total_puntos,
        "mayor_puntaje": mayor_puntaje,
        "promedio": promedio
    })

@rol_required('administrador')
def historial_puntaje(request, id_usuario):
    usuario = get_object_or_404(Usuario, pk=id_usuario)
    puntajes = Puntaje.objects.filter(usuario=usuario).order_by('-fecha')
    
    if request.method == 'POST':
        form = AsignarPuntajeForm(request.POST)
        if form.is_valid():
            nuevo_puntaje = form.save(commit=False)
            nuevo_puntaje.usuario = usuario
            nuevo_puntaje.save()
            return redirect('historial_puntaje_admin', id_usuario=id_usuario)
    else:
        form = AsignarPuntajeForm()
    
    context = {
        'usuario': usuario,
        'puntajes': puntajes,
        'form': form,
    }
    return render(request, 'administrador/historial_puntaje.html', context)

@rol_required('administrador')
def cambiar_foto_admin(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)

    # Solo administradores
    if usuario.rol != "administrador":
        messages.error(request, "No tienes permisos.")
        return redirect("admi_inicio")

    if request.method == "POST":
        foto = request.FILES.get("foto")
        if foto:
            usuario.foto = foto
            usuario.save()
            messages.success(request, "Foto de perfil actualizada.")
            return redirect("perfil_admin")  # redirige al perfil del admin

    return render(request, "administrador/cambiar_foto.html", {"usuario": usuario})

@rol_required('administrador')
def asignar_puntaje(request, id_usuario):
    usuario = get_object_or_404(Usuario, id_usuario=id_usuario)

    if request.method == "POST":
        form = PuntajeForm(request.POST)
        if form.is_valid():
            puntaje = form.save(commit=False)
            puntaje.usuario = usuario
            puntaje.save()
            messages.success(request, "Puntaje asignado correctamente.")
            return redirect("historial_puntaje", id_usuario=usuario.id_usuario)
    else:
        form = PuntajeForm()

    return render(request, "administrador/asignar_puntaje.html", {
        "usuario": usuario,
        "form": form
    })

@rol_required('administrador')
def admi_notificaciones(request):
    # Validar sesión del administrador
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario = Usuario.objects.filter(id_usuario=usuario_id, rol="administrador").first()
    if not usuario:
        return redirect("login")

    # ---- FILTROS ----
    query = request.GET.get("buscar", "")
    tipo_filtro = request.GET.get("tipo", "")
    usuario_filtro = request.GET.get("usuario", "")

    notificaciones = Notificacion.objects.all()

    # Filtro por texto
    if query:
        notificaciones = notificaciones.filter(
            Q(mensaje__icontains=query) |
            Q(tipo__icontains=query)
        )

    # Filtro por tipo
    if tipo_filtro:
        notificaciones = notificaciones.filter(tipo=tipo_filtro)

    # Filtro por usuario
    if usuario_filtro:
        notificaciones = notificaciones.filter(usuario_id=usuario_filtro)

    notificaciones = notificaciones.order_by('-fecha_envio')

    # Obtener lista de usuarios para selector
    usuarios = Usuario.objects.all()

    # ---- ENVÍO DE NOTIFICACIONES ----
    if request.method == "POST":
        id_usuario = request.POST.get("usuario_id")
        tipo = request.POST.get("tipo")
        mensaje = request.POST.get("mensaje")

        if id_usuario and tipo and mensaje:
            Notificacion.objects.create(
                usuario_id=id_usuario,
                tipo=tipo,
                mensaje=mensaje
            )

            return redirect("admi_notificaciones")

    return render(request, "administrador/notificaciones.html", {
        "usuario": usuario,
        "notificaciones": notificaciones,
        "usuarios": usuarios,
        "query": query,
        "tipo_filtro": tipo_filtro,
        "usuario_filtro": usuario_filtro
    })

@rol_required('administrador')
def admi_eliminar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    
    if jornada.estado != "pendiente":
        messages.error(request, "Solo se pueden eliminar jornadas con estado pendiente.")
        return redirect("admi_creacion_jornadas")
    
    jornada.delete()
    messages.success(request, "Jornada eliminada correctamente.")
    return redirect("admi_creacion_jornadas")

@rol_required('administrador')
def admi_modificar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)

    if request.method == "POST":
        form = JornadaForm(request.POST, instance=jornada)
        if form.is_valid():
            form.save()
            messages.success(request, "Jornada modificada correctamente.")
            return redirect("admi_creacion_jornadas")
    else:
        form = JornadaForm(instance=jornada)

    return render(request, "administrador/modificar_jornada.html", {"form": form, "jornada": jornada})


# ---------------------------
# PANEL RESIDENTE
# ---------------------------
@rol_required('residente')
def residente_lista_jornadas(request):
    from django.core.paginator import Paginator
    
    usuario_id = request.session.get("usuario_id")
    filtro = request.GET.get('filtro', '')
    
    jornadas_query = Jornada.objects.filter(
        estado='activa'
    ).order_by('fecha')
    
    if filtro == 'inscrito':
        ids_inscritos = Inscripcion.objects.filter(
            usuario_id=usuario_id, 
            estado='activa'
        ).values_list('jornada_id', flat=True)
        jornadas_query = jornadas_query.filter(id_jornada__in=ids_inscritos)
    elif filtro == 'no_inscrito':
        ids_inscritos = Inscripcion.objects.filter(
            usuario_id=usuario_id, 
            estado='activa'
        ).values_list('jornada_id', flat=True)
        jornadas_query = jornadas_query.exclude(id_jornada__in=ids_inscritos)
    
    jornadas = list(jornadas_query)
    
    for j in jornadas:
        j.inscritos_activos = Inscripcion.objects.filter(
            jornada=j, estado='activa'
        ).count()
        j.esta_inscrito = Inscripcion.objects.filter(
            jornada=j, usuario_id=usuario_id, estado='activa'
        ).exists()

    paginator = Paginator(jornadas, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "residente/lista_jornadas.html", {
        "jornadas": page_obj,
        "filtro": filtro
    })

@rol_required('residente')
def residente_ver_jornada(request, id_jornada):
    # ⚡ Cambiado de id=id_jornada a id_jornada=id_jornada
    jornada = get_object_or_404(Jornada, id_jornada=id_jornada)

    return render(request, "residente/ver_jornada.html", {
        "jornada": jornada
    })

@rol_required('residente')
def residente_foro_publicaciones(request):

    FECHA_CORTE = timezone.datetime(2025, 11, 23, tzinfo=timezone.get_current_timezone())

    publicaciones = TemaForo.objects.filter(
        fecha_publicacion__gte=FECHA_CORTE
    ).order_by("-fecha_publicacion")

    return render(request, "residente/foro_publicaciones.html", {
        "publicaciones": publicaciones
    })

@rol_required('residente')
def residente_publicacion_foro(request):

    if request.method == "POST":

        titulo = request.POST.get("titulo")
        contenido = request.POST.get("contenido")

        # Recoger correctamente el usuario logueado
        usuario_id = request.session.get("usuario_id")

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
            return redirect("residente_foro_publicaciones")

        except Exception as e:
            messages.error(request, f"Error al guardar la publicación: {e}")

    return render(request, "residente/publicacion_foro.html")

@rol_required('residente')
def residente_panel(request):
    return render(request, "residente/panel.html")


@rol_required('residente')
def residente_index(request):
    return render(request, "residente/index.html")

@rol_required('residente')
def residente_inicio(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")
    
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)
    return render(request, 'residente/inicio.html', {'usuario': usuario})

@rol_required('residente')
def residente_inscripcion(request, id_jornada):
    jornada = get_object_or_404(Jornada, id_jornada=id_jornada)
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)

    # Bloquear inscripción a jornadas no activas
    if jornada.estado != 'activa':
        messages.error(request, "No puedes inscribirte en esta jornada porque esta " + jornada.estado + ".")
        return render(request, "residente/inscripcion.html", {
            "jornada": jornada,
            "usuario": usuario
        })

    if request.method == "POST":

        # Verificar si ya está inscrito
        ya_inscrito = Inscripcion.objects.filter(
            usuario=usuario,
            jornada=jornada,
            estado='activa'
        ).exists()

        if ya_inscrito:
            messages.error(request, "Ya estas inscrito en esta jornada.")
            return render(request, "residente/inscripcion.html", {
                "jornada": jornada,
                "usuario": usuario
            })

        # Verificar cupo máximo
        inscritos_activos = Inscripcion.objects.filter(
            jornada=jornada,
            estado='activa'
        ).count()

        if jornada.cupo_maximo and inscritos_activos >= jornada.cupo_maximo:
            messages.error(request, "Lo sentimos, esta jornada ya alcanzo el cupo maximo.")
            return render(request, "residente/inscripcion.html", {
                "jornada": jornada,
                "usuario": usuario
            })

        # Guardar inscripción
        Inscripcion.objects.create(
            usuario=usuario,
            jornada=jornada,
            estado='activa'
        )

        mensaje = (
            f"Hola {usuario.nombre}!\n\n"
            f"Tu inscripcion a la jornada fue exitosa. Aqui estan los detalles:\n\n"
            f"Jornada: {jornada.titulo}\n"
            f"Fecha: {jornada.fecha}\n"
            f"Hora: {jornada.hora}\n"
            f"Lugar: {jornada.direccion}, {jornada.barrio}\n"
            f"Tipo de material: {jornada.tipo_material}\n\n"
            f"Te esperamos. Recuerda llegar a tiempo.\n"
            f"Equipo Recicla Comuna 4"
        )

        Notificacion.objects.create(
            usuario=usuario,
            tipo="inscripcion",
            mensaje=mensaje
        )

        send_mail(
            subject="Confirmacion de inscripcion - Recicla Comuna 4",
            message=mensaje,
            from_email="reciclacomuna@gmail.com",
            recipient_list=[usuario.correo],
            fail_silently=True,
        )

        return render(request, "residente/inscripcion.html", {
            "jornada": jornada,
            "usuario": usuario,
            "inscripcion_exitosa": True
        })

    return render(request, "residente/inscripcion.html", {
        "jornada": jornada,
        "usuario": usuario
    })

@rol_required('residente')
def residente_configuracion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)

    if request.method == "POST":

        password_actual = request.POST.get("password_actual")
        password_nueva = request.POST.get("password_nueva")
        password_confirmacion = request.POST.get("password_confirmacion")

        # Verifica que sea este formulario
        if password_actual and password_nueva and password_confirmacion:

            # 1. Validar contraseña actual ENCRIPTADA
            if not check_password(password_actual, usuario.contrasena):
                messages.error(request, "❌ La contraseña actual es incorrecta.")
                return redirect("residente_configuracion")

            # 2. Validar coincidencia
            if password_nueva != password_confirmacion:
                messages.error(request, "❌ Las nuevas contraseñas no coinciden.")
                return redirect("residente_configuracion")

            # 3. Guardar nueva contraseña encriptada
            usuario.contrasena = make_password(password_nueva)
            usuario.save()

            messages.success(request, "✔ Contraseña actualizada. Inicia sesión nuevamente.")
            return redirect("login")

    return render(request, "residente/configuracion.html", {"usuario": usuario})

@rol_required('residente')
def residente_recoleccion(request):
    return render(request, "residente/recoleccion.html")

@rol_required('residente')
def residente_cat_recompensas(request):
    from .models import Recompensa
    
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    
    recompensas = Recompensa.objects.filter(disponible=True, cantidad_disponible__gt=0).order_by('-fecha_creacion')
    return render(request, "residente/cat_recompensas.html", {
        'recompensas': recompensas,
        'usuario': usuario
    })

@rol_required('residente')
def residente_canje_recompensa(request):
    from django.http import JsonResponse
    from .models import Recompensa, CanjeRecompensa, Puntaje
    
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'}, status=405)
    
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    
    if not usuario:
        return JsonResponse({'success': False, 'error': 'Usuario no encontrado'}, status=400)
    
    recompensa_id = request.POST.get('recompensa_id')
    direccion = request.POST.get('direccion', '').strip()
    barrio = request.POST.get('barrio', '').strip()
    observaciones = request.POST.get('observaciones', '').strip()
    
    if not recompensa_id or not direccion or not barrio:
        return JsonResponse({'success': False, 'error': 'Todos los campos son requeridos'}, status=400)
    
    try:
        recompensa = Recompensa.objects.get(id_recompensa=recompensa_id)
    except Recompensa.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Recompensa no encontrada'}, status=400)
    
    if recompensa.cantidad_disponible <= 0:
        return JsonResponse({'success': False, 'error': 'Recompensa agotada'}, status=400)
    
    puntos_usuario = usuario.puntaje_total
    if puntos_usuario < recompensa.puntos_requeridos:
        return JsonResponse({'success': False, 'error': 'Puntos insuficientes'}, status=400)
    
    try:
        CanjeRecompensa.objects.create(
            usuario=usuario,
            recompensa=recompensa,
            direccion=direccion,
            barrio=barrio,
            observaciones=observaciones if observaciones else None
        )
        
        recompensa.cantidad_disponible -= 1
        if recompensa.cantidad_disponible <= 0:
            recompensa.disponible = False
        recompensa.save()
        
        Puntaje.objects.create(
            usuario=usuario,
            puntos=-recompensa.puntos_requeridos,
            motivo=f"Canje de recompensa: {recompensa.titulo}",
            recompensa=recompensa
        )
        
        return JsonResponse({'success': True, 'message': 'Canje exitoso'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@rol_required('residente')
def residente_como_participar(request):
    return render(request, "residente/como_participar.html")

@rol_required('residente')
def residente_educacion(request):
    return render(request, "residente/educacion.html")

@rol_required('residente')
def residente_contacto(request):
    return render(request, "residente/contacto.html")

@rol_required('residente')
def perfil_residente(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)

    puntajes = Puntaje.objects.filter(usuario=usuario).order_by('-fecha')

    # total de puntos (agregado)
    total_puntos = puntajes.aggregate(total=Sum('puntos'))['total'] or 0

    # mayor puntaje (Max) - asegúrate de importar Max como mostré arriba
    mayor_puntaje = puntajes.aggregate(mayor=Max('puntos'))['mayor'] or 0

    # cuenta y promedio (evitar llamadas repetidas a .count())
    count = puntajes.count()
    promedio = (total_puntos / count) if count > 0 else 0
    promedio = round(promedio, 2)

    return render(request, 'residente/perfil.html', {
        'usuario': usuario,
        'puntajes': puntajes,
        'total_puntos': total_puntos,
        'mayor_puntaje': mayor_puntaje,
        'promedio': promedio,
    })
 
@rol_required('residente')       
def cambiar_foto(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)

    if request.method == "POST":
        foto = request.FILES.get("foto")
        if foto:
            usuario.foto = foto
            usuario.save()
            return redirect("perfil_residente")

    return render(request, "residente/cambiar_foto.html", {"usuario": usuario})

@rol_required('residente')
def residente_notificaciones(request):

    # Validar sesión del administrador
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    # Obtener usuario desde tu tabla personalizada
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return redirect("login")

    # Cargar notificaciones correctamente
    notificaciones = Notificacion.objects.filter(
        usuario_id=usuario.id_usuario
    ).order_by('-fecha_envio')

    return render(request, "residente/notificaciones.html", {
        "usuario": usuario,
        "notificaciones": notificaciones
    })








# ---------------------------
# PANEL ORGANIZADOR
# ---------------------------

# CREAR JORNADA
@rol_required('organizador')
def organizador_creacion_jornadas(request):
    print("DEBUG SESION:", request.session.get("usuario_id"), request.session.get("usuario_rol"))

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
            "jornadas": jornadas
        })

@rol_required('organizador')
def organizador_eliminar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    
    if jornada.estado != "pendiente":
        messages.error(request, "Solo se pueden eliminar jornadas con estado pendiente.")
        return redirect("organizador_creacion_jornadas")
    
    jornada.delete()
    messages.success(request, "Jornada eliminada correctamente.")
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

# FORO
@rol_required('organizador')
def organizador_foro_publicaciones(request):

    FECHA_CORTE = timezone.datetime(2025, 11, 23, tzinfo=timezone.get_current_timezone())

    publicaciones = TemaForo.objects.filter(
        fecha_publicacion__gte=FECHA_CORTE
    ).order_by("-fecha_publicacion")

    return render(request, "organizador/foro_publicaciones.html", {
        "publicaciones": publicaciones
    })

@rol_required('organizador')
def organizador_publicacion_foro(request):

    if request.method == "POST":

        titulo = request.POST.get("titulo")
        contenido = request.POST.get("contenido")

        # Recoger correctamente el usuario logueado
        usuario_id = request.session.get("usuario_id")

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
            return redirect("organizador_foro_publicaciones")

        except Exception as e:
            messages.error(request, f"Error al guardar la publicación: {e}")

    return render(request, "organizador/publicacion_foro.html")

@rol_required('organizador')
def organizador_recoleccion(request):
    return render(request, "organizador/recoleccion.html")

@rol_required('organizador')
def organizador_recompensa(request):
    from .models import Recompensa
    
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
        
        return redirect('organizador_recompensa')
    
    recompensas = Recompensa.objects.all().order_by('-fecha_creacion')
    return render(request, "organizador/recompensa.html", {'recompensas': recompensas})

@rol_required('organizador')
def organizador_recompensa_canjes(request, recompensa_id):
    from .models import CanjeRecompensa, Recompensa
    
    recompensa = get_object_or_404(Recompensa, id_recompensa=recompensa_id)
    canjes = CanjeRecompensa.objects.filter(recompensa=recompensa).select_related('usuario')
    
    return render(request, "organizador/recompensa_canjes.html", {
        'recompensa': recompensa,
        'canjes': canjes
    })

@rol_required('organizador')
def organizador_educacion(request):
    return render(request, "organizador/educacion.html")

@rol_required('organizador')
def organizador_contacto(request):
    return render(request, "organizador/contacto.html")

@rol_required('organizador')
def organizador_inicio(request):
    return render(request, "organizador/inicio.html")

@rol_required('organizador')
def organizador_asistencia(request):
    from .models import AccionDestacada
    # Mostrar todas las jornadas excepto las canceladas
    jornadas_finalizadas = Jornada.objects.exclude(estado='cancelada').order_by('-fecha')

    jornada_id = request.GET.get('jornada_id') or request.POST.get('jornada_id')
    jornada = None
    inscripciones = []

    if jornada_id:
        jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
        inscripciones = Inscripcion.objects.filter(
            jornada=jornada,
            estado='activa'
        ).select_related('usuario')

    if request.method == "POST" and jornada:
        for inscripcion in inscripciones:
            descripcion = request.POST.get(f"accion_{inscripcion.id_inscripcion}", "").strip()
            puntos = request.POST.get(f"puntos_{inscripcion.id_inscripcion}", 5)

            if descripcion:
                AccionDestacada.objects.create(
                    inscripcion=inscripcion,
                    descripcion=descripcion,
                    puntos_sugeridos=puntos,
                    validada=False
                )

        messages.success(request, "Acciones destacadas registradas. El administrador las validara.")
        return redirect("organizador_asistencia")

    return render(request, "organizador/asistencia.html", {
        "jornadas_finalizadas": jornadas_finalizadas,
        "jornada": jornada,
        "inscripciones": inscripciones
    })

# CONFIGURACION
@rol_required('organizador')
def organizador_configuracion(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)

    if request.method == "POST":

        password_actual = request.POST.get("password_actual")
        password_nueva = request.POST.get("password_nueva")
        password_confirmacion = request.POST.get("password_confirmacion")

        # Verifica que sea este formulario
        if password_actual and password_nueva and password_confirmacion:

            # 1. Validar contraseña actual ENCRIPTADA
            if not check_password(password_actual, usuario.contrasena):
                messages.error(request, "❌ La contraseña actual es incorrecta.")
                return redirect("organizador_configuracion")

            # 2. Validar coincidencia
            if password_nueva != password_confirmacion:
                messages.error(request, "❌ Las nuevas contraseñas no coinciden.")
                return redirect("organizador_configuracion")

            # 3. Guardar nueva contraseña encriptada
            usuario.contrasena = make_password(password_nueva)
            usuario.save()

            messages.success(request, "✔ Contraseña actualizada. Inicia sesión nuevamente.")
            return redirect("login")

    return render(request, "organizador/configuracion.html", {"usuario": usuario})

@rol_required('organizador')
def perfil_organizador(request):
        usuario_id = request.session.get("usuario_id")
        usuario = get_object_or_404(Usuario, id_usuario=usuario_id)

        puntajes = Puntaje.objects.filter(usuario=usuario).order_by('-fecha')

        # total de puntos (agregado)
        total_puntos = puntajes.aggregate(total=Sum('puntos'))['total'] or 0

        # mayor puntaje (Max) - asegúrate de importar Max como mostré arriba
        mayor_puntaje = puntajes.aggregate(mayor=Max('puntos'))['mayor'] or 0

        # cuenta y promedio (evitar llamadas repetidas a .count())
        count = puntajes.count()
        promedio = (total_puntos / count) if count > 0 else 0
        promedio = round(promedio, 2)

        return render(request, 'organizador/perfil.html', {
            'usuario': usuario,
            'puntajes': puntajes,
            'total_puntos': total_puntos,
            'mayor_puntaje': mayor_puntaje,
            'promedio': promedio,
        })
            
@rol_required('organizador')
def cambiar_foto_organizador(request):
    usuario_id = request.session.get("usuario_id")
    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)

    # Solo administradores
    if usuario.rol != "organizador":
        messages.error(request, "No tienes permisos.")
        return redirect("organizador_inicio")

    if request.method == "POST":
        foto = request.FILES.get("foto")
        if foto:
            usuario.foto = foto
            usuario.save()
            messages.success(request, "Foto de perfil actualizada.")
            return redirect("perfil_organizador")  # redirige al perfil del admin

    return render(request, "organizador/cambiar_foto.html", {"usuario": usuario})


@rol_required('administrador')
def admi_inicio(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    _avisar_notificaciones_nuevas(request, usuario)
    return render(request, "administrador/inicio.html")


@rol_required('organizador')
def organizador_inicio(request):
    usuario_id = request.session.get("usuario_id")
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    _avisar_notificaciones_nuevas(request, usuario)
    return render(request, "organizador/inicio.html")


@rol_required('organizador')
def organizador_notificaciones(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return redirect("login")

    _avisar_notificaciones_nuevas(request, usuario)
    notificaciones = Notificacion.objects.filter(
        usuario_id=usuario.id_usuario
    ).order_by('-fecha_envio')

    return render(request, "organizador/notificaciones.html", {
        "usuario": usuario,
        "notificaciones": notificaciones
    })


@rol_required('residente')
def residente_inicio(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)
    _asegurar_notificaciones_jornadas_usuario(usuario)
    _avisar_notificaciones_nuevas(request, usuario)
    return render(request, "residente/inicio.html", {"usuario": usuario})


@rol_required('residente')
def residente_notificaciones(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return redirect("login")

    _asegurar_notificaciones_jornadas_usuario(usuario)
    _avisar_notificaciones_nuevas(request, usuario)

    notificaciones = Notificacion.objects.filter(
        usuario_id=usuario.id_usuario
    ).order_by('-fecha_envio')

    return render(request, "residente/notificaciones.html", {
        "usuario": usuario,
        "notificaciones": notificaciones
    })


@rol_required('administrador')
def admi_notificaciones(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario = Usuario.objects.filter(id_usuario=usuario_id, rol="administrador").first()
    if not usuario:
        return redirect("login")

    query = request.GET.get("buscar", "")
    tipo_filtro = request.GET.get("tipo", "")
    usuario_filtro = request.GET.get("usuario", "")
    barrio_filtro = request.GET.get("barrio", "")
    rol_filtro = request.GET.get("rol", "")

    notificaciones = Notificacion.objects.select_related("usuario").all()

    if query:
        notificaciones = notificaciones.filter(
            Q(mensaje__icontains=query) |
            Q(tipo__icontains=query) |
            Q(usuario__nombre__icontains=query) |
            Q(usuario__apellido__icontains=query) |
            Q(usuario__barrio__icontains=query)
        )

    if tipo_filtro:
        notificaciones = notificaciones.filter(tipo=tipo_filtro)

    if usuario_filtro:
        notificaciones = notificaciones.filter(usuario_id=usuario_filtro)

    if barrio_filtro:
        notificaciones = notificaciones.filter(usuario__barrio__iexact=barrio_filtro)

    if rol_filtro:
        notificaciones = notificaciones.filter(usuario__rol=rol_filtro)

    notificaciones = notificaciones.order_by("-fecha_envio")
    paginator = Paginator(notificaciones, 10)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    usuarios = Usuario.objects.all().order_by("nombre", "apellido")
    barrios = (
        Usuario.objects.exclude(barrio__isnull=True)
        .exclude(barrio__exact="")
        .values_list("barrio", flat=True)
        .distinct()
        .order_by("barrio")
    )
    roles = [rol for rol, _ in Usuario.ROL_CHOICES]

    if request.method == "POST":
        destino = request.POST.get("destino")
        id_usuario = request.POST.get("usuario_id")
        barrio_envio = request.POST.get("barrio_envio", "").strip()
        rol_envio = request.POST.get("rol_envio", "").strip()
        tipo = request.POST.get("tipo")
        mensaje = request.POST.get("mensaje")

        destinatarios = Usuario.objects.none()

        if destino == "usuario" and id_usuario:
            destinatarios = Usuario.objects.filter(id_usuario=id_usuario)
        elif destino == "barrio" and barrio_envio:
            destinatarios = Usuario.objects.filter(
                barrio__iexact=barrio_envio,
                estado="activo"
            )
        elif destino == "todos_barrios":
            destinatarios = Usuario.objects.exclude(
                barrio__isnull=True
            ).exclude(
                barrio__exact=""
            ).filter(
                estado="activo"
            )
        elif destino == "rol" and rol_envio:
            destinatarios = Usuario.objects.filter(
                rol=rol_envio,
                estado="activo"
            )

        if destinatarios.exists() and tipo and mensaje:
            Notificacion.objects.bulk_create([
                Notificacion(usuario=u, tipo=tipo, mensaje=mensaje, canal="web")
                for u in destinatarios
            ])
            messages.success(request, f"La notificacion se envio correctamente a {destinatarios.count()} usuario(s).")
            return redirect("admi_notificaciones")

        messages.error(request, "No se pudo enviar la notificacion. Verifica el destino, el tipo y el mensaje.")
        return redirect("admi_notificaciones")

    return render(request, "administrador/notificaciones.html", {
        "usuario": usuario,
        "notificaciones": page_obj,
        "page_obj": page_obj,
        "usuarios": usuarios,
        "barrios": barrios,
        "roles": roles,
        "query": query,
        "tipo_filtro": tipo_filtro,
        "usuario_filtro": usuario_filtro,
        "barrio_filtro": barrio_filtro,
        "rol_filtro": rol_filtro
    })


# Helpers finales de notificaciones de jornadas.
def _canales_notificacion_usuario(usuario):
    canales = ["web"]
    if getattr(usuario, "canal_notificacion_correo", False):
        canales.append("correo")
    if getattr(usuario, "canal_notificacion_push", False):
        canales.append("push")
    return canales


def _enviar_notificaciones_automaticas_jornada(jornada, accion):
    barrio = (getattr(jornada, "barrio", "") or "").strip()
    if not barrio:
        return 0

    residentes = Usuario.objects.filter(
        rol="residente",
        estado="activo",
    )

    fecha_jornada = "por definir"
    if getattr(jornada, "fecha", None):
        if hasattr(jornada.fecha, "strftime"):
            fecha_jornada = jornada.fecha.strftime("%d/%m/%Y")
        else:
            try:
                fecha_jornada = datetime.strptime(str(jornada.fecha), "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                fecha_jornada = str(jornada.fecha)

    hora_jornada = "por definir"
    if getattr(jornada, "hora", None):
        if hasattr(jornada.hora, "strftime"):
            hora_jornada = jornada.hora.strftime("%H:%M")
        else:
            hora_texto = str(jornada.hora)
            try:
                hora_jornada = datetime.strptime(hora_texto, "%H:%M:%S").strftime("%H:%M")
            except ValueError:
                try:
                    hora_jornada = datetime.strptime(hora_texto, "%H:%M").strftime("%H:%M")
                except ValueError:
                    hora_jornada = hora_texto

    accion_texto = "creada" if accion == "creacion" else "actualizada"
    mensaje = (
        f"La jornada '{jornada.titulo}' fue {accion_texto} para el barrio {barrio}. "
        f"Fecha: {fecha_jornada}. Hora: {hora_jornada}. Direccion: {jornada.direccion or 'Por definir'}."
    )

    enviados = 0
    for residente in residentes:
        if (getattr(residente, "barrio", "") or "").strip().lower() != barrio.lower():
            continue

        canales = _canales_notificacion_usuario(residente)

        for canal in canales:
            Notificacion.objects.create(
                usuario=residente,
                tipo="jornada",
                canal=canal,
                mensaje=mensaje,
            )
            enviados += 1

            if canal == "correo" and residente.correo:
                send_mail(
                    subject=f"Jornada {accion_texto}: {jornada.titulo}",
                    message=mensaje,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[residente.correo],
                    fail_silently=True,
                )

    return enviados


def _asegurar_notificaciones_jornadas_usuario(usuario):
    if not usuario or getattr(usuario, "rol", "") != "residente" or getattr(usuario, "estado", "") != "activo":
        return 0

    barrio_usuario = (getattr(usuario, "barrio", "") or "").strip().lower()
    if not barrio_usuario:
        return 0

    creadas = 0
    jornadas = Jornada.objects.filter(estado__in=["activa", "pendiente"]).order_by("-fecha")

    for jornada in jornadas:
        barrio_jornada = (getattr(jornada, "barrio", "") or "").strip().lower()
        if barrio_jornada != barrio_usuario:
            continue

        fecha_jornada = "por definir"
        if getattr(jornada, "fecha", None):
            if hasattr(jornada.fecha, "strftime"):
                fecha_jornada = jornada.fecha.strftime("%d/%m/%Y")
            else:
                fecha_jornada = str(jornada.fecha)

        hora_jornada = "por definir"
        if getattr(jornada, "hora", None):
            if hasattr(jornada.hora, "strftime"):
                hora_jornada = jornada.hora.strftime("%H:%M")
            else:
                hora_jornada = str(jornada.hora)

        mensaje = (
            f"La jornada '{jornada.titulo}' fue creada para el barrio {jornada.barrio}. "
            f"Fecha: {fecha_jornada}. Hora: {hora_jornada}. Direccion: {jornada.direccion or 'Por definir'}."
        )

        existe = Notificacion.objects.filter(
            usuario=usuario,
            tipo="jornada",
            canal="web",
            mensaje=mensaje,
        ).exists()

        if not existe:
            Notificacion.objects.create(
                usuario=usuario,
                tipo="jornada",
                canal="web",
                mensaje=mensaje,
            )
            creadas += 1

    return creadas


def _avisar_notificaciones_nuevas(request, usuario):
    if not usuario:
        return

    ultima_notificacion = Notificacion.objects.filter(
        usuario=usuario
    ).order_by("-fecha_envio").first()

    if not ultima_notificacion:
        return

    clave = f"ultima_notificacion_vista_{usuario.id_usuario}"
    ultima_vista = request.session.get(clave)
    marca_actual = ultima_notificacion.fecha_envio.isoformat()

    if ultima_vista != marca_actual:
        messages.info(request, "Tienes una nueva notificacion.")
        request.session[clave] = marca_actual


def _enviar_notificaciones_automaticas_foro(publicacion, autor=None):
    if not publicacion:
        return 0

    destinatarios = Usuario.objects.filter(estado="activo")
    if autor and getattr(autor, "id_usuario", None):
        destinatarios = destinatarios.exclude(id_usuario=autor.id_usuario)

    mensaje = f"Hay una nueva publicacion en el foro: {publicacion.titulo}."
    enviados = 0

    for usuario in destinatarios:
        canales = _canales_notificacion_usuario(usuario)
        for canal in canales:
            Notificacion.objects.create(
                usuario=usuario,
                tipo="foro",
                canal=canal,
                mensaje=mensaje,
            )
            enviados += 1

            if canal == "correo" and usuario.correo:
                send_mail(
                    subject=f"Nueva publicacion en el foro: {publicacion.titulo}",
                    message=mensaje,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[usuario.correo],
                    fail_silently=True,
                )

    return enviados


@rol_required('residente')
def residente_inicio(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario = get_object_or_404(Usuario, id_usuario=usuario_id)
    _asegurar_notificaciones_jornadas_usuario(usuario)
    _avisar_notificaciones_nuevas(request, usuario)
    return render(request, "residente/inicio.html", {"usuario": usuario})


@rol_required('residente')
def residente_notificaciones(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return redirect("login")

    _asegurar_notificaciones_jornadas_usuario(usuario)
    _avisar_notificaciones_nuevas(request, usuario)

    notificaciones = Notificacion.objects.filter(
        usuario_id=usuario.id_usuario
    ).order_by("-fecha_envio")

    paginator = Paginator(notificaciones, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, "residente/notificaciones.html", {
        "usuario": usuario,
        "notificaciones": page_obj
    })


@rol_required('residente')
def residente_eliminar_notificacion(request, notificacion_id):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")
    
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return redirect("login")
    
    notificacion = Notificacion.objects.filter(
        id_notificacion=notificacion_id,
        usuario_id=usuario.id_usuario
    ).first()
    
    if notificacion:
        notificacion.delete()
        messages.success(request, "Notificación eliminada correctamente.")
    
    return redirect("residente_notificaciones")


@rol_required('residente')
def residente_eliminar_todas_notificaciones(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")
    
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return redirect("login")
    
    Notificacion.objects.filter(usuario_id=usuario.id_usuario).delete()
    messages.success(request, "Todas las notificaciones han sido eliminadas.")
    
    return redirect("residente_notificaciones")


@rol_required('organizador')
def organizador_notificaciones(request):

    # Validar sesión del administrador
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    # Obtener usuario desde tu tabla personalizada
    usuario = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario:
        return redirect("login")

    # Cargar notificaciones correctamente
    notificaciones = Notificacion.objects.filter(
        usuario_id=usuario.id_usuario
    ).order_by('-fecha_envio')

    return render(request, "organizador/notificaciones.html", {
        "usuario": usuario,
        "notificaciones": notificaciones
    })



# ---------------------------
# PANEL USUARIO
# ---------------------------

def usuario_inicio(request):
    return render(request, "usuario/inicio.html")

def usuario_como_participar(request):
    return render(request, "usuario/como_participar.html")

def usuario_educacion(request):
    return render(request, "usuario/educacion.html")

def usuario_contacto(request):
    return render(request, "usuario/contacto.html")


def usuario_foro_publicaciones(request):

    FECHA_CORTE = timezone.datetime(2025, 11, 23, tzinfo=timezone.get_current_timezone())

    publicaciones = TemaForo.objects.filter(
        fecha_publicacion__gte=FECHA_CORTE
    ).order_by("-fecha_publicacion")

    return render(request, "usuario/foro_publicaciones.html", {
        "publicaciones": publicaciones
    })



# ---------------------------
# LOGOUT
# ---------------------------

def logout_view(request):
    # Elimina la sesión completa
    request.session.flush()
    messages.success(request, "Sesión cerrada correctamente.")
    
    return redirect('login')  # Cambia 'login' si tu url del login tiene otro nombre


@rol_required('administrador')
def admi_creacion_jornadas(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario_actual = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario_actual or usuario_actual.rol != "administrador":
        messages.error(request, "Solo los administradores pueden acceder al formulario de creacion de jornadas.")
        return _alerta_y_redireccion(request, "/login/")

    barrios = _obtener_barrios_disponibles()

    if request.method == "POST":
        datos_jornada = {
            "titulo": request.POST.get("titulo"),
            "descripcion": request.POST.get("descripcion"),
            "fecha": request.POST.get("fecha"),
            "hora": request.POST.get("hora"),
            "direccion": request.POST.get("direccion"),
            "barrio": request.POST.get("barrio"),
            "tipo_material": request.POST.get("tipo_material"),
            "cupo_maximo": request.POST.get("cupo_maximo"),
            "estado": request.POST.get("estado"),
        }

        if not _validar_datos_jornada(request, datos_jornada, usuario_actual):
            return _alerta_y_redireccion(request, "/admi/creacionjornadas/")

        jornada = Jornada(
            titulo=datos_jornada["titulo"],
            descripcion=datos_jornada["descripcion"],
            fecha=datos_jornada["fecha"],
            hora=datos_jornada["hora"],
            barrio=datos_jornada["barrio"],
            direccion=datos_jornada["direccion"],
            tipo_material=datos_jornada["tipo_material"],
            cupo_maximo=datos_jornada["cupo_maximo"],
            estado=datos_jornada["estado"],
            id_organizador=usuario_actual,
        )

        if not _validar_publicacion_jornada(jornada):
            messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
            return _alerta_y_redireccion(request, "/admi/creacionjornadas/")

        jornada.save()
        _enviar_notificaciones_automaticas_jornada(jornada, "creacion")
        return HttpResponse("""
            <script>
                alert('El formulario de jornada se envio correctamente y la jornada fue creada.');
                window.location.href = '/admi/creacionjornadas/';
            </script>
        """)

    # Obtener filtros del GET
    filtro_estado = request.GET.get('estado', '')
    filtro_material = request.GET.get('tipo_material', '')
    
    # Query base
    jornadas = Jornada.objects.all().order_by("-fecha")
    
    # Aplicar filtros
    if filtro_estado:
        jornadas = jornadas.filter(estado=filtro_estado)
    if filtro_material:
        jornadas = jornadas.filter(tipo_material=filtro_material)
    
    # Paginación
    paginator = Paginator(jornadas, 10)  # 10 jornadas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "administrador/creacionjornadas.html", {
        "jornadas": page_obj,
        "barrios": barrios,
        "filtro_estado": filtro_estado,
        "filtro_material": filtro_material,
    })


@rol_required('organizador')
def organizador_creacion_jornadas(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario_actual = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario_actual or usuario_actual.rol != "organizador":
        messages.error(request, "Solo los organizadores pueden acceder al formulario de creacion de jornadas.")
        return _alerta_y_redireccion(request, "/login/")

    barrios = _obtener_barrios_disponibles()

    if request.method == "POST":
        datos_jornada = {
            "titulo": request.POST.get("titulo"),
            "descripcion": request.POST.get("descripcion"),
            "fecha": request.POST.get("fecha"),
            "hora": request.POST.get("hora"),
            "direccion": request.POST.get("direccion"),
            "barrio": request.POST.get("barrio"),
            "tipo_material": request.POST.get("tipo_material"),
            "cupo_maximo": request.POST.get("cupo_maximo"),
            "estado": request.POST.get("estado"),
        }

        if not _validar_datos_jornada(request, datos_jornada, usuario_actual):
            return _alerta_y_redireccion(request, "/organizador/creacionjornadas/")

        jornada = Jornada(
            titulo=datos_jornada["titulo"],
            descripcion=datos_jornada["descripcion"],
            fecha=datos_jornada["fecha"],
            hora=datos_jornada["hora"],
            barrio=datos_jornada["barrio"],
            direccion=datos_jornada["direccion"],
            tipo_material=datos_jornada["tipo_material"],
            cupo_maximo=datos_jornada["cupo_maximo"],
            estado=datos_jornada["estado"],
            id_organizador=usuario_actual,
        )

        if not _validar_publicacion_jornada(jornada):
            messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
            return _alerta_y_redireccion(request, "/organizador/creacionjornadas/")

        jornada.save()
        _enviar_notificaciones_automaticas_jornada(jornada, "creacion")
        return HttpResponse("""
            <script>
                alert('El formulario de jornada se envio correctamente y la jornada fue creada.');
                window.location.href = '/organizador/creacionjornadas/';
            </script>
        """)

    jornadas = Jornada.objects.all().order_by("-fecha")
    return render(request, "organizador/creacionjornadas.html", {
        "jornadas": jornadas,
        "barrios": barrios,
    })


@rol_required('administrador')
def admi_creacion_jornadas(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario_actual = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario_actual or usuario_actual.rol != "administrador":
        messages.error(request, "Solo los administradores pueden acceder al formulario de creacion de jornadas.")
        return redirect("login")

    barrios = _obtener_barrios_disponibles()

    if request.method == "POST":
        datos_jornada = {
            "titulo": request.POST.get("titulo"),
            "descripcion": request.POST.get("descripcion"),
            "fecha": request.POST.get("fecha"),
            "hora": request.POST.get("hora"),
            "direccion": request.POST.get("direccion"),
            "barrio": request.POST.get("barrio"),
            "tipo_material": request.POST.get("tipo_material"),
            "cupo_maximo": request.POST.get("cupo_maximo"),
            "estado": request.POST.get("estado"),
        }

        if not _validar_datos_jornada(request, datos_jornada, usuario_actual):
            filtro_estado = request.GET.get('estado', '')
            filtro_material = request.GET.get('tipo_material', '')
            jornadas = Jornada.objects.all().order_by("-fecha")
            if filtro_estado:
                jornadas = jornadas.filter(estado=filtro_estado)
            if filtro_material:
                jornadas = jornadas.filter(tipo_material=filtro_material)
            paginator = Paginator(jornadas, 10)
            page_obj = paginator.get_page(request.GET.get('page'))
            return render(request, "administrador/creacionjornadas.html", {
                "jornadas": page_obj,
                "barrios": barrios,
                "filtro_estado": filtro_estado,
                "filtro_material": filtro_material,
            })

        jornada = Jornada(
            titulo=datos_jornada["titulo"],
            descripcion=datos_jornada["descripcion"],
            fecha=datos_jornada["fecha"],
            hora=datos_jornada["hora"],
            barrio=datos_jornada["barrio"],
            direccion=datos_jornada["direccion"],
            tipo_material=datos_jornada["tipo_material"],
            cupo_maximo=datos_jornada["cupo_maximo"],
            estado=datos_jornada["estado"],
            id_organizador=usuario_actual,
        )

        if not _validar_publicacion_jornada(jornada):
            messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
            return redirect("admi_creacion_jornadas")

        jornada.save()
        _enviar_notificaciones_automaticas_jornada(jornada, "creacion")
        return HttpResponse("""
            <script>
                alert('El formulario de jornada se envio correctamente y la jornada fue creada.');
                window.location.href = '/admi/creacionjornadas/';
            </script>
        """)

    filtro_estado = request.GET.get('estado', '')
    filtro_material = request.GET.get('tipo_material', '')
    
    jornadas = Jornada.objects.all().order_by("-fecha")
    
    if filtro_estado:
        jornadas = jornadas.filter(estado=filtro_estado)
    if filtro_material:
        jornadas = jornadas.filter(tipo_material=filtro_material)
    
    paginator = Paginator(jornadas, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    return render(request, "administrador/creacionjornadas.html", {
        "jornadas": page_obj,
        "barrios": barrios,
        "filtro_estado": filtro_estado,
        "filtro_material": filtro_material,
    })


@rol_required('administrador')
def admi_detalle_jornada(request, jornada_id):
    """Vista para ver los detalles de una jornada incluyendo participantes"""
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")
    
    usuario_actual = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario_actual or usuario_actual.rol != "administrador":
        messages.error(request, "Solo los administradores pueden acceder a esta página.")
        return redirect("login")
    
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    
    # Obtener participantes (inscripciones)
    inscripciones = Inscripcion.objects.filter(
        jornada=jornada,
        estado='activa'
    ).select_related('usuario')
    
    # Obtener registros de asistencia
    from .models import Asistencia
    ids_inscripcion = list(inscripciones.values_list('id_inscripcion', flat=True))
    asistentes = {}
    if ids_inscripcion:
        registros_asistencia = Asistencia.objects.filter(inscripcion_id__in=ids_inscripcion)
        for reg in registros_asistencia:
            asistentes[reg.inscripcion_id] = reg
    
    # Preparar datos de participantes
    participantes = []
    for inscripcion in inscripciones:
        usuario = inscripcion.usuario
        asistencia = asistentes.get(inscripcion.id_inscripcion)
        participantes.append({
            'nombre': usuario.nombre if usuario else 'No especificado',
            'correo': usuario.correo if usuario else '',
            'telefono': usuario.telefono if usuario else '',
            'asistio': asistencia.presente if asistencia else None,
            'puntos': asistencia.puntos_asignados if asistencia else None
        })
    
    return render(request, "administrador/detalle_jornada.html", {
        "jornada": jornada,
        "participantes": participantes,
        "total_participantes": len(participantes)
    })


@rol_required('administrador')
def admi_modificar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)

    if jornada.estado not in ["pendiente", "activa"]:
        messages.error(request, "Solo se pueden editar jornadas con estado pendiente o activa.")
        return redirect("admi_creacion_jornadas")

    if request.method == "POST":
        errores = []
        
        # Validaciones manuales
        if not request.POST.get("titulo", "").strip():
            errores.append("El título es obligatorio.")
        if not request.POST.get("descripcion", "").strip():
            errores.append("La descripción es obligatoria.")
        if not request.POST.get("fecha", "").strip():
            errores.append("La fecha es obligatoria.")
        if not request.POST.get("hora", "").strip():
            errores.append("La hora es obligatoria.")
        if not request.POST.get("direccion", "").strip():
            errores.append("El punto de encuentro es obligatorio.")
        if not request.POST.get("barrio", "").strip():
            errores.append("El barrio es obligatorio.")
        if not request.POST.get("tipo_material", "").strip():
            errores.append("El tipo de material es obligatorio.")
        if not request.POST.get("cupo_maximo", "").strip():
            errores.append("El cupo máximo es obligatorio.")
        if not request.POST.get("estado", "").strip():
            errores.append("El estado es obligatorio.")
        
        descripcion = request.POST.get("descripcion", "").strip()
        if descripcion and len(descripcion) < 10:
            errores.append("La descripción debe contener mínimo 10 caracteres.")
        
        try:
            cupos = int(request.POST.get("cupo_maximo", 0))
            if cupos < 5 or cupos > 50:
                errores.append("El cupo máximo debe estar entre 5 y 50 personas.")
        except:
            errores.append("El cupo máximo debe ser un número válido.")
        
        if errores:
            messages.error(request, errores[0])
            return redirect("admi_detalle_jornada", jornada_id=jornada.id_jornada)

        # Actualizar la jornada
        jornada.titulo = request.POST.get("titulo")
        jornada.descripcion = request.POST.get("descripcion")
        jornada.fecha = request.POST.get("fecha")
        jornada.hora = request.POST.get("hora")
        jornada.direccion = request.POST.get("direccion")
        jornada.barrio = request.POST.get("barrio")
        jornada.tipo_material = request.POST.get("tipo_material")
        jornada.cupo_maximo = int(request.POST.get("cupo_maximo", 0))
        jornada.estado = request.POST.get("estado")
        
        organizador = jornada.id_organizador or Usuario.objects.filter(id_usuario=request.session.get("usuario_id")).first()
        if not jornada.id_organizador:
            jornada.id_organizador = organizador
        
        if not _validar_publicacion_jornada(jornada):
            messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
            return redirect("admi_detalle_jornada", jornada_id=jornada.id_jornada)
        
        jornada.save()
        _enviar_notificaciones_automaticas_jornada(jornada, "edicion")
        messages.success(request, "Jornada modificada correctamente.")
        return redirect("admi_detalle_jornada", jornada_id=jornada.id_jornada)
    
    return redirect("admi_detalle_jornada", jornada_id=jornada.id_jornada)


@rol_required('organizador')
def organizador_creacion_jornadas(request):
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")

    usuario_actual = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario_actual or usuario_actual.rol != "organizador":
        messages.error(request, "Solo los organizadores pueden acceder al formulario de creacion de jornadas.")
        return redirect("login")

    barrios = _obtener_barrios_disponibles()

    if request.method == "POST":
        datos_jornada = {
            "titulo": request.POST.get("titulo"),
            "descripcion": request.POST.get("descripcion"),
            "fecha": request.POST.get("fecha"),
            "hora": request.POST.get("hora"),
            "direccion": request.POST.get("direccion"),
            "barrio": request.POST.get("barrio"),
            "tipo_material": request.POST.get("tipo_material"),
            "cupo_maximo": request.POST.get("cupo_maximo"),
            "estado": request.POST.get("estado"),
        }

        if not _validar_datos_jornada(request, datos_jornada, usuario_actual):
            jornadas = Jornada.objects.all().order_by("-fecha")
            return render(request, "organizador/creacionjornadas.html", {
                "jornadas": jornadas,
                "barrios": barrios,
            })

        jornada = Jornada(
            titulo=datos_jornada["titulo"],
            descripcion=datos_jornada["descripcion"],
            fecha=datos_jornada["fecha"],
            hora=datos_jornada["hora"],
            barrio=datos_jornada["barrio"],
            direccion=datos_jornada["direccion"],
            tipo_material=datos_jornada["tipo_material"],
            cupo_maximo=datos_jornada["cupo_maximo"],
            estado=datos_jornada["estado"],
            id_organizador=usuario_actual,
        )

        if not _validar_publicacion_jornada(jornada):
            messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
            return redirect("organizador_creacion_jornadas")

        jornada.save()
        _enviar_notificaciones_automaticas_jornada(jornada, "creacion")
        return HttpResponse("""
            <script>
                alert('El formulario de jornada se envio correctamente y la jornada fue creada.');
                window.location.href = '/organizador/creacionjornadas/';
            </script>
        """)

    # Obtener filtros del GET
    filtro_estado = request.GET.get('estado', '')
    filtro_material = request.GET.get('tipo_material', '')
    
    # Query base
    jornadas = Jornada.objects.all().order_by("-fecha")
    
    # Aplicar filtros
    if filtro_estado:
        jornadas = jornadas.filter(estado=filtro_estado)
    if filtro_material:
        jornadas = jornadas.filter(tipo_material=filtro_material)
    
    # Paginación
    paginator = Paginator(jornadas, 10)  # 10 jornadas por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "organizador/creacionjornadas.html", {
        "jornadas": page_obj,
        "barrios": barrios,
        "filtro_estado": filtro_estado,
        "filtro_material": filtro_material,
    })


@rol_required('organizador')
def organizador_detalle_jornada(request, jornada_id):
    """Vista para ver los detalles de una jornada incluyendo participantes"""
    usuario_id = request.session.get("usuario_id")
    if not usuario_id:
        return redirect("login")
    
    usuario_actual = Usuario.objects.filter(id_usuario=usuario_id).first()
    if not usuario_actual or usuario_actual.rol != "organizador":
        messages.error(request, "Solo los organizadores pueden acceder a esta página.")
        return redirect("login")
    
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)
    
    # Obtener participantes (inscripciones)
    inscripciones = Inscripcion.objects.filter(
        jornada=jornada,
        estado='activa'
    ).select_related('usuario')
    
    # Obtener registros de asistencia
    from .models import Asistencia
    ids_inscripcion = list(inscripciones.values_list('id_inscripcion', flat=True))
    asistentes = {}
    if ids_inscripcion:
        registros_asistencia = Asistencia.objects.filter(inscripcion_id__in=ids_inscripcion)
        for reg in registros_asistencia:
            asistentes[reg.inscripcion_id] = reg
    
    # Preparar datos de participantes
    participantes = []
    for inscripcion in inscripciones:
        usuario = inscripcion.usuario
        asistencia = asistentes.get(inscripcion.id_inscripcion)
        participantes.append({
            'nombre': usuario.nombre if usuario else 'No especificado',
            'correo': usuario.correo if usuario else '',
            'telefono': usuario.telefono if usuario else '',
            'asistio': asistencia.presente if asistencia else None,
            'puntos': asistencia.puntos_asignados if asistencia else None
        })
    
    return render(request, "organizador/detalle_jornada.html", {
        "jornada": jornada,
        "participantes": participantes,
        "total_participantes": len(participantes)
    })


@rol_required('organizador')
def organizador_modificar_jornada(request, jornada_id):
    jornada = get_object_or_404(Jornada, id_jornada=jornada_id)

    if jornada.estado not in ["pendiente", "activa"]:
        messages.error(request, "Solo se pueden editar jornadas con estado pendiente o activa.")
        return redirect("organizador_creacion_jornadas")

    if request.method == "POST":
        errores = []
        
        # Validaciones manuales
        if not request.POST.get("titulo", "").strip():
            errores.append("El título es obligatorio.")
        if not request.POST.get("descripcion", "").strip():
            errores.append("La descripción es obligatoria.")
        if not request.POST.get("fecha", "").strip():
            errores.append("La fecha es obligatoria.")
        if not request.POST.get("hora", "").strip():
            errores.append("La hora es obligatoria.")
        if not request.POST.get("direccion", "").strip():
            errores.append("El punto de encuentro es obligatorio.")
        if not request.POST.get("barrio", "").strip():
            errores.append("El barrio es obligatorio.")
        if not request.POST.get("tipo_material", "").strip():
            errores.append("El tipo de material es obligatorio.")
        if not request.POST.get("cupo_maximo", "").strip():
            errores.append("El cupo máximo es obligatorio.")
        if not request.POST.get("estado", "").strip():
            errores.append("El estado es obligatorio.")
        
        descripcion = request.POST.get("descripcion", "").strip()
        if descripcion and len(descripcion) < 10:
            errores.append("La descripción debe contener mínimo 10 caracteres.")
        
        try:
            cupos = int(request.POST.get("cupo_maximo", 0))
            if cupos < 5 or cupos > 50:
                errores.append("El cupo máximo debe estar entre 5 y 50 personas.")
        except:
            errores.append("El cupo máximo debe ser un número válido.")
        
        if errores:
            messages.error(request, errores[0])
            return redirect("organizador_detalle_jornada", jornada_id=jornada.id_jornada)

        # Actualizar la jornada
        jornada.titulo = request.POST.get("titulo")
        jornada.descripcion = request.POST.get("descripcion")
        jornada.fecha = request.POST.get("fecha")
        jornada.hora = request.POST.get("hora")
        jornada.direccion = request.POST.get("direccion")
        jornada.barrio = request.POST.get("barrio")
        jornada.tipo_material = request.POST.get("tipo_material")
        jornada.cupo_maximo = int(request.POST.get("cupo_maximo", 0))
        jornada.estado = request.POST.get("estado")
        
        organizador = jornada.id_organizador or Usuario.objects.filter(id_usuario=request.session.get("usuario_id")).first()
        if not jornada.id_organizador:
            jornada.id_organizador = organizador
        
        if not _validar_publicacion_jornada(jornada):
            messages.error(request, "Debes asignar al menos un organizador antes de publicar la jornada.")
            return redirect("organizador_detalle_jornada", jornada_id=jornada.id_jornada)
        
        jornada.save()
        _enviar_notificaciones_automaticas_jornada(jornada, "edicion")
        messages.success(request, "Jornada modificada correctamente.")
        return redirect("organizador_detalle_jornada", jornada_id=jornada.id_jornada)
    
    return redirect("organizador_detalle_jornada", jornada_id=jornada.id_jornada)

