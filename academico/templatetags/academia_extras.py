from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Permite acceder a claves de diccionario con una variable en la plantilla."""
    return dictionary.get(key)