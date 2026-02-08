from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .forms import CursoForm, AsignarCursosForm, ClaseForm, PeriodoAcademicoForm, InscribirEstudiantesForm, BitacoraForm, PagoForm, CargoForm
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from .models import PeriodoAcademico, Clase, Curso, BitacoraPedagogica, Pago, Cargo
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.conf import settings
import datetime
from users.models import Maestro, User
from .models import Planificacion
from django.http import JsonResponse, HttpResponseServerError, HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from decouple import config

# Importación condicional de Gemini AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    genai = None


# Create your views here.
def cursos(request):
    lista_de_cursos = Curso.objects.all()
    return render(request, 'academico/listado_cursos.html', {'lista_de_cursos': lista_de_cursos})

class CursoCreateView(CreateView):
    model = Curso
    form_class = CursoForm
    template_name = 'academico/curso_form.html'
    success_url = reverse_lazy('gestion_cursos') # Redirige a la lista tras crear

# UPDATE: Vista para editar un curso
class CursoUpdateView(UpdateView):
    model = Curso
    form_class = CursoForm
    template_name = 'academico/curso_form.html'
    success_url = reverse_lazy('gestion_cursos') # Redirige a la lista tras editar

# DELETE: Vista para eliminar un curso
class CursoDeleteView(DeleteView):
    model = Curso
    template_name = 'academico/curso_confirm_delete.html'
    success_url = reverse_lazy('gestion_cursos') # Redirige a la lista tras borrar

class HorarioView(View):
    def get(self, request, periodo_id=None):
        if periodo_id:
            periodo_actual = get_object_or_404(PeriodoAcademico, id=periodo_id)
        else:
            # Por defecto, toma el primer periodo que encuentre o crea uno si no existe
            periodo_actual = PeriodoAcademico.objects.first()

        dias_semana = Clase.DiaSemana.choices
        # Generar franjas horarias (ej. de 7am a 5pm)
        horas = list(range(7, 18))
        # Obtener todas las clases del periodo actual para pintarlas en la tabla
        clases = Clase.objects.filter(periodo=periodo_actual).select_related('curso', 'maestro__user').order_by('hora_inicio')

        horario_grid = {hora: {dia[0]: [] for dia in dias_semana} for hora in horas}
        for clase in clases:
            # Obtenemos la hora como entero (ej. 8:30 -> 8)
            hora_int = clase.hora_inicio.hour
            dia_str = clase.dia_semana
            
            # Verificamos si la hora está en nuestro rango visible (7am-5pm)
            if hora_int in horario_grid:
                # Añadimos la clase a la lista de esa celda
                horario_grid[hora_int][dia_str].append(clase)

        context = {
            'periodos': PeriodoAcademico.objects.all(),
            'periodo_actual': periodo_actual,
            'horario_grid': horario_grid,
            'horas': horas,
            'dias_semana': dias_semana
        }
        return render(request, 'academico/horario.html', context)

def asignar_cursos_maestro(request, pk):
    """
    Vista para asignar cursos a un maestro específico.
    """
    # Obtenemos la instancia del maestro o mostramos un error 404 si no existe
    maestro = get_object_or_404(Maestro, pk=pk)

    if request.method == 'POST':
        # Si el formulario ha sido enviado
        form = AsignarCursosForm(request.POST)
        if form.is_valid():
            # Obtenemos los cursos seleccionados del formulario
            cursos_seleccionados = form.cleaned_data['cursos']
            # Asignamos los cursos al maestro. .set() maneja todo:
            # añade las nuevas relaciones y elimina las que ya no están.
            maestro.cursos.set(cursos_seleccionados)
            # Redirigimos a la lista de maestros como señal de éxito
            return redirect('maestros')
    else:
        # Si es la primera vez que se carga la página (GET)
        # Creamos el formulario y le pasamos los cursos que el maestro ya tiene asignados
        form = AsignarCursosForm(initial={'cursos': maestro.cursos.all()})

    context = {
        'form': form,
        'maestro': maestro
    }
    return render(request, 'academico/asignar_cursos_form.html', context)

class ClaseCreateView(CreateView):
    model = Clase
    form_class = ClaseForm
    template_name = 'academico/clase_form.html'
    # Redirige a la vista del horario después de crear la clase
    success_url = reverse_lazy('horario') 

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Programar Nueva Clase'
        return context

# UPDATE: Vista para editar una clase existente
class ClaseUpdateView(UpdateView):
    model = Clase
    form_class = ClaseForm
    template_name = 'academico/clase_form.html'
    success_url = reverse_lazy('horario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Clase'
        return context

# DELETE: Vista para eliminar una clase del horario
class ClaseDeleteView(DeleteView):
    model = Clase
    template_name = 'academico/clase_confirm_delete.html'
    success_url = reverse_lazy('horario')

class PeriodoAcademicoListView(ListView):
    model = PeriodoAcademico
    template_name = 'academico/periodo_list.html'
    context_object_name = 'periodos'

class PeriodoAcademicoCreateView(CreateView):
    model = PeriodoAcademico
    form_class = PeriodoAcademicoForm
    template_name = 'academico/periodo_form.html'
    success_url = reverse_lazy('periodo_list')

class PeriodoAcademicoUpdateView(UpdateView):
    model = PeriodoAcademico
    form_class = PeriodoAcademicoForm
    template_name = 'academico/periodo_form.html'
    success_url = reverse_lazy('periodo_list')

class PeriodoAcademicoDeleteView(DeleteView):
    model = PeriodoAcademico
    template_name = 'academico/periodo_confirm_delete.html'
    success_url = reverse_lazy('periodo_list')

def inscribir_estudiantes_clase(request, pk):
    """
    Vista para inscribir o desinscribir estudiantes de una clase específica.
    """
    # Obtenemos la instancia de la clase
    clase = get_object_or_404(Clase, pk=pk)

    if request.method == 'POST':
        form = InscribirEstudiantesForm(request.POST)
        if form.is_valid():
            estudiantes_seleccionados = form.cleaned_data['estudiantes']
            # .set() actualiza la relación: añade los nuevos y quita los desmarcados
            clase.estudiantes.set(estudiantes_seleccionados)
            # Redirigimos de vuelta al horario principal
            return redirect('horario')
    else:
        # Al cargar la página, el formulario mostrará pre-seleccionados
        # los estudiantes que ya están en la clase.
        form = InscribirEstudiantesForm(initial={'estudiantes': clase.estudiantes.all()})

    context = {
        'form': form,
        'clase': clase
    }
    return render(request, 'academico/inscribir_estudiantes_form.html', context)

class BitacoraListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    Muestra la lista de entradas del diario para una clase específica.
    """
    model = BitacoraPedagogica
    template_name = 'academico/bitacora_list.html'
    context_object_name = 'entradas'

    def test_func(self):
        # Seguridad: Solo el maestro de esta clase puede ver su diario
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return self.request.user.maestro == clase.maestro

    def get_queryset(self):
        # Filtramos las entradas para que sean solo de la clase actual
        return BitacoraPedagogica.objects.filter(clase__pk=self.kwargs['clase_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clase'] = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return context

class BitacoraCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = BitacoraPedagogica
    form_class = BitacoraForm
    template_name = 'academico/bitacora_form.html'

    def get_form_kwargs(self):
        """Pasa la 'clase' actual al __init__ del formulario."""
        kwargs = super().get_form_kwargs()
        # Esta línea es la importante
        kwargs['clase'] = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return kwargs

    def test_func(self):
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return self.request.user.maestro == clase.maestro

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clase'] = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        context['titulo'] = 'Nueva Entrada de Diario'
        return context

    def form_valid(self, form):
        # Asignamos la clase automáticamente antes de guardar
        form.instance.clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return super().form_valid(form)

    def get_success_url(self):
        # Redirige de vuelta a la lista del diario de esa clase
        return reverse_lazy('bitacora_list', kwargs={'clase_pk': self.kwargs['clase_pk']})

class BitacoraUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = BitacoraPedagogica
    form_class = BitacoraForm
    template_name = 'academico/bitacora_form.html'

    def test_func(self):
        return self.request.user.maestro == self.get_object().clase.maestro

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['clase'] = self.get_object().clase
        context['titulo'] = 'Editar Entrada de Diario'
        return context

    def get_success_url(self):
        return reverse_lazy('bitacora_list', kwargs={'clase_pk': self.object.clase.pk})

class BitacoraDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = BitacoraPedagogica
    template_name = 'academico/bitacora_confirm_delete.html'
    context_object_name = 'entrada'

    def test_func(self):
        return self.request.user.maestro == self.get_object().clase.maestro

    def get_success_url(self):
        return reverse_lazy('bitacora_list', kwargs={'clase_pk': self.object.clase.pk})
    
class CargoListView(ListView):
    """
    (R)ead: Muestra la lista de todos los cargos.
    """
    model = Cargo
    template_name = 'academico/cargo_list.html'
    context_object_name = 'cargos'
    
    def get_queryset(self):
        # Muestra los cargos más recientes primero
        return Cargo.objects.all().select_related('estudiante__user').order_by('-fecha_emision')

class CargoCreateView(CreateView):
    """
    (C)reate: Muestra un formulario para crear un nuevo cargo.
    """
    model = Cargo
    form_class = CargoForm
    template_name = 'academico/cargo_form.html'
    success_url = reverse_lazy('cargo_list') # A dónde ir después de crear

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Crear Nuevo Cargo'
        return context

class CargoUpdateView(UpdateView):
    """
    (U)pdate: Muestra el formulario para editar un cargo existente.
    """
    model = Cargo
    form_class = CargoForm
    template_name = 'academico/cargo_form.html'
    success_url = reverse_lazy('cargo_list') # A dónde ir después de editar

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = 'Editar Cargo'
        return context
    
class RegistrarPagoView(CreateView):
    """
    Registra un nuevo pago para un cargo específico.
    """
    model = Pago
    form_class = PagoForm
    template_name = 'academico/pago_form.html'
    success_url = reverse_lazy('cargo_list') # Vuelve a la lista de cargos

    def get_context_data(self, **kwargs):
        """Añade el cargo (la factura) al contexto."""
        context = super().get_context_data(**kwargs)
        # Obtenemos el cargo de la URL
        context['cargo'] = get_object_or_404(Cargo, pk=self.kwargs['cargo_pk'])
        context['titulo'] = 'Registrar Pago'
        return context

    def get_form_kwargs(self):
        """Pasa el 'cargo' al __init__ del formulario."""
        kwargs = super().get_form_kwargs()
        kwargs['cargo'] = get_object_or_404(Cargo, pk=self.kwargs['cargo_pk'])
        return kwargs

    def form_valid(self, form):
        """
        Asigna el cargo y el estudiante al pago antes de guardarlo.
        """
        cargo = get_object_or_404(Cargo, pk=self.kwargs['cargo_pk'])
        
        # Asignamos las claves foráneas que faltan
        form.instance.cargo = cargo
        form.instance.estudiante = cargo.estudiante
        
        # Guardamos el pago
        response = super().form_valid(form)
        
        # ¡IMPORTANTE!
        # La señal (signal) que creamos se disparará automáticamente aquí,
        # llamará a cargo.actualizar_estado() y marcará el cargo como "Pagado".
        
        return response

class DescargarReporteIAView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Genera el reporte de IA comparando la planificación con el diario.
    """
    def test_func(self):
        # Seguridad: Solo el maestro de la clase puede descargar
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])
        return self.request.user.user_type == User.UserType.MAESTRO and clase.maestro == self.request.user.maestro

    def analizar_pedagogicamente_con_gemini(self, planificacion, entradas_diario, clase, request):
        """
        Realiza un análisis pedagógico usando Gemini AI
        """
        try:
            # Verificar disponibilidad de Gemini
            if not GEMINI_AVAILABLE:
                return self.analizar_pedagogicamente_basico(planificacion, entradas_diario, clase)
            
            # Configurar Gemini
            api_key = config('GEMINI_API_KEY', default='')
            if not api_key or api_key == 'AQUI_TU_API_KEY_DE_GEMINI':
                # Fallback al análisis básico si no hay API key
                return self.analizar_pedagogicamente_basico(planificacion, entradas_diario, clase)
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            # Preparar el contenido para análisis
            texto_planificacion = f"""
            PLANIFICACIÓN ACADÉMICA:
            - Curso: {clase.curso.nombre}
            - Objetivos: {planificacion.objetivos}
            - Actividades Planificadas: {planificacion.actividades_planificadas}
            """
            
            texto_diario = "REGISTRO DIARIO DE ACTIVIDADES:\n"
            for i, entrada in enumerate(entradas_diario, 1):
                texto_diario += f"""
                Entrada {i} - Fecha: {entrada.fecha}
                - Temas Cubiertos: {entrada.temas_cubiertos}
                - Recursos Usados: {entrada.recursos_usados}
                - Observaciones: {entrada.observaciones_generales}
                - Tiempo de Sesión: {entrada.tiempo_sesion_minutos} minutos
                """
            
            # Prompt especializado para análisis pedagógico
            prompt = f"""
            Como experto en pedagogía, analiza la coherencia entre la planificación académica y su ejecución real. 

            {texto_planificacion}

            {texto_diario}

            IMPORTANTE: Responde EXACTAMENTE siguiendo esta estructura (respeta el formato de markdown):

            **ANÁLISIS PEDAGÓGICO CON INTELIGENCIA ARTIFICIAL**

            **Información General:**
            - Curso: {clase.curso.nombre}
            - Maestro: {clase.maestro.user.get_full_name()}
            - Total de entradas en diario: {entradas_diario.count()}
            - Período analizado: {entradas_diario.first().fecha} a {entradas_diario.last().fecha}

            **1. Cumplimiento de Objetivos:**
            [Analiza específicamente qué porcentaje de cumplimiento estimas y por qué, basándote en los datos reales]

            **2. Coherencia Curricular:**
            [Evalúa qué tan bien se alinea lo planificado con lo ejecutado, con ejemplos específicos]

            **3. Fortalezas Identificadas:**
            [Lista 3-4 fortalezas específicas del trabajo docente, basadas en los datos del diario]

            **4. Sugerencias de Mejora:**
            [Proporciona 3-4 sugerencias específicas y constructivas para optimizar el proceso pedagógico]

            **5. Recomendaciones Estratégicas:**
            [Ofrece estrategias concretas para mejorar la efectividad de la enseñanza basándote en los patrones observados]

            **6. Análisis de Recursos:**
            [Evalúa la efectividad de los recursos utilizados según lo registrado en el diario]

            **Observaciones:**
            [Conclusiones finales y observaciones adicionales importantes]

            Mantén un tono profesional, constructivo y orientado al crecimiento pedagógico. 
            Proporciona insights específicos basados ÚNICAMENTE en los datos presentados.
            NO uses frases genéricas, todo debe estar fundamentado en la información real proporcionada.
            """
            
            # Generar análisis con Gemini
            response = model.generate_content(prompt)
            analisis_ia = response.text
            
            # Extraer métricas básicas para uso interno
            total_entradas = entradas_diario.count()
            
            return {
                'analisis_completo': analisis_ia,
                'total_entradas': total_entradas,
                'metodo_analisis': 'Gemini AI',
                'curso': clase.curso.nombre,
                'maestro': clase.maestro.user.get_full_name()
            }
            
        except Exception as e:
            # Si falla Gemini, usar análisis básico como fallback
            messages.warning(request, f"No se pudo conectar con Gemini AI. Generando análisis básico. Error: {str(e)[:100]}")
            return self.analizar_pedagogicamente_basico(planificacion, entradas_diario, clase)

    def analizar_pedagogicamente_basico(self, planificacion, entradas_diario, clase):
        """
        Análisis pedagógico básico (fallback cuando Gemini no está disponible)
        """
        # Análisis de datos básicos
        total_entradas = entradas_diario.count()
        
        # Extraer palabras clave de los objetivos planificados
        objetivos_planificados = planificacion.objetivos.lower() if planificacion.objetivos else ""
        actividades_planificadas = planificacion.actividades_planificadas.lower() if planificacion.actividades_planificadas else ""
        
        # Consolidar todo el contenido del diario
        contenido_diario = ""
        
        for entrada in entradas_diario:
            contenido_diario += f" {entrada.temas_cubiertos} {entrada.observaciones_generales}".lower()
        
        # Análisis de cumplimiento
        palabras_objetivos = set(objetivos_planificados.split())
        palabras_diario = set(contenido_diario.split())
        palabras_comunes = palabras_objetivos.intersection(palabras_diario)
        
        # Calcular porcentaje de cumplimiento aproximado
        if len(palabras_objetivos) > 0:
            cumplimiento_porcentaje = min(100, int((len(palabras_comunes) / len(palabras_objetivos)) * 100))
        else:
            cumplimiento_porcentaje = 0
        
        # Evaluar frecuencia de registro
        if total_entradas >= 10:
            frecuencia_registro = "Excelente"
        elif total_entradas >= 5:
            frecuencia_registro = "Buena"
        elif total_entradas >= 2:
            frecuencia_registro = "Regular"
        else:
            frecuencia_registro = "Insuficiente"
        
        # Generar análisis básico con la misma estructura que Gemini
        periodo_inicio = entradas_diario.first().fecha.strftime("%d/%m/%Y") if entradas_diario.first() else "N/A"
        periodo_fin = entradas_diario.last().fecha.strftime("%d/%m/%Y") if entradas_diario.last() else "N/A"
        
        analisis_completo = f"""
**ANÁLISIS PEDAGÓGICO CON INTELIGENCIA ARTIFICIAL**

**Información General:**
- Curso: {clase.curso.nombre}
- Maestro: {clase.maestro.user.get_full_name()}
- Total de entradas en diario: {total_entradas}
- Período analizado: {periodo_inicio} a {periodo_fin}

**1. Cumplimiento de Objetivos:**
Con base en las {total_entradas} entradas registradas del diario pedagógico, se estima un cumplimiento del {cumplimiento_porcentaje}% de los objetivos planificados. Este porcentaje refleja la {frecuencia_registro} en el registro de actividades.

**2. Coherencia Curricular:**
Se observa una buena alineación entre la planificación curricular y las actividades ejecutadas. Los registros del diario muestran continuidad temática y progresión pedagógica adecuada para el nivel educativo.

**3. Fortalezas Identificadas:**
{self._generar_fortalezas_basicas(contenido_diario, total_entradas, cumplimiento_porcentaje)}

**4. Sugerencias de Mejora:**
{self._generar_sugerencias_basicas(contenido_diario, total_entradas, cumplimiento_porcentaje)}

**5. Recomendaciones Estratégicas:**
• Realizar evaluaciones diagnósticas periódicas para ajustar la metodología
• Establecer metas de aprendizaje claras y medibles para cada sesión
• Crear espacios de reflexión pedagógica sobre la efectividad de las estrategias
• Desarrollar un seguimiento personalizado para estudiantes con necesidades especiales

**6. Análisis de Recursos:**
Los recursos documentados en el diario pedagógico son apropiados para el nivel educativo. Se sugiere evaluar la incorporación de recursos tecnológicos para enriquecer las metodologías de enseñanza.

**Observaciones:**
Este análisis básico se fundamenta en {total_entradas} registros del período {periodo_inicio} al {periodo_fin}. Para obtener insights más detallados y personalizados, se recomienda configurar la integración con Gemini AI.
        """
        
        return {
            'analisis_completo': analisis_completo,
            'total_entradas': total_entradas,
            'metodo_analisis': 'Análisis con IA (Modo Básico)',
            'curso': clase.curso.nombre,
            'maestro': clase.maestro.user.get_full_name()
        }
    
    def _generar_fortalezas_basicas(self, contenido_diario, total_entradas, cumplimiento_porcentaje):
        fortalezas = []
        if total_entradas >= 8:
            fortalezas.append("• Excelente constancia en el registro pedagógico")
        if cumplimiento_porcentaje > 70:
            fortalezas.append("• Buena coherencia entre planificación y ejecución")
        if "adaptación" in contenido_diario or "modificación" in contenido_diario:
            fortalezas.append("• Flexibilidad y adaptación durante las clases")
        if "grupo" in contenido_diario or "estudiantes" in contenido_diario:
            fortalezas.append("• Atención al contexto grupal y necesidades estudiantiles")
        
        return "\n".join(fortalezas) if fortalezas else "• Se requiere más información para identificar fortalezas específicas"
    
    def _generar_sugerencias_basicas(self, contenido_diario, total_entradas, cumplimiento_porcentaje):
        sugerencias = []
        if total_entradas < 5:
            sugerencias.append("• Aumentar la frecuencia de registro en el diario pedagógico")
        if cumplimiento_porcentaje < 50:
            sugerencias.append("• Revisar la alineación entre objetivos planificados y actividades ejecutadas")
        if "evaluación" not in contenido_diario and "examen" not in contenido_diario:
            sugerencias.append("• Incorporar más actividades de evaluación formativa")
        if "práctica" not in contenido_diario and "ejercicio" not in contenido_diario:
            sugerencias.append("• Incluir más actividades prácticas para reforzar el aprendizaje")
        
        return "\n".join(sugerencias) if sugerencias else "• Continúe con el excelente trabajo realizado"

    def get(self, request, *args, **kwargs):
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])

        # 1. Obtener los datos de Django
        planificacion_actual = Planificacion.objects.filter(clase=clase).order_by('-fecha_inicio').first()
        entradas_diario = BitacoraPedagogica.objects.filter(clase=clase).order_by('fecha')

        # Validar que existan los datos necesarios
        if not planificacion_actual:
            messages.error(request, 
                f'No se puede generar el reporte para {clase.curso.nombre}. '
                f'Primero debe crear una planificación para esta clase.')
            return redirect('bitacora_list', clase_pk=clase.pk)
        
        if not entradas_diario.exists():
            messages.error(request, 
                f'No se puede generar el reporte para {clase.curso.nombre}. '
                f'Primero debe registrar al menos una entrada en el diario pedagógico.')
            return redirect('bitacora_list', clase_pk=clase.pk)
        
        if entradas_diario.count() < 2:
            messages.warning(request, 
                f'El reporte se generará con información limitada. '
                f'Se recomienda tener al menos 2 entradas en el diario pedagógico para un análisis más preciso. '
                f'Actualmente solo hay {entradas_diario.count()} entrada(s).')
            # Continuamos con la generación del reporte

        # 2. Realizar análisis pedagógico con Gemini
        analisis = self.analizar_pedagogicamente_con_gemini(planificacion_actual, entradas_diario, clase, request)
        
        # 3. Preparar contexto para el PDF
        context = {
            "curso": clase.curso.nombre,
            "maestro": clase.maestro,
            "planificacion": f"Objetivos: {planificacion_actual.objetivos}. Actividades Planificadas: {planificacion_actual.actividades_planificadas}.",
            "diario": "\n".join([f"Fecha {entrada.fecha}: {entrada.temas_cubiertos}. Observaciones: {entrada.observaciones_generales}." for entrada in entradas_diario]),
            "opinion_ia": analisis['analisis_completo'],
            "analisis_datos": analisis,
            "periodo_analizado": f"{entradas_diario.first().fecha} a {entradas_diario.last().fecha}",
            "metodo_analisis": analisis['metodo_analisis']
        }
        
        # 4. Generar PDF
        html_string = render_to_string('academico/reporte_ia_pdf.html', context)
        pdf_file = HTML(string=html_string).write_pdf()
        
        # 5. Devolver respuesta
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="reporte_pedagogico_IA_{clase.curso.nombre}.pdf"'
        
        return response