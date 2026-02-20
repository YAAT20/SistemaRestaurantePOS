from django.db import models
from django.db import transaction

class Producto(models.Model):
    nombre = models.CharField(max_length=100)
    stock = models.IntegerField()
    punto_pedido = models.IntegerField()
    unidad_medida = models.CharField(max_length=20, default="unidad")
    precio_compra = models.DecimalField(max_digits=7, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=7, decimal_places=2)
    activo = models.BooleanField(default=True)

    @transaction.atomic
    def ajustar_stock(self, cantidad, tipo, usuario=None, pedido=None, descripcion=None):
        if tipo == MovimientoInventario.TIPO_SALIDA and self.stock < cantidad:
            raise ValueError(f"Stock insuficiente para {self.nombre}")

        if tipo == MovimientoInventario.TIPO_SALIDA:
            self.stock -= cantidad
        else:
            self.stock += cantidad

        self.save()
        MovimientoInventario.objects.create(
            producto=self,
            tipo=tipo,
            cantidad=cantidad,
            descripcion=descripcion or f"Pedido #{pedido.id if pedido else ''}",
            usuario=usuario,
            pedido=pedido
        )

    def stock_inicial(self):
        entradas = MovimientoInventario.objects.filter(
            producto=self, tipo=MovimientoInventario.TIPO_ENTRADA
        ).aggregate(total=models.Sum('cantidad'))['total'] or 0
        salidas = MovimientoInventario.objects.filter(
            producto=self, tipo=MovimientoInventario.TIPO_SALIDA
        ).aggregate(total=models.Sum('cantidad'))['total'] or 0
        return self.stock + salidas - entradas

    def stock_inicial_actual(self):
        return f"{self.stock_inicial()}/{self.stock}"    

class MovimientoInventario(models.Model):
    TIPO_ENTRADA = 'entrada'
    TIPO_SALIDA = 'salida'
    TIPOS = [
        (TIPO_ENTRADA, 'Entrada'),
        (TIPO_SALIDA, 'Salida'),
    ]

    plato = models.ForeignKey('menu.Plato', null=True, blank=True, on_delete=models.CASCADE)
    producto = models.ForeignKey('inventario.Producto', null=True, blank=True, on_delete=models.CASCADE)
    usuario = models.ForeignKey('usuarios.Usuario', null=True, blank=True, on_delete=models.SET_NULL)

    tipo = models.CharField(max_length=10, choices=TIPOS)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    pedido = models.ForeignKey('pedidos.Pedido', null=True, blank=True, on_delete=models.SET_NULL)
    
    def asociado(self):
        """Retorna el objeto asociado, sea producto o plato"""
        return self.producto or self.plato

    def es_producto(self):
        return self.producto is not None

    def es_plato(self):
        return self.plato is not None

    def __str__(self):
        detalle = ""
        if self.es_producto():
            detalle = f"{self.cantidad} {self.producto.unidad_medida} de {self.producto.nombre}"
        elif self.es_plato():
            detalle = f"{self.cantidad} {self.plato}"

        pedido_info = f" (Pedido #{self.pedido.numero_diario})" if self.pedido else ""
        return f"{self.tipo} - {detalle}{pedido_info}"