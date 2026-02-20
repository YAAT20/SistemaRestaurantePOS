from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from .models import Mesa, Pedido, Cliente
from menu.models import Plato
from administracion.models import ConfiguracionRestaurante
from django.shortcuts import get_object_or_404
from pedidos.utils import render_to_pdf
from django.utils import timezone
from django.http import HttpResponse, Http404
from django.views.generic import *
from django.urls import reverse_lazy
from django.db import transaction
from inventario.models import Producto
from datetime import time
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.utils.timezone import localdate, localtime
from django.core.serializers.json import DjangoJSONEncoder
import json
from datetime import timedelta
from datetime import date, datetime
from django.db import models
import logging
from pedidos.services import imprimir_pedido_cocina

logger = logging.getLogger(__name__)

def home(request):
    return render(request, 'base.html')

class MesasPedidosView(LoginRequiredMixin, TemplateView):
    template_name = "pedidos/mesa_pedidos.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        mesas_info = []
        mesas = Mesa.objects.prefetch_related("pedidos__detalles", "pedidos__mozo").all().order_by("numero")

        hoy = localtime().date()
        inicio = localtime().replace(hour=0, minute=0, second=0, microsecond=0)
        fin = inicio + timedelta(days=1)

        for mesa in mesas:
            pedidos_dia = mesa.pedidos.filter(
                fecha_hora__gte=inicio,
                fecha_hora__lt=fin
            ).order_by("-fecha_hora")

            pedidos_activos = pedidos_dia.exclude(estado__in=["PAGADO", "CANCELADO"])

            # Determinar color
            if pedidos_activos.exists():
                if pedidos_activos.filter(estado="EN_COCINA").exists():
                    color = "bg-warning text-dark"
                elif pedidos_activos.filter(estado="COMPLETO").exists():
                    color = "bg-info text-dark"
                else:
                    color = "bg-danger text-white"
                estado_mesa = "OCUPADA"
            else:
                color = "bg-success text-white"
                estado_mesa = "LIBRE"

            mesas_info.append({
                "mesa": mesa,
                "pedidos": pedidos_dia,
                "pedidos_activos": pedidos_activos.count(),
                "estado": estado_mesa,
                "color": color,
            })

        context["mesas_info"] = mesas_info
        context["modo"] = self.request.GET.get("modo", "lista")
        return context
    
class MesaDetailView(LoginRequiredMixin, DetailView):
    model = Mesa
    template_name = 'pedidos/mesa_detail.html'
    context_object_name = 'mesa'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = localdate()

        pedidos_dia = self.object.pedidos.filter(
            fecha_hora__date=hoy
        ).order_by('-fecha_hora')

        context['pedidos_dia'] = pedidos_dia
        return context

class PedidoListView(LoginRequiredMixin, ListView):
    model = Pedido
    template_name = 'pedidos/pedido_list.html'
    context_object_name = 'pedidos'
    paginate_by = 15

    def get_queryset(self):
        qs = Pedido.objects.select_related("mesa", "mozo")

        # Parámetros GET
        fecha = self.request.GET.get("fecha")
        fecha_inicio = self.request.GET.get("fecha_inicio")
        fecha_fin = self.request.GET.get("fecha_fin")
        estado = self.request.GET.get("estado")

        # Filtrado por estado
        if estado:
            qs = qs.filter(estado=estado)

        if fecha_inicio or fecha_fin:
            try:
                if fecha_inicio:
                    inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
                    inicio_datetime = timezone.make_aware(datetime.combine(inicio_date, time.min))
                else:
                    # Si no hay fecha_inicio, usamos algo muy antiguo
                    inicio_datetime = timezone.make_aware(datetime.combine(date.min, time.min))

                if fecha_fin:
                    fin_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    fin_datetime = timezone.make_aware(datetime.combine(fin_date, time.max))
                else:
                    # Si no hay fecha_fin, usamos fecha muy lejana
                    fin_datetime = timezone.make_aware(datetime.combine(date.max, time.max))

                qs = qs.filter(fecha_hora__range=[inicio_datetime, fin_datetime])

            except ValueError as e:
                print(f"ERROR parseando fechas: {e}")

        elif fecha:
            try:
                # Crear fecha objeto
                fecha_date = datetime.strptime(fecha, '%Y-%m-%d').date()
                
                # Inicio y fin del día en timezone local
                inicio_dia = timezone.make_aware(
                    datetime.combine(fecha_date, time.min)
                )
                fin_dia = timezone.make_aware(
                    datetime.combine(fecha_date, time.max)
                )
                
                qs = qs.filter(fecha_hora__range=[inicio_dia, fin_dia])
                
            except ValueError as e:
                print(f"ERROR parseando fecha: {e}")
        else:
            # Por defecto → pedidos del día actual
            hoy = date.today()
            inicio_hoy = timezone.make_aware(
                datetime.combine(hoy, time.min)
            )
            fin_hoy = timezone.make_aware(
                datetime.combine(hoy, time.max)
            )
            qs = qs.filter(fecha_hora__range=[inicio_hoy, fin_hoy])

        # Debug final
        count = qs.count()
        if count > 0:
            primeros = list(qs.values('id', 'fecha_hora')[:3])

        return qs.order_by('-fecha_hora')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Agrupar por mesa con pedidos y estado
        mesas_data = {}
        for pedido in self.object_list:
            mesa_key = pedido.mesa
            if mesa_key not in mesas_data:
                mesas_data[mesa_key] = {
                    'mesa': mesa_key,
                    'pedidos': [],
                    'tiene_pendientes': False
                }
            mesas_data[mesa_key]['pedidos'].append(pedido)

            # Determinar si la mesa tiene pedidos pendientes
            if pedido.estado not in ['PAGADO', 'CANCELADO']:
                mesas_data[mesa_key]['tiene_pendientes'] = True

        context['mesas'] = list(mesas_data.values())
        context['today'] = date.today().isoformat()
        return context

def mesa_fragment(request, pk):
    mesa = get_object_or_404(Mesa, pk=pk)
    inicio = localtime().replace(hour=0, minute=0, second=0, microsecond=0)
    fin = inicio + timedelta(days=1)

    pedidos_dia = mesa.pedidos.filter(
        fecha_hora__gte=inicio,
        fecha_hora__lt=fin
    ).order_by("-fecha_hora")

    pedidos_activos = pedidos_dia.exclude(estado__in=["PAGADO", "CANCELADO"])

    pedido_referencia = pedidos_activos.first()
    if pedido_referencia:
        if pedido_referencia.estado == "EN_COCINA":
            color = "bg-warning text-dark"
        elif pedido_referencia.estado == "COMPLETO":
            color = "bg-info text-dark"
        else:
            color = "bg-danger text-white"
    else:
        color = "bg-success text-white"

    return render(request, "pedidos/includes/_mesa_pedidos_fragment.html", {
        "mesa": mesa,
        "pedidos_activos": pedidos_activos,
        "color": color,
    })

class PedidoDeleteView(LoginRequiredMixin, DeleteView):
    model = Pedido
    template_name = 'pedidos/pedido_confirm_delete.html'
    success_url = reverse_lazy('pedidos:pedido_list')
    
class CrearPedidoView(View):
    template_name = 'pedidos/pedido_form.html'

    def get(self, request):
        mesa_id = request.GET.get('mesa')
        if mesa_id:
            mesas = Mesa.objects.filter(models.Q(id=mesa_id) | models.Q(estado='LIBRE'))
        else:
            mesas = Mesa.objects.filter(estado='LIBRE')

        mesa_id = int(mesa_id) if mesa_id else None
        ahora = timezone.localtime().time()
        turno_tarde = ahora >= time(15, 0) or ahora < time(8, 0)

        desayunos = Plato.objects.filter(disponible=True, stock_actual__gt=0, tipo="desayuno").order_by("nombre")
        platos_menu = Plato.objects.filter(disponible=True, stock_actual__gt=0, tipo="menu").order_by("nombre")
        platos_entrada = Plato.objects.filter(disponible=True, stock_actual__gt=0, tipo="entrada").order_by("nombre")
        platos_carta = Plato.objects.filter(disponible=True, stock_actual__gt=0, tipo="carta").order_by("nombre")
        productos_disponibles = Producto.objects.filter(stock__gt=0)

        categorias = [
            {'nombre': 'Desayunos', 'items': desayunos, 'color': 'btn-outline-success', 'tipo': 'desayuno'},
            {'nombre': 'Platos del Menú', 'items': platos_menu, 'color': 'btn-outline-primary', 'tipo': 'menu'},
            {'nombre': 'Entradas', 'items': platos_entrada, 'color': 'btn-outline-success', 'tipo': 'entrada'},
            {'nombre': 'Platos a la Carta', 'items': platos_carta, 'color': 'btn-outline-warning', 'tipo': 'carta'},
            {'nombre': 'Productos', 'items': productos_disponibles, 'color': 'btn-outline-info', 'tipo': 'producto'},
        ]

        return render(request, self.template_name, {
            'pedido': None,
            'mesas': mesas,
            'categorias': categorias,
            'mesa_id': mesa_id,
            'pedido_json': json.dumps([], cls=DjangoJSONEncoder),
            'turno_tarde': turno_tarde,
        })

    @transaction.atomic
    def post(self, request):
        mesa_id = request.POST.get('mesa')
        nombre_cliente = request.POST.get('cliente_nombre', '').strip()
        telefono_cliente = request.POST.get('cliente_telefono', '').strip()
        cliente = None

        if telefono_cliente:
            cliente, _ = Cliente.objects.get_or_create(
                telefono=telefono_cliente,
                defaults={'nombre': nombre_cliente}
            )

        mesa = get_object_or_404(Mesa, id=mesa_id)

        pedido = Pedido.objects.create(
            mesa=mesa,
            mozo=request.user,
            cliente=cliente,
            estado='PENDIENTE',
        )

        mesa.estado = 'OCUPADA'
        mesa.save()

        # Procesar platos y productos
        for key, value in request.POST.items():
            if key.startswith('plato_'):
                plato_id = int(key.split('_', 1)[1])
                cantidad = int(value or 0)
                if cantidad <= 0:
                    continue
                plato = get_object_or_404(Plato, id=plato_id)
                observaciones = request.POST.get(f'observaciones_{plato_id}', '')

                # Aquí ya no hay lógica de "extra" ni asociaciones
                pedido.agregar_plato(plato, cantidad, request.user, observaciones)

            elif key.startswith('producto_'):
                producto_id = int(key.split('_', 1)[1])
                cantidad = int(value or 0)
                if cantidad <= 0:
                    continue
                producto = get_object_or_404(Producto, id=producto_id)
                pedido.agregar_producto(producto, cantidad, request.user)

        return redirect('pedidos:pedido_resumen', pk=pedido.id)

class EditarPedidoView(LoginRequiredMixin, View):
    template_name = 'pedidos/pedido_form.html'
    
    def get(self, request, pk):
        pedido = get_object_or_404(Pedido, id=pk, mozo=request.user)

        detalles = pedido.detalles.all()
        pedido_json = [
            {
                "id": str(det.plato.id if det.plato else det.producto.id),
                "tipo": "plato" if det.plato else "producto",
                "nombre": det.plato.nombre if det.plato else det.producto.nombre,
                "precio": float(det.precio_unitario),
                "cantidad": det.cantidad,
                "obs": det.observaciones,
                "preparado": det.preparado,
            }
            for det in detalles
        ]

        ahora = timezone.localtime().time()
        turno_tarde = ahora >= time(15, 0) or ahora < time(8, 0)
        
        platos_desayuno = Plato.objects.filter(disponible=True, stock_actual__gt=0, tipo="desayuno").order_by("nombre")
        platos_menu = Plato.objects.filter(disponible=True, stock_actual__gt=0, tipo="menu").order_by("nombre")
        platos_entrada = Plato.objects.filter(disponible=True, stock_actual__gt=0, tipo="entrada").order_by("nombre")
        platos_carta = Plato.objects.filter(disponible=True, stock_actual__gt=0, tipo="carta").order_by("nombre")
        productos_disponibles = Producto.objects.filter(stock__gt=0)

        categorias = [
            {'nombre': 'Desayunos', 'items': platos_desayuno, 'color': 'btn-outline-secondary', 'tipo': 'desayuno'},
            {'nombre': 'Platos del Menú', 'items': platos_menu, 'color': 'btn-outline-primary', 'tipo': 'menu'},
            {'nombre': 'Entradas', 'items': platos_entrada, 'color': 'btn-outline-success', 'tipo': 'entrada'},
            {'nombre': 'Platos a la Carta', 'items': platos_carta, 'color': 'btn-outline-warning', 'tipo': 'carta'},
            {'nombre': 'Productos', 'items': productos_disponibles, 'color': 'btn-outline-info', 'tipo': 'producto'},
        ]

        return render(request, self.template_name, {
            'pedido': pedido,
            'mesas': Mesa.objects.all(),
            'categorias': categorias,
            'pedido_json': json.dumps(pedido_json, cls=DjangoJSONEncoder),
            'turno_tarde': turno_tarde,
        })

    @transaction.atomic
    def post(self, request, pk):
        pedido = get_object_or_404(Pedido, id=pk, mozo=request.user)

        # 🔹 Caso: pedido ya enviado a cocina → solo crear nuevos detalles
        if pedido.enviado_cocina:
            for key, value in request.POST.items():
                if key.startswith('plato_') or key.startswith('producto_'):
                    cantidad = int(value or 0)
                    if cantidad <= 0:
                        continue

                    if key.startswith('plato_'):
                        plato_id = int(key.split('_', 1)[1])
                        plato = get_object_or_404(Plato, id=plato_id)
                        observaciones = request.POST.get(f'observaciones_{plato_id}', '')

                        if plato.stock_actual < cantidad:
                            raise ValueError(f"No hay suficiente stock para {plato.nombre}")
                        plato.stock_actual -= cantidad
                        plato.save()

                        pedido.agregar_plato(plato, cantidad, request.user, observaciones)

                    elif key.startswith('producto_'):
                        producto_id = int(key.split('_', 1)[1])
                        producto = get_object_or_404(Producto, id=producto_id)

                        if producto.stock < cantidad:
                            raise ValueError(f"No hay suficiente stock para {producto.nombre}")
                        producto.stock -= cantidad
                        producto.save()

                        pedido.agregar_producto(producto, cantidad, request.user, f"Pedido #{pedido.id} (extra cocina)")

            messages.success(request, "Se añadieron nuevos ítems al pedido y fueron enviados a cocina.")
            return redirect("pedidos:pedido_resumen", pk=pedido.id)

        # 🔹 Caso: pedido aún no enviado → lógica normal (sumar cantidades)
        detalles_actuales = {}
        for det in pedido.detalles.all():
            if det.plato:
                detalles_actuales[f"plato_{det.plato.id}"] = det
            elif det.producto:
                detalles_actuales[f"producto_{det.producto.id}"] = det

        procesados = set()

        for key, value in request.POST.items():
            if key.startswith('plato_') or key.startswith('producto_'):
                cantidad = int(value or 0)
                if cantidad <= 0:
                    continue

                if key.startswith('plato_'):
                    plato_id = int(key.split('_', 1)[1])
                    plato = get_object_or_404(Plato, id=plato_id)
                    observaciones = request.POST.get(f'observaciones_{plato_id}', '')

                    if key in detalles_actuales:
                        det = detalles_actuales[key]
                        nueva_cantidad = det.cantidad + cantidad

                        if plato.stock_actual < cantidad:
                            raise ValueError(f"No hay suficiente stock para {plato.nombre}")

                        plato.stock_actual -= cantidad
                        plato.save()

                        det.cantidad = nueva_cantidad
                        det.observaciones = observaciones
                        det.save(update_fields=["cantidad", "observaciones"])
                    else:
                        if plato.stock_actual < cantidad:
                            raise ValueError(f"No hay suficiente stock para {plato.nombre}")
                        plato.stock_actual -= cantidad
                        plato.save()
                        pedido.agregar_plato(plato, cantidad, request.user, observaciones)

                elif key.startswith('producto_'):
                    producto_id = int(key.split('_', 1)[1])
                    producto = get_object_or_404(Producto, id=producto_id)

                    if key in detalles_actuales:
                        det = detalles_actuales[key]
                        nueva_cantidad = det.cantidad + cantidad

                        if producto.stock < cantidad:
                            raise ValueError(f"No hay suficiente stock para {producto.nombre}")

                        producto.stock -= cantidad
                        producto.save()

                        det.cantidad = nueva_cantidad
                        det.save(update_fields=["cantidad"])
                    else:
                        if producto.stock < cantidad:
                            raise ValueError(f"No hay suficiente stock para {producto.nombre}")
                        producto.stock -= cantidad
                        producto.save()
                        pedido.agregar_producto(producto, cantidad, request.user, f"Pedido #{pedido.id} (edición)")

                procesados.add(key)

        # 🔹 Eliminar ítems quitados
        for key, det in detalles_actuales.items():
            if key not in procesados:
                if det.plato:
                    det.plato.stock_actual += det.cantidad
                    det.plato.save()
                elif det.producto:
                    det.producto.stock += det.cantidad
                    det.producto.save()
                det.delete()

        messages.success(request, 'Pedido actualizado correctamente')
        return redirect('pedidos:pedido_resumen', pk=pedido.id)

        
class PedidoResumenView(LoginRequiredMixin, DetailView):
    model = Pedido
    template_name = 'pedidos/pedido_resumen.html'
    context_object_name = 'pedido'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['detalles'] = self.object.detalles.all()
        return context
    
def ver_boleta_pdf(request, pk):
    pedido = get_object_or_404(Pedido, id=pk)
    detalles = pedido.detalles.all()
    subtotal = sum(detalle.subtotal for detalle in detalles)
    total = subtotal

    context = {
        'pedido': pedido,
        'detalles': detalles,
        'subtotal': subtotal,
        'total': total,
        'fecha': timezone.now(),
        'config': ConfiguracionRestaurante.objects.first()
    }

    pdf = render_to_pdf('boletas/boleta_preliminar.html', context)

    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"boleta_pedido_{pedido.id}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    raise Http404("Error al generar el PDF")

@login_required
@require_POST
def marcar_como_pagado(request, pk):
    pedido = get_object_or_404(Pedido, id=pk)

    if request.user.rol not in ['MOZO', 'ADMIN']:
        messages.error(request, 'No tienes permisos para cambiar el estado del pedido.')
        return redirect('pedidos:pedido_resumen', pk=pedido.id)

    try:
        # Cambiar estado a PAGADO
        mensaje = pedido.cambiar_estado('PAGADO', usuario=request.user)

        # Registrar hora de pago
        pedido.fecha_pago = timezone.now()
        pedido.save(update_fields=["fecha_pago"])

        # Liberar la mesa
        pedido.mesa.estado = 'LIBRE'
        pedido.mesa.save()

        messages.success(request, mensaje)
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('pedidos:pedido_resumen', pk=pedido.id)


@login_required
@require_POST
def marcar_como_cortesia(request, pk):
    pedido = get_object_or_404(Pedido, id=pk)

    if request.user.rol not in ['MOZO', 'ADMIN']:
        messages.error(request, 'No tienes permisos para cambiar el estado del pedido.')
        return redirect('pedidos:pedido_resumen', pk=pedido.id)

    try:
        # Marcar como cortesía
        pedido.es_cortesia = True
        mensaje = pedido.cambiar_estado('PAGADO', usuario=request.user)

        # Registrar hora de pago
        pedido.fecha_pago = timezone.now()
        pedido.save(update_fields=["fecha_pago", "es_cortesia"])

        # Liberar la mesa
        pedido.mesa.estado = 'LIBRE'
        pedido.mesa.save()

        # Poner precio_unitario en 0 para todos los detalles
        pedido.detalles.update(precio_unitario=0)

        messages.success(request, f"{mensaje} (total en 0 por cortesía)")
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('pedidos:pedido_resumen', pk=pedido.id)

@login_required
@require_POST
def cambiar_estado_pedido(request, pk):
    pedido = get_object_or_404(Pedido, id=pk)
    nuevo_estado = request.POST.get('estado')

    if request.user.rol not in ['MOZO', 'ADMIN']:
        messages.error(request, 'No tienes permisos para cambiar el estado del pedido.')
        return redirect('pedidos:pedido_resumen', pk=pedido.id)

    try:
        # Cambiar estado
        mensaje = pedido.cambiar_estado(nuevo_estado, usuario=request.user)
        messages.success(request, mensaje)

        # 👉 Si es cocina, imprimir automáticamente
        if nuevo_estado == 'EN_COCINA':
            ok, error = imprimir_pedido_cocina(pedido)
            if ok:
                messages.success(request, f'Pedido #{pedido.numero_diario} enviado a cocina e impreso correctamente.')
            else:
                messages.error(request, f'El pedido cambió de estado pero no se imprimió: {error}')

    except ValueError as e:
        messages.error(request, str(e))

    return redirect('pedidos:pedido_resumen', pk=pedido.id)
