from django.contrib import admin
from .models import User, Estudiante, Maestro, PadreDeFamilia
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from unfold.admin import ModelAdmin
from .forms import CustomUserCreationForm, CustomUserChangeForm

@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User
    
    list_display = (
        'username', 'email', 'first_name', 'last_name', 
        'user_type', 'is_staff'
    )
    
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (None, {'fields': ('user_type',)}),
    )

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Información Personal", {"fields": ("first_name", "last_name", "email")}),
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

@admin.register(Estudiante)
class EstudianteAdmin(ModelAdmin):
    pass

@admin.register(Maestro)
class MaestroAdmin(ModelAdmin):
    pass

@admin.register(PadreDeFamilia)
class PadreDeFamiliaAdmin(ModelAdmin):
    pass