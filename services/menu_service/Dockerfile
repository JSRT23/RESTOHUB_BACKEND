FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic necesita SECRET_KEY aunque sea dummy
# Las vars de DB/RabbitMQ no se usan en este paso
RUN SECRET_KEY=build-dummy-secret \
    DEBUG=False \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --no-input

EXPOSE 8000

# Producción usa gunicorn, desarrollo usa runserver
CMD gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level info