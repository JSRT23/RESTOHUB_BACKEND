FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic con vars dummy (DB/RabbitMQ no se usan en este paso)
RUN DJANGO_SECRET_KEY=build-dummy-secret \
    DEBUG=False \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --no-input

EXPOSE 8000

# migrate corre en runtime cuando la DB ya está disponible
CMD python manage.py migrate --no-input && \
    gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level info