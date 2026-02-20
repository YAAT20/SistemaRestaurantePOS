from datetime import datetime, time
from decimal import Decimal
from django.db import models
from django.utils import timezone
from pedidos.models import Pedido
from usuarios.models import Usuario

class CierreCaja(models.Model):
    TURNOS = (
        ('MAÑANA', 'Mañana (8am-3pm)'),
        ('TARDE', 'Tarde (3pm-12am)')
    )
    ESTADOS = (
        ('VENTAS_REGISTRADAS', 'Ventas registradas'),
        ('EFECTIVO_VERIFICADO', 'Efectivo verificado'),
        ('CERRADO', 'Cerrado'),
    )
    
    mozo = models.ForeignKey(
        Usuario, on_delete=models.PROTECT,
        limit_choices_to={'rol': 'mozo'}
    )
    fecha = models.DateField()
    turno = models.CharField(max_length=10, choices=TURNOS)
    estado = models.CharField(
        max_length=20, choices=ESTADOS,
        default='VENTAS_REGISTRADAS'
    )
    
    # Totales del sistema
    total_menu_sistema = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_carta_sistema = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_otros_sistema = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_sistema = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Totales físicos
    efectivo_reportado = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    tarjetas_reportadas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    otros_medios = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Auditoría
    diferencia = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    cerrado_en = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Cierre de Caja'
        verbose_name_plural = 'Cierres de Caja'
        ordering = ['-fecha', '-creado_en']
    
    def __str__(self):
        return f"Cierre #{self.id} - {self.get_turno_display()} ({self.fecha})"
    
    def calcular_totales_sistema(self):
        """Calcula totales de ventas por categoría usando fecha de pago si existe."""
        fecha_inicio = timezone.make_aware(datetime.combine(self.fecha, time.min))
        fecha_fin = timezone.make_aware(datetime.combine(self.fecha, time.max))

        pedidos = Pedido.objects.filter(
            mozo=self.mozo,
            estado='PAGADO'
        ).prefetch_related('detalles__plato', 'detalles__producto')

        # Filtrar manualmente usando fecha_pago si existe, sino fecha_hora
        pedidos = [
            p for p in pedidos
            if (
                (p.fecha_pago and fecha_inicio <= p.fecha_pago <= fecha_fin) or
                (not p.fecha_pago and fecha_inicio <= p.fecha_hora <= fecha_fin)
            ) and p.turno == self.turno
        ]

        total_menu = Decimal('0.00')
        total_carta = Decimal('0.00')
        total_otros = Decimal('0.00')

        for pedido in pedidos:
            for detalle in pedido.detalles.all():
                subtotal = detalle.subtotal or Decimal('0.00')

                if getattr(detalle, 'plato', None):
                    tipo_plato = (getattr(detalle.plato, 'tipo', '') or '').upper()
                    if tipo_plato == 'MENU':
                        total_menu += subtotal
                    else:
                        total_carta += subtotal

                elif getattr(detalle, 'producto', None):
                    tipo_prod = getattr(detalle.producto, 'tipo', None)
                    if tipo_prod and isinstance(tipo_prod, str) and tipo_prod.upper() == 'MENU':
                        total_menu += subtotal
                    else:
                        total_otros += subtotal
                else:
                    total_otros += subtotal

        self.total_menu_sistema = total_menu
        self.total_carta_sistema = total_carta
        self.total_otros_sistema = total_otros
        self.total_sistema = total_menu + total_carta + total_otros
        self.save()

    def verificar_efectivo(self, efectivo, tarjetas, otros=0):
        """Registra el dinero físico contado y calcula diferencia."""
        self.efectivo_reportado = efectivo
        self.tarjetas_reportadas = tarjetas
        self.otros_medios = otros
        self.estado = 'EFECTIVO_VERIFICADO'
        
        total_fisico = (efectivo or 0) + (tarjetas or 0) + (otros or 0)
        self.diferencia = total_fisico - self.total_sistema
        self.save()
    
    def cerrar_caja(self, observaciones=''):
        """Cierra definitivamente la caja."""
        self.estado = 'CERRADO'
        self.observaciones = observaciones
        self.cerrado_en = timezone.now()
        self.save()