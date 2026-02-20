from django.db import models

class OrdenCocina(models.Model):
    pedido = models.OneToOneField('pedidos.Pedido', on_delete=models.CASCADE, null=True)
    impreso = models.BooleanField(default=False)
    fecha_impresion = models.DateTimeField(blank=True, null=True)
