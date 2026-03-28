# syntax=docker/dockerfile:1

# ── Stage 1: Build React frontend ───────────────────────────────────────────
FROM node:20-alpine AS frontend-build

WORKDIR /app
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm ci
COPY frontend/ ./frontend/
RUN cd frontend && npm run build

# ── Stage 2: Python runtime ──────────────────────────────────────────────────
FROM python:3.12-alpine3.19

ENV PYCURL_SSL_LIBRARY=openssl

# Install dependencies
RUN apk add --no-cache ffmpeg libcurl

WORKDIR /app

RUN apk add --no-cache --virtual .build-dependencies build-base curl-dev \
    && pip install pycurl \
    && apk del .build-dependencies

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY *.py ./
COPY streamonitor ./streamonitor

# Copy built frontend into the Litestar static folder
COPY --from=frontend-build /app/streamonitor/managers/httpmanager_v2/static ./streamonitor/managers/httpmanager_v2/static

EXPOSE 5000
CMD [ "python3", "Downloader.py"]
