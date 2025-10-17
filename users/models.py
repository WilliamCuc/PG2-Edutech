# usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from academico.models import Curso

class User(AbstractUser):
    """
    Modelo de Usuario Personalizado.
    Hereda de AbstractUser para mantener todo el sistema de autenticación de Django,
    pero añade un campo 'user_type' para diferenciar roles.
    """
    class UserType(models.TextChoices):
        ESTUDIANTE = 'ESTUDIANTE', 'Estudiante'
        MAESTRO = 'MAESTRO', 'Maestro'
        ADMIN = 'ADMIN', 'Admin'
        # Puedes añadir más roles aquí en el futuro (ej. PADRE, SECRETARIA, etc.)

    # El campo 'username' de AbstractUser será el identificador principal
    # (ej. matrícula para estudiantes, código de empleado para maestros).
    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        verbose_name='Tipo de Usuario'
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_user_type_display()})"

class Estudiante(models.Model):
    """
    Perfil para usuarios de tipo Estudiante.
    Contiene la información académica y personal específica de un estudiante.
    """
    # Relación uno a uno con el modelo de usuario. Si se elimina el usuario, se elimina el perfil.
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True, # El usuario es la clave primaria de este modelo.
        related_name='estudiante' # Para acceder desde el user: user.estudiante
    )
    
    # Campos específicos del estudiante
    matricula = models.CharField(max_length=20, unique=True, verbose_name='Matrícula')
    fecha_nacimiento = models.DateField(verbose_name='Fecha de Nacimiento')
    
    # Ejemplo de relaciones con otros modelos que crearás más adelante
    # grado = models.ForeignKey('Grado', on_delete=models.SET_NULL, null=True, related_name='estudiantes')
    # tutor = models.ForeignKey('Tutor', on_delete=models.SET_NULL, null=True, related_name='tutelados')

    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'

    def __str__(self):
        # Accedemos a los datos del modelo User relacionado
        return self.user.get_full_name()

class Maestro(models.Model):
    """
    Perfil para usuarios de tipo Maestro.
    Contiene la información profesional y de contacto específica de un maestro.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='maestro' # Para acceder desde el user: user.maestro
    )
    
    # Campos específicos del maestro
    numero_empleado = models.CharField(max_length=20, unique=True, verbose_name='Número de Empleado')
    especialidad = models.CharField(max_length=100, verbose_name='Especialidad Principal')
    fecha_contratacion = models.DateField(verbose_name='Fecha de Contratación')
    telefono_contacto = models.CharField(max_length=15, blank=True, null=True, verbose_name='Teléfono de Contacto')
    cursos = models.ManyToManyField(
        Curso,
        blank=True, # Un maestro puede no tener cursos asignados inicialmente.
        related_name='maestros',
        verbose_name='Cursos Asignados'
    )


    class Meta:
        verbose_name = 'Maestro'
        verbose_name_plural = 'Maestros'

    def __str__(self):
        return self.user.get_full_name()
