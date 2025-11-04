from django.contrib import admin
from .models import User, Estudiante, Maestro, PadreDeFamilia
from django.contrib.auth.admin import UserAdmin
from .forms import CustomUserCreationForm, CustomUserChangeForm

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    
    list_display = (
        'username', 'email', 'first_name', 'last_name', 
        'user_type', 'is_staff'
    )
    
    # Esto controla el formulario de AÑADIR (ya lo tenías)
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('user_type',)}),
    )

    # 👇 ¡ESTE ES EL BLOQUE QUE FALTA! 👇
    # Esto controla el formulario de EDICIÓN
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Información Personal", {"fields": ("first_name", "last_name", "email")}),
        
        # Aquí añadimos nuestro campo personalizado
        ("Roles y Tipo", {"fields": ("user_type",)}), 
        
        (
            "Permisos",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("Fechas Importantes", {"fields": ("last_login", "date_joined")}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Estudiante)
admin.site.register(Maestro)
admin.site.register(PadreDeFamilia)