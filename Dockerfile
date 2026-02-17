FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app/

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    python3-dev \
    gcc \
    curl \
    netcat-openbsd \
    fonts-dejavu \
    fonts-dejavu-core \
    fonts-dejavu-extra \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

COPY . /app/

RUN mkdir -p /app/staticfiles /app/media /app/logs && \
    chmod 755 /app/logs && \
    chmod +x /app/entrypoint.sh && \
    chown -R www-data:www-data /app/logs

# Note: collectstatic moved to entrypoint.sh to have access to environment variables

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "-c", "gunicorn.conf.py"]
