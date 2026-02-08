# usuarios/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from academico.models import Curso, Grado

class User(AbstractUser):
    class UserType(models.TextChoices):
        ESTUDIANTE = 'ESTUDIANTE', 'Estudiante'
        MAESTRO = 'MAESTRO', 'Maestro'
        ADMIN = 'ADMIN', 'Admin'
        PADRE = 'PADRE', 'Padre de Familia'

    user_type = models.CharField(
        max_length=20,
        choices=UserType.choices,
        verbose_name='Tipo de Usuario'
    )

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_user_type_display()})"

class Estudiante(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='estudiante'
    )
    grado = models.ForeignKey(
        Grado,
        on_delete=models.SET_NULL, # Si se borra el grado, no se borra el estudiante
        null=True,
        blank=True,
        related_name="estudiantes",
        verbose_name="Grado Asignado"
    )
    
    matricula = models.CharField(max_length=20, unique=True, verbose_name='Matrícula')
    fecha_nacimiento = models.DateField(verbose_name='Fecha de Nacimiento')
    nombre_padre = models.CharField(max_length=100, verbose_name='Nombre del Padre o Tutor')
    telefono_contacto = models.CharField(max_length=15, blank=True, null=True, verbose_name='Teléfono de Contacto')
    direccion = models.TextField(blank=True, null=True, verbose_name='Dirección Residencial')
    contacto_emergencia = models.CharField(max_length=100, verbose_name='Contacto de Emergencia')
    enfermedades_alergias = models.TextField(blank=True, null=True, verbose_name='Enfermedades o Alergias')
    
    class Meta:
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'

    def __str__(self):
        return self.user.get_full_name()

class Maestro(models.Model):
    class EstadoMaestro(models.TextChoices):
        ACTIVO = 'ACTIVO', 'Activo'
        INACTIVO = 'INACTIVO', 'Inactivo'
        LICENCIA = 'LICENCIA', 'Con Licencia'
        PADRE = 'PADRE', 'Padre de Familia'

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='maestro'
    )
    numero_empleado = models.CharField(max_length=20, unique=True, verbose_name='Número de Empleado')
    especialidad = models.CharField(max_length=100, verbose_name='Especialidad Principal (Ej. Matemáticas)')
    fecha_contratacion = models.DateField(verbose_name='Fecha de Contratación')
    telefono_contacto = models.CharField(max_length=20, blank=True, verbose_name='Teléfono Principal')
    cursos = models.ManyToManyField(
        Curso,
        blank=True,
        related_name='maestros',
        verbose_name='Cursos Asignados'
    )

    foto_perfil = models.ImageField(
        upload_to='fotos_perfil/maestros/', 
        null=True, 
        blank=True, 
        verbose_name="Foto de Perfil"
    )
    
    titulo_academico = models.CharField(
        max_length=255, 
        blank=True, 
        verbose_name="Título Académico Principal"
    )
    
    biografia = models.TextField(
        blank=True, 
        verbose_name="Biografía Corta / Resumen Profesional"
    )
    direccion = models.TextField(
        blank=True, 
        verbose_name="Dirección de Contacto"
    )

    contacto_emergencia_nombre = models.CharField(
        max_length=100, 
        blank=True, 
        verbose_name="Nombre de Contacto de Emergencia"
    )
    contacto_emergencia_telefono = models.CharField(
        max_length=20, 
        blank=True, 
        verbose_name="Teléfono de Emergencia"
    )
    
    estado = models.CharField(
        max_length=10, 
        choices=EstadoMaestro.choices, 
        default=EstadoMaestro.ACTIVO,
        verbose_name="Estado Administrativo"
    )

    class Meta:
        verbose_name = 'Maestro'
        verbose_name_plural = 'Maestros'

    def __str__(self):
        return self.user.get_full_name()

class PadreDeFamilia(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='padre_familia'
    )
    
    hijos = models.ManyToManyField(
        Estudiante,
        related_name='padres',
        verbose_name="Hijos/Tutelados"
    )
    
    telefono_contacto = models.CharField(max_length=20, blank=True, verbose_name='Teléfono de Contacto')

    class Meta:
        verbose_name = 'Padre de Familia'
        verbose_name_plural = 'Padres de Familia'

    def __str__(self):
        return self.user.get_full_name()