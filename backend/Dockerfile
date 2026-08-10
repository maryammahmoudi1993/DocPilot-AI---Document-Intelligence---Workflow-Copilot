# Local-development image (see root docker-compose.yml). Not a production
# deployment artifact — no gunicorn/entrypoint hardening here yet; that
# belongs to the deployment phase.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# libpq5: runtime client library psycopg[binary] needs.
# tesseract-ocr: real OCR provider (apps/processing/providers.py).
# poppler-utils: pdf2image needs it (pdftoppm) to render PDF pages to
# images before handing them to tesseract.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 tesseract-ocr poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# This project's installable package IS its source (apps/, common/,
# config/ — no separate requirements.txt), so the dependency-install layer
# can't be cached independently of a source copy the way a
# requirements.txt-based image usually is. Acceptable trade-off at
# portfolio scale; revisit (e.g. a generated requirements.txt) if build
# times become a real problem.
COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
