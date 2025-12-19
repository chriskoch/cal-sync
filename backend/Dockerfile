FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install Python dependencies
# Using binary packages (psycopg2-binary) to avoid needing build tools
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run migrations and start server
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
