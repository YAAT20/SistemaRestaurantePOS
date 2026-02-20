from django.urls import path
from . import views

app_name = 'inventario'

urlpatterns = [
    # Productos
    path('productos/', views.ProductoListView.as_view(), name='producto_list'),
    path('productos/nuevo/', views.ProductoCreateView.as_view(), name='producto_create'),
    path('productos/<int:pk>/editar/', views.ProductoUpdateView.as_view(), name='producto_update'),
    path('productos/<int:pk>/eliminar/', views.ProductoDeleteView.as_view(), name='producto_delete'),
    # Movimientos
    path('movimientos/', views.MovimientoInventarioListView.as_view(), name='movimiento_list'),
]