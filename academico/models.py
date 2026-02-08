from django.db import models
from django.db.models import Sum
import datetime
from django.utils import timezone
from django.conf import settings
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
    recurso_adjunto = models.FileField(
        upload_to='actividades/recursos/', 
        blank=True, 
        null=True, 
        verbose_name="Archivo Adjunto (PDF, etc.)"
    )

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


    
class Cargo(models.Model):
    """
    Representa una factura o un cargo asignado a un estudiante.
    Ej. Colegiatura, Inscripción, Examen Extraordinario.
    """
    class EstadoCargo(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        PAGADO = 'PAGADO', 'Pagado'
        VENCIDO = 'VENCIDO', 'Vencido'
        CANCELADO = 'CANCELADO', 'Cancelado'

    estudiante = models.ForeignKey('users.Estudiante', on_delete=models.PROTECT, related_name='cargos')
    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.SET_NULL, null=True, blank=True)
    concepto = models.CharField(max_length=200, verbose_name="Concepto")
    monto = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Base")
    
    fecha_emision = models.DateField(auto_now_add=True)
    fecha_vencimiento = models.DateField(verbose_name="Fecha de Vencimiento")

    estado = models.CharField(max_length=10, choices=EstadoCargo.choices, default=EstadoCargo.PENDIENTE)

    class Meta:
        verbose_name = "Cargo"
        verbose_name_plural = "Cargos"
        ordering = ['-fecha_vencimiento']

    def __str__(self):
        return f"{self.concepto} - {self.estudiante.user.get_full_name()} (${self.monto})"

    @property
    def monto_pagado(self):
        """Calcula cuánto se ha pagado para este cargo."""
        total_pagado = self.pagos.aggregate(Sum('monto'))['monto__sum'] or 0
        return total_pagado

    @property
    def saldo_pendiente(self):
        """Calcula el saldo que falta por pagar."""
        return self.monto - self.monto_pagado

    def actualizar_estado(self):
        """Actualiza el estado del cargo basado en los pagos."""
        if self.saldo_pendiente <= 0:
            self.estado = self.EstadoCargo.PAGADO
        elif self.fecha_vencimiento < datetime.date.today():
            self.estado = self.EstadoCargo.VENCIDO
        else:
            self.estado = self.EstadoCargo.PENDIENTE
        self.save()

class Pago(models.Model):
    """
    Representa una transacción o pago realizado por un estudiante.
    Un pago se aplica a un cargo específico.
    """
    class MetodoPago(models.TextChoices):
        EFECTIVO = 'EFECTIVO', 'Efectivo'
        TARJETA = 'TARJETA', 'Tarjeta'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferencia'

    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name='pagos')
    estudiante = models.ForeignKey('users.Estudiante', on_delete=models.PROTECT, related_name='pagos_realizados')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Pago")
    metodo_pago = models.CharField(max_length=20, choices=MetodoPago.choices)
    referencia = models.CharField(max_length=100, blank=True, null=True, verbose_name="Referencia/Boleta")

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-fecha_pago']

    def __str__(self):
        return f"Pago de ${self.monto} por {self.estudiante.user.get_full_name()}"
    
class AsistenciaClase(models.Model):
    """
    Guarda el registro de asistencia de un estudiante a una clase
    en una fecha específica.
    """
    class EstadoAsistencia(models.TextChoices):
        PRESENTE = 'P', 'Presente'
        AUSENTE = 'A', 'Ausente'
        TARDANZA = 'T', 'Tardanza'
        JUSTIFICADO = 'J', 'Justificado'

    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='asistencias')
    estudiante = models.ForeignKey('users.Estudiante', on_delete=models.CASCADE, related_name='asistencias_clase')
    fecha = models.DateField(default=timezone.now, verbose_name="Fecha de la clase")
    estado = models.CharField(
        max_length=1, 
        choices=EstadoAsistencia.choices, 
        default=EstadoAsistencia.AUSENTE,
        verbose_name="Estado"
    )
    observacion = models.CharField(max_length=100, blank=True, verbose_name="Observación (opcional)")

    class Meta:
        verbose_name = "Registro de Asistencia de Clase"
        verbose_name_plural = "Registros de Asistencia de Clase"
        # Un estudiante solo tiene un registro por clase por día
        unique_together = ('clase', 'estudiante', 'fecha')
        ordering = ['-fecha', 'estudiante__user__last_name']

    def __str__(self):
        return f"{self.estudiante.user.get_full_name()} - {self.clase.curso.nombre} ({self.fecha})"
    
class Competencia(models.Model):
    """
    Representa una competencia o estándar de aprendizaje,
    generalmente vinculada a un curso y definida por el admin.
    Ej: "Resuelve problemas de suma y resta" (para Matemáticas 1ro)
    """
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='competencias')
    codigo = models.CharField(max_length=20, unique=True, blank=True, null=True, verbose_name="Código (Opcional)")
    descripcion = models.TextField(verbose_name="Descripción de la Competencia")
    
    class Meta:
        verbose_name = "Competencia"
        verbose_name_plural = "Competencias"
        ordering = ['curso', 'codigo']

    def __str__(self):
        return f"{self.curso.nombre} - {self.descripcion[:50]}..."

class Planificacion(models.Model):
    """
    La planificación semanal o mensual de un maestro para una clase.
    """
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='planificaciones')
    titulo = models.CharField(max_length=200, verbose_name="Título del Plan (Ej. Semana 1: Fracciones)")
    fecha_inicio = models.DateField(verbose_name="Fecha de Inicio")
    fecha_fin = models.DateField(verbose_name="Fecha de Fin")
    
    objetivos = models.TextField(blank=True, verbose_name="Objetivos de Aprendizaje")
    actividades_planificadas = models.TextField(blank=True, verbose_name="Actividades Planificadas")
    recursos_planificados = models.TextField(blank=True, verbose_name="Recursos a Utilizar")
    
    # El "Alineamiento"
    competencias = models.ManyToManyField(
        Competencia,
        blank=True,
        related_name='planificaciones',
        verbose_name="Competencias a Desarrollar"
    )

    class Meta:
        verbose_name = "Planificación"
        verbose_name_plural = "Planificaciones"
        ordering = ['-fecha_inicio']

    def __str__(self):
        return self.titulo
    
class Grado(models.Model):
    """
    Representa un "paquete" o plantilla para un grado/sección.
    Define las clases (horario) y los costos asociados.
    Ej: "1ro Primaria - Sección A"
    """
    nombre = models.CharField(max_length=100, unique=True)
    periodo = models.ForeignKey(PeriodoAcademico, on_delete=models.PROTECT, related_name="grados")
    
    # --- Parte Académica (La plantilla de horario) ---
    clases = models.ManyToManyField(
        Clase,
        blank=True,
        related_name="grados_asignados",
        verbose_name="Plantilla de Clases"
    )
    
    # --- Parte Financiera (La plantilla de costos) ---
    monto_inscripcion = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        verbose_name="Monto de Inscripción"
    )
    monto_utiles = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        verbose_name="Monto de Útiles/Libros"
    )
    monto_colegiatura_mensual = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        verbose_name="Monto de Colegiatura Mensual"
    )

    class Meta:
        verbose_name = "Grado (Plantilla)"
        verbose_name_plural = "Grados (Plantillas)"
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.periodo.nombre})"

class BitacoraPedagogica(models.Model):
    """
    Representa una entrada en el diario pedagógico de un maestro para una clase específica
    en una fecha concreta.
    """
    clase = models.ForeignKey(Clase, on_delete=models.CASCADE, related_name='bitacoras')
    planificacion = models.ForeignKey(
        Planificacion,
        on_delete=models.SET_NULL, # Si se borra el plan, no se borra el diario
        null=True,
        blank=True, # Hacemos que sea opcional
        related_name='entradas_diario',
        verbose_name="Planificación Asociada"
    )
    fecha = models.DateField(verbose_name="Fecha de la Entrada")
    temas_cubiertos = models.TextField(verbose_name="Temas Cubiertos")
    objetivos_sesion = models.TextField(blank=True, verbose_name="Objetivos de la Sesión")
    temas_cubiertos = models.TextField(verbose_name="Temas Cubiertos / Actividades Realizadas")
    recursos_usados = models.TextField(blank=True, verbose_name="Recursos Usados")
    adaptacion_curricular = models.TextField(blank=True, verbose_name="Adaptación Curricular")
    tiempo_sesion_minutos = models.IntegerField(null=True, blank=True, verbose_name="Tiempo de la Sesión (minutos)")
    observaciones_generales = models.TextField(blank=True, verbose_name="Observaciones Generales (grupo, etc.)")
    objetivos_sesion = models.TextField(
        blank=True, 
        verbose_name="Objetivos de la Sesión"
    )
    recursos_usados = models.TextField(
        blank=True, 
        verbose_name="Recursos Usados"
    )
    adaptacion_curricular = models.TextField(
        blank=True, 
        verbose_name="Adaptación Curricular"
    )
    observaciones_generales = models.TextField(
        blank=True, 
        verbose_name="Observaciones (Comportamiento, Aprendizaje)"
    )
    
    # --- NUEVOS CAMPOS DE EVIDENCIA ---
    reflexiones_logros = models.TextField(
        blank=True, 
        verbose_name="Reflexiones sobre Logro de Objetivos"
    )
    evidencia_archivo = models.FileField(
        upload_to='bitacora/archivos/', 
        blank=True, null=True, 
        verbose_name="Archivo de Evidencia (muestra, PDF, etc.)"
    )
    evidencia_foto = models.ImageField(
        upload_to='bitacora/fotos/', 
        blank=True, null=True, 
        verbose_name="Foto de Evidencia"
    )

    class Meta:
        verbose_name = "Bitácora Pedagógica"
        verbose_name_plural = "Bitácoras Pedagógicas"
        ordering = ['-fecha']
        # Un maestro solo puede tener una entrada de bitácora por clase y por día
        unique_together = ('clase', 'fecha')

    def __str__(self):
        return f"Bitácora del {self.fecha} - {self.clase.curso.nombre}"
    