FROM python:3.13-alpine

RUN addgroup -S -g 10001 monitor \
    && adduser -S -D -H -u 10001 -G monitor monitor \
    && mkdir -p /data \
    && chown monitor:monitor /data

WORKDIR /app

COPY monitor.py /app/monitor.py
COPY app /app/app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

USER 10001:10001

EXPOSE 8090

CMD ["python", "/app/monitor.py"]
