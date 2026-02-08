from django.db import models
from django.conf import settings

# Create your models here.

class Noticia(models.Model):
    """
    Representa un boletín, noticia o anuncio publicado por un administrador.
    """
    titulo = models.CharField(max_length=255)
    contenido = models.TextField(verbose_name="Contenido de la noticia")
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='noticias_publicadas',
        limit_choices_to={'user_type': 'ADMIN'} # Solo los admins pueden ser autores
    )
    publicado = models.BooleanField(default=True, verbose_name="¿Está publicado?")

    class Meta:
        verbose_name = "Noticia"
        verbose_name_plural = "Noticias"
        ordering = ['-fecha_publicacion']

    def __str__(self):
        return self.titulo
    
class Notificacion(models.Model):
    """
    Un mensaje corto enviado por un administrador a un grupo de usuarios.
    """
    class TargetAudiencia(models.TextChoices):
        TODOS = 'TODOS', 'Todos los Usuarios'
        ESTUDIANTES = 'ESTUDIANTES', 'Solo Estudiantes'
        MAESTROS = 'MAESTROS', 'Solo Maestros'
        PADRES = 'PADRES', 'Solo Padres de Familia'

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        limit_choices_to={'user_type': 'ADMIN'}
    )
    audiencia = models.CharField(
        max_length=20,
        choices=TargetAudiencia.choices,
        default=TargetAudiencia.TODOS,
        verbose_name="Dirigido a"
    )
    mensaje = models.TextField(verbose_name="Contenido del Mensaje")
    fecha_envio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-fecha_envio']

    def __str__(self):
        return f"Notificación para {self.get_audiencia_display()} por {self.autor.username}"