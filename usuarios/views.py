from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Usuario
from usuarios.mixins import AdminRequiredMixin 
from usuarios.form import UsuarioLoginForm
from django.contrib.auth.views import LoginView, LogoutView

from django.urls import reverse_lazy

class UsuarioLoginView(LoginView):
    template_name = 'usuarios/login.html'
    authentication_form = UsuarioLoginForm

    def get_success_url(self):
        user = self.request.user
        if user.rol == 'ADMIN':
            return reverse_lazy('administracion:reporte_dashboard')
        elif user.rol == 'MOZO':
            return reverse_lazy('menu:plato_list') 
        return reverse_lazy('home')

class UsuarioLogoutView(LogoutView):
    next_page = '/usuarios/login/'

class UsuarioListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Usuario
    template_name = 'usuarios/usuarios_list.html'
    context_object_name = 'usuarios'

class UsuarioCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Usuario
    template_name = 'usuarios/usuario_form.html'
    fields = ['username', 'first_name', 'last_name', 'email', 'rol', 'password']
    success_url = reverse_lazy('usuarios:usuario_list')

    def form_valid(self, form):
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()
        return super().form_valid(form)

class UsuarioUpdateView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Usuario
    template_name = 'usuarios/usuario_form.html'
    fields = ['first_name', 'last_name', 'email', 'rol']
    success_url = reverse_lazy('usuarios:usuario_list')

class UsuarioDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    model = Usuario
    template_name = 'usuarios/usuario_confirm_delete.html'
    success_url = reverse_lazy('usuarios:usuario_list')