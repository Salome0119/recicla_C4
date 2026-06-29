from django.core.management.base import BaseCommand
from django.conf import settings
import smtplib

class Command(BaseCommand):
    help = 'Prueba conexión SMTP'

    def handle(self, *args, **options):
        host = settings.EMAIL_HOST
        port = settings.EMAIL_PORT
        user = settings.EMAIL_HOST_USER
        password = settings.EMAIL_HOST_PASSWORD
        
        if not password:
            self.stdout.write(self.style.WARNING('EMAIL_HOST_PASSWORD no está configurado'))
            return
        
        self.stdout.write(f'Conectando a {host}:{port} como {user}...')
        
        try:
            server = smtplib.SMTP(host, port)
            server.starttls()
            server.login(user, password)
            server.quit()
            self.stdout.write(self.style.SUCCESS('Conexión SMTP exitosa'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error SMTP: {e}'))