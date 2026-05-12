FROM python:3.12-slim

WORKDIR /app

COPY requirements.in requirements.txt* ./
RUN pip install --no-cache-dir -r requirements.in

COPY . .

ENV DB_CREATE_TABLES=true

CMD ["python", "-m", "uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "8085"]
