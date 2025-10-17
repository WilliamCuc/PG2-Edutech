from django import forms
from .models import Curso, Clase, PeriodoAcademico
from users.models import Estudiante

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['nombre', 'descripcion', 'codigo', 'creditos']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'}),
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'}),
            'codigo': forms.TextInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'}),
            'creditos': forms.NumberInput(attrs={'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'}),
        }

class AsignarCursosForm(forms.Form):
    """
    Este formulario toma un maestro y muestra todos los cursos disponibles,
    permitiendo seleccionar cuáles se le asignarán.
    """
    cursos = forms.ModelMultipleChoiceField(
        queryset=Curso.objects.all(),
        widget=forms.CheckboxSelectMultiple, # Muestra los cursos como checkboxes
        required=False, # Permite que un maestro no tenga ningún curso
        label="Seleccione los cursos a asignar"
    )

class ClaseForm(forms.ModelForm):
    class Meta:
        model = Clase
        # Incluimos todos los campos necesarios para definir una clase
        fields = [
            'periodo', 
            'curso', 
            'maestro', 
            'dia_semana', 
            'hora_inicio', 
            'hora_fin'
        ]
        widgets = {
            # Usamos widgets de HTML5 para una mejor experiencia de usuario
            'hora_inicio': forms.TimeInput(attrs={'type': 'time'}),
            'hora_fin': forms.TimeInput(attrs={'type': 'time'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Añadimos clases de Tailwind a todos los campos para que se vean bien
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'

class PeriodoAcademicoForm(forms.ModelForm):
    class Meta:
        model = PeriodoAcademico
        fields = ['nombre', 'fecha_inicio', 'fecha_fin']
        widgets = {
            'fecha_inicio': forms.DateInput(attrs={'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'

class InscribirEstudiantesForm(forms.Form):
    """
    Formulario para seleccionar múltiples estudiantes y asignarlos a una clase.
    """
    estudiantes = forms.ModelMultipleChoiceField(
        queryset=Estudiante.objects.all(), # Obtenemos todos los estudiantes del sistema
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Seleccione los estudiantes a inscribir"
    )
