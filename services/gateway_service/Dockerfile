FROM python:3.11-slim

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic con vars dummy
RUN DJANGO_SECRET_KEY=build-dummy-secret \
    DEBUG=False \
    ALLOWED_HOSTS=* \
    python manage.py collectstatic --no-input

EXPOSE 8000

# Gateway usa SQLite en memoria — no necesita migrate real
# pero lo corremos igual para las tablas de Django admin/sessions
CMD python manage.py migrate --no-input && \
    gunicorn config.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --log-level info