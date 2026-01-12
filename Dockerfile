FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py ./
COPY app/ ./app/

# По умолчанию приложение слушает порт 7777 (через переменную PORT).
ENV PORT=7777

CMD ["python", "app.py"]

