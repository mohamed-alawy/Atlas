FROM ghcr.io/astral-sh/uv:0.9.28-python3.10-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libvips-dev pkg-config \
    libjpeg-dev \
    gcc unzip zip \
    python3-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY src/requirements.txt .

RUN uv pip install -r requirements.txt --system

COPY src/ .

RUN mkdir -p /app/models/db_schemas/atlas

COPY docker/atlas/alembic.ini /app/models/db_schemas/atlas/alembic.ini

COPY docker/atlas/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]