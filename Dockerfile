FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=10000

WORKDIR /app

COPY pyproject.toml README.md ./
COPY simucespe ./simucespe
COPY data/parsed ./data/parsed

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN mkdir -p /app/data/runtime

EXPOSE 10000

CMD ["simucespe-api", "--host", "0.0.0.0"]

