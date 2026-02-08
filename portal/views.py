from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, FormView, DetailView, UpdateView, DeleteView, ListView
from academico.models import Clase, PeriodoAcademico, Actividad, Entrega, AsistenciaClase, Planificacion, Competencia
from .forms import ActividadForm, EntregaForm, CalificacionForm, NoticiaForm, NotificacionForm, AsistenciaForm, PlanificacionForm
from portal.models import Noticia
from users.models import User, Maestro, Estudiante, PadreDeFamilia
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.db.models import Exists, OuterRef, Subquery, DecimalField, Avg, Q
from .models import Notificacion
from django.utils import timezone
from django.forms import formset_factory
from django.views import View
from collections import defaultdict
from django.http import HttpResponseBadRequest
from django.db import transaction


class PortalEstudianteView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'portal/portal_estudiante.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.ESTUDIANTE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        estudiante = self.request.user.estudiante
        
        periodo_actual = PeriodoAcademico.objects.order_by('-fecha_inicio').first()

        clases_inscritas = []
        if periodo_actual:
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
        context['notificaciones'] = Notificacion.objects.filter(
            Q(audiencia=Notificacion.TargetAudiencia.TODOS) |
            Q(audiencia=Notificacion.TargetAudiencia.ESTUDIANTES)
        ).order_by('-fecha_envio')[:5]
        
        return context
    
class PortalMaestroView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'portal/portal_maestro.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        maestro = self.request.user.maestro
        
        periodo_actual = PeriodoAcademico.objects.order_by('-fecha_inicio').first()

        clases_asignadas = []
        if periodo_actual:
            clases_asignadas = Clase.objects.filter(
                maestro=maestro,
                periodo=periodo_actual
            ).select_related('curso').prefetch_related('estudiantes__user').order_by('dia_semana', 'hora_inicio')

        context['maestro'] = maestro
        context['clases_asignadas'] = clases_asignadas
        context['periodo_actual'] = periodo_actual
        context['titulo'] = 'Mi Portal de Maestro'
        context['notificaciones'] = Notificacion.objects.filter(
            Q(audiencia=Notificacion.TargetAudiencia.TODOS) |
            Q(audiencia=Notificacion.TargetAudiencia.MAESTROS)
        ).order_by('-fecha_envio')[:5]
        
        return context

@login_required
def portal_redirect_view(request):
    if request.user.user_type == User.UserType.ESTUDIANTE:
        return redirect('portal_estudiante')
    elif request.user.user_type == User.UserType.MAESTRO:
        return redirect('portal_maestro')
    elif request.user.is_superuser or request.user.user_type == User.UserType.ADMIN:
        return redirect('admin:index')
    elif request.user.user_type == User.UserType.PADRE:
        return redirect('portal_padre')
    else:
        return redirect('página_de_error_o_inicio_general')

class ActividadCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Actividad
    form_class = ActividadForm
    template_name = 'portal/actividad_form.html'

    def test_func(self):
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return self.request.user.user_type == User.UserType.MAESTRO and clase.maestro == self.request.user.maestro

    def form_valid(self, form):
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        form.instance.clase = clase
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('portal_maestro')
    
class ActividadDetailView(LoginRequiredMixin, UserPassesTestMixin, FormView):
    template_name = 'portal/actividad_detail.html'
    form_class = EntregaForm

    def test_func(self):
        return self.request.user.user_type == User.UserType.ESTUDIANTE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        actividad = get_object_or_404(Actividad, pk=self.kwargs['pk'])
        estudiante = self.request.user.estudiante
        
        entrega_existente = Entrega.objects.filter(actividad=actividad, estudiante=estudiante).first()

        context['actividad'] = actividad
        context['entrega_existente'] = entrega_existente
        return context

    def form_valid(self, form):
        actividad = get_object_or_404(Actividad, pk=self.kwargs['pk'])
        estudiante = self.request.user.estudiante

        Entrega.objects.update_or_create(
            actividad=actividad,
            estudiante=estudiante,
            defaults={
                'archivo': form.cleaned_data.get('archivo'),
                'comentarios': form.cleaned_data.get('comentarios')
            }
        )
        return redirect('portal_estudiante')

class ActividadEntregasView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Actividad
    template_name = 'portal/actividad_entregas.html'
    context_object_name = 'actividad'

    def test_func(self):
        actividad = self.get_object()
        return self.request.user.user_type == User.UserType.MAESTRO and actividad.clase.maestro == self.request.user.maestro

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['entregas'] = self.object.entregas.all().select_related('estudiante__user')
        return context

class CalificarEntregaView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Entrega
    form_class = CalificacionForm
    template_name = 'portal/calificar_entrega_form.html'
    context_object_name = 'entrega'

    def test_func(self):
        entrega = self.get_object()
        return self.request.user.user_type == User.UserType.MAESTRO and entrega.actividad.clase.maestro == self.request.user.maestro

    def get_success_url(self):
        return reverse('actividad_entregas', kwargs={'pk': self.object.actividad.pk})

class PortalAdminView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Noticia
    template_name = 'portal/portal_admin.html'
    context_object_name = 'noticias'
    paginate_by = 5

    def test_func(self):
        return self.request.user.user_type == User.UserType.ADMIN

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Portal Administrativo'
        
        context['notificacion_form'] = NotificacionForm() 
        return context

    def post(self, request, *args, **kwargs):
        form = NotificacionForm(request.POST)
        if form.is_valid():
            notificacion = form.save(commit=False)
            notificacion.autor = request.user
            notificacion.save()
            
            return redirect('portal_admin')
        else:
            return self.get(request, *args, **kwargs)

class NoticiaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Noticia
    form_class = NoticiaForm
    template_name = 'portal/noticia_form.html'
    success_url = reverse_lazy('portal_admin')

    def test_func(self):
        return self.request.user.user_type == User.UserType.ADMIN

    def form_valid(self, form):
        form.instance.autor = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Publicar Nueva Noticia'
        return context

class NoticiaUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Noticia
    form_class = NoticiaForm
    template_name = 'portal/noticia_form.html'
    success_url = reverse_lazy('portal_admin')

    def test_func(self):
        return self.request.user == self.get_object().autor or self.request.user.is_superuser

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Noticia'
        return context

class NoticiaDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Noticia
    template_name = 'portal/noticia_confirm_delete.html'
    success_url = reverse_lazy('portal_admin')

    def test_func(self):
        return self.request.user == self.get_object().autor or self.request.user.is_superuser
    
AsistenciaFormSet = formset_factory(AsistenciaForm, extra=0)

class TomarAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'portal/tomar_asistencia.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def get_clase(self):
        return get_object_or_404(
            Clase, 
            pk=self.kwargs['clase_pk'], 
            maestro=self.request.user.maestro
        )

    def get_fecha_seleccionada(self):
        fecha_str = self.kwargs.get('fecha')
        if fecha_str:
            try:
                return datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                pass # Si el formato es incorrecto, usa hoy
        return timezone.now().date()

    def get(self, request, *args, **kwargs):
        clase = self.get_clase()
        fecha_seleccionada = self.get_fecha_seleccionada()
        
        estudiantes = clase.estudiantes.all().select_related('user')
        
        asistencia_dia = AsistenciaClase.objects.filter(clase=clase, fecha=fecha_seleccionada)
        asistencia_map = {a.estudiante_id: a.estado for a in asistencia_dia}
        
        initial_data = []
        estudiantes_data = []
        
        for est in estudiantes:
            estado_actual = asistencia_map.get(est.pk, 'A')
            initial_data.append({'estudiante_id': est.pk, 'estado': estado_actual})
            estudiantes_data.append({'nombre': est.user.get_full_name(), 'id': est.pk})

        formset = AsistenciaFormSet(initial=initial_data)
        alumnos_con_form = zip(estudiantes_data, formset)

        fecha_anterior = fecha_seleccionada - timedelta(days=1)
        fecha_siguiente = fecha_seleccionada + timedelta(days=1)
        es_hoy = (fecha_seleccionada == timezone.now().date())

        context = {
            'clase': clase,
            'formset': formset,
            'alumnos_con_form': alumnos_con_form,
            'fecha_seleccionada': fecha_seleccionada,
            'fecha_anterior_str': fecha_anterior.isoformat(),
            'fecha_siguiente_str': fecha_siguiente.isoformat(),
            'es_hoy': es_hoy,
        }
        return render(request, self.template_name, context)

    def post(self, request, *args, **kwargs):
        clase = self.get_clase()
        fecha_seleccionada = self.get_fecha_seleccionada()
        
        formset = AsistenciaFormSet(request.POST)

        if formset.is_valid():
            for form_data in formset.cleaned_data:
                estudiante_id = form_data['estudiante_id']
                estado = form_data['estado']
                
                AsistenciaClase.objects.update_or_create(
                    clase=clase,
                    estudiante_id=estudiante_id,
                    fecha=fecha_seleccionada,
                    defaults={'estado': estado}
                )
            
            return redirect('portal_maestro')
        
        return self.get(request, *args, **kwargs)

class PlanificacionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Planificacion
    template_name = 'portal/planificacion_list.html'
    context_object_name = 'planificaciones'

    def test_func(self):
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return self.request.user.maestro == clase.maestro

    def get_queryset(self):
        return Planificacion.objects.filter(clase__pk=self.kwargs['clase_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clase'] = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return context

class PlanificacionCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Planificacion
    form_class = PlanificacionForm
    template_name = 'portal/planificacion_form.html'

    def test_func(self):
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return self.request.user.maestro == clase.maestro

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['clase'] = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return kwargs

    def form_valid(self, form):
        form.instance.clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('planificacion_list', kwargs={'clase_pk': self.kwargs['clase_pk']})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nueva Planificación'
        return context

class PlanificacionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Planificacion
    form_class = PlanificacionForm
    template_name = 'portal/planificacion_form.html'

    def test_func(self):
        return self.request.user.maestro == self.get_object().clase.maestro

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['clase'] = self.get_object().clase
        return kwargs
    
    def get_success_url(self):
        return reverse_lazy('planificacion_list', kwargs={'clase_pk': self.object.clase.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Planificación'
        return context

class PlanificacionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Planificacion
    template_name = 'portal/planificacion_confirm_delete.html'
    
    def test_func(self):
        return self.request.user.maestro == self.get_object().clase.maestro

    def get_success_url(self):
        return reverse_lazy('planificacion_list', kwargs={'clase_pk': self.object.clase.pk})
    
class MisCalificacionesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Entrega
    template_name = 'portal/mis_calificaciones.html'
    context_object_name = 'entregas'

    def test_func(self):
        return self.request.user.user_type == User.UserType.ESTUDIANTE

    def get_queryset(self):
        return Entrega.objects.filter(
            estudiante=self.request.user.estudiante,
            calificacion__isnull=False
        ).select_related(
            'actividad__clase__curso',
            'actividad'
        ).order_by('actividad__clase__curso__nombre', 'actividad__fecha_entrega')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        entregas_por_curso = defaultdict(list)
        for entrega in context['entregas']:
            curso_nombre = entrega.actividad.clase.curso.nombre
            entregas_por_curso[curso_nombre].append(entrega)
            
        calificaciones_agrupadas = {}
        for curso, entregas_lista in entregas_por_curso.items():
            total_curso = sum(entrega.calificacion for entrega in entregas_lista)
            promedio_curso = total_curso / len(entregas_lista)
            
            calificaciones_agrupadas[curso] = {
                'entregas': entregas_lista,
                'promedio': promedio_curso
            }
            
        context['calificaciones_agrupadas'] = calificaciones_agrupadas
        context['titulo'] = 'Mis Calificaciones'
        return context


class PortalPadreView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'portal/portal_padre_seleccion.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.PADRE

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        padre = self.request.user.padre_familia
        context['hijos'] = padre.hijos.all().select_related('user')
        context['titulo'] = 'Portal de Padre de Familia'
        return context

class PadreEstudianteDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'portal/portal_estudiante_dashboard.html'

    def test_func(self):
        if not self.request.user.user_type == User.UserType.PADRE:
            return False
        
        try:
            estudiante_a_ver = Estudiante.objects.get(pk=self.kwargs['estudiante_pk'])
            padre_logueado = self.request.user.padre_familia
            
            return estudiante_a_ver in padre_logueado.hijos.all()
        except Estudiante.DoesNotExist:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = Estudiante.objects.get(pk=self.kwargs['estudiante_pk'])
        
        periodo_actual = PeriodoAcademico.objects.order_by('-fecha_inicio').first()
        clases_inscritas = []
        actividades = Actividad.objects.none()

        if periodo_actual:
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
        context['user'] = estudiante.user
        context['clases_inscritas'] = clases_inscritas
        context['periodo_actual'] = periodo_actual
        context['actividades'] = actividades
        context['noticias'] = Noticia.objects.filter(publicado=True).order_by('-fecha_publicacion')[:5]
        context['notificaciones'] = Notificacion.objects.filter(
            Q(audiencia=Notificacion.TargetAudiencia.TODOS) |
            Q(audiencia=Notificacion.TargetAudiencia.ESTUDIANTES) |
            Q(audiencia=Notificacion.TargetAudiencia.PADRES)
        ).order_by('-fecha_envio')[:5]
        context['titulo'] = f"Portal de {estudiante.user.first_name}"
        
        return context
    
class PadreMisCalificacionesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Muestra todas las calificaciones de un estudiante específico,
    para que su padre las vea.
    """
    model = Entrega
    template_name = 'portal/mis_calificaciones.html' # Reutilizamos la plantilla
    context_object_name = 'entregas'

    def test_func(self):
        # Seguridad:
        if not self.request.user.user_type == User.UserType.PADRE:
            return False
        try:
            estudiante_a_ver = Estudiante.objects.get(pk=self.kwargs['estudiante_pk'])
            padre_logueado = self.request.user.padre_familia
            return estudiante_a_ver in padre_logueado.hijos.all()
        except Estudiante.DoesNotExist:
            return False

    def get_queryset(self):
        # Obtenemos el estudiante de la URL
        estudiante = Estudiante.objects.get(pk=self.kwargs['estudiante_pk'])
        return Entrega.objects.filter(
            estudiante=estudiante,
            calificacion__isnull=False
        ).select_related(
            'actividad__clase__curso', 'actividad'
        ).order_by('actividad__clase__curso__nombre', 'actividad__fecha_entrega')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = Estudiante.objects.get(pk=self.kwargs['estudiante_pk'])

        # (Lógica de agrupación de notas, copiada de MisCalificacionesView)
        calificaciones_por_curso = defaultdict(list)
        for entrega in context['entregas']:
            curso_nombre = entrega.actividad.clase.curso.nombre
            calificaciones_por_curso[curso_nombre].append(entrega)

        calificaciones_agrupadas = {}
        for curso, entregas_lista in calificaciones_por_curso.items():
            total_curso = sum(entrega.calificacion for entrega in entregas_lista)
            promedio_curso = total_curso / len(entregas_lista)
            calificaciones_agrupadas[curso] = {
                'entregas': entregas_lista,
                'promedio': promedio_curso
            }

        context['calificaciones_agrupadas'] = calificaciones_agrupadas
        context['titulo'] = f"Calificaciones de {estudiante.user.first_name}"
        context['es_padre'] = True # Bandera para la plantilla
        context['estudiante'] = estudiante # Para el enlace de "Volver"
        return context
    
class CalificacionesPeriodoView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Muestra la "boleta" o el reporte de calificaciones finales
    de un estudiante para un periodo específico.
    """
    template_name = 'portal/calificaciones_periodo.html'

    def test_func(self):
        # Pueden entrar estudiantes o padres (viendo a un hijo)
        return self.request.user.user_type in [User.UserType.ESTUDIANTE, User.UserType.PADRE]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Determinamos qué estudiante estamos viendo
        if self.request.user.user_type == User.UserType.ESTUDIANTE:
            estudiante = self.request.user.estudiante
        else:
            # (Si es un padre, asumimos que el PK del estudiante viene en la URL)
            # Esta lógica la podemos refinar luego
            estudiante = get_object_or_404(Estudiante, pk=self.kwargs.get('estudiante_pk'))
            context['es_padre'] = True
            
        # Obtenemos el periodo seleccionado (de la sesión)
        periodo_actual_id = self.request.session.get('periodo_seleccionado_id')
        periodo = get_object_or_404(PeriodoAcademico, pk=periodo_actual_id)
        
        # --- LA CONSULTA CLAVE ---
        # Agrupa todas las entregas por curso y calcula el promedio
        calificaciones_finales = Entrega.objects.filter(
            estudiante=estudiante,
            actividad__clase__periodo=periodo,
            calificacion__isnull=False
        ).values(
            'actividad__clase__curso__nombre' # Agrupar por nombre de curso
        ).annotate(
            promedio_final=Avg('calificacion') # Calcular el promedio
        ).order_by(
            'actividad__clase__curso__nombre'
        )
        
        context['estudiante'] = estudiante
        context['periodo'] = periodo
        context['reporte_notas'] = calificaciones_finales
        context['titulo'] = f"Boleta de Calificaciones - {periodo.nombre}"
        return context
    
class PeriodoSeleccionadoMixin:
    """
    Mixin que proporciona el método get_periodo_actual()
    leyendo desde la sesión, con un fallback inteligente.
    """
    def get_periodo_actual(self):
        # 1. Intentar obtener el periodo desde la sesión (lo que el usuario eligió)
        periodo_id = self.request.session.get('periodo_seleccionado_id')
        periodo_actual = None
        
        if periodo_id:
            try:
                periodo_actual = PeriodoAcademico.objects.get(pk=periodo_id)
            except PeriodoAcademico.DoesNotExist:
                # El ID en la sesión era inválido o viejo, lo borramos
                if 'periodo_seleccionado_id' in self.request.session:
                     del self.request.session['periodo_seleccionado_id']

        # 2. Si no hay nada en la sesión (es la primera visita o se borró)
        #    usamos el fallback inteligente.
        if not periodo_actual:
            periodo_fallback = None
            user = self.request.user

            try:
                # --- INICIO DE LA NUEVA LÓGICA DE FALLBACK ---
                if user.user_type == User.UserType.ESTUDIANTE and user.estudiante.grado:
                    # FALLBACK 1: El periodo del grado del estudiante
                    periodo_fallback = user.estudiante.grado.periodo
                
                elif user.user_type == User.UserType.PADRE and user.padre_familia.hijos.exists():
                    # FALLBACK 2: El periodo del grado del primer hijo
                    primer_hijo = user.padre_familia.hijos.first()
                    if primer_hijo and primer_hijo.grado:
                        periodo_fallback = primer_hijo.grado.periodo
                # --- FIN DE LA NUEVA LÓGICA DE FALLBACK ---

            except AttributeError: 
                # Pasa si el estudiante no tiene grado, o el grado no tiene periodo
                pass 
            
            # FALLBACK 3: (Maestros, Admins, o si los fallbacks 1 y 2 fallan)
            # Usamos el más reciente del sistema.
            if not periodo_fallback:
                periodo_fallback = PeriodoAcademico.objects.order_by('-fecha_inicio').first()

            # Asignamos el fallback y lo guardamos en la sesión
            periodo_actual = periodo_fallback
            if periodo_actual:
                self.request.session['periodo_seleccionado_id'] = periodo_actual.pk
                
        return periodo_actual
    
class CambiarPeriodoView(LoginRequiredMixin, View):
    """
    Una vista simple que actualiza el periodo seleccionado
    en la sesión del usuario y redirige de vuelta.
    """
    def post(self, request, *args, **kwargs):
        periodo_id = request.POST.get('periodo_id')
        
        # Obtenemos la URL a la que debemos redirigir (la página actual)
        # 'inicio' es un fallback seguro.
        next_url = request.POST.get('next', 'inicio') 

        if not periodo_id:
            return HttpResponseBadRequest("No se proporcionó un ID de periodo.")

        try:
            # Guardamos el ID en la sesión
            request.session['periodo_seleccionado_id'] = int(periodo_id)
        except ValueError:
            return HttpResponseBadRequest("ID de periodo inválido.")
        
        return redirect(next_url)