# inventario/views.py
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from .models import Producto, MovimientoInventario
from usuarios.mixins import AdminRequiredMixin

# -------------------------------
# Productos
# -------------------------------
class ProductoListView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'inventario/producto_list.html'
    context_object_name = 'productos'

class ProductoCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Producto
    template_name = 'inventario/producto_form.html'
    fields = '__all__'
    success_url = reverse_lazy('inventario:producto_list')

class ProductoUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Producto
    template_name = 'inventario/producto_form.html'
    fields = '__all__'
    success_url = reverse_lazy('inventario:producto_list')

class ProductoDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Producto
    template_name = 'inventario/producto_confirm_delete.html'
    success_url = reverse_lazy('inventario:producto_list')


# -------------------------------
# Movimientos de Inventario
# -------------------------------
class MovimientoInventarioListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = MovimientoInventario
    template_name = 'inventario/movimiento_list.html'
    context_object_name = 'movimientos'
    def get_queryset(self):
        return MovimientoInventario.objects.select_related('producto', 'plato', 'usuario', 'pedido').order_by('-fecha')
