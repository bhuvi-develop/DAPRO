FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && apt-get clean
COPY requirements.txt requirements-dev.txt constraints.txt ./
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then pip install -r requirements-dev.txt -c constraints.txt; else pip install -r requirements.txt -c constraints.txt; fi
COPY . .
RUN useradd -u 10001 -m dapro && mkdir -p /app/storage && chown -R dapro /app
USER dapro
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
