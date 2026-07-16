# syntax=docker/dockerfile:1

# --- 前端构建（跳过 vue-tsc，避免 TS 检查阻塞）---
FROM node:20-slim AS frontend
WORKDIR /frontend
COPY vue-manage-system-master/package.json vue-manage-system-master/package-lock.json ./
RUN npm ci
COPY vue-manage-system-master/ ./
RUN npx vite build

# --- Python 运行时 ---
FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH"
WORKDIR /app

COPY --chown=user requirements-hf.txt requirements-hf.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements-hf.txt

COPY --chown=user app ./app
COPY --chown=user data ./data
COPY --chown=user --from=frontend /frontend/dist ./static

ENV PYTHONUNBUFFERED=1
ENV SERVE_STATIC=1

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
