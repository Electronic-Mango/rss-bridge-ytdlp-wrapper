FROM python:3.12-alpine

RUN wget 'https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz'
RUN apk add xz
RUN tar --xz -xvf ffmpeg-master-latest-linuxarm64-gpl.tar.xz ffmpeg-master-latest-linuxarm64-gpl/bin/
RUN mv ffmpeg-master-latest-linuxarm64-gpl/bin/ ffmpeg/
RUN rm -rf ffmpeg-*
RUN ln -s /ffmpeg/ff* /usr/local/bin/

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

CMD ["uvicorn", "--host", "0.0.0.0", "main:app"]
