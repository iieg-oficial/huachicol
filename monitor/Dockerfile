FROM python:3.13-alpine

WORKDIR /app

COPY monitor.py /app/monitor.py
COPY app /app/app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8090

CMD ["python", "/app/monitor.py"]
