from django.apps import AppConfig


class AcademicoConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'academico'
    verbose_name = 'Gestión Académica'

    def ready(self):
        import academico.signals