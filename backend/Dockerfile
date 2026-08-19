FROM python:3.12-slim

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend /app/backend
COPY lib /app/lib
COPY schema.sql /app/schema.sql
COPY ingredients.yaml /app/ingredients.yaml
COPY data /app/data
COPY fixtures /app/fixtures
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["python", "-m", "backend.boot"]
