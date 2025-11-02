# Dockerfile for Fastapi Auth Service
FROM python:3.11-slim

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY ./app /app/app

CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]

EXPOSE 8000