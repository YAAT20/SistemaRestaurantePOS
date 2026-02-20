from django.views.generic import *
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import CierreCaja
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
from pedidos.models import Pedido
from django.utils import timezone
from datetime import datetime, time
from django.utils import timezone

class CierreCajaListView(LoginRequiredMixin, ListView):
    model = CierreCaja
    template_name = 'caja/cierre_list.html'
    context_object_name = 'cierres'
    
class IniciarCierreView(LoginRequiredMixin, CreateView):
    """Paso 1: Registrar ventas del sistema"""
    model = CierreCaja
    fields = ['turno']
    template_name = 'caja/cierre_form.html'
    
    def form_valid(self, form):
        fecha_local = timezone.localtime(timezone.now()).date()

        # Verificar si ya existe un cierre para este turno
        if CierreCaja.objects.filter(
            mozo=self.request.user,
            fecha=fecha_local,
            turno=form.cleaned_data['turno']
        ).exists():
            messages.error(self.request, 'Ya existe un cierre para este turno')
            return redirect('caja:cierre_list')
        
        form.instance.mozo = self.request.user
        form.instance.fecha = fecha_local
        self.object = form.save()  # Guardamos manualmente

        # Calcular totales del sistema
        self.object.calcular_totales_sistema()
        
        messages.success(self.request, 'Ventas registradas correctamente')
        return redirect('caja:verificar_efectivo', pk=self.object.pk)

class VerificarEfectivoView(LoginRequiredMixin, UpdateView):
    """Paso 2: Comparar con dinero físico"""
    model = CierreCaja
    fields = ['efectivo_reportado', 'tarjetas_reportadas', 'otros_medios']
    template_name = 'caja/verificar_efectivo.html'
    
    def form_valid(self, form):
        cierre = form.save(commit=False)
        cierre.verificar_efectivo(
            efectivo=form.cleaned_data['efectivo_reportado'],
            tarjetas=form.cleaned_data['tarjetas_reportadas'],
            otros=form.cleaned_data['otros_medios']
        )
        messages.success(self.request, 'Efectivo verificado correctamente')
        return redirect('caja:cierre_detail', pk=cierre.pk)

class CerrarDefinitivoView(LoginRequiredMixin, UpdateView):
    """Paso 3: Cierre definitivo"""
    model = CierreCaja
    fields = ['observaciones']
    template_name = 'caja/cerrar_definitivo.html'
    
    def form_valid(self, form):
        cierre = form.save(commit=False)
        cierre.cerrar_caja(observaciones=form.cleaned_data['observaciones'])
        messages.success(self.request, 'Caja cerrada correctamente')
        return redirect('caja:cierre_detail', pk=cierre.pk)

class CierreCajaDetailView(LoginRequiredMixin, DetailView):
    model = CierreCaja
    template_name = 'caja/cierre_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cierre = self.object
        context['cierre'] = cierre

        fecha_inicio = timezone.make_aware(datetime.combine(cierre.fecha, time.min))
        fecha_fin = timezone.make_aware(datetime.combine(cierre.fecha, time.max))

        pedidos = Pedido.objects.filter(
            mozo=cierre.mozo,
            fecha_hora__range=(fecha_inicio, fecha_fin),
            turno=cierre.turno,
            estado='PAGADO'
        ).select_related('mesa').prefetch_related('detalles__plato', 'detalles__producto')

        context.update({
            'pedidos': pedidos,
            'puede_verificar': cierre.estado == 'VENTAS_REGISTRADAS',
            'puede_cerrar': cierre.estado == 'EFECTIVO_VERIFICADO' and cierre.estado != 'CERRADO',
            'detalle_items': self._obtener_detalle_items(pedidos),
            'total_general': self._calcular_total(pedidos)
        })
        return context

    def _obtener_detalle_items(self, pedidos):
        """Genera reporte detallado de platos y productos vendidos"""
        detalles = []
        for pedido in pedidos:
            for detalle in pedido.detalles.all():
                nombre_item = detalle.plato.nombre if detalle.plato else detalle.producto.nombre
                tipo_item = detalle.plato.get_tipo_display() if detalle.plato else "Producto"
                detalles.append({
                    'item': nombre_item,
                    'tipo': tipo_item,
                    'cantidad': detalle.cantidad,
                    'subtotal': detalle.subtotal if callable(detalle.subtotal) else detalle.subtotal
                })
        return detalles

    def _calcular_total(self, pedidos):
        """Suma todos los subtotales de los detalles"""
        total = 0
        for pedido in pedidos:
            for detalle in pedido.detalles.all():
                total += detalle.subtotal if callable(detalle.subtotal) else detalle.subtotal
        return total