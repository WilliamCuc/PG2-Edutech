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
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'user_type'),
        }),
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

    def get_fieldsets(self, request, obj=None):
        if obj and obj.user_type in (User.UserType.ESTUDIANTE, User.UserType.PADRE):
            return (
                (None, {"fields": ("username", "password")}),
                ("Información Personal", {"fields": ("first_name", "last_name", "email")}),
                ("Roles y Tipo", {"fields": ("user_type",)}),
                ("Fechas Importantes", {"fields": ("last_login", "date_joined")}),
            )
        return super().get_fieldsets(request, obj)

    def save_model(self, request, obj, form, change):
        if obj.user_type in (User.UserType.ESTUDIANTE, User.UserType.PADRE):
            obj.is_staff = False
            obj.is_superuser = False
        super().save_model(request, obj, form, change)

@admin.register(Estudiante)
class EstudianteAdmin(ModelAdmin):
    pass

@admin.register(Maestro)
class MaestroAdmin(ModelAdmin):
    pass

@admin.register(PadreDeFamilia)
class PadreDeFamiliaAdmin(ModelAdmin):
    pass