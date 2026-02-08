from django.urls import path
from . import views

urlpatterns = [
    path('estudiante/', views.PortalEstudianteView.as_view(), name='portal_estudiante'),
    path('estudiante/calificaciones/', views.MisCalificacionesView.as_view(), name='mis_calificaciones'),
    path('maestro/', views.PortalMaestroView.as_view(), name='portal_maestro'),
    path('clase/<int:clase_pk>/crear-actividad/', views.ActividadCreateView.as_view(), name='actividad_create'),
    path('actividad/<int:pk>/', views.ActividadDetailView.as_view(), name='actividad_detail'),
    path('actividad/<int:pk>/entregas/', views.ActividadEntregasView.as_view(), name='actividad_entregas'),
    path('entrega/<int:pk>/calificar/', views.CalificarEntregaView.as_view(), name='calificar_entrega'),
    path('admin/', views.PortalAdminView.as_view(), name='portal_admin'),
    path('noticias/nueva/', views.NoticiaCreateView.as_view(), name='noticia_create'),
    path('noticias/<int:pk>/editar/', views.NoticiaUpdateView.as_view(), name='noticia_update'),
    path('noticias/<int:pk>/eliminar/', views.NoticiaDeleteView.as_view(), name='noticia_delete'),
    path('clase/<int:clase_pk>/asistencia/', views.TomarAsistenciaView.as_view(), name='tomar_asistencia'),
    path('clase/<int:clase_pk>/asistencia/<str:fecha>/', views.TomarAsistenciaView.as_view(), name='tomar_asistencia_fecha'),
    path('clase/<int:clase_pk>/planificacion/', views.PlanificacionListView.as_view(), name='planificacion_list'),
    path('clase/<int:clase_pk>/planificacion/nueva/', views.PlanificacionCreateView.as_view(), name='planificacion_create'),
    path('planificacion/<int:pk>/editar/', views.PlanificacionUpdateView.as_view(), name='planificacion_update'),
    path('planificacion/<int:pk>/eliminar/', views.PlanificacionDeleteView.as_view(), name='planificacion_delete'),
    path('padre/', views.PortalPadreView.as_view(), name='portal_padre'),
    path('padre/ver/<str:estudiante_pk>/', views.PadreEstudianteDashboardView.as_view(), name='portal_padre_ver_estudiante'),
    path('padre/ver/<str:estudiante_pk>/calificaciones/', views.PadreMisCalificacionesView.as_view(), name='portal_padre_calificaciones'),
    path('estudiante/boleta/', views.CalificacionesPeriodoView.as_view(), name='boleta_estudiante'),
    path('cambiar-periodo/', views.CambiarPeriodoView.as_view(), name='cambiar_periodo'),
]