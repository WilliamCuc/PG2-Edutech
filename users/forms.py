from django import forms
from .models import User, Maestro, Estudiante
from django.db import transaction

class MaestroForm(forms.ModelForm):
    # Campos del modelo User
    first_name = forms.CharField(label='Nombres', max_length=150, required=True)
    last_name = forms.CharField(label='Apellidos', max_length=150, required=True)
    email = forms.EmailField(label='Correo Electrónico', required=True)
    
    class Meta:
        model = Maestro
        # Campos del modelo Maestro + campos añadidos
        fields = [
            'first_name', 'last_name', 'email',
            'numero_empleado', 'especialidad', 'fecha_contratacion', 'telefono_contacto'
        ]
        widgets = {
            'fecha_contratacion': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si estamos editando (la instancia existe), poblamos los campos del User
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            
        # Añadimos clases de Tailwind a todos los campos
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'

    def form_valid(self, form):
        # Usamos una transacción para que todo sea una única operación
        with transaction.atomic():
            # PASO 1: Crear el objeto 'User' para la autenticación
            user = User.objects.create_user(
                username=form.cleaned_data['numero_empleado'], # Usamos la matrícula como username
                password='passwordtemporal123', # Contraseña inicial
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                user_type=User.UserType.ESTUDIANTE
            )
            # PASO 2: Vincular el 'User' recién creado con el perfil 'Estudiante'
            form.instance.user = user
        
        # Finalmente, se guarda el objeto Estudiante con su usuario ya asignado.
        return super().form_valid(form)


# --- Formularios para Estudiante ---

class EstudianteForm(forms.ModelForm):
    # Campos del modelo User
    first_name = forms.CharField(label='Nombres', max_length=150, required=True)
    last_name = forms.CharField(label='Apellidos', max_length=150, required=True)
    email = forms.EmailField(label='Correo Electrónico', required=False)

    class Meta:
        model = Estudiante
        fields = [
            'first_name', 'last_name', 'email',
            'matricula', 'fecha_nacimiento'
        ]
        widgets = {
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'

    def form_valid(self, form):
        # Usamos una transacción para que todo sea una única operación
        with transaction.atomic():
            # PASO 1: Crear el objeto 'User' para la autenticación
            user = User.objects.create_user(
                username=form.cleaned_data['matricula'], # Usamos la matrícula como username
                password='passwordtemporal123', # Contraseña inicial
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                user_type=User.UserType.ESTUDIANTE
            )
            # PASO 2: Vincular el 'User' recién creado con el perfil 'Estudiante'
            form.instance.user = user
        
        # Finalmente, se guarda el objeto Estudiante con su usuario ya asignado.
        return super().form_valid(form)
    

