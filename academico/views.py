from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .forms import CursoForm, AsignarCursosForm, ClaseForm, PeriodoAcademicoForm, InscribirEstudiantesForm, BitacoraForm, PagoForm, CargoForm
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from .models import PeriodoAcademico, Clase, Curso, BitacoraPedagogica, Pago, Cargo
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
import datetime
from users.models import Maestro, User
from .models import Planificacion
import requests
from django.http import JsonResponse, HttpResponseServerError, HttpResponse
from django.template.loader import render_to_string # 👈 Importa esto
from weasyprint import HTML # 👈 Importa WeasyPrint


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
        horas = [datetime.time(h) for h in range(7, 18)] 
        
        # Obtener todas las clases del periodo actual para pintarlas en la tabla
        clases = Clase.objects.filter(periodo=periodo_actual).select_related('curso', 'maestro__user')
        
        horario = {}
        for hora in horas:
            horario[hora] = {dia[0]: None for dia in dias_semana}

        for clase in clases:
            # Simplificación: Asume que la clase empieza en una hora en punto.
            # Una lógica más compleja manejaría bloques de más de 1 hora.
            if clase.hora_inicio in horario:
                horario[clase.hora_inicio][clase.dia_semana] = clase

        context = {
            'periodos': PeriodoAcademico.objects.all(),
            'periodo_actual': periodo_actual,
            'horario': horario,
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

    def get(self, request, *args, **kwargs):
        clase = get_object_or_404(Clase, pk=self.kwargs['clase_pk'])

        # 1. Obtener los datos de Django
        # (Aquí puedes filtrar por fechas, pero por ahora tomamos el primero y todos)
        planificacion_actual = Planificacion.objects.filter(clase=clase).order_by('-fecha_inicio').first()
        entradas_diario = BitacoraPedagogica.objects.filter(clase=clase).order_by('fecha')

        if not planificacion_actual or not entradas_diario.exists():
            return JsonResponse({"error": "No hay suficientes datos (planificación o diario) para generar un reporte."}, status=404)

        # 2. Convertir los datos a texto simple para la IA
        texto_plan = f"Objetivos: {planificacion_actual.objetivos}. Actividades Planificadas: {planificacion_actual.actividades_planificadas}."
        
        texto_diario = ""
        for entrada in entradas_diario:
            texto_diario += f"Fecha {entrada.fecha}: {entrada.temas_cubiertos}. Observaciones: {entrada.observaciones_generales}.\n"
        
        # 3. Preparar el JSON para n8n
        json_para_n8n = {
            "plan": texto_plan,
            "diario": texto_diario,
            "curso": clase.curso.nombre
        }

        # 4. Llamar al Webhook de n8n
        # ¡IMPORTANTE! Cambia esta URL por la URL de tu webhook de n8n
        # y usa el nombre del servicio de Docker, no 'localhost'.
        webhook_url = "http://n8n_ia:5678/webhook-test/d545ed76-0dd8-49e7-b686-dea2598465bc"
        
        try:
            response = requests.post(webhook_url, json=json_para_n8n, timeout=15)
            response.raise_for_status() # Lanza un error si n8n falla
            print(response.text)
            
            opinion_ia = response.text
            
            # 2. (Opcional) Limpiamos el texto que viene de la IA
            if opinion_ia.startswith("**OPINIÓN:**"):
                opinion_ia = opinion_ia.replace("**OPINIÓN:**", "").strip()
        except requests.exceptions.ConnectionError:
            return HttpResponseServerError("Error: No se pudo conectar al servicio de n8n. ¿Está encendido?")
        except requests.exceptions.RequestException as e:
            return HttpResponseServerError(f"Error al llamar a la IA: {e}")

        # 5. Devolver la respuesta (POR AHORA)
        # En el futuro, aquí generarías el PDF con estos datos.
        context = {
            "curso": clase.curso.nombre,
            "maestro": clase.maestro,
            "planificacion": texto_plan,
            "diario": texto_diario,
            "opinion_ia": opinion_ia
        }
        
        # Renderizamos la plantilla HTML a un string
        html_string = render_to_string('academico/reporte_ia_pdf.html', context)
        
        # Generamos el PDF en memoria
        pdf_file = HTML(string=html_string).write_pdf()
        
        # Creamos la respuesta HTTP
        response = HttpResponse(pdf_file, content_type='application/pdf')
        
        # Añadimos la cabecera para que el navegador lo descargue
        response['Content-Disposition'] = f'attachment; filename="reporte_{clase.curso.nombre}.pdf"'
        
        return response