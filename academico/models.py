from django.db import models

# Create your models here.
class Curso(models.Model):
    """
    Representa una materia o curso que se imparte en la escuela.
    """
    nombre = models.CharField(max_length=100, unique=True, verbose_name='Nombre del Curso')
    codigo = models.CharField(max_length=10, unique=True, verbose_name='Código del Curso')
    descripcion = models.TextField(blank=True, null=True, verbose_name='Descripción')
    creditos = models.PositiveIntegerField(default=5, verbose_name='Créditos')

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'

    def __str__(self):
        return self.nombre

class AsignacionEstudianteCurso(models.Model):
    """
    Relaciona estudiantes con los cursos en los que están inscritos.
    """
    estudiante = models.ForeignKey('users.Estudiante', on_delete=models.CASCADE, related_name='cursos_inscritos')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='estudiantes_inscritos')
    clase = models.CharField(max_length=100, verbose_name='Clase')
    fecha_inscripcion = models.DateField(auto_now_add=True, verbose_name='Fecha de Inscripción')

    class Meta:
        unique_together = ('estudiante', 'curso') # Un estudiante no puede inscribirse dos veces en el mismo curso
        verbose_name = 'Asignación Estudiante-Curso'
        verbose_name_plural = 'Asignaciones Estudiante-Curso'

    def __str__(self):
        return f"{self.estudiante.user.get_full_name()} - {self.curso.nombre}"
    
class PeriodoAcademico(models.Model):
    """
    Representa un ciclo escolar, como "Semestre 2025-1" o "Año Escolar 2025".
    """
    nombre = models.CharField(max_length=100, unique=True, verbose_name="Nombre del Periodo")
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()

    class Meta:
        verbose_name = "Periodo Académico"
        verbose_name_plural = "Periodos Académicos"

    def __str__(self):
        return self.nombre

class Clase(models.Model):
    """
    El corazón del sistema. Define una clase específica que se imparte.
    Conecta un Curso, un Maestro, un Horario y un Periodo.
    Por ejemplo: "Clase de Matemáticas I" con el "Prof. López" los "Lunes de 8-10 am"
    en el "Semestre 2025-1".
    """
    class DiaSemana(models.TextChoices):
        LUNES = 'LUN', 'Lunes'
        MARTES = 'MAR', 'Martes'
        MIERCOLES = 'MIE', 'Miércoles'
        JUEVES = 'JUE', 'Jueves'
        VIERNES = 'VIE', 'Viernes'
        SABADO = 'SAB', 'Sábado'
    
    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.CASCADE, related_name='clases')
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='clases')
    maestro = models.ForeignKey('users.Maestro', on_delete=models.SET_NULL, null=True, blank=True, related_name='clases')
    
    # Horario
    dia_semana = models.CharField(max_length=3, choices=DiaSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    
    # Estudiantes inscritos
    estudiantes = models.ManyToManyField(
        'users.Estudiante',
        blank=True, # Una clase puede empezar sin estudiantes
        related_name='clases_inscritas'
    )

    class Meta:
        verbose_name = "Clase"
        verbose_name_plural = "Clases"
        # Evitar que se cree la misma clase (mismo curso, maestro, día y hora) en el mismo periodo
        unique_together = ('periodo', 'curso', 'maestro', 'dia_semana', 'hora_inicio')

    def __str__(self):
        return f"{self.curso.nombre} ({self.get_dia_semana_display()} {self.hora_inicio:%H:%M} - {self.hora_fin:%H:%M})"

class Actividad(models.Model):
    """
    Representa una tarea, proyecto o cualquier actividad asignada por un maestro
    a una clase específica.
    """
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='actividades')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateTimeField(verbose_name="Fecha Límite de Entrega")

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        ordering = ['fecha_entrega']

    def __str__(self):
        return f"{self.titulo} - {self.clase.curso.nombre}"

class Entrega(models.Model):
    """
    Representa la entrega de una actividad por parte de un estudiante.
    """
    actividad = models.ForeignKey(Actividad, on_delete=models.CASCADE, related_name='entregas')
    estudiante = models.ForeignKey('users.Estudiante', on_delete=models.CASCADE, related_name='entregas')
    fecha_entrega = models.DateTimeField(auto_now_add=True)
    archivo = models.FileField(upload_to='entregas/', blank=True, null=True, verbose_name="Archivo Adjunto")
    comentarios = models.TextField(blank=True, verbose_name="Comentarios del Estudiante")
    calificacion = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    comentarios_maestro = models.TextField(blank=True, verbose_name="Comentarios del Maestro")

    class Meta:
        verbose_name = "Entrega"
        verbose_name_plural = "Entregas"
        # Un estudiante solo puede hacer una entrega por actividad
        unique_together = ('actividad', 'estudiante')

    def __str__(self):
        return f"Entrega de {self.estudiante.user.get_full_name()} para {self.actividad.titulo}"
