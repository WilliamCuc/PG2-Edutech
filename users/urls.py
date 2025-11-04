from django.urls import path
from . import views

urlpatterns = [
    path('maestros/', views.MaestroListView.as_view(), name='maestros'),
    path('maestros/nuevo/', views.MaestroCreateView.as_view(), name='maestro_create'),
    path('maestros/<str:pk>/editar/', views.MaestroUpdateView.as_view(), name='maestro_update'),
    path('maestros/<str:pk>/eliminar/', views.MaestroDeleteView.as_view(), name='maestro_delete'),
    path('maestros/<str:pk>/', views.MaestroDetailView.as_view(), name='maestro_detail'),

    # Rutas para Estudiantes
    path('estudiantes/', views.EstudianteListView.as_view(), name='estudiante_list'),
    path('estudiantes/nuevo/', views.EstudianteCreateView.as_view(), name='estudiante_create'),
    path('estudiantes/<str:pk>/editar/', views.EstudianteUpdateView.as_view(), name='estudiante_update'),
    path('estudiantes/<str:pk>/eliminar/', views.EstudianteDeleteView.as_view(), name='estudiante_delete'),

]