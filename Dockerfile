FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN apt-get update && apt-get install -y tesseract-ocr poppler-utils && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

COPY .env .
COPY . .

# Expose port for Streamlit web serving layers if overridden
EXPOSE 8501

# DEFAULT BEHAVIOR: Boot only the background ingestion engine loop
CMD ["python", "master_app.py"]