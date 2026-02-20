from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.UsuarioLoginView.as_view(), name='login'),
    path('logout/', views.UsuarioLogoutView.as_view(), name='logout'),  
    path('', views.UsuarioListView.as_view(), name='usuario_list'),
    path('nuevo/', views.UsuarioCreateView.as_view(), name='usuario_create'),
    path('<int:pk>/editar/', views.UsuarioUpdateView.as_view(), name='usuario_update'),
    path('<int:pk>/eliminar/', views.UsuarioDeleteView.as_view(), name='usuario_delete'),
]