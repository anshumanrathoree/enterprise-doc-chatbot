FROM python:3.11-slim

WORKDIR /app
COPY requirements-reranker.txt .
RUN apt-get update && apt-get install -y build-essential git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements-reranker.txt

COPY app.py /app/app.py

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]