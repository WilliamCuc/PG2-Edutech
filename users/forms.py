from django import forms
from .models import User, Maestro, Estudiante
from django.db import transaction
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

class CustomUserCreationForm(UserCreationForm):
    """
    Un formulario para crear nuevos usuarios.
    """
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'user_type')

class CustomUserChangeForm(UserChangeForm):
    """
    Un formulario para editar usuarios existentes.
    """
    class Meta(UserChangeForm.Meta):
        model = User

class MaestroForm(forms.ModelForm):
    first_name = forms.CharField(label='Nombres', max_length=150, required=True)
    last_name = forms.CharField(label='Apellidos', max_length=150, required=True)
    email = forms.EmailField(label='Correo Electrónico', required=True)
    
    class Meta:
        model = Maestro
        fields = [
            'first_name', 'last_name', 'email',
            'numero_empleado', 'especialidad', 'fecha_contratacion', 'telefono_contacto',
            'foto_perfil',
            'titulo_academico',
            'biografia',
            'direccion',
            'contacto_emergencia_nombre',
            'contacto_emergencia_telefono'
        ]
        widgets = {
            'fecha_contratacion': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email
            
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500'
        
        self.order_fields([
            'first_name', 'last_name', 'email', 
            'foto_perfil', 'telefono_contacto', 'titulo_academico',
            'especialidad', 'biografia', 'direccion', 
            'contacto_emergencia_nombre', 'contacto_emergencia_telefono'
        ])

    def form_valid(self, form):
        with transaction.atomic():
            user = User.objects.create_user(
                username=form.cleaned_data['numero_empleado'], # Usamos la matrícula como username
                password='passwordtemporal123', # Contraseña inicial
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                user_type=User.UserType.ESTUDIANTE
            )
            form.instance.user = user
        
        return super().form_valid(form)


class EstudianteForm(forms.ModelForm):
    first_name = forms.CharField(label='Nombres', max_length=150, required=True)
    last_name = forms.CharField(label='Apellidos', max_length=150, required=True)
    email = forms.EmailField(label='Correo Electrónico', required=False)

    class Meta:
        model = Estudiante
        fields = [
            'first_name', 'last_name', 'email',
            'matricula', 'fecha_nacimiento',
            'nombre_padre', 'telefono_contacto', 'direccion',
            'contacto_emergencia', 'enfermedades_alergias',
            'grado'
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
        with transaction.atomic():
            user = User.objects.create_user(
                username=form.cleaned_data['matricula'], # Usamos la matrícula como username
                password='passwordtemporal123', # Contraseña inicial
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name'],
                user_type=User.UserType.ESTUDIANTE
            )
            form.instance.user = user
        
        return super().form_valid(form)
