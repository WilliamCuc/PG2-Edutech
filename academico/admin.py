from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Competencia, Planificacion, Curso, Clase, PeriodoAcademico, Grado, Cargo, Pago

@admin.register(Competencia)
class CompetenciaAdmin(ModelAdmin):
    pass

@admin.register(Planificacion)
class PlanificacionAdmin(ModelAdmin):
    pass

@admin.register(Curso)
class CursoAdmin(ModelAdmin):
    pass

@admin.register(Clase)
class ClaseAdmin(ModelAdmin):
    pass

@admin.register(PeriodoAcademico)
class PeriodoAcademicoAdmin(ModelAdmin):
    pass

@admin.register(Grado)
class GradoAdmin(ModelAdmin):
    pass

@admin.register(Cargo)
class CargoAdmin(ModelAdmin):
    pass

@admin.register(Pago)
class PagoAdmin(ModelAdmin):
    pass