from django.db import models
from menu.models import Plato
from usuarios.models import Usuario
from django.conf import settings
from django.contrib.auth.models import User

class ConfiguracionRestaurante(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.TextField()
    telefono = models.CharField(max_length=20)
    logo = models.ImageField(upload_to='logo/', blank=True, null=True)
    whatsapp_api_key = models.CharField(max_length=255, blank=True, null=True)
    mostrar_precios_en_boleta = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre
    
class ReporteVenta(models.Model):
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    fecha_generacion = models.DateTimeField(auto_now_add=True)
    tipo_reporte = models.CharField(max_length=20, choices=[
        ('diario','Diario'),
        ('semanal','Semanal'),
        ('mensual','Mensual'),
    ])
    total_ventas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ventas_menu_dia = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ventas_carta = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    ventas_productos = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    plato_mas_vendido = models.ForeignKey(
        'menu.Plato', 
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reportes_plato'
    )
    cantidad_plato_mas_vendido = models.PositiveIntegerField(default=0)

    producto_mas_vendido = models.ForeignKey(
        'inventario.Producto',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='reportes_producto'
    )
    cantidad_producto_mas_vendido = models.PositiveIntegerField(default=0)

    usuario_generador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )

    def __str__(self):
        return f"{self.tipo_reporte} ({self.fecha_inicio} a {self.fecha_fin})"