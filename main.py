from pathlib import Path
from os import getenv
from urllib.parse import urlencode

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from httpx import get
from lxml.etree import SubElement, fromstring, tostring
from yt_dlp import YoutubeDL

load_dotenv()
RSS_BRIDGE_URL = getenv("RSS_BRIDGE_URL")
ENCODING = "UTF-8"
DOWNLOAD_API_URL = getenv("DOWNLOAD_API_URL")
VIDEO_FILENAME = getenv("VIDEO_FILENAME", "video_file.mp4")

app = FastAPI()


@app.get("/rss")
def rss(request: Request):
    params = {
        "action": "display",
        "bridge": "YoutubeBridge",
        "context": "By custom name",
        "format": "Mrss",
    }
    params |= request.query_params
    rss_bridge_response = get(RSS_BRIDGE_URL, params=params)
    extended_response = insert_media(rss_bridge_response.text.encode(ENCODING))
    return PlainTextResponse(extended_response)


def insert_media(xml: bytes) -> str:
    tree = fromstring(xml)
    for item in tree.xpath("//item"):
        media_content = SubElement(item, "media_content")
        media_url = SubElement(media_content, "url")
        media_url_query = urlencode({"video_url": item.find("link").text})
        media_url.text = f"{DOWNLOAD_API_URL}/download?{media_url_query}"
    return tostring(tree, xml_declaration=True, pretty_print=True, encoding=ENCODING)


@app.get("/download")
def download(video_url: str):
    Path(VIDEO_FILENAME).unlink(missing_ok=True)
    with YoutubeDL({"outtmpl": VIDEO_FILENAME}) as ytdl:
        ytdl.download(video_url)
    return FileResponse(VIDEO_FILENAME)
