from django.urls import path
from . import views
app_name = 'pedidos'

urlpatterns = [
    path('pedidos/crear/', views.CrearPedidoView.as_view(), name='crear_pedido'),
    path('pedidos/<int:pk>/editar/', views.EditarPedidoView.as_view(), name='editar_pedido'),
    path('pedidos/<int:pk>/', views.PedidoResumenView.as_view(), name='pedido_resumen'),
    path('pedidos/<int:pk>/eliminar/', views.PedidoDeleteView.as_view(), name='pedido_delete'),
    path('pedidos/<int:pk>/marcar-pagado/', views.marcar_como_pagado, name='marcar_como_pagado'),
    path('pedido/<int:pk>/cortesia/', views.marcar_como_cortesia, name='marcar_como_cortesia'),
    path('mesas/', views.MesasPedidosView.as_view(), name='mesas_pedidos'),
    path('pedidos/lista/', views.PedidoListView.as_view(), name='pedido_list'),
    path('pedidos/<int:pk>/boleta/', views.ver_boleta_pdf, name='ver_boleta_pdf'),

    path('pedidos/<int:pk>/cambiar-estado/', views.cambiar_estado_pedido, name='cambiar_estado'),
    path('mesa/<int:pk>/', views.MesaDetailView.as_view(), name='mesa_detail'),
    path("mesa/<int:pk>/fragment/", views.mesa_fragment, name="mesa_fragment"),
]
