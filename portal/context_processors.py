from academico.models import PeriodoAcademico

def periodos_context(request):
    """
    Hace que la lista de periodos y el periodo seleccionado
    estén disponibles en todas las plantillas.
    """
    if not request.user.is_authenticated:
        return {} # No hacer nada si no está logueado
    
    # 1. Obtiene TODOS los periodos de la base de datos
    periodos = PeriodoAcademico.objects.all().order_by('-fecha_inicio')
    
    # 2. Obtiene el ID que el usuario seleccionó (de la sesión)
    periodo_seleccionado_id = request.session.get('periodo_seleccionado_id')
    
    return {
        'lista_todos_periodos': periodos,
        'periodo_seleccionado_id': periodo_seleccionado_id
    }