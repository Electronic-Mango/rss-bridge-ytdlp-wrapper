from os import getenv
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse
from httpx import URL, get
from lxml.etree import SubElement, fromstring, strip_elements, tostring
from yt_dlp import YoutubeDL, match_filter_func

load_dotenv()
RSS_BRIDGE_URL = getenv("RSS_BRIDGE_URL")
DURATION_MAX = getenv("DURATION_MAX")
ENCODING = "UTF-8"
DOWNLOADED_FILENAME = str(uuid4())

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
    remove_old_video_file()
    if video_file := download_video(video_url):
        return FileResponse(video_file)
    else:
        return FileResponse(download_thumbnail(video_url))


def remove_old_video_file() -> None:
    for entry in Path(".").iterdir():
        if entry.is_file() and DOWNLOADED_FILENAME == entry.stem:
            entry.unlink(missing_ok=True)


def download_video(video_url: str) -> Path | None:
    params = prepare_target_params() | prepare_duration_params()
    return download_file(params, video_url)


def download_thumbnail(video_url: str) -> Path | None:
    params = prepare_target_params() | prepare_thumbnail_params()
    return download_file(params, video_url)


def prepare_target_params() -> dict[str, str]:
    return {"outtmpl": f"{DOWNLOADED_FILENAME}.%(ext)s"}


def prepare_duration_params() -> dict[str, str]:
    return {"match_filter": match_filter_func(f"duration<={DURATION_MAX}")} if DURATION_MAX else {}


def prepare_thumbnail_params() -> dict[str, bool]:
    return {"writethumbnail": True, "skip_download": True}


def download_file(params: dict[str, Any], video_url: str) -> Path | None:
    with YoutubeDL(params) as ytdl:
        ytdl.download(video_url)
    return find_downloaded_file()


def find_downloaded_file() -> Path | None:
    for entry in Path(".").iterdir():
        if entry.is_file() and DOWNLOADED_FILENAME == entry.stem:
            return entry
    return None
