from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    path('', views.PlatoListView.as_view(), name='plato_list'),
    path('nuevo/', views.PlatoCreateView.as_view(), name='plato_create'),
    path('editar/<int:pk>/', views.PlatoUpdateView.as_view(), name='plato_update'),
    path('eliminar/<int:pk>/', views.PlatoDeleteView.as_view(), name='plato_delete'),
    path('toggle/<int:pk>/', views.toggle_disponibilidad, name='toggle_disponibilidad'),
    path('reponer/', views.ReponerStockView.as_view(), name='reponer_stock'),
    path('configurar-dia/', views.ConfigurarPlatosDelDiaView.as_view(), name='configurar_platos_del_dia'),
    path("carta/", views.CartaDelDiaView.as_view(), name="carta_del_dia"),
    path("platos/<int:plato_id>/ingredientes/", views.asignar_ingrediente, name="asignar_ingrediente"),

]