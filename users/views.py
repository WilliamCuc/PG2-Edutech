from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView
from .models import User, Maestro, Estudiante
from .forms import MaestroForm, EstudianteForm
from django.db import transaction
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from academico.models import PeriodoAcademico, Clase, Actividad, Entrega, Cargo, Pago
from portal.models import Noticia, Notificacion
from django.db.models import OuterRef, Subquery, Exists, Q, DecimalField
from django.utils import timezone
from datetime import timedelta

class MaestroListView(ListView):
    model = Maestro
    template_name = 'users/maestros/lista.html'
    context_object_name = 'maestros' # 👈 Usaremos 'maestros' en el template

    def get_queryset(self):
        """
        Esta función se encarga de filtrar y ordenar los resultados
        basado en los parámetros de la URL (GET).
        """
        # Empezamos con todos los maestros
        queryset = Maestro.objects.all().select_related('user').prefetch_related('cursos')

        # 1. Búsqueda (parámetro 'q')
        search_query = self.request.GET.get('q', None)
        if search_query:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search_query) |
                Q(user__last_name__icontains=search_query) |
                Q(especialidad__icontains=search_query) |
                Q(numero_empleado__icontains=search_query)
            )

        # 2. Filtrado por Estado (parámetro 'status')
        status_filter = self.request.GET.get('status', None)
        if status_filter and status_filter != 'all':
            queryset = queryset.filter(estado=status_filter)
        
        # 3. Ordenamiento (parámetro 'sort')
        sort_by = self.request.GET.get('sort', 'user__first_name') # Ordenar por nombre A-Z por defecto
        queryset = queryset.order_by(sort_by)

        return queryset

    def get_context_data(self, **kwargs):
        """
        Pasa los valores actuales de los filtros a la plantilla
        para que los <select> e <input> se queden seleccionados.
        """
        context = super().get_context_data(**kwargs)
        
        # Pasa los valores GET actuales
        context['q'] = self.request.GET.get('q', '')
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_sort'] = self.request.GET.get('sort', 'user__first_name')
        
        # Pasa todos los parámetros GET para la paginación
        context['get_params'] = self.request.GET.urlencode()
        
        return context

class MaestroCreateView(CreateView):
    model = Maestro
    form_class = MaestroForm
    template_name = 'users/maestros/maestro_form.html'
    success_url = reverse_lazy('maestros')

    def form_valid(self, form):
        with transaction.atomic():
            # Crear el usuario primero
            user = User.objects.create_user(
                username=form.cleaned_data['numero_empleado'],
                password='passwordtemporal123',
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data['email'],
                user_type=User.UserType.MAESTRO
            )
            form.instance.user = user
        return super().form_valid(form)

class MaestroUpdateView(UpdateView):
    model = Maestro
    form_class = MaestroForm
    template_name = 'users/maestros/maestro_form.html'
    success_url = reverse_lazy('maestros')
    
    def form_valid(self, form):
        with transaction.atomic():
            maestro = self.get_object()
            user = maestro.user
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.email = form.cleaned_data['email']
            user.save()
        return super().form_valid(form)

class MaestroDeleteView(DeleteView):
    model = Maestro
    template_name = 'users/maestro_confirm_delete.html'
    success_url = reverse_lazy('maestros')

class EstudianteListView(ListView):
    model = Estudiante
    template_name = 'users/estudiantes/lista.html'
    context_object_name = 'estudiantes'

class EstudianteCreateView(CreateView):
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'users/estudiantes/estudiante_form.html'
    success_url = reverse_lazy('estudiante_list')

    @transaction.atomic
    def form_valid(self, form):
        with transaction.atomic():
            user = User.objects.create_user(
                username=form.cleaned_data['matricula'],
                password='passwordtemporal123',
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                email=form.cleaned_data.get('email', ''),
                user_type=User.UserType.ESTUDIANTE
            )
            form.instance.user = user
        response = super().form_valid(form)

        nuevo_grado = self.object.grado
        if nuevo_grado:
            self.object.clases_inscritas.set(nuevo_grado.clases.all())
            self._generar_cargos(self.object, nuevo_grado)

        return response
    
    def _generar_cargos(self, estudiante, grado):
        """Crea los cargos de Inscripción, Útiles y 12 Colegiaturas."""
        hoy = timezone.now().date()

        # 1. Cargo de Inscripción (solo si no existe)
        if grado.monto_inscripcion > 0 and not Cargo.objects.filter(estudiante=estudiante, concepto="Inscripción").exists():
            Cargo.objects.create(
                estudiante=estudiante,
                periodo=grado.periodo,
                concepto="Inscripción",
                monto=grado.monto_inscripcion,
                fecha_vencimiento=hoy + timedelta(days=30)
            )

        # 2. Cargo de Útiles/Libros (solo si no existe)
        if grado.monto_utiles > 0 and not Cargo.objects.filter(estudiante=estudiante, concepto="Útiles y Libros").exists():
            Cargo.objects.create(
                estudiante=estudiante,
                periodo=grado.periodo,
                concepto="Útiles y Libros",
                monto=grado.monto_utiles,
                fecha_vencimiento=hoy + timedelta(days=30)
            )

        # 3. Cargos de Colegiaturas (12 meses, solo si no existen)
        if grado.monto_colegiatura_mensual > 0:
            for i in range(12):
                mes_str = (hoy + timedelta(days=30*i)).strftime('%Y-%m')
                concepto = f"Colegiatura {mes_str}"
                
                if not Cargo.objects.filter(estudiante=estudiante, concepto=concepto).exists():
                    Cargo.objects.create(
                        estudiante=estudiante,
                        periodo=grado.periodo,
                        concepto=concepto,
                        monto=grado.monto_colegiatura_mensual,
                        fecha_vencimiento=(hoy + timedelta(days=30*i)).replace(day=5) # Vence el día 5
                    )

class EstudianteUpdateView(UpdateView):
    model = Estudiante
    form_class = EstudianteForm
    template_name = 'users/estudiante_form.html'
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
    template_name = 'users/estudiante_confirm_delete.html'
    success_url = reverse_lazy('estudiante_list')

class MaestroDetailView(DetailView):
    model = Maestro
    template_name = 'users/maestros/detail.html'
    context_object_name = 'maestro'
