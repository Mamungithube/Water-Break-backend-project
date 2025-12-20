FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Create entrypoint script
RUN echo '#!/bin/bash\n\
echo "================================="\n\
echo "Waiting for PostgreSQL to start..."\n\
echo "================================="\n\
\n\
# Wait for PostgreSQL\n\
while ! nc -z db 5432; do\n\
  echo "Waiting for database connection..."\n\
  sleep 1\n\
done\n\
\n\
echo "✓ PostgreSQL is ready!"\n\
echo ""\n\
echo "Running migrations..."\n\
python manage.py makemigrations --noinput\n\
python manage.py migrate --noinput\n\
echo "✓ Migrations completed!"\n\
echo ""\n\
echo "Starting Django server..."\n\
echo "================================="\n\
exec "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]