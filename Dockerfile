FROM python:3.13.15-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=gestion_eebc.settings.prod \
    PORT=8000

WORKDIR /app

# WeasyPrint runtime dependencies for Debian. Keep these explicit so PDF
# rendering is reproducible instead of depending on the host image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        fonts-dejavu-core \
        libharfbuzz-subset0 \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements ./requirements
COPY requirements.txt ./requirements.txt

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements/prod.txt \
    && python -m pip check

COPY . .

# Validate the system/Python PDF stack before the image can be published.
RUN python - <<'PY'
from weasyprint import HTML

pdf = HTML(string='<html><body><p>EEBC Docker PDF check</p></body></html>').write_pdf()
if not pdf.startswith(b'%PDF'):
    raise RuntimeError('WeasyPrint did not produce a valid PDF payload')
print(f'WeasyPrint OK ({len(pdf)} bytes)')
PY

# Build-time Django checks use the isolated build settings: no PostgreSQL,
# Redis, SMTP or media provider is contacted while creating the image.
RUN DJANGO_SETTINGS_MODULE=gestion_eebc.settings.build python manage.py check --fail-level ERROR \
    && DJANGO_SETTINGS_MODULE=gestion_eebc.settings.build python manage.py collectstatic --noinput

RUN chmod +x /app/start.sh \
    && addgroup --system eebc \
    && adduser --system --ingroup eebc --home /app eebc \
    && chown -R eebc:eebc /app

USER eebc

EXPOSE 8000

CMD ["./start.sh"]
