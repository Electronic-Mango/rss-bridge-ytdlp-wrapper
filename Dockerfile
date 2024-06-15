FROM python:3.12-alpine

RUN apk add ffmpeg

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

ENTRYPOINT ["fastapi"]
CMD ["run", "main.py", "--host", "0.0.0.0"]
