from os import getenv
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from httpx import URL, get
from lxml.etree import SubElement, fromstring, strip_elements, tostring
from starlette.background import BackgroundTask
from yt_dlp import YoutubeDL, match_filter_func

load_dotenv()
RSS_BRIDGE_URL = getenv("RSS_BRIDGE_URL")
DURATION_MAX = getenv("DURATION_MAX")
ENCODING = "UTF-8"

app = FastAPI()


@app.get("/rss")
def rss(request: Request, remove_existing_media: bool = False):
    params = dict(request.query_params) | {"format": "Mrss"}
    params.pop("remove_existing_media", None)
    bridge_response = get(RSS_BRIDGE_URL, params=params)
    rss_text = bridge_response.text.encode(ENCODING)
    extended_response = insert_media(rss_text, remove_existing_media, request.base_url)
    return PlainTextResponse(extended_response)


def insert_media(xml: bytes, remove_existing_media: bool, base_url: URL) -> str:
    download_url = base_url.replace(path="/download")
    tree = fromstring(xml)
    media_namespace = (tree.nsmap or {}).get("media", "http://search.yahoo.com/mrss/")
    if remove_existing_media:
        strip_elements(tree, f"{{{media_namespace}}}content")
    for item in tree.xpath("//item"):
        item_download_url = download_url.include_query_params(video_url=item.find("link").text)
        SubElement(item, f"{{{media_namespace}}}content", {"url": str(item_download_url)})
    return tostring(tree, xml_declaration=True, pretty_print=True, encoding=ENCODING)


@app.get("/download")
def download(video_url: str):
    filename = str(uuid4())
    file = download_video(video_url, filename) or download_thumbnail(video_url, filename)
    return FileResponse(file, background=BackgroundTask(lambda: file.unlink()))


def download_video(video_url: str, filename: str) -> Path | None:
    params = prepare_target_params(filename)
    if DURATION_MAX:
        params["match_filter"] = match_filter_func(f"duration<={DURATION_MAX}")
    return download_file(params, video_url, filename)


def download_thumbnail(video_url: str, filename: str) -> Path | None:
    params = prepare_target_params(filename) | {"writethumbnail": True, "skip_download": True}
    return download_file(params, video_url, filename)


def prepare_target_params(filename: str) -> dict[str, str]:
    return {"outtmpl": f"{filename}.%(ext)s"}


def download_file(params: dict[str, Any], video_url: str, filename: str) -> Path | None:
    with YoutubeDL(params) as ytdl:
        ytdl.download(video_url)
    return find_downloaded_file(filename)


def find_downloaded_file(filename: str) -> Path | None:
    return next((e for e in Path().iterdir() if e.is_file() and e.stem == filename), None)
