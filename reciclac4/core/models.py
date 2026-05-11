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
    telefono = models.CharField(max_length=20, null=True, blank=True)
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
        No permite acceso a usuarios suspendidos ni rechazados
        Residentes: estado 'activo'
        Organizadores/Administradores: estado 'aprobado'
        """
        if self.estado in ('suspendido', 'rechazado'):
            return False
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
            ('en_curso', 'En curso'),
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
    id_inscripcion = models.AutoField(primary_key=True)  # ← nombre correcto
    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        db_column='id_usuario'   # ← le dice a Django que la columna se llama id_usuario
    )
    jornada = models.ForeignKey(
        Jornada,
        on_delete=models.CASCADE,
        db_column='jornada_id'   # ← coincide con tu BD
    )
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=10,
        choices=[('activa', 'Activa'), ('cancelada', 'Cancelada')],
        default='activa'
    )

    class Meta:
        db_table = 'core_inscripcion'
        managed = True  # ← importante, la tabla ya existe



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
    motivo = models.CharField(max_length=255, null=True, blank=True)
    jornada = models.ForeignKey(
        Jornada,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    recompensa = models.ForeignKey(
        'Recompensa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

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


class Asistencia(models.Model):
    id_asistencia = models.AutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        Inscripcion,
        on_delete=models.CASCADE,
        db_column='id_inscripcion'
    )
    nombre_usuario = models.CharField(max_length=100, null=True, blank=True)
    presente = models.BooleanField(default=False)
    puntos_asignados = models.IntegerField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'asistencia'
        managed = True


class AccionDestacada(models.Model):
    id = models.AutoField(primary_key=True)
    inscripcion = models.ForeignKey(
        Inscripcion,
        on_delete=models.CASCADE,
        db_column='inscripcion_id'
    )
    descripcion = models.CharField(max_length=255)
    puntos_sugeridos = models.IntegerField(default=5)
    validada = models.BooleanField(default=False)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'core_accion_destacada'
        managed = True


class Recompensa(models.Model):
    id_recompensa = models.AutoField(primary_key=True)
    titulo = models.CharField(max_length=100)
    descripcion = models.TextField()
    puntos_requeridos = models.IntegerField()
    imagen = models.ImageField(upload_to='recompensas/', blank=True, null=True)
    disponible = models.BooleanField(default=True)
    cantidad_disponible = models.IntegerField(default=0)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    last_update = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_recompensa'
        managed = True
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.titulo


class CanjeRecompensa(models.Model):
    id_canje = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='canjes')
    recompensa = models.ForeignKey(Recompensa, on_delete=models.CASCADE, related_name='canjes')
    fecha_canje = models.DateTimeField(auto_now_add=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    barrio = models.CharField(max_length=100, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'core_canje_recompensa'
        managed = True
        ordering = ['-fecha_canje']

    def __str__(self):
        return f"{self.usuario.nombre} - {self.recompensa.titulo}"

# class ContactMessage(models.Model):
#     nombre = models.CharField(max_length=100)
#     correo = models.EmailField()
#     mensaje = models.TextField()
#     fecha = models.DateTimeField(auto_now_add=True)
#     rol = models.CharField(max_length=20, blank=True)  # rol que envía el mensaje
#     leido = models.BooleanField(default=False)

#     class Meta:
#         db_table = 'core_contact_message'
#         ordering = ['-fecha']
#         managed = True

#     def __str__(self):
#         return f"{self.nombre} - {self.correo}"

