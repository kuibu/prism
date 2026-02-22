FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install third-party dependencies from pyproject first.
# This keeps dependency layers cached when only application source changes.
COPY services/gateway_api/pyproject.toml /tmp/gateway_api/pyproject.toml
COPY services/gateway_api/scripts/export_requirements.py /tmp/gateway_api/export_requirements.py
RUN python /tmp/gateway_api/export_requirements.py \
    /tmp/gateway_api/pyproject.toml \
    /tmp/gateway_api/requirements-dev.txt
RUN pip install --upgrade pip && pip install -r /tmp/gateway_api/requirements-dev.txt

COPY services/gateway_api /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
