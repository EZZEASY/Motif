# Multi-stage build: Frontend + Backend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.14-slim
WORKDIR /app

# Install ffmpeg for video processing
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgomp1 && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/pyproject.toml backend/
RUN pip install --no-cache-dir -e backend/

# Copy backend code
COPY backend/ backend/

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Expose port
ENV PORT=8080
EXPOSE 8080

CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080"]
