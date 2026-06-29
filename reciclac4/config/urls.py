from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.login.urls')),
    path('', include('apps.usuario.urls')),
    path('', include('apps.organizador.urls')),
    path('', include('apps.residente.urls')),
    path('', include('apps.administrador.urls')),
    path('', include('reciclac4.core.urls')),
]

# Esto permite mostrar imágenes subidas (MEDIA)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
