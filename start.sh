#!/bin/bash

# Aplicar migraciones de base de datos
echo "Aplicando migraciones..."
python manage.py migrate

# Recolectar archivos estáticos
echo "Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

# Iniciar el servidor Gunicorn
echo "Iniciando servidor..."
exec gunicorn edutech.wsgi:application --bind 0.0.0.0:$PORT --workers 3