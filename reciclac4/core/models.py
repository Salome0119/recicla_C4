from django.db import models
from django.utils import timezone


class UserChangeLog(models.Model):
    usuario = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='change_logs')
    quien = models.CharField(max_length=150)
    accion = models.CharField(max_length=50)   # e.g. 'crear','editar','suspender','restaurar'
    detalle = models.TextField(blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)


    class Meta:
        db_table = 'core_userchangelog'
class Usuario(models.Model):
    # Opciones para el campo estado
    ESTADO_CHOICES = [
    ("pendiente", "Pendiente de aprobación"),
    ("aprobado", "Aprobado"),
    ("rechazado", "Rechazado"),
    ("activo", "Activo"),
    ("suspendido", "Suspendido"),   # 🔥 AGREGAR ESTO
]

    
    ROL_CHOICES = [
        ("residente", "Residente"),
        ("organizador", "Organizador"),
        ("administrador", "Administrador"),
    ]

    id_usuario = models.AutoField(primary_key=True)  
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    correo = models.CharField(max_length=100, unique=True)
    contrasena = models.CharField(max_length=255)
    fecha_nacimiento = models.DateField(null=True, blank=True)
    barrio = models.CharField(max_length=100, null=True, blank=True)
    recibe_notificaciones_jornadas = models.BooleanField(default=True)
    canal_notificacion_correo = models.BooleanField(default=True)
    canal_notificacion_web = models.BooleanField(default=True)
    canal_notificacion_push = models.BooleanField(default=False)
    


    rol = models.CharField(max_length=20, choices=ROL_CHOICES)

    # CAMBIO IMPORTANTE: Usar choices para el estado
    estado = models.CharField(
        max_length=20, 
        choices=ESTADO_CHOICES, 
        default="pendiente"
    )
    
    foto = models.ImageField(upload_to='fotos_perfil/', blank=True, null=True)

    fecha_registro = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)
    reset_token = models.CharField(max_length=128, blank=True, null=True)
    class Meta:
        managed = True
        db_table = 'usuarios'

    def __str__(self):
        return f"{self.nombre} {self.apellido} <{self.correo}>"
    
    def puede_acceder(self):
        """
        Verifica si el usuario puede iniciar sesión
        Residentes: estado 'activo'
        Organizadores/Administradores: estado 'aprobado'
        """
        if self.rol == "residente":
            return self.estado == "activo"
        else:
            return self.estado == "aprobado"
        
    @property
    def puntaje_total(self):
        return self.puntajes.aggregate(total=models.Sum('puntos'))['total'] or 0
    
class Jornada(models.Model):
    id_jornada = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=100, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    fecha = models.DateField(null=True, blank=True)
    hora = models.TimeField(null=True, blank=True)
    direccion = models.CharField(max_length=200, null=True, blank=True)
    barrio = models.CharField(max_length=100, null=True, blank=True)
    tipo_material = models.CharField(max_length=100, null=True, blank=True)
    cupo_maximo = models.IntegerField(null=True, blank=True)
    estado = models.CharField(
        max_length=10,
        choices=[
            ('pendiente', 'Pendiente'),
            ('activa', 'Activa'),
            ('finalizada', 'Finalizada'),
            ('cancelada', 'Cancelada'),
        ],
        default='pendiente'
    )

    id_organizador = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        db_column='id_organizador'
    )

    last_update = models.DateTimeField(auto_now=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # sin default

    class Meta:
        db_table = 'jornada'   # 💥 CONEXIÓN DIRECTA A TU TABLA
        managed = True      # 🔥 IMPORTANTE: Django no crea la tabla

    def __str__(self):
        return self.titulo

class Inscripcion(models.Model):
    id = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    jornada = models.ForeignKey(Jornada, on_delete=models.CASCADE)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_inscripcion'



class TemaForo(models.Model):
    id_tema = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=100, null=True, blank=True)
    contenido = models.TextField(null=True, blank=True)

    id_usuario = models.ForeignKey(
        'Usuario',               # ← evita circular import
        on_delete=models.CASCADE,
        db_column='id_usuario',
        null=True,
        blank=True
    )

    fecha_publicacion = models.DateTimeField(default=timezone.now)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tema_foro'
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return self.titulo if self.titulo else "Sin título"


class Puntaje(models.Model):
    id = models.BigAutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='puntajes')
    puntos = models.IntegerField(default=0)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_puntaje'
class Notificacion(models.Model):
    CANAL_CHOICES = [
        ('correo', 'Correo electrónico'),
        ('web', 'Aplicación web'),
        ('push', 'Notificación push'),
    ]

    id_notificacion = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    tipo = models.CharField(max_length=50, null=True, blank=True)
    canal = models.CharField(max_length=20, choices=CANAL_CHOICES, default='web')
    mensaje = models.TextField(null=True, blank=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'notificacion'

    def __str__(self):
        return f"Notificación {self.id_notificacion} - {self.tipo}"

