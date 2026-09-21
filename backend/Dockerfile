FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for Docker layer caching
COPY requirements.lock.txt .
RUN pip install --no-cache-dir -r requirements.lock.txt

# Copy backend source
COPY app/ app/

# Respect dynamic PORT from Render/Railway/Cloud Run (default 8000)
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

EXPOSE ${PORT}

CMD uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT}
