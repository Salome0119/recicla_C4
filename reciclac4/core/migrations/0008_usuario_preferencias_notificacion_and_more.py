from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_denuncia_comentario_reaccion'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='canal_notificacion_correo',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='canal_notificacion_push',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='usuario',
            name='canal_notificacion_web',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='usuario',
            name='recibe_notificaciones_jornadas',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='notificacion',
            name='canal',
            field=models.CharField(
                choices=[
                    ('correo', 'Correo electrónico'),
                    ('web', 'Aplicación web'),
                    ('push', 'Notificación push'),
                ],
                default='web',
                max_length=20,
            ),
        ),
    ]
