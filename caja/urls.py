from django.urls import path
from . import views

app_name = 'caja'

urlpatterns = [
    path('', views.CierreCajaListView.as_view(), name='cierre_list'),
    path('iniciar/', views.IniciarCierreView.as_view(), name='iniciar_cierre'),
    path('<int:pk>/verificar/', views.VerificarEfectivoView.as_view(), name='verificar_efectivo'),
    path('<int:pk>/cerrar/', views.CerrarDefinitivoView.as_view(), name='cerrar_definitivo'),
    path('<int:pk>/', views.CierreCajaDetailView.as_view(), name='cierre_detail'),
]