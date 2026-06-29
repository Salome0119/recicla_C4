from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from reciclac4.core.models import Usuario
from reciclac4.core.forms import PasswordResetRequestForm
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.utils.crypto import get_random_string

def login_view(request):
    if request.method == "POST":
        correo = request.POST.get("correo")
        contrasena = request.POST.get("contrasena")
        print(f"DEBUG LOGIN: correo={correo}")

        usuario = authenticate(request, correo=correo, password=contrasena)

        if usuario is None:
            print(f"DEBUG LOGIN: authenticate devolvió None")
            messages.error(request, "Correo o contraseña incorrectos")
            return redirect("login")
        
        print(f"DEBUG LOGIN: usuario autenticado, rol={usuario.rol}, estado={usuario.estado}")

        if not usuario.puede_acceder():
            print(f"DEBUG LOGIN: puede_acceder()=False (estado={usuario.estado}, rol={usuario.rol})")
            if usuario.estado == 'pendiente':
                if usuario.rol == 'organizador':
                    messages.error(request, "Tu cuenta de organizador está pendiente de aprobación por el administrador.")
                else:
                    messages.error(request, "Tu cuenta está pendiente de aprobación.")
            elif usuario.estado == 'rechazado':
                messages.error(request, "Tu solicitud fue rechazada.")
            elif usuario.estado == 'suspendido':
                messages.error(request, "Tu cuenta ha sido suspendida. No puedes acceder al sistema.")
            else:
                messages.error(request, f"Estado de cuenta no válido ({usuario.estado}). Contacta al administrador.")
            return redirect("login")

        request.session["usuario_id"] = usuario.id_usuario
        request.session["usuario_nombre"] = usuario.nombre
        request.session["usuario_rol"] = (usuario.rol or "").strip().lower()

        rol_normalizado = (usuario.rol or "").strip().lower()
        print(f"DEBUG LOGIN: rol_normalizado={rol_normalizado}")

        if rol_normalizado == "administrador":
            return redirect("admi_inicio")
        elif rol_normalizado == "organizador":
            return redirect("organizador_inicio")
        else:
            return redirect("residente_inicio")

    return render(request, "login/login.html")


def register_view(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        apellido = request.POST.get("apellido")
        correo = request.POST.get("correo")
        contrasena = request.POST.get("contrasena")
        fecha_nacimiento = request.POST.get("fecha_nacimiento")
        barrio = request.POST.get("barrio")
        rol = request.POST.get("rol")

        if Usuario.objects.filter(correo=correo).exists():
            messages.error(request, "El correo ya está registrado.")
            return redirect("login")

        if rol == "residente":
            estado_inicial = "activo"
            mensaje_exito = "🎉 Registro exitoso. Ya puedes iniciar sesión."
        else:
            estado_inicial = "pendiente"
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
                fail_silently=True,
            )

        messages.success(request, mensaje_exito)
        return redirect("login")

    return render(request, "login/login.html", {"show_register": True})


def solicitudes_pendientes(request):
    if not request.session.get("usuario_id"):
        return redirect("login")
    
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
            fail_silently=True,
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
            fail_silently=True,
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
                
                print(f"TOKEN GUARDADO: {usuario.reset_token}")
                
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
                    fail_silently=True,
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
        usuario.reset_token = ""
        usuario.save()
        
        messages.success(request, "Contraseña actualizada correctamente. Puedes iniciar sesión.")
        return redirect("login")
    
    return render(request, "login/password_reset_confirm.html")


def logout_view(request):
    from django.contrib.auth import logout as auth_logout
    auth_logout(request)
    messages.success(request, "Sesión cerrada correctamente.")
    return redirect('login')


def aprobar_todos_organizadores(request):
    pendientes = Usuario.objects.filter(rol='organizador', estado='pendiente')
    count = pendientes.count()
    for u in pendientes:
        u.estado = 'aprobado'
        u.save()
    return HttpResponse(f"""
    <div style="text-align: center; padding: 50px; font-family: Arial;">
        <h2 style="color: #27AE60;">✅ {count} organizadores aprobados</h2>
        <p>Se han aprobado {count} usuarios organizadores pendientes.</p>
        <a href="/" style="color: #2e7d32;">Volver al inicio</a>
    </div>
    """)