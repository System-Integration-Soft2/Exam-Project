FROM python:3.11-slim

WORKDIR /app

COPY GRPC/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY GRPC/ .

EXPOSE 9000

CMD ["python", "server.py"]
