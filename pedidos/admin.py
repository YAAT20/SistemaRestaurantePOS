from django.contrib import admin
from .models import Pedido, DetallePedido, Boleta, Mesa

admin.site.register(Mesa)
admin.site.register(Pedido)
admin.site.register(DetallePedido)
admin.site.register(Boleta)