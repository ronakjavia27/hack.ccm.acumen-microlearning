FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN apt-get update && apt-get install -y tesseract-ocr poppler-utils && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# Secrets are NOT baked into the image (.dockerignore keeps .env out). Pass them at run time:
#   docker run --env-file .env -v "$PWD/input_pdfs:/app/input_pdfs" -v "$PWD/output_files:/app/output_files" <image>
COPY . .

# DEFAULT BEHAVIOR: run the ingestion pipeline in watch mode (see `python generator.py --help`)
CMD ["python", "generator.py"]
