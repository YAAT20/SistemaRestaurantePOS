from escpos.printer import Network
from django.utils import timezone

def imprimir_pedido_cocina(pedido):
    """
    Imprime solo los detalles no enviados (preparado=False) y luego los marca como preparados.
    """
    try:
        detalles = pedido.detalles.filter(preparado=False)
        if not detalles.exists():
            return False, "No hay ítems nuevos para enviar a cocina."

        p = Network("192.168.0.100", port=9100, timeout=10)

        # Encabezado
        p.set(align='center', bold=True, width=2, height=2)
        p.text("*** COCINA ***\n")
        p.set(align='left', bold=False, width=1, height=1)
        p.text(f"Mesa: {pedido.mesa.numero}\n")
        p.text(f"Pedido #{pedido.numero_diario}\n")
        p.text(f"Hora: {timezone.localtime().strftime('%H:%M:%S')}\n")        
        p.text("------------------------------\n")

        # Imprimir ítems nuevos
        for det in detalles:
            nombre = det.plato.nombre if det.plato else det.producto.nombre
            p.text(f"{det.cantidad}x {nombre}\n")
            if det.observaciones:
                p.text(f"   ({det.observaciones})\n")

        p.text("------------------------------\n")
        p.text("   Preparar con prioridad\n")
        p.cut()
        p._raw(b'\x1b\x0c')  # flush

        # ✅ Marcar los detalles como enviados
        ahora = timezone.localtime()        
        detalles.update(preparado=True, hora_impresion=ahora)

        return True, None
    except Exception as e:
        return False, str(e)