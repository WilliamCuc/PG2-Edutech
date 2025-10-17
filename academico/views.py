from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .forms import CursoForm, AsignarCursosForm, ClaseForm, PeriodoAcademicoForm, InscribirEstudiantesForm
from django.shortcuts import render, get_object_or_404, redirect
from django.views import View
from .models import PeriodoAcademico, Clase, Curso
import datetime
from users.models import Maestro


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

