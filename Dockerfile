# Stage 1: Frontend Builder
FROM node:20-alpine AS frontend-builder

WORKDIR /frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Copy frontend source
COPY frontend/ ./

# Build frontend (produces /frontend/dist)
RUN npm run build

# Stage 2: Backend Runtime (Final Image)
FROM python:3.12-slim

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend application code
COPY backend/ ./

# Copy built frontend from Stage 1
COPY --from=frontend-builder /frontend/dist ./static

# Expose single port
EXPOSE 8000

# Run migrations and start server
# Use exec form (JSON array) to ensure proper signal handling and lifespan event execution
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
