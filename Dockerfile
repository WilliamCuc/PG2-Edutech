# 1. Usar una imagen oficial de Python como base
FROM python:3.12-slim

# 2. Evitar que Python guarde en buffer los outputs, para ver los logs en tiempo real
ENV PYTHONUNBUFFERED 1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        pkg-config \
        default-libmysqlclient-dev \
    && apt-get install -y git \
    && rm -rf /var/lib/apt/lists/*

# instalar git

# 3. Establecer el directorio de trabajo dentro del contenedor
WORKDIR /app

# 4. Copiar el archivo de dependencias PRIMERO para aprovechar el cache de Docker
# Si no cambian las dependencias, Docker no reinstalará todo cada vez.
COPY requirements.txt .

# 5. Instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copiar el resto del código de la aplicación al directorio de trabajo
COPY . .

# El comando para correr la app se definirá en docker-compose.yml