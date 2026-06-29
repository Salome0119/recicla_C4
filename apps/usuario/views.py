from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from reciclac4.core.models import TemaForo, Comentario, Usuario
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail

def usuario_inicio(request):
    return render(request, "usuario/inicio.html")

def usuario_como_participar(request):
    return render(request, "usuario/como_participar.html")

def usuario_educacion(request):
    return render(request, "usuario/educacion.html")

def usuario_contacto(request):
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
            asunto_admin = f'Nuevo mensaje de contacto - {nombre}'
            mensaje_admin = f'''
            Nuevo mensaje recibido desde el formulario de contacto (Usuario):

            Nombre: {nombre}
            Correo: {correo}
            Rol: Usuario visitante

            Mensaje:
            {mensaje}

            ---
            Recicla Comuna 4
            '''
            
            admin_email = getattr(settings, 'EMAIL_HOST_USER', 'reciclacomuna@gmail.com')
            
            asunto_usuario = 'Hemos recibido tu mensaje - Recicla Comuna 4'
            mensaje_usuario = f'''
            Hola {nombre}:

            Hemos recibido tu mensaje correctamente. Nuestro equipo se pondrá en contacto contigo pronto.

            Tu mensaje:
            {mensaje}

            Si necesitas contactarnos directamente:
            Teléfono: 315 5959444
            Correo: reciclacomuna@gmail.com

            ---
            Recicla Comuna 4
            '''
            
            try:
                send_mail(
                    asunto_admin,
                    mensaje_admin,
                    settings.DEFAULT_FROM_EMAIL,
                    [admin_email],
                )
                
                send_mail(
                    asunto_usuario,
                    mensaje_usuario,
                    settings.DEFAULT_FROM_EMAIL,
                    [correo],
                )
                
                messages.success(request, 'Mensaje enviado correctamente.')
            except Exception as e:
                messages.error(request, f'Error: {type(e).__name__}. Inténtalo más tarde.')
            
            return redirect('usuario_contacto')
    
    return render(request, "usuario/contacto.html")

def usuario_foro_publicaciones(request):
    sort = request.GET.get('sort', 'newest')

    if sort == 'oldest':
        order_by = 'fecha_publicacion'
    else:
        order_by = '-fecha_publicacion'

    # Mostrar todas las publicaciones (sin filtro fijo por fecha)
    publicaciones_qs = TemaForo.objects.all().order_by(order_by).prefetch_related(
        'comentarios__usuario',
        'comentarios__respuestas__usuario'
    )
    
    paginator = Paginator(publicaciones_qs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, "usuario/foro_publicaciones.html", {
        "page_obj": page_obj,
        "sort": sort
    })

@require_POST
@csrf_exempt
def usuario_comentar(request, tema_id):
    if not request.session.get('usuario_id'):
        return JsonResponse({'error': 'Debes iniciar sesión para comentar'}, status=401)

    try:
        data = json.loads(request.body)
        texto = data.get('contenido', '').strip()
        parent_id = data.get('parent_id')

        if not texto:
            return JsonResponse({'error': 'El comentario no puede estar vacío'}, status=400)

        usuario = Usuario.objects.get(id_usuario=request.session['usuario_id'])
        tema = TemaForo.objects.get(id_tema=tema_id)

        parent = None
        if parent_id:
            parent = Comentario.objects.filter(id_comentario=parent_id).first()

        comentario = Comentario.objects.create(
            tema=tema,
            usuario=usuario,
            texto=texto,
            parent=parent
        )

        return JsonResponse({
            'id': comentario.id_comentario,
            'autor': f"{comentario.usuario.nombre} {comentario.usuario.apellido}",
            'fecha': comentario.created_at.strftime("%d/%m/%Y %H:%M"),
            'contenido': comentario.texto
        })
    except Usuario.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
    except TemaForo.DoesNotExist:
        return JsonResponse({'error': 'Publicación no encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@csrf_exempt
def usuario_denunciar(request, tema_id):
    if not request.session.get('usuario_id'):
        return JsonResponse({'error': 'Debes iniciar sesión para denunciar'}, status=401)

    try:
        data = json.loads(request.body)
        motivo = data.get('motivo', '').strip()
        if not motivo:
            return JsonResponse({'error': 'El motivo no puede estar vacío'}, status=400)

        return JsonResponse({'mensaje': 'Denuncia recibida. Gracias por tu reporte.'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_POST
@csrf_exempt
def usuario_reaccionar(request, tema_id):
    if not request.session.get('usuario_id'):
        return JsonResponse({'error': 'Debes iniciar sesión para reaccionar'}, status=401)

    try:
        data = json.loads(request.body)
        tipo = data.get('tipo')
        
        return JsonResponse({'mensaje': 'Reacción registrada'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)