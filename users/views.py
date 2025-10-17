from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from .models import User, Maestro, Estudiante
from .forms import MaestroForm, EstudianteForm
from django.db import transaction # Para asegurar que ambas creaciones sean exitosas

# Create your views here.
def maestros(request):
    # Lógica para manejar la vista de maestros
    lista_de_maestros = Maestro.objects.all()
    
    return render(request, 'users/maestros/lista.html', {'lista_de_maestros': lista_de_maestros})

class MaestroCreateView(CreateView):
    model = Maestro
    form_class = MaestroForm
    template_name = 'usuarios/maestro_form.html'
    success_url = reverse_lazy('maestro_list')

    def form_valid(self, form):
        # Usamos una transacción para asegurar la integridad de los datos
        with transaction.atomic():
            # Crear el usuario primero
            user = User.objects.create_user(
                username=form.cleaned_data['numero_empleado'], # Usamos el número de empleado como username
                password='passwordtemporal123',  # Puedes generar una contraseña aleatoria
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                user_type=User.UserType.MAESTRO
            )
            # Asignar el usuario creado al perfil del maestro
            form.instance.user = user
        return super().form_valid(form)

class MaestroUpdateView(UpdateView):
    model = Maestro
    form_class = MaestroForm
    template_name = 'usuarios/maestro_form.html'
    success_url = reverse_lazy('maestro_list')
    
    def form_valid(self, form):
        with transaction.atomic():
            # Actualizar los datos del usuario relacionado
            maestro = self.get_object()
            user = maestro.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
        return super().form_valid(form)

class MaestroDeleteView(DeleteView):
    model = Maestro
    template_name = 'usuarios/maestro_confirm_delete.html'
    success_url = reverse_lazy('maestro_list')

# ======================= VISTAS PARA ESTUDIANTES =======================

class EstudianteListView(ListView):
    model = Estudiante
    template_name = 'users/estudiantes/lista.html'
    context_object_name = 'estudiantes'

class EstudianteCreateView(CreateView):
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'users/estudiantes/estudiante_form.html'
    success_url = reverse_lazy('estudiante_list')

    def form_valid(self, form):
        with transaction.atomic():
            user = User.objects.create_user(
                username=form.cleaned_data['matricula'], # Usamos la matrícula como username
                password='passwordtemporal123',
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data.get('email', ''),
                user_type=User.UserType.ESTUDIANTE
            )
            form.instance.user = user
        return super().form_valid(form)

class EstudianteUpdateView(UpdateView):
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'usuarios/estudiante_form.html'
    success_url = reverse_lazy('estudiante_list')
    
    def form_valid(self, form):
        with transaction.atomic():
            estudiante = self.get_object()
            user = estudiante.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data.get('email', '')
            user.save()
        return super().form_valid(form)

class EstudianteDeleteView(DeleteView):
    model = Estudiante
    template_name = 'usuarios/estudiante_confirm_delete.html'
    success_url = reverse_lazy('estudiante_list')

class MaestroDetailView(DetailView):
    model = Maestro
    template_name = 'users/maestros/detail.html'
    context_object_name = 'maestro'
