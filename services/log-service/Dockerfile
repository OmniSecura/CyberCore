FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.in .
RUN pip install --no-cache-dir -r requirements.in

COPY . .

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8083

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8083"]
