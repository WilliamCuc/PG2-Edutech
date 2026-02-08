from django.contrib import admin
from .models import Competencia, Planificacion, Curso, Clase, PeriodoAcademico, Grado, Cargo, Pago

# Register your models here.
admin.site.register(Competencia)
admin.site.register(Planificacion)
admin.site.register(Curso)
admin.site.register(Clase)
admin.site.register(PeriodoAcademico)
admin.site.register(Grado)
admin.site.register(Cargo)
admin.site.register(Pago)