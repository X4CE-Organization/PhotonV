# ---------------------------------------------------------------------------
# PhotonV - 开源微视频平台
# 单镜像：前端构建产物 + FastAPI 后端一起托管，只需要一个进程、一个端口
# ---------------------------------------------------------------------------

# ------------------------------ 前端构建 -----------------------------------
FROM node:22-alpine AS web
WORKDIR /app/frontend
# 国内服务器可以加 --registry=https://registry.npmmirror.com 加速
ARG NPM_REGISTRY=https://registry.npmjs.org
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund --registry=$NPM_REGISTRY
COPY frontend/ ./
RUN npm run build

# ------------------------------ 运行环境 -----------------------------------
FROM python:3.12-slim
ARG APT_MIRROR=deb.debian.org
ARG PIP_INDEX=https://pypi.org/simple

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8080 \
    DATA_DIR=/app/data

RUN if [ "$APT_MIRROR" != "deb.debian.org" ]; then \
      sed -i "s|deb.debian.org|$APT_MIRROR|g" /etc/apt/sources.list.d/debian.sources 2>/dev/null || true; \
    fi \
 && apt-get update \
 && apt-get install -y --no-install-recommends postgresql-client ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt -i $PIP_INDEX

COPY backend/ /app/backend/
COPY --from=web /app/frontend/dist /app/frontend/dist
COPY docs/ /app/docs/

VOLUME ["/app/data"]
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','8080')+'/api/health').read()" || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "/app/backend", "--host", "0.0.0.0", "--port", "8080"]
