from django import forms
from .models import Curso, Clase, PeriodoAcademico, BitacoraPedagogica, Cargo, Pago, Planificacion
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

class BitacoraForm(forms.ModelForm):
    class Meta:
        model = BitacoraPedagogica
        # Excluimos la 'clase' porque la tomaremos de la URL
        fields = [
            'fecha', 
            'objetivos_sesion',
            'temas_cubiertos', 
            'planificacion',
            'recursos_usados',
            'adaptacion_curricular',
            'observaciones_generales',
            'reflexiones_logros',
            'evidencia_archivo',
            'evidencia_foto',
        ]
        widgets = {
            'fecha': forms.DateInput(attrs={'type': 'date'}),
            'objetivos_sesion': forms.Textarea(attrs={'rows': 3}),
            'temas_cubiertos': forms.Textarea(attrs={'rows': 4}),
            'recursos_usados': forms.Textarea(attrs={'rows': 3}),
            'adaptacion_curricular': forms.Textarea(attrs={'rows': 3}),
            'observaciones_generales': forms.Textarea(attrs={'rows': 4}),
            'reflexiones_logros': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        # Atrapamos el argumento 'clase' que viene de la vista
        clase = kwargs.pop('clase', None) 
        
        # Llamamos al constructor padre (esta línea faltaba o era incorrecta)
        super().__init__(*args, **kwargs) 

        # Si recibimos la 'clase', filtramos el campo 'planificacion'
        if clase:
            self.fields['planificacion'].queryset = Planificacion.objects.filter(clase=clase)
        
        # Aplicamos los estilos de Tailwind (esto ya lo tenías)
        for field_name, field in self.fields.items():
            if field_name != 'competencias': # (este 'if' es de otro form, pero no hace daño)
                field.widget.attrs.update({
                    'class': 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
                })

class CargoForm(forms.ModelForm):
    class Meta:
        model = Cargo
        # Dejamos fuera 'estado' porque se manejará automáticamente
        fields = [
            'estudiante', 
            'periodo', 
            'concepto', 
            'monto', 
            'fecha_vencimiento'
        ]
        widgets = {
            'fecha_vencimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'

class PagoForm(forms.ModelForm):
    """
    Formulario para registrar un pago nuevo.
    """
    class Meta:
        model = Pago
        # Los campos que el contador llenará:
        fields = ['monto', 'metodo_pago', 'referencia']
        widgets = {
            'referencia': forms.TextInput(attrs={'placeholder': 'Ej. No. de boleta, ID de transacción'}),
        }

    def __init__(self, *args, **kwargs):
        # Haremos que el monto del pago sea por defecto el saldo pendiente.
        # Pasaremos el 'cargo' desde la vista.
        cargo = kwargs.pop('cargo', None)
        super().__init__(*args, **kwargs)

        if cargo:
            # Ponemos el saldo pendiente como el monto por defecto
            self.fields['monto'].initial = cargo.saldo_pendiente

        # Aplicamos las clases de Tailwind
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'