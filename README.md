# RSS-Bridge yt-dlp wrapper

Simple REST API allowing inserting full videos into an RSS feed.
Uses [RSS-Bridge](https://github.com/RSS-Bridge/rss-bridge) for RSS feed itself and [yt-dlp](https://github.com/yt-dlp/yt-dlp) for downloading videos.

Built with [`httpx`](https://www.python-httpx.org/), [`lxml`](https://lxml.de/), [`FastAPI`](https://fastapi.tiangolo.com/) and `Python 3.12`.



## Description

API wraps an RSS-Bridge response adding its own media to RSS feed entries.
Inserted media has URL pointing back to this API to the `download` endpoint.

When RSS reader tries to download elements from RSS feed it will access this API to download full videos.

**API works only with XML RSS feeds**, it will automatically access the XML/MRSS version of feeds from RSS-Bridge.


## Usage

API requires setting `RSS_BRIDGE_URL` environment variable to a URL with working RSS-Bridge.
This can be done directly, or through `.env` file.

### Docker compose

1. Create `.env` file with `RSS_BRIDGE_URL` environment variable set
2. Start the container through `docker compose up -d --build`

### Manually

You can start this API as you would normally start [`FastAPI` API](https://fastapi.tiangolo.com/deployment/manually/) using `main.py` file and `app` API object, e.g.:
```bash
fastapi run main.py

# or

uvicorn main:app --host 0.0.0.0 --port 80
```



## Endpoints

API has an automatically generated documentation at `docs` or `redoc` endpoints.

| Endpoint   | Query parameters                                                                                                                                                            | Response        |
|------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| `download` | `video_url` - URL passed to `yt-dlp` to download.                                                                                                                           | Downloaded file |
| `rss`      | All query parameters normally passed to RSS-Bridge.<br/>`remove_existing_media` - allows specifying whether existing media should be removed from RSS, defaults to `False`. | RSS feed as XML |



## Examples

Search for RSS feed through RSS-Bridge and copy all query parameters:
```http
https://rss-bridge.org/bridge01/?action=display&bridge=YoutubeBridge&context=By+custom+name&custom=tombates&duration_min=&duration_max=&format=Mrss
```

In this case query string is:
```http
?action=display&bridge=YoutubeBridge&context=By+custom+name&custom=tombates&duration_min=&duration_max=&format=Mrss
```

Paste it over to `rss` endpoint of this API
(`format` parameter will be set to `Mrss` in the API, passed value here will be ignored).
You can also optionally set `remove_existing_media=true` if you want existing media elements to be removed:
```http
localhost:8123/rss?action=display&bridge=YoutubeBridge&context=By+custom+name&custom=tombates&duration_min=&duration_max=&format=Mrss
localhost:8123/rss?action=display&bridge=YoutubeBridge&context=By+custom+name&custom=tombates&duration_min=&duration_max=&format=Mrss&remove_existing_media=true
```

Each `item` element in the RSS feed XML should have a `media:content` element with `url` attribute:
```xml
<item>
  ...
  <media:content url="http://localhost:8123/download?video_url=https%3A%2F%2Fwww.youtube.com%2Fwatch%3Fv%3DPc0uWhgLJ6Y"/>
</item>
```

That URL will use `download` endpoint of this API to download full video through yt-dlp.



## Disclaimer

This API is not affiliated with [RSS-Bridge](https://github.com/RSS-Bridge/rss-bridge) or [yt-dlp](https://github.com/yt-dlp/yt-dlp), it's an independent project.

