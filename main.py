from os import getenv
from pathlib import Path
from typing import Any, Callable
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response
from httpx import URL, get
from lxml.etree import Element, SubElement, fromstring, strip_elements, tostring
from starlette.background import BackgroundTask
from yt_dlp import YoutubeDL, match_filter_func

load_dotenv()
RSS_BRIDGE_URL = getenv("RSS_BRIDGE_URL")
DURATION_MAX = getenv("DURATION_MAX")
FORMAT = getenv("FORMAT")
FORMAT_SORT = getenv("FORMAT_SORT")
ENCODING = "UTF-8"

app = FastAPI()


@app.get("/rss")
def rss(request: Request, remove_existing_media: bool = False):
    return handle_rss(request, remove_existing_media)


@app.get("/shorts")
def shorts(request: Request, remove_existing_media: bool = False):
    return handle_rss(request, remove_existing_media, shorts_filter)


def handle_rss(
    request: Request,
    remove_existing_media: bool,
    remove_entries_filter: Callable[[Element], bool] = None,
) -> Response:
    params = dict(request.query_params) | {"format": "Mrss"}
    params.pop("remove_existing_media", None)
    bridge_response = get(RSS_BRIDGE_URL, params=params)
    rss_text = bridge_response.text.encode(ENCODING)
    rss_tree = fromstring(rss_text)
    filter_entries(rss_tree, remove_entries_filter)
    insert_media(rss_tree, remove_existing_media, request.base_url)
    response = tostring(rss_tree, xml_declaration=True, pretty_print=True, encoding=ENCODING)
    return PlainTextResponse(response)


def filter_entries(tree: Element, remove_entries_filter: Callable[[Element], bool] | None) -> None:
    if not remove_entries_filter:
        return
    for item in tree.xpath("//item"):
        if remove_entries_filter(item):
            item.getparent().remove(item)


def shorts_filter(item: Element) -> bool:
    title = item.find("title").text
    description = item.find("description").text
    return "#short" not in f"{title} {description}".lower()


def insert_media(tree: Element, remove_existing_media: bool, base_url: URL) -> None:
    download_url = base_url.replace(path="/download")
    media_namespace = (tree.nsmap or {}).get("media", "http://search.yahoo.com/mrss/")
    if remove_existing_media:
        strip_elements(tree, f"{{{media_namespace}}}content")
    for item in tree.xpath("//item"):
        item_download_url = download_url.include_query_params(video_url=item.find("link").text)
        SubElement(item, f"{{{media_namespace}}}content", {"url": str(item_download_url)})


@app.get("/download")
def download(video_url: str):
    filename = str(uuid4())
    file = download_video(video_url, filename) or download_thumbnail(video_url, filename)
    return FileResponse(file, background=BackgroundTask(lambda: file.unlink()))


def download_video(video_url: str, filename: str) -> Path | None:
    params = prepare_target_params(filename)
    if FORMAT:
        params["format"] = FORMAT
    if FORMAT_SORT:
        params["format_sort"] = [FORMAT_SORT]
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
