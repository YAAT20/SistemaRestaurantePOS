from django.urls import path
from . import views

app_name = 'cocina'
urlpatterns = [
    path('', views.OrdenCocinaListView.as_view(), name='orden_list'),
    path('<int:pk>/marcar-impreso/', views.marcar_impreso, name='marcar_impreso'),
    path('orden/<int:pedido_id>/completar/', views.marcar_como_completo, name='marcar_completo'),
]