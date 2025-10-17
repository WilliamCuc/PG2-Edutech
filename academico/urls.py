from django.urls import path
from . import views

# Si no tienes este archivo, créalo dentro de tu app 'academia'
# y no olvides incluirlo en el urls.py principal de tu proyecto.

urlpatterns = [
    path('cursos/', views.cursos, name='gestion_cursos'),
    path('cursos/nuevo/', views.CursoCreateView.as_view(), name='curso_create'),
    path('cursos/<int:pk>/editar/', views.CursoUpdateView.as_view(), name='curso_update'),
    path('cursos/<int:pk>/eliminar/', views.CursoDeleteView.as_view(), name='curso_delete'),
    path('horario/', views.HorarioView.as_view(), name='horario'),
    path('horario/<int:periodo_id>/', views.HorarioView.as_view(), name='horario_periodo'),
    path('maestros/<int:pk>/asignar-cursos/', views.asignar_cursos_maestro, name='asignar_cursos_maestro'),
    path('clase/nueva/', views.ClaseCreateView.as_view(), name='clase_create'),
    path('clase/<int:pk>/editar/', views.ClaseUpdateView.as_view(), name='clase_update'),
    path('clase/<int:pk>/eliminar/', views.ClaseDeleteView.as_view(), name='clase_delete'),
    path('periodos/', views.PeriodoAcademicoListView.as_view(), name='periodo_list'),
    path('periodos/nuevo/', views.PeriodoAcademicoCreateView.as_view(), name='periodo_create'),
    path('periodos/<int:pk>/editar/', views.PeriodoAcademicoUpdateView.as_view(), name='periodo_update'),
    path('periodos/<int:pk>/eliminar/', views.PeriodoAcademicoDeleteView.as_view(), name='periodo_delete'),
    path('clase/<int:pk>/inscribir/', views.inscribir_estudiantes_clase, name='clase_inscribir_estudiantes'),
]