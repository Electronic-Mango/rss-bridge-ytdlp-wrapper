from os import getenv
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

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
DEFAULT_MEDIA_NAMESPACE = getenv("DEFAULT_MEDIA_NAMESPACE", "http://search.yahoo.com/mrss/")
VIDEO_FILENAME = str(uuid4())

app = FastAPI()


@app.get("/rss")
def rss(request: Request):
    params = dict(request.query_params) | {"format": "Mrss"}
    rss_bridge_response = get(RSS_BRIDGE_URL, params=params)
    extended_response = insert_media(rss_bridge_response.text.encode(ENCODING))
    return PlainTextResponse(extended_response)


def insert_media(xml: bytes) -> str:
    tree = fromstring(xml)
    media_namespace = (tree.nsmap or {}).get("media", DEFAULT_MEDIA_NAMESPACE)
    for item in tree.xpath("//item"):
        media_url_query = urlencode({"video_url": item.find("link").text})
        media_url = f"{DOWNLOAD_API_URL}/download?{media_url_query}"
        SubElement(item, f"{{{media_namespace}}}content", {"url": media_url})
    return tostring(tree, xml_declaration=True, pretty_print=True, encoding=ENCODING)


@app.get("/download")
def download(video_url: str):
    remove_old_video_file()
    with YoutubeDL({"outtmpl": f"{VIDEO_FILENAME}.%(ext)s"}) as ytdl:
        ytdl.download(video_url)
    return FileResponse(find_video_filename())


def remove_old_video_file() -> None:
    for entry in Path(".").iterdir():
        if entry.is_file() and VIDEO_FILENAME in entry.name:
            entry.unlink(missing_ok=True)


def find_video_filename() -> str:
    for entry in Path(".").iterdir():
        if entry.is_file() and VIDEO_FILENAME in (filename := entry.name):
            return filename
