from django.db import models
from django.db import transaction
from inventario.models import MovimientoInventario

class Plato(models.Model):
    TIPO = (
        ('menu', 'Menú del Día'),
        ('carta', 'Plato a la Carta'),
        ('entrada', 'Plato de Entrada Diario'),
        ('desayuno', 'Desayuno'),
    )
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    tipo = models.CharField(max_length=10, choices=TIPO)
    disponible = models.BooleanField(default=True)
    stock_diario = models.PositiveIntegerField(default=0)
    stock_actual = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.nombre

    @transaction.atomic
    def descontar_stock(self, cantidad, usuario=None, pedido=None):
        if self.stock_actual < cantidad:
            raise ValueError(f"Stock insuficiente para {self.nombre}")

        # Descuento del plato
        self.stock_actual -= cantidad
        self.save()

        # Registrar movimiento
        MovimientoInventario.objects.create(
            plato=self,
            tipo=MovimientoInventario.TIPO_SALIDA,
            cantidad=cantidad,
            descripcion=f"Pedido #{pedido.id if pedido else ''}",
            usuario=usuario
        )
        # Si el plato tiene receta → descontar insumos
        for ingrediente in self.ingredientes.all():
            total_consumo = ingrediente.cantidad * cantidad
            ingrediente.producto.ajustar_stock(
                cantidad=total_consumo,
                tipo=MovimientoInventario.TIPO_SALIDA,
                usuario=usuario,
                pedido=pedido,
                descripcion=f"Consumo de insumos por {cantidad}x {self.nombre}"
            )

    @transaction.atomic
    def reponer_stock(self, cantidad, usuario=None, descripcion="Reposición por cancelación"):

        self.stock_actual += cantidad
        self.save()

        MovimientoInventario.objects.create(
            plato=self,
            tipo=MovimientoInventario.TIPO_ENTRADA,
            cantidad=cantidad,
            descripcion=descripcion,
            usuario=usuario
        )

        # Reponer insumos
        for ingrediente in self.ingredientes.all():
            total_reposicion = ingrediente.cantidad * cantidad
            ingrediente.producto.ajustar_stock(
                cantidad=total_reposicion,
                tipo=MovimientoInventario.TIPO_ENTRADA,
                usuario=usuario,
                descripcion=f"Reposición de insumos por cancelación de {cantidad}x {self.nombre}"
            )

class PlatoDelDia(models.Model):
    plato = models.ForeignKey(Plato, on_delete=models.CASCADE)
    fecha = models.DateField(auto_now_add=True)

    class Meta:
        unique_together = ('plato', 'fecha')

    def __str__(self):
        return f"{self.plato.nombre} ({self.fecha})"
    
class Receta(models.Model):
    plato = models.ForeignKey('menu.Plato', on_delete=models.CASCADE, related_name="ingredientes")
    producto = models.ForeignKey('inventario.Producto', on_delete=models.CASCADE)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    unidad = models.CharField(max_length=20, default="unidad")

    def __str__(self):
        return f"{self.cantidad} {self.unidad} de {self.producto.nombre} para {self.plato.nombre}"
