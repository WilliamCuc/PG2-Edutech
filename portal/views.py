from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, CreateView, FormView, DetailView, UpdateView, DeleteView, ListView
from academico.models import Clase, PeriodoAcademico, Actividad, Entrega, AsistenciaClase, Planificacion, Competencia, BitacoraPedagogica
from .forms import ActividadForm, EntregaForm, CalificacionForm, EntregaEditForm, NoticiaForm, NotificacionForm, AsistenciaForm, PlanificacionForm
from portal.models import Noticia
from users.models import User, Maestro, Estudiante, PadreDeFamilia
from datetime import datetime, timedelta, date
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.db.models import Exists, OuterRef, Subquery, DecimalField, Avg, Q, Case, When, Value, IntegerField, Count, F, ExpressionWrapper, DurationField
from .models import Notificacion
from django.utils import timezone
from django.forms import formset_factory
from django.views import View
from collections import defaultdict, OrderedDict
from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.db import transaction


def portal_redirect_view(request):
    if not request.user.is_authenticated:
        return redirect('login')

    user_type = request.user.user_type

    if user_type == User.UserType.ESTUDIANTE:
        return redirect('portal_estudiante')
    elif user_type == User.UserType.MAESTRO:
        return redirect('portal_maestro')
    elif user_type == User.UserType.ADMIN:
        return redirect('portal_admin')
    elif user_type == User.UserType.PADRE:
        return redirect('portal_padre')
    else:
        return redirect('admin:index')


class PeriodoSeleccionadoMixin:
    def get_periodo_actual(self):
        periodo_id = self.request.session.get('periodo_seleccionado_id')
        periodo_actual = None

        if periodo_id:
            try:
                periodo_actual = PeriodoAcademico.objects.get(pk=periodo_id)
            except PeriodoAcademico.DoesNotExist:
                if 'periodo_seleccionado_id' in self.request.session:
                    del self.request.session['periodo_seleccionado_id']

        if not periodo_actual:
            periodo_fallback = None
            user = self.request.user

            try:
                if user.user_type == User.UserType.ESTUDIANTE:
                    estudiante = user.get_estudiante_profile()
                    if estudiante and estudiante.grado:
                        periodo_fallback = estudiante.grado.periodo

                elif user.user_type == User.UserType.PADRE and hasattr(user, 'padre_familia') and user.padre_familia.hijos.exists():
                    primer_hijo = user.padre_familia.hijos.first()
                    if primer_hijo and primer_hijo.grado:
                        periodo_fallback = primer_hijo.grado.periodo

            except AttributeError:
                pass

            if not periodo_fallback:
                periodo_fallback = PeriodoAcademico.objects.order_by('-fecha_inicio').first()

            periodo_actual = periodo_fallback
            if periodo_actual:
                self.request.session['periodo_seleccionado_id'] = periodo_actual.pk

        return periodo_actual


class PortalEstudianteView(LoginRequiredMixin, UserPassesTestMixin, PeriodoSeleccionadoMixin, TemplateView):
    template_name = 'portal/portal_estudiante.html'

    def test_func(self):
        return (self.request.user.user_type == User.UserType.ESTUDIANTE and
                self.request.user.get_estudiante_profile() is not None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = self.request.user.get_estudiante_profile()
        self.request.session['estudiante_seleccionado_pk'] = estudiante.pk

        periodo_actual = self.get_periodo_actual()
        clases_inscritas = []
        actividades = Actividad.objects.none()

        if periodo_actual:
            day_order = Case(
                When(dia_semana='LUN', then=Value(0)),
                When(dia_semana='MAR', then=Value(1)),
                When(dia_semana='MIE', then=Value(2)),
                When(dia_semana='JUE', then=Value(3)),
                When(dia_semana='VIE', then=Value(4)),
                When(dia_semana='SAB', then=Value(5)),
                output_field=IntegerField(),
            )
            clases_inscritas = Clase.objects.filter(
                estudiantes=estudiante,
                periodo=periodo_actual
            ).select_related('curso', 'maestro__user').order_by(day_order, 'hora_inicio')

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

        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
        horario_por_dia = OrderedDict()
        for dia in orden_dias:
            horario_por_dia[dia] = []
        for clase in clases_inscritas:
            dia_display = clase.get_dia_semana_display()
            horario_por_dia[dia_display].append(clase)

        actividades_por_curso = OrderedDict()
        for actividad in actividades:
            curso_nombre = actividad.clase.curso.nombre
            if curso_nombre not in actividades_por_curso:
                actividades_por_curso[curso_nombre] = []
            actividades_por_curso[curso_nombre].append(actividad)

        context['estudiante'] = estudiante
        context['clases_inscritas'] = clases_inscritas
        context['periodo_actual'] = periodo_actual
        context['actividades'] = actividades
        context['horario_por_dia'] = horario_por_dia
        context['actividades_por_curso'] = actividades_por_curso
        context['noticias'] = Noticia.objects.filter(publicado=True).order_by('-fecha_publicacion')[:5]
        context['notificaciones'] = Notificacion.objects.filter(
            Q(audiencia=Notificacion.TargetAudiencia.TODOS) |
            Q(audiencia=Notificacion.TargetAudiencia.ESTUDIANTES) |
            Q(audiencia=Notificacion.TargetAudiencia.PADRES)
        ).order_by('-fecha_envio')[:5]
        return context


class MisCalificacionesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Entrega
    template_name = 'portal/mis_calificaciones.html'
    context_object_name = 'entregas'

    def test_func(self):
        return (self.request.user.user_type == User.UserType.ESTUDIANTE and
                self.request.user.get_estudiante_profile() is not None)

    def get_queryset(self):
        estudiante = self.request.user.get_estudiante_profile()
        return Entrega.objects.filter(
            estudiante=estudiante,
            calificacion__isnull=False
        ).select_related(
            'actividad__clase__curso', 'actividad'
        ).order_by('actividad__clase__curso__nombre', 'actividad__fecha_entrega')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
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
        context['es_padre'] = False
        return context


class PortalMaestroView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'portal/portal_maestro.html'

    def test_func(self):
        return (self.request.user.user_type == User.UserType.MAESTRO and
                self.request.user.get_maestro_profile() is not None)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        maestro = self.request.user.get_maestro_profile()
        periodo_actual = PeriodoAcademico.objects.order_by('-fecha_inicio').first()

        cursos_con_clases = []
        kpi = {
            'total_estudiantes': 0,
            'total_cursos': 0,
            'total_clases_semana': 0,
            'total_actividades': 0,
            'total_entregas': 0,
            'total_entregas_calificadas': 0,
            'promedio_general': None,
            'tasa_asistencia': None,
            'total_bitacoras': 0,
            'total_planificaciones': 0,
            'total_bitacoras_con_tiempo': 0,
            'tiempo_promedio_bitacora': None,
            'tiempo_promedio_segundos': None,
            'total_actividades_con_tiempo': 0,
            'tiempo_promedio_actividad': None,
            'total_planificaciones_con_tiempo': 0,
            'tiempo_promedio_planificacion': None,
        }

        if periodo_actual and maestro:
            clases = Clase.objects.filter(
                maestro=maestro,
                periodo=periodo_actual
            ).select_related('curso').prefetch_related(
                'estudiantes__user'
            ).order_by('curso__nombre')

            kpi['total_clases_semana'] = clases.count()
            todas_clases_ids = list(clases.values_list('pk', flat=True))

            clases_por_curso = OrderedDict()
            for clase in clases:
                curso_nombre = clase.curso.nombre
                if curso_nombre not in clases_por_curso:
                    clases_por_curso[curso_nombre] = {
                        'curso': clase.curso,
                        'clases': [],
                        'estudiantes': [],
                        'estudiantes_set': set(),
                        'clase_ids': [],
                    }
                clases_por_curso[curso_nombre]['clases'].append(clase)
                clases_por_curso[curso_nombre]['clase_ids'].append(clase.pk)
                for est in clase.estudiantes.all():
                    if est.pk not in clases_por_curso[curso_nombre]['estudiantes_set']:
                        clases_por_curso[curso_nombre]['estudiantes'].append(est)
                        clases_por_curso[curso_nombre]['estudiantes_set'].add(est.pk)

            actividades = Actividad.objects.filter(
                clase__in=todas_clases_ids
            ).prefetch_related('entregas').select_related('clase__curso').order_by('-fecha_creacion')

            actividades_por_curso = OrderedDict()
            for actividad in actividades:
                curso_nombre = actividad.clase.curso.nombre
                if curso_nombre not in actividades_por_curso:
                    actividades_por_curso[curso_nombre] = []
                actividades_por_curso[curso_nombre].append(actividad)

            kpi['total_actividades'] = actividades.count()

            entregas = Entrega.objects.filter(
                actividad__clase__in=todas_clases_ids
            )
            kpi['total_entregas'] = entregas.count()
            kpi['total_entregas_calificadas'] = entregas.filter(calificacion__isnull=False).count()

            prom_gral = entregas.filter(calificacion__isnull=False).aggregate(
                avg=Avg('calificacion')
            )['avg']
            kpi['promedio_general'] = round(prom_gral, 1) if prom_gral else None

            asistencias = AsistenciaClase.objects.filter(clase__in=todas_clases_ids)
            total_asistencias = asistencias.count()
            if total_asistencias > 0:
                presentes = asistencias.filter(estado=AsistenciaClase.EstadoAsistencia.PRESENTE).count()
                kpi['tasa_asistencia'] = round((presentes / total_asistencias) * 100, 1)

            kpi['total_planificaciones'] = Planificacion.objects.filter(
                clase__in=todas_clases_ids
            ).count()

            bitacoras_con_tiempo = BitacoraPedagogica.objects.filter(
                clase__in=todas_clases_ids,
                fecha_inicio_calculo__isnull=False,
                fecha_fin_calculo__isnull=False,
            )
            kpi['total_bitacoras_con_tiempo'] = bitacoras_con_tiempo.count()
            avg_seconds = None
            if kpi['total_bitacoras_con_tiempo'] > 0:
                tiempos = bitacoras_con_tiempo.annotate(
                    duracion=ExpressionWrapper(
                        F('fecha_fin_calculo') - F('fecha_inicio_calculo'),
                        output_field=DurationField()
                    )
                ).values_list('duracion', flat=True)
                total_seconds = sum(t.total_seconds() for t in tiempos if t and t.total_seconds() > 0)
                count_valid = sum(1 for t in tiempos if t and t.total_seconds() > 0)
                if count_valid > 0:
                    avg_seconds = total_seconds / count_valid
                    if avg_seconds < 3600:
                        kpi['tiempo_promedio_bitacora'] = f"{int(avg_seconds // 60)}m {int(avg_seconds % 60)}s"
                    else:
                        horas = int(avg_seconds // 3600)
                        minutos = int((avg_seconds % 3600) // 60)
                        kpi['tiempo_promedio_bitacora'] = f"{horas}h {minutos}m"
                    kpi['tiempo_promedio_segundos'] = round(avg_seconds, 1)
                else:
                    kpi['tiempo_promedio_bitacora'] = None
                    kpi['tiempo_promedio_segundos'] = None
            else:
                kpi['tiempo_promedio_bitacora'] = None
                kpi['tiempo_promedio_segundos'] = None

            def _calc_timing_stats(qs):
                total_con_tiempo = qs.count()
                avg_str = None
                if total_con_tiempo > 0:
                    tiempos = qs.annotate(
                        duracion=ExpressionWrapper(
                            F('fecha_fin_calculo') - F('fecha_inicio_calculo'),
                            output_field=DurationField()
                        )
                    ).values_list('duracion', flat=True)
                    segs = [t.total_seconds() for t in tiempos if t and t.total_seconds() > 0]
                    if segs:
                        avg_s = sum(segs) / len(segs)
                        if avg_s < 3600:
                            avg_str = f"{int(avg_s // 60)}m {int(avg_s % 60)}s"
                        else:
                            horas = int(avg_s // 3600)
                            minutos = int((avg_s % 3600) // 60)
                            avg_str = f"{horas}h {minutos}m"
                return total_con_tiempo, avg_str

            actividades_con_tiempo = Actividad.objects.filter(
                clase__in=todas_clases_ids,
                fecha_inicio_calculo__isnull=False,
                fecha_fin_calculo__isnull=False,
            )
            kpi['total_actividades_con_tiempo'], kpi['tiempo_promedio_actividad'] = _calc_timing_stats(actividades_con_tiempo)

            planificaciones_con_tiempo = Planificacion.objects.filter(
                clase__in=todas_clases_ids,
                fecha_inicio_calculo__isnull=False,
                fecha_fin_calculo__isnull=False,
            )
            kpi['total_planificaciones_con_tiempo'], kpi['tiempo_promedio_planificacion'] = _calc_timing_stats(planificaciones_con_tiempo)

            all_students_set = set()
            for data in clases_por_curso.values():
                for est in data['estudiantes']:
                    all_students_set.add(est.pk)
            kpi['total_estudiantes'] = len(all_students_set)
            kpi['total_cursos'] = len(clases_por_curso)

            for curso_nombre, data in clases_por_curso.items():
                curso_clase_ids = data['clase_ids']
                curso_actividades = actividades_por_curso.get(curso_nombre, [])
                total_acts = len(curso_actividades)
                total_ent_curso = sum(
                    a.entregas.count() for a in curso_actividades
                )
                total_entregadas_curso = sum(
                    a.entregas.filter(calificacion__isnull=False).count()
                    for a in curso_actividades
                )
                prom_curso = None
                curso_entregas_calif = Entrega.objects.filter(
                    actividad__in=curso_actividades,
                    calificacion__isnull=False
                ).aggregate(avg=Avg('calificacion'))['avg']
                if curso_entregas_calif:
                    prom_curso = round(curso_entregas_calif, 1)

                tasa_asistencia_curso = None
                asistencias_curso = AsistenciaClase.objects.filter(clase__in=curso_clase_ids)
                total_asist_curso = asistencias_curso.count()
                if total_asist_curso > 0:
                    presentes_curso = asistencias_curso.filter(
                        estado=AsistenciaClase.EstadoAsistencia.PRESENTE
                    ).count()
                    tasa_asistencia_curso = round((presentes_curso / total_asist_curso) * 100, 1)

                planif_count = Planificacion.objects.filter(
                    clase__in=curso_clase_ids
                ).count()

                bitacora_count = BitacoraPedagogica.objects.filter(
                    clase__in=curso_clase_ids
                ).count()

                bitacoras_tiempo_curso = BitacoraPedagogica.objects.filter(
                    clase__in=curso_clase_ids,
                    fecha_inicio_calculo__isnull=False,
                    fecha_fin_calculo__isnull=False,
                )
                curso_bitacoras_con_tiempo = bitacoras_tiempo_curso.count()
                tiempo_promedio_curso_str = None
                if curso_bitacoras_con_tiempo > 0:
                    tiempos_curso = bitacoras_tiempo_curso.annotate(
                        duracion=ExpressionWrapper(
                            F('fecha_fin_calculo') - F('fecha_inicio_calculo'),
                            output_field=DurationField()
                        )
                    ).values_list('duracion', flat=True)
                    segs = [t.total_seconds() for t in tiempos_curso if t and t.total_seconds() > 0]
                    if segs:
                        avg_s = sum(segs) / len(segs)
                        if avg_s < 3600:
                            tiempo_promedio_curso_str = f"{int(avg_s // 60)}m {int(avg_s % 60)}s"
                        else:
                            tiempo_promedio_curso_str = f"{int(avg_s // 3600)}h {int((avg_s % 3600) // 60)}m"

                actividades_tiempo_curso = Actividad.objects.filter(
                    clase__in=curso_clase_ids,
                    fecha_inicio_calculo__isnull=False,
                    fecha_fin_calculo__isnull=False,
                )
                curso_actividades_con_tiempo, tiempo_promedio_actividad_str = _calc_timing_stats(actividades_tiempo_curso)

                planificaciones_tiempo_curso = Planificacion.objects.filter(
                    clase__in=curso_clase_ids,
                    fecha_inicio_calculo__isnull=False,
                    fecha_fin_calculo__isnull=False,
                )
                curso_planificaciones_con_tiempo, tiempo_promedio_planificacion_str = _calc_timing_stats(planificaciones_tiempo_curso)

                cursos_con_clases.append({
                    'curso': data['curso'],
                    'clases': data['clases'],
                    'estudiantes': data['estudiantes'],
                    'actividades': curso_actividades,
                    'total_actividades': total_acts,
                    'total_entregas': total_ent_curso,
                    'total_entregas_calificadas': total_entregadas_curso,
                    'promedio': prom_curso,
                    'tasa_asistencia': tasa_asistencia_curso,
                    'planificaciones': planif_count,
                    'bitacoras': bitacora_count,
                    'num_estudiantes': len(data['estudiantes']),
                    'bitacoras_con_tiempo': curso_bitacoras_con_tiempo,
                    'tiempo_promedio_bitacora': tiempo_promedio_curso_str,
                    'actividades_con_tiempo': curso_actividades_con_tiempo,
                    'tiempo_promedio_actividad': tiempo_promedio_actividad_str,
                    'planificaciones_con_tiempo': curso_planificaciones_con_tiempo,
                    'tiempo_promedio_planificacion': tiempo_promedio_planificacion_str,
                })

        context['periodo_actual'] = periodo_actual
        context['cursos_con_clases'] = cursos_con_clases
        context['kpi'] = kpi
        context['notificaciones'] = Notificacion.objects.filter(
            Q(audiencia=Notificacion.TargetAudiencia.TODOS) |
            Q(audiencia=Notificacion.TargetAudiencia.MAESTROS)
        ).order_by('-fecha_envio')[:5]
        return context


class ActividadCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Actividad
    form_class = ActividadForm
    template_name = 'portal/actividad_form.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        maestro = request.user.get_maestro_profile()
        if not maestro or self.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para crear actividades en esta clase.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.clase = self.clase
        inicio_str = self.request.session.pop('actividad_inicio', None)
        if inicio_str:
            try:
                form.instance.fecha_inicio_calculo = timezone.datetime.fromisoformat(inicio_str)
            except (ValueError, TypeError):
                pass
        form.instance.fecha_fin_calculo = timezone.now()
        messages.success(self.request, f"Actividad '{form.instance.titulo}' creada exitosamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Nueva Actividad - {self.clase.curso.nombre}"
        self.request.session['actividad_inicio'] = timezone.now().isoformat()
        return context

    def get_success_url(self):
        return reverse('portal_maestro')


class ActividadDetailView(LoginRequiredMixin, DetailView):
    model = Actividad
    template_name = 'portal/actividad_detail.html'
    context_object_name = 'actividad'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        actividad = self.get_object()

        estudiante = None
        if self.request.user.user_type == User.UserType.ESTUDIANTE:
            estudiante = self.request.user.get_estudiante_profile()

        entrega_existente = None
        if estudiante:
            try:
                entrega_existente = Entrega.objects.get(
                    actividad=actividad,
                    estudiante=estudiante
                )
            except Entrega.DoesNotExist:
                pass

        context['entrega_existente'] = entrega_existente

        if estudiante:
            if entrega_existente:
                context['form'] = EntregaForm(instance=entrega_existente)
            else:
                context['form'] = EntregaForm()

        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        actividad = self.object

        if request.user.user_type != User.UserType.ESTUDIANTE:
            return HttpResponseForbidden("Solo los estudiantes pueden entregar actividades.")

        estudiante = request.user.get_estudiante_profile()
        if not estudiante:
            return HttpResponseForbidden("No tienes un perfil de estudiante.")

        entrega, created = Entrega.objects.get_or_create(
            actividad=actividad,
            estudiante=estudiante,
            defaults={'fecha_entrega': timezone.now()}
        )

        form = EntregaForm(request.POST, request.FILES, instance=entrega)
        if form.is_valid():
            form.save()
            messages.success(request, "Tu entrega ha sido guardada exitosamente.")
            return redirect('actividad_detail', pk=actividad.pk)
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return self.render_to_response(context)


class ActividadEntregasView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Actividad
    template_name = 'portal/actividad_entregas.html'
    context_object_name = 'actividad'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        actividad = self.get_object()
        context['entregas'] = Entrega.objects.filter(
            actividad=actividad
        ).select_related('estudiante__user').order_by('estudiante__user__last_name')
        return context


class ActividadUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Actividad
    form_class = ActividadForm
    template_name = 'portal/actividad_form.html'
    context_object_name = 'actividad'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        maestro = request.user.get_maestro_profile()
        if not maestro or self.object.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para editar esta actividad.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.fecha_fin_calculo = timezone.now()
        messages.success(self.request, "Actividad actualizada exitosamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editar Actividad - {self.object.titulo}"
        return context

    def get_success_url(self):
        return reverse('portal_maestro')


class ActividadDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Actividad
    template_name = 'portal/actividad_confirm_delete.html'
    context_object_name = 'actividad'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        maestro = request.user.get_maestro_profile()
        if not maestro or self.object.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para eliminar esta actividad.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Actividad '{self.object.titulo}' eliminada.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('portal_maestro')


class CalificarEntregaView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Entrega
    form_class = CalificacionForm
    template_name = 'portal/calificar_entrega_form.html'
    context_object_name = 'entrega'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        maestro = request.user.get_maestro_profile()
        if not maestro or self.object.actividad.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para calificar esta entrega.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Calificación guardada exitosamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('actividad_entregas', kwargs={'pk': self.object.actividad.pk})


class EntregaUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Entrega
    form_class = EntregaEditForm
    template_name = 'portal/entrega_form.html'
    context_object_name = 'entrega'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        maestro = request.user.get_maestro_profile()
        if not maestro or self.object.actividad.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para editar esta entrega.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        maestro = self.request.user.get_maestro_profile()
        kwargs['maestro'] = maestro
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Entrega actualizada exitosamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('actividad_entregas', kwargs={'pk': self.object.actividad.pk})


class EntregaDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Entrega
    template_name = 'portal/entrega_confirm_delete.html'
    context_object_name = 'entrega'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        maestro = request.user.get_maestro_profile()
        if not maestro or self.object.actividad.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para eliminar esta entrega.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, "Entrega eliminada exitosamente.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('actividad_entregas', kwargs={'pk': self.object.actividad.pk})


class PortalAdminView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'portal/portal_admin.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.ADMIN

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notificacion_form'] = NotificacionForm()
        return context

    def post(self, request, *args, **kwargs):
        form = NotificacionForm(request.POST)
        if form.is_valid():
            notificacion = form.save(commit=False)
            notificacion.autor = request.user
            notificacion.save()
            messages.success(request, "Notificación enviada exitosamente.")
            return redirect('portal_admin')
        else:
            context = self.get_context_data(**kwargs)
            context['notificacion_form'] = form
            return self.render_to_response(context)


class NoticiaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Noticia
    form_class = NoticiaForm
    template_name = 'portal/noticia_form.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.ADMIN

    def form_valid(self, form):
        form.instance.autor = self.request.user
        messages.success(self.request, "Noticia publicada exitosamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Publicar Nueva Noticia"
        return context

    def get_success_url(self):
        return reverse('portal_admin')


class NoticiaUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Noticia
    form_class = NoticiaForm
    template_name = 'portal/noticia_form.html'
    context_object_name = 'noticia'

    def test_func(self):
        return self.request.user.user_type == User.UserType.ADMIN

    def form_valid(self, form):
        messages.success(self.request, "Noticia actualizada exitosamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editar Noticia: {self.object.titulo}"
        return context

    def get_success_url(self):
        return reverse('portal_admin')


class NoticiaDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Noticia
    template_name = 'portal/noticia_confirm_delete.html'
    context_object_name = 'noticia'

    def test_func(self):
        return self.request.user.user_type == User.UserType.ADMIN

    def form_valid(self, form):
        messages.success(self.request, f"Noticia '{self.object.titulo}' eliminada.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('portal_admin')


AsistenciaFormSet = formset_factory(AsistenciaForm, extra=0)


class TomarAsistenciaView(LoginRequiredMixin, UserPassesTestMixin, View):
    template_name = 'portal/tomar_asistencia.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def get_clase(self):
        return get_object_or_404(
            Clase.objects.select_related('curso', 'maestro__user'),
            pk=self.kwargs['clase_pk']
        )

    def verificar_maestro(self, clase):
        maestro = self.request.user.get_maestro_profile()
        if not maestro or clase.maestro != maestro:
            return False
        return True

    def get_fecha(self):
        if 'fecha' in self.kwargs:
            try:
                return datetime.strptime(self.kwargs['fecha'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                pass
        return timezone.now().date()

    def get(self, request, *args, **kwargs):
        clase = self.get_clase()
        if not self.verificar_maestro(clase):
            return HttpResponseForbidden("No tienes permiso para tomar asistencia en esta clase.")

        fecha_seleccionada = self.get_fecha()
        return self.render_asistencia(request, clase, fecha_seleccionada)

    def post(self, request, *args, **kwargs):
        clase = self.get_clase()
        if not self.verificar_maestro(clase):
            return HttpResponseForbidden("No tienes permiso para tomar asistencia en esta clase.")

        fecha_seleccionada = self.get_fecha()
        formset = AsistenciaFormSet(request.POST)

        if formset.is_valid():
            with transaction.atomic():
                for form in formset:
                    estudiante_id = form.cleaned_data['estudiante_id']
                    estado = form.cleaned_data['estado']

                    if not clase.estudiantes.filter(pk=estudiante_id).exists():
                        continue

                    AsistenciaClase.objects.update_or_create(
                        clase=clase,
                        estudiante_id=estudiante_id,
                        fecha=fecha_seleccionada,
                        defaults={'estado': estado}
                    )

            messages.success(request, f"Asistencia guardada para el {fecha_seleccionada.strftime('%d/%m/%Y')}.")
        else:
            messages.error(request, "Error al guardar la asistencia. Verifica los datos.")

        if 'fecha' in self.kwargs:
            return redirect('tomar_asistencia_fecha', clase_pk=clase.pk, fecha=fecha_seleccionada.strftime('%Y-%m-%d'))
        return redirect('tomar_asistencia', clase_pk=clase.pk)

    def render_asistencia(self, request, clase, fecha_seleccionada):
        estudiantes = clase.estudiantes.select_related('user').order_by('user__last_name', 'user__first_name')

        initial_data = []
        for estudiante in estudiantes:
            try:
                asistencia = AsistenciaClase.objects.get(
                    clase=clase,
                    estudiante=estudiante,
                    fecha=fecha_seleccionada
                )
                estado_inicial = asistencia.estado
            except AsistenciaClase.DoesNotExist:
                estado_inicial = AsistenciaClase.EstadoAsistencia.PRESENTE

            initial_data.append({
                'estudiante_id': estudiante.pk,
                'estado': estado_inicial,
            })

        formset = AsistenciaFormSet(initial=initial_data)

        alumnos_con_form = []
        for estudiante, form in zip(estudiantes, formset):
            alumnos_con_form.append((
                {
                    'nombre': estudiante.user.get_full_name(),
                    'id': estudiante.pk,
                },
                form
            ))

        fecha_anterior = fecha_seleccionada - timedelta(days=1)
        fecha_siguiente = fecha_seleccionada + timedelta(days=1)
        es_hoy = (fecha_seleccionada == timezone.now().date())

        context = {
            'clase': clase,
            'fecha_seleccionada': fecha_seleccionada,
            'fecha_anterior': fecha_anterior,
            'fecha_siguiente': fecha_siguiente,
            'es_hoy': es_hoy,
            'formset': formset,
            'alumnos_con_form': alumnos_con_form,
        }

        return render(request, self.template_name, context)


class PlanificacionListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Planificacion
    template_name = 'portal/planificacion_list.html'
    context_object_name = 'planificaciones'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.clase = get_object_or_404(
            Clase.objects.select_related('curso'),
            pk=self.kwargs['clase_pk']
        )
        maestro = request.user.get_maestro_profile()
        if not maestro or self.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para ver esta planificación.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Planificacion.objects.filter(
            clase=self.clase
        ).prefetch_related('competencias').order_by('-fecha_inicio')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clase'] = self.clase
        return context


class PlanificacionCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Planificacion
    form_class = PlanificacionForm
    template_name = 'portal/planificacion_form.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.clase = get_object_or_404(
            Clase.objects.select_related('curso'),
            pk=self.kwargs['clase_pk']
        )
        maestro = request.user.get_maestro_profile()
        if not maestro or self.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para crear planificaciones en esta clase.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['clase'] = self.clase
        return kwargs

    def form_valid(self, form):
        form.instance.clase = self.clase
        inicio_str = self.request.session.pop('planificacion_inicio', None)
        if inicio_str:
            try:
                form.instance.fecha_inicio_calculo = timezone.datetime.fromisoformat(inicio_str)
            except (ValueError, TypeError):
                pass
        form.instance.fecha_fin_calculo = timezone.now()
        messages.success(self.request, "Planificación creada exitosamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Nueva Planificación - {self.clase.curso.nombre}"
        context['clase_pk'] = self.clase.pk
        self.request.session['planificacion_inicio'] = timezone.now().isoformat()
        return context

    def get_success_url(self):
        return reverse('planificacion_list', kwargs={'clase_pk': self.clase.pk})


class PlanificacionUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Planificacion
    form_class = PlanificacionForm
    template_name = 'portal/planificacion_form.html'
    context_object_name = 'planificacion'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        maestro = request.user.get_maestro_profile()
        if not maestro or self.object.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para editar esta planificación.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['clase'] = self.object.clase
        return kwargs

    def form_valid(self, form):
        form.instance.fecha_fin_calculo = timezone.now()
        messages.success(self.request, "Planificación actualizada exitosamente.")
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editar Planificación: {self.object.titulo}"
        context['clase_pk'] = self.object.clase.pk
        return context

    def get_success_url(self):
        return reverse('planificacion_list', kwargs={'clase_pk': self.object.clase.pk})


class PlanificacionDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Planificacion
    template_name = 'portal/planificacion_confirm_delete.html'

    def test_func(self):
        return self.request.user.user_type == User.UserType.MAESTRO

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        maestro = request.user.get_maestro_profile()
        if not maestro or self.object.clase.maestro != maestro:
            return HttpResponseForbidden("No tienes permiso para eliminar esta planificación.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, f"Planificación '{self.object.titulo}' eliminada.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('planificacion_list', kwargs={'clase_pk': self.object.clase.pk})


class PortalPadreView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'portal/portal_padre_seleccion.html'

    def test_func(self):
        return (self.request.user.user_type == User.UserType.PADRE and
                hasattr(self.request.user, 'padre_familia'))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        padre = self.request.user.padre_familia
        context['hijos'] = padre.hijos.select_related('user').all()
        return context


class PadreEstudianteDashboardView(LoginRequiredMixin, UserPassesTestMixin, PeriodoSeleccionadoMixin, TemplateView):
    template_name = 'portal/portal_estudiante_dashboard.html'

    def test_func(self):
        if self.request.user.user_type != User.UserType.PADRE:
            return False
        if not hasattr(self.request.user, 'padre_familia'):
            return False
        try:
            estudiante = Estudiante.objects.get(pk=self.kwargs['estudiante_pk'])
            padre = self.request.user.padre_familia
            return estudiante in padre.hijos.all()
        except Estudiante.DoesNotExist:
            return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        estudiante = get_object_or_404(
            Estudiante.objects.select_related('user'),
            pk=self.kwargs['estudiante_pk']
        )
        self.request.session['estudiante_seleccionado_pk'] = estudiante.pk

        periodo_actual = self.get_periodo_actual()
        clases_inscritas = []
        actividades = Actividad.objects.none()

        if periodo_actual:
            day_order = Case(
                When(dia_semana='LUN', then=Value(0)),
                When(dia_semana='MAR', then=Value(1)),
                When(dia_semana='MIE', then=Value(2)),
                When(dia_semana='JUE', then=Value(3)),
                When(dia_semana='VIE', then=Value(4)),
                When(dia_semana='SAB', then=Value(5)),
                output_field=IntegerField(),
            )
            clases_inscritas = Clase.objects.filter(
                estudiantes=estudiante,
                periodo=periodo_actual
            ).select_related('curso', 'maestro__user').order_by(day_order, 'hora_inicio')

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

        orden_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']
        horario_por_dia = OrderedDict()
        for dia in orden_dias:
            horario_por_dia[dia] = []
        for clase in clases_inscritas:
            dia_display = clase.get_dia_semana_display()
            horario_por_dia[dia_display].append(clase)

        actividades_por_curso = OrderedDict()
        for actividad in actividades:
            curso_nombre = actividad.clase.curso.nombre
            if curso_nombre not in actividades_por_curso:
                actividades_por_curso[curso_nombre] = []
            actividades_por_curso[curso_nombre].append(actividad)

        context['estudiante'] = estudiante
        context['clases_inscritas'] = clases_inscritas
        context['periodo_actual'] = periodo_actual
        context['actividades'] = actividades
        context['horario_por_dia'] = horario_por_dia
        context['actividades_por_curso'] = actividades_por_curso
        context['notificaciones'] = Notificacion.objects.filter(
            Q(audiencia=Notificacion.TargetAudiencia.TODOS) |
            Q(audiencia=Notificacion.TargetAudiencia.PADRES)
        ).order_by('-fecha_envio')[:5]
        return context


class PadreMisCalificacionesView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Entrega
    template_name = 'portal/mis_calificaciones.html'
    context_object_name = 'entregas'

    def test_func(self):
        if self.request.user.user_type != User.UserType.PADRE:
            return False
        try:
            estudiante_a_ver = Estudiante.objects.get(pk=self.kwargs['estudiante_pk'])
            padre_logueado = self.request.user.padre_familia
            return estudiante_a_ver in padre_logueado.hijos.all()
        except Estudiante.DoesNotExist:
            return False

    def get_queryset(self):
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
        context['es_padre'] = True
        context['estudiante'] = estudiante
        return context


class CalificacionesPeriodoView(LoginRequiredMixin, UserPassesTestMixin, PeriodoSeleccionadoMixin, TemplateView):
    template_name = 'portal/calificaciones_periodo.html'

    def test_func(self):
        return self.request.user.user_type in [User.UserType.ESTUDIANTE, User.UserType.PADRE]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.user_type == User.UserType.ESTUDIANTE:
            estudiante = self.request.user.get_estudiante_profile()
        else:
            estudiante_pk = self.request.session.get('estudiante_seleccionado_pk')
            if estudiante_pk:
                estudiante = get_object_or_404(Estudiante, pk=estudiante_pk)
            else:
                estudiante = None
            context['es_padre'] = True

        periodo = self.get_periodo_actual()

        if not periodo or not estudiante:
            context['titulo'] = "Boleta de Calificaciones (Sin datos)"
            context['reporte_notas'] = []
            context['periodo'] = None
            context['estudiante'] = estudiante
            return context

        calificaciones_finales = Entrega.objects.filter(
            estudiante=estudiante,
            actividad__clase__periodo=periodo,
            calificacion__isnull=False
        ).values(
            'actividad__clase__curso__nombre'
        ).annotate(
            promedio_final=Avg('calificacion')
        ).order_by('actividad__clase__curso__nombre')

        context['estudiante'] = estudiante
        context['periodo'] = periodo
        context['reporte_notas'] = calificaciones_finales
        context['titulo'] = f"Boleta de Calificaciones - {periodo.nombre}"
        return context


class CambiarPeriodoView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        periodo_id = request.POST.get('periodo_id')
        next_url = request.POST.get('next', 'home')

        if not periodo_id:
            return HttpResponseBadRequest("No se proporcionó un ID de periodo.")

        try:
            request.session['periodo_seleccionado_id'] = int(periodo_id)
        except ValueError:
            return HttpResponseBadRequest("ID de periodo inválido.")

        return redirect(next_url)
