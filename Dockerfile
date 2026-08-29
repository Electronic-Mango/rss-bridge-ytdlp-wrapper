FROM python:3.12-alpine

COPY --from=denoland/deno:bin /deno /usr/local/bin/deno
RUN apk add ffmpeg

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENTRYPOINT ["fastapi", "run", "main.py"]
CMD ["--host", "0.0.0.0"]
