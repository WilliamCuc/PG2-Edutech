from django.contrib import admin
from .models import User, Estudiante, Maestro

# Registra tus modelos aquí
admin.site.register(User)
admin.site.register(Estudiante)
admin.site.register(Maestro)
