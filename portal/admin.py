from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Noticia, Notificacion

@admin.register(Noticia)
class NoticiaAdmin(ModelAdmin):
    """
    Configuración personalizada para el modelo Noticia en el admin.
    """
    # Qué columnas mostrar en la lista de noticias
    list_display = ('titulo', 'autor', 'fecha_publicacion', 'publicado')
    
    # Qué campos permitir para filtrar
    list_filter = ('publicado', 'fecha_publicacion')
    
    # Qué campos usar para la búsqueda
    search_fields = ('titulo', 'contenido')
    
    # Oculta el campo 'autor' del formulario, ya que lo asignaremos automáticamente
    exclude = ('autor',)

    def save_model(self, request, obj, form, change):
        """
        Esta función se llama al guardar la noticia desde el admin.
        """
        if not obj.pk:
            obj.autor = request.user
            
        super().save_model(request, obj, form, change)

@admin.register(Notificacion)
class NotificacionAdmin(ModelAdmin):
    list_display = ('mensaje', 'audiencia', 'autor', 'fecha_envio')
    list_filter = ('audiencia', 'fecha_envio')
    exclude = ('autor',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.autor = request.user
        super().save_model(request, obj, form, change)