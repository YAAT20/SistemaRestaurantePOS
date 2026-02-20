from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import ConfiguracionRestaurante, ReporteVenta
from django.shortcuts import redirect, render
from django.contrib import messages
from django.utils import timezone
from datetime import datetime, timedelta, time
from django.db.models import Sum, F
from django.contrib.auth.decorators import login_required
from pedidos.models import Pedido, DetallePedido
from menu.models import Plato
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Sum, F
from inventario.models import Producto
from usuarios.mixins import AdminRequiredMixin
from usuarios.decorators import admin_required

# CRUD Configuración Restaurante
class ConfiguracionListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = ConfiguracionRestaurante
    template_name = 'administracion/configuracion_list.html'
    context_object_name = 'configuraciones'

class ConfiguracionCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = ConfiguracionRestaurante
    permission_required = 'administracion.add_configuracionrestaurante'
    template_name = 'administracion/configuracion_form.html'
    fields = '__all__'
    success_url = reverse_lazy('administracion:configuracion_list')

class ConfiguracionUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = ConfiguracionRestaurante
    permission_required = 'administracion.change_configuracionrestaurante'
    template_name = 'administracion/configuracion_form.html'
    fields = '__all__'
    success_url = reverse_lazy('administracion:configuracion_list')

class ConfiguracionDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = ConfiguracionRestaurante
    permission_required = 'administracion.delete_configuracionrestaurante'
    template_name = 'administracion/configuracion_confirm_delete.html'
    success_url = reverse_lazy('administracion:configuracion_list')

# Reportes
class ReporteVentaListView(LoginRequiredMixin, ListView):
    model = ReporteVenta
    template_name = 'administracion/reporte_list.html'
    context_object_name = 'reportes'

class ReporteVentaDetailView(LoginRequiredMixin, DetailView):
    model = ReporteVenta
    template_name = 'administracion/reporte_detail.html'
    context_object_name = 'reporte'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        detalles = DetallePedido.objects.filter(
            pedido__estado='PAGADO',
            pedido__fecha_pago__range=(self.object.fecha_inicio, self.object.fecha_fin)
        )

        tipos = ['entrada', 'menu', 'carta', 'desayuno']
        platos_por_tipo = {}

        for tipo in tipos:
            data = detalles.filter(plato__tipo=tipo).values('plato__nombre').annotate(total=Sum('cantidad')).order_by('-total').first()
            if data:
                platos_por_tipo[tipo] = {
                    'nombre': data['plato__nombre'],
                    'cantidad': data['total']
                }
            else:
                platos_por_tipo[tipo] = None

        context['platos_por_tipo'] = platos_por_tipo
        return context

@login_required
@admin_required
def generar_reporte_ventas(request, tipo='diario'):
    hoy = timezone.localdate()

    # 📌 Determinar rango de fechas
    if tipo == 'diario':
        fecha_inicio, fecha_fin = hoy, hoy
    elif tipo == 'semanal':
        fecha_inicio, fecha_fin = hoy - timedelta(days=hoy.weekday()), hoy
    elif tipo == 'mensual':
        fecha_inicio, fecha_fin = hoy.replace(day=1), hoy
    else:
        messages.error(request, "Tipo de reporte no válido")
        return redirect('administracion:reporte_list')

    inicio = timezone.make_aware(datetime.combine(fecha_inicio, time.min))
    fin = timezone.make_aware(datetime.combine(fecha_fin, time.max))

    # 📌 Pedidos pagados en el rango
    pedidos = Pedido.objects.filter(estado='PAGADO', fecha_pago__range=(inicio, fin))
    detalles = DetallePedido.objects.filter(pedido__in=pedidos)

    # Totales por categoría
    ventas_menu_dia = detalles.filter(plato__tipo='menu').aggregate(
        total=Sum(F('cantidad') * F('precio_unitario'))
    )['total'] or 0

    ventas_carta = detalles.filter(plato__tipo='carta').aggregate(
        total=Sum(F('cantidad') * F('precio_unitario'))
    )['total'] or 0

    ventas_productos = detalles.filter(producto__isnull=False).aggregate(
        total=Sum(F('cantidad') * F('precio_unitario'))
    )['total'] or 0

    total_ventas = ventas_menu_dia + ventas_carta + ventas_productos

    # 📌 Plato más vendido
    plato_data = detalles.filter(plato__isnull=False) \
        .values('plato').annotate(total_cantidad=Sum('cantidad')) \
        .order_by('-total_cantidad').first()

    plato_mas_vendido, cantidad_plato_mas_vendido = None, 0
    if plato_data:
        plato_mas_vendido = Plato.objects.get(id=plato_data['plato'])
        cantidad_plato_mas_vendido = plato_data['total_cantidad']

    # 📌 Producto más vendido
    producto_data = detalles.filter(producto__isnull=False) \
        .values('producto').annotate(total_cantidad=Sum('cantidad')) \
        .order_by('-total_cantidad').first()

    producto_mas_vendido, cantidad_producto_mas_vendido = None, 0
    if producto_data:
        producto_mas_vendido = Producto.objects.get(id=producto_data['producto'])
        cantidad_producto_mas_vendido = producto_data['total_cantidad']

    # 📌 Crear registro del reporte
    ReporteVenta.objects.create(
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        tipo_reporte=tipo,
        total_ventas=total_ventas,
        ventas_menu_dia=ventas_menu_dia,
        ventas_carta=ventas_carta,
        ventas_productos=ventas_productos,
        plato_mas_vendido=plato_mas_vendido,
        cantidad_plato_mas_vendido=cantidad_plato_mas_vendido,
        producto_mas_vendido=producto_mas_vendido,
        cantidad_producto_mas_vendido=cantidad_producto_mas_vendido,
        usuario_generador=request.user,
    )

    messages.success(request, f"Reporte {tipo} generado correctamente.")
    return redirect('administracion:reporte_list')

@login_required
@admin_required
def reporte_dashboard(request):
    hoy = timezone.localdate()
    TIPOS_VALIDOS = ['menu', 'carta', 'desayuno']

    # --- RANGOS DE FECHA ---
    inicio_dia = timezone.make_aware(datetime.combine(hoy, time.min))
    fin_dia = timezone.make_aware(datetime.combine(hoy, time.max))

    inicio_semana = timezone.make_aware(datetime.combine(hoy - timedelta(days=hoy.weekday()), time.min))
    fin_semana = fin_dia

    inicio_mes = timezone.make_aware(datetime.combine(hoy.replace(day=1), time.min))
    fin_mes = fin_dia

    # --- TOTALES ---
    ventas_hoy = DetallePedido.objects.filter(
        pedido__estado='PAGADO',
        pedido__fecha_pago__range=(inicio_dia, fin_dia)
    ).aggregate(total=Sum(F('cantidad') * F('precio_unitario')))['total'] or 0

    ventas_semana = DetallePedido.objects.filter(
        pedido__estado='PAGADO',
        pedido__fecha_pago__range=(inicio_semana, fin_semana)
    ).aggregate(total=Sum(F('cantidad') * F('precio_unitario')))['total'] or 0

    ventas_mes = DetallePedido.objects.filter(
        pedido__estado='PAGADO',
        pedido__fecha_pago__range=(inicio_mes, fin_mes)
    ).aggregate(total=Sum(F('cantidad') * F('precio_unitario')))['total'] or 0

    # --- REPORTES ---
    reportes = ReporteVenta.objects.order_by('-fecha_generacion')[:10]

    total_por_tipo = ReporteVenta.objects.values('tipo_reporte').annotate(
        total=Sum('total_ventas')
    )

    ventas_mensuales = ReporteVenta.objects.filter(tipo_reporte='mensual').order_by('fecha_inicio').values(
        'fecha_inicio', 'total_ventas'
    )

    # --- TOP PLATOS Y PRODUCTOS ---
    top_platos = (
        DetallePedido.objects.filter(
            plato__isnull=False, 
            pedido__estado='PAGADO',
            plato__tipo__in=TIPOS_VALIDOS
        )
        .values('plato__nombre')
        .annotate(total=Sum('cantidad'))
        .order_by('-total')[:5]
    )

    top_productos_cantidad = (
        DetallePedido.objects.filter(
            producto__isnull=False, 
            pedido__estado='PAGADO'
        )
        .values('producto__nombre')
        .annotate(cantidad=Sum('cantidad'))
        .order_by('-cantidad')[:5]
    )

    top_productos_monto = (
        DetallePedido.objects.filter(
            producto__isnull=False, 
            pedido__estado='PAGADO'
        )
        .annotate(subtotal=F('cantidad') * F('precio_unitario'))
        .values('producto__nombre')
        .annotate(total=Sum('subtotal'))
        .order_by('-total')[:5]
    )

    # --- PLATO MÁS VENDIDO (DÍA Y MES) ---
    def obtener_plato_mas_vendido(inicio, fin):
        data = (
            DetallePedido.objects.filter(
                pedido__estado='PAGADO',
                pedido__fecha_pago__range=(inicio, fin),
                plato__isnull=False,
                plato__tipo__in=TIPOS_VALIDOS
            )
            .values('plato')
            .annotate(total_cantidad=Sum('cantidad'))
            .order_by('-total_cantidad')
            .first()
        )
        if data:
            from menu.models import Plato
            plato = Plato.objects.get(id=data['plato'])
            cantidad = data['total_cantidad']
            return plato, cantidad
        return None, 0

    plato_dia, cantidad_plato_dia = obtener_plato_mas_vendido(inicio_dia, fin_dia)
    plato_mes, cantidad_plato_mes = obtener_plato_mas_vendido(inicio_mes, fin_mes)

    # --- PRODUCTO MÁS VENDIDO (DÍA Y MES) ---
    def obtener_producto_mas_vendido(inicio, fin):
        data = (
            DetallePedido.objects.filter(
                pedido__estado='PAGADO',
                pedido__fecha_pago__range=(inicio, fin),
                producto__isnull=False
            )
            .values('producto')
            .annotate(total_cantidad=Sum('cantidad'))
            .order_by('-total_cantidad')
            .first()
        )
        if data:
            from inventario.models import Producto
            producto = Producto.objects.get(id=data['producto'])
            cantidad = data['total_cantidad']
            return producto, cantidad
        return None, 0

    producto_dia, cantidad_producto_dia = obtener_producto_mas_vendido(inicio_dia, fin_dia)
    producto_mes, cantidad_producto_mes = obtener_producto_mas_vendido(inicio_mes, fin_mes)

    # --- CONTEXTO ---
    context = {
        'ventas_hoy': ventas_hoy,
        'ventas_semana': ventas_semana,
        'ventas_mes': ventas_mes,
        'reportes': reportes,
        'total_por_tipo': json.dumps(list(total_por_tipo), cls=DjangoJSONEncoder),
        'ventas_mensuales': json.dumps(list(ventas_mensuales), cls=DjangoJSONEncoder),
        'top_platos': json.dumps(list(top_platos), cls=DjangoJSONEncoder),
        'top_productos_cantidad': json.dumps(list(top_productos_cantidad), cls=DjangoJSONEncoder),
        'top_productos_monto': json.dumps(list(top_productos_monto), cls=DjangoJSONEncoder),
        'plato_dia': plato_dia,
        'cantidad_plato_dia': cantidad_plato_dia,
        'plato_mes': plato_mes,
        'cantidad_plato_mes': cantidad_plato_mes,
        'producto_dia': producto_dia,
        'cantidad_producto_dia': cantidad_producto_dia,
        'producto_mes': producto_mes,
        'cantidad_producto_mes': cantidad_producto_mes,
    }

    return render(request, 'administracion/reporte_dashboard.html', context)