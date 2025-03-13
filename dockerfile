# Stage 1: Build frontend (React)
FROM node:20-alpine AS frontend-builder
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend ./
RUN npm run build

# Stage 2: Build backend dependencies and prepare environment
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04 AS backend-builder

# Install Python and dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-dev build-essential git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy backend requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 \
    && pip install -r requirements.txt

# Stage 3: Final runtime environment
FROM nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04

# Install Python runtime and system dependencies required by OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip \
    libgl1-mesa-glx libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy backend dependencies
COPY --from=backend-builder /usr/local/lib/python3.10/dist-packages /usr/local/lib/python3.10/dist-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend application source code
COPY *.py ./

# Copy built frontend files to backend
COPY --from=frontend-builder /frontend/dist ./frontend/dist

# Update PATH environment variable
ENV PATH=/usr/local/bin:$PATH

# Default command
CMD ["python3", "main.py"]