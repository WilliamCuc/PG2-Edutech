from django.urls import path
from . import views

urlpatterns = [
    path('estudiante/', views.PortalEstudianteView.as_view(), name='portal_estudiante'),
    path('maestro/', views.PortalMaestroView.as_view(), name='portal_maestro'),
    path('clase/<int:clase_pk>/crear-actividad/', views.ActividadCreateView.as_view(), name='actividad_create'),
    path('actividad/<int:pk>/', views.ActividadDetailView.as_view(), name='actividad_detail'),
    path('actividad/<int:pk>/entregas/', views.ActividadEntregasView.as_view(), name='actividad_entregas'),
    path('entrega/<int:pk>/calificar/', views.CalificarEntregaView.as_view(), name='calificar_entrega'),
]