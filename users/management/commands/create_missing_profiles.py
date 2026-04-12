from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from users.models import User, Maestro, Estudiante


class Command(BaseCommand):
    help = 'Crea perfiles de maestro y estudiante faltantes para usuarios existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Solo muestra qué se haría sin ejecutar cambios',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Contador para estadísticas
        maestros_creados = 0
        estudiantes_creados = 0
        
        # Buscar usuarios maestros sin perfil
        usuarios_maestros = User.objects.filter(
            user_type=User.UserType.MAESTRO
        ).exclude(maestro__isnull=False)
        
        self.stdout.write(f"Encontrados {usuarios_maestros.count()} maestros sin perfil")
        
        for usuario in usuarios_maestros:
            if dry_run:
                self.stdout.write(f"[DRY RUN] Crearía perfil de maestro para: {usuario.get_full_name()}")
            else:
                maestro = Maestro.objects.create(
                    user=usuario,
                    numero_empleado=f"EMP-{usuario.id:04d}",
                    especialidad="Por definir",
                    fecha_contratacion=timezone.now().date(),
                    telefono_contacto=""
                )
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Creado perfil de maestro para: {usuario.get_full_name()}")
                )
                maestros_creados += 1
        
        # Buscar usuarios estudiantes sin perfil
        usuarios_estudiantes = User.objects.filter(
            user_type=User.UserType.ESTUDIANTE
        ).exclude(estudiante__isnull=False)
        
        self.stdout.write(f"Encontrados {usuarios_estudiantes.count()} estudiantes sin perfil")
        
        for usuario in usuarios_estudiantes:
            if dry_run:
                self.stdout.write(f"[DRY RUN] Crearía perfil de estudiante para: {usuario.get_full_name()}")
            else:
                estudiante = Estudiante.objects.create(
                    user=usuario,
                    matricula=f"EST-{usuario.id:04d}",
                    fecha_nacimiento=timezone.now().date() - timedelta(days=365*15),  # Fecha placeholder
                    nombre_padre="Por definir",
                    contacto_emergencia="Por definir"
                )
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Creado perfil de estudiante para: {usuario.get_full_name()}")
                )
                estudiantes_creados += 1
        
        # Resumen
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"\n[DRY RUN] Se crearían:\n"
                    f"- {usuarios_maestros.count()} perfiles de maestro\n"
                    f"- {usuarios_estudiantes.count()} perfiles de estudiante\n"
                    f"\nEjecuta sin --dry-run para aplicar los cambios"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Perfiles creados exitosamente:\n"
                    f"- {maestros_creados} perfiles de maestro\n"
                    f"- {estudiantes_creados} perfiles de estudiante"
                )
            )
        
        self.stdout.write("\n🚀 ¡Listo! Los usuarios ahora pueden acceder a sus portales.")