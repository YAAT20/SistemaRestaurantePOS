from django.urls import path
from .views import *

app_name = 'administracion'

urlpatterns = [
    # Configuración
    path('configuracion/', ConfiguracionListView.as_view(), name='configuracion_list'),
    path('configuracion/nueva/', ConfiguracionCreateView.as_view(), name='configuracion_create'),
    path('configuracion/<int:pk>/editar/', ConfiguracionUpdateView.as_view(), name='configuracion_update'),
    path('configuracion/<int:pk>/eliminar/', ConfiguracionDeleteView.as_view(), name='configuracion_delete'),

    # Reportes
    path('reportes/', ReporteVentaListView.as_view(), name='reporte_list'),
    path('reportes/<int:pk>/', ReporteVentaDetailView.as_view(), name='reporte_detail'),
    path('reportes/generar/<str:tipo>/', generar_reporte_ventas, name='generar_reporte'),
    path('reporte-dashboard/', reporte_dashboard, name='reporte_dashboard'),
]
