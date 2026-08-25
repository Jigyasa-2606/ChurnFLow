FROM python:3.11-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONPATH=/app

COPY apps/worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY packages/features /opt/features
RUN pip install --no-cache-dir /opt/features

COPY apps/worker/worker ./worker

CMD ["python", "-m", "worker"]
