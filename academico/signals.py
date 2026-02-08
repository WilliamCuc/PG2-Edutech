from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Pago

@receiver(post_save, sender=Pago)
def actualizar_estado_cargo_on_save(sender, instance, **kwargs):
    """
    Cuando un pago es guardado, actualiza el estado del cargo asociado.
    """
    instance.cargo.actualizar_estado()

@receiver(post_delete, sender=Pago)
def actualizar_estado_cargo_on_delete(sender, instance, **kwargs):
    """
    Cuando un pago es eliminado, actualiza el estado del cargo asociado.
    """
    instance.cargo.actualizar_estado()