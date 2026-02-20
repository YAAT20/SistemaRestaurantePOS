from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from pedidos.views import home
from django.contrib import admin
from django.urls import path, include
from pedidos.views import home

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('menu/', include('menu.urls')),
    path('pedidos/', include('pedidos.urls', namespace='pedidos')),
    path('cocina/', include('cocina.urls', namespace='cocina')),
    path('inventario/', include('inventario.urls', namespace='inventario')),
    path('caja/', include('caja.urls', namespace='caja')),
    path('administracion/', include('administracion.urls', namespace='administracion')),
    path('usuarios/', include('usuarios.urls', namespace='usuarios')),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)