from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from .models import OrdenCocina
from pedidos.models import Pedido
from django.contrib.auth.decorators import login_required

class OrdenCocinaListView(LoginRequiredMixin, ListView):
    model = OrdenCocina
    template_name = 'cocina/orden_list.html'
    context_object_name = 'ordenes'
    
    def get_queryset(self):
        return OrdenCocina.objects.filter(impreso=False).order_by('-pedido__fecha_hora')
    
@login_required
def marcar_impreso(request, pk):
    if request.method == 'POST':
        orden = get_object_or_404(OrdenCocina, pk=pk)
        orden.impreso = True
        orden.fecha_impresion = timezone.now()
        orden.save()
        messages.success(request, f'Orden #{orden.id} marcada como impresa')
    return redirect('cocina:orden_list')

@login_required
def marcar_como_completo(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    
    if request.method == 'POST':
        pedido.estado = 'COMPLETO'
        pedido.save()
        messages.success(request, f'Pedido #{pedido.id} marcado como completo')
        return redirect('cocina:orden_list')
    
    # Si es GET, mostrar página de confirmación
    return render(request, 'cocina/marcar_completo.html', {
        'pedido': pedido,
        'ordenes': OrdenCocina.objects.filter(pedido=pedido)
    })