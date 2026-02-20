from channels.generic.websocket import AsyncWebsocketConsumer
import json

class CocinaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add(
            'cocina',
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            'cocina',
            self.channel_name
        )

    async def notificacion_pedido(self, event):
        message = event['message']
        
        await self.send(text_data=json.dumps({
            'type': 'notificacion',
            'message': message
        }))