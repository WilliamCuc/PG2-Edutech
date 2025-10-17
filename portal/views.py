from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, FormView, DetailView, UpdateView
from academico.models import Clase, PeriodoAcademico, Actividad, Entrega
from .forms import ActividadForm, EntregaForm, CalificacionForm
from users.models import User
import datetime
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.db.models import Exists, OuterRef, Subquery, DecimalField

class PortalEstudianteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Muestra el portal principal para el estudiante, incluyendo su horario de clases
    para el periodo académico actual.
    """
    template_name = 'portal/portal_estudiante.html'

    def test_func(self):
        # 1. Condición de seguridad: ¿El usuario es un estudiante?
        return self.request.user.user_type == User.UserType.ESTUDIANTE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtenemos el perfil del estudiante del usuario que ha iniciado sesión
        estudiante = self.request.user.estudiante
        
        # 2. Lógica para encontrar el periodo académico actual
        # (Simplificación: tomamos el último periodo creado como el actual)
        periodo_actual = PeriodoAcademico.objects.order_by('-fecha_inicio').first()

        clases_inscritas = []
        if periodo_actual:
            # 3. Filtramos las clases en las que el estudiante está inscrito para el periodo actual
            clases_inscritas = Clase.objects.filter(
                estudiantes=estudiante,
                periodo=periodo_actual
            ).select_related('curso', 'maestro__user').order_by('dia_semana', 'hora_inicio')
            
            subquery_entrega = Entrega.objects.filter(
                actividad=OuterRef('pk'), 
                estudiante=estudiante
            )

            subquery_calificacion = subquery_entrega.values('calificacion')[:1]

            
            actividades = Actividad.objects.filter(
                clase__in=clases_inscritas
            ).select_related('clase__curso').annotate(
                fue_entregada=Exists(subquery_entrega),
                calificacion_obtenida=Subquery(subquery_calificacion, output_field=DecimalField())
            ).order_by('fecha_entrega')


        context['estudiante'] = estudiante
        context['clases_inscritas'] = clases_inscritas
        context['periodo_actual'] = periodo_actual
        context['actividades'] = actividades
        context['titulo'] = 'Mi Portal de Estudiante'
        
        return context
    
class PortalMaestroView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Muestra el portal principal para el maestro, con la lista de clases
    que imparte en el periodo académico actual.
    """
    template_name = 'portal/portal_maestro.html'

    def test_func(self):
        # Condición de seguridad: ¿El usuario es un maestro?
        return self.request.user.user_type == User.UserType.MAESTRO

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtenemos el perfil del maestro que ha iniciado sesión
        maestro = self.request.user.maestro
        
        # Buscamos el periodo académico actual
        periodo_actual = PeriodoAcademico.objects.order_by('-fecha_inicio').first()

        clases_asignadas = []
        if periodo_actual:
            # Filtramos las clases asignadas al maestro para el periodo actual
            # Usamos prefetch_related para obtener los estudiantes de forma eficiente
            clases_asignadas = Clase.objects.filter(
                maestro=maestro,
                periodo=periodo_actual
            ).select_related('curso').prefetch_related('estudiantes__user').order_by('dia_semana', 'hora_inicio')

        context['maestro'] = maestro
        context['clases_asignadas'] = clases_asignadas
        context['periodo_actual'] = periodo_actual
        context['titulo'] = 'Mi Portal de Maestro'
        
        return context

@login_required
def portal_redirect_view(request):
    """
    Redirige al usuario a su portal correspondiente después de iniciar sesión.
    """
    if request.user.user_type == User.UserType.ESTUDIANTE:
        return redirect('portal_estudiante')
    elif request.user.user_type == User.UserType.MAESTRO:
        return redirect('portal_maestro')
    elif request.user.is_superuser or request.user.user_type == User.UserType.ADMIN:
        # Si es un superusuario o admin, lo enviamos al panel de administración
        return redirect('admin:index')
    else:
        # Puedes definir una página por defecto para otros casos si los tienes
        return redirect('página_de_error_o_inicio_general')

class ActividadCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Actividad
    form_class = ActividadForm
    template_name = 'portal/actividad_form.html'

    def test_func(self):
        # El usuario debe ser maestro Y el maestro de la clase
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return self.request.user.user_type == User.UserType.MAESTRO and clase.maestro == self.request.user.maestro

    def form_valid(self, form):
        # Asignamos la clase a la actividad antes de guardarla
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        form.instance.clase = clase
        return super().form_valid(form)

    def get_success_url(self):
        # Redirige de vuelta al portal del maestro (o a una vista de detalle de la clase)
        return reverse_lazy('portal_maestro')
    
class ActividadDetailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'portal/actividad_detail.html'
    form_class = EntregaForm

    def test_func(self):
        # Solo estudiantes pueden ver esta página
        return self.request.user.user_type == User.UserType.ESTUDIANTE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        actividad = get_object_or_404(Actividad, pk=self.kwargs['pk'])
        estudiante = self.request.user.estudiante
        
        # Buscamos si ya existe una entrega para mostrarla
        entrega_existente = Entrega.objects.filter(actividad=actividad, estudiante=estudiante).first()

        # Asignamos las variables al contexto para usarlas en la plantilla
        context['actividad'] = actividad
        context['entrega_existente'] = entrega_existente
        return context

    def form_valid(self, form):
        actividad = get_object_or_404(Actividad, pk=self.kwargs['pk'])
        estudiante = self.request.user.estudiante

        # Usamos update_or_create para manejar tanto la primera entrega como las re-entregas
        Entrega.objects.update_or_create(
            actividad=actividad,
            estudiante=estudiante,
            defaults={
                'archivo': form.cleaned_data.get('archivo'), # Usar .get() es más seguro
                'comentarios': form.cleaned_data.get('comentarios')
            }
        )
        return redirect('portal_estudiante')

class ActividadEntregasView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """
    Muestra los detalles de una actividad y una lista de todas las entregas
    de los estudiantes para que el maestro las califique.
    """
    model = Actividad
    template_name = 'portal/actividad_entregas.html'
    context_object_name = 'actividad'

    def test_func(self):
        # Seguridad: Solo el maestro de la clase puede ver esta página
        actividad = self.get_object()
        return self.request.user.user_type == User.UserType.MAESTRO and actividad.clase.maestro == self.request.user.maestro

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtenemos todas las entregas asociadas a esta actividad
        context['entregas'] = self.object.entregas.all().select_related('estudiante__user')
        return context

class CalificarEntregaView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Muestra el formulario para calificar una entrega específica.
    """
    model = Entrega
    form_class = CalificacionForm
    template_name = 'portal/calificar_entrega_form.html'
    context_object_name = 'entrega'

    def test_func(self):
        # Seguridad: Solo el maestro de la clase puede calificar
        entrega = self.get_object()
        return self.request.user.user_type == User.UserType.MAESTRO and entrega.actividad.clase.maestro == self.request.user.maestro

    def get_success_url(self):
        # Redirige de vuelta a la lista de entregas de la actividad
        return reverse('actividad_entregas', kwargs={'pk': self.object.actividad.pk})
