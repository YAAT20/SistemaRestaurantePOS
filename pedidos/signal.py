from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache
from .models import Pedido
import json
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

@receiver(post_save, sender=Pedido)
def notificar_cocina(sender, instance, created, **kwargs):
    if instance.enviado_cocina and kwargs.get('update_fields') is not None:
        channel_layer = get_channel_layer()
        
        # Notificación por WebSocket
        async_to_sync(channel_layer.group_send)(
            'cocina',
            {
                'type': 'notificacion_pedido',
                'message': {
                    'tipo': 'nuevo_pedido',
                    'pedido_id': instance.id,
                    'mesa': instance.mesa.numero,
                    'cantidad_items': instance.detalles.count()
                }
            }
        )
        
        # También puedes implementar notificación por email
        # send_mail_to_kitchen(instance)