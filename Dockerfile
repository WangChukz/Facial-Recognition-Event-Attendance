FROM python:3.11-slim-bookworm

WORKDIR /app

# System deps for InsightFace / OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libgomp1 \
    libgl1 libglib2.0-0 libxcb1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY backend/app ./app

# Copy AI models & faiss indexes (pre-built, committed to repo)
COPY faiss_indexes ./faiss_indexes
# COPY ai_models ./ai_models

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Production: no --reload
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
