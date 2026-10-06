FROM denoland/deno:bin-2.6.0 AS deno
FROM python:3.12-slim

COPY --from=deno /deno /usr/local/bin/deno

ENV PYTHONUNBUFFERED=1
ENV PATH="/usr/local/bin:${PATH}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-10000} --timeout 650 server:app"]
