"""
KHUSHI — Built-in aiohttp web server for the web player.
Serves KHUSHI/web/index.html on the configured host:port.
"""

import logging
import os

from aiohttp import web

_log = logging.getLogger(__name__)

_WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
_INDEX   = os.path.join(_WEB_DIR, "index.html")


async def _handle_index(request: web.Request) -> web.Response:
    try:
        with open(_INDEX, "r", encoding="utf-8") as f:
            html = f.read()
        return web.Response(text=html, content_type="text/html", charset="utf-8")
    except FileNotFoundError:
        return web.Response(text="<h1>Web player not found.</h1>",
                            content_type="text/html", status=404)


async def _handle_health(request: web.Request) -> web.Response:
    return web.Response(text="OK", content_type="text/plain")


async def _handle_static(request: web.Request) -> web.Response:
    filename = request.match_info.get("filename", "")
    path = os.path.join(_WEB_DIR, filename)
    if os.path.isfile(path) and os.path.abspath(path).startswith(os.path.abspath(_WEB_DIR)):
        return web.FileResponse(path)
    raise web.HTTPNotFound()


def _make_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/", _handle_index)
    app.router.add_get("/health", _handle_health)
    app.router.add_get("/static/{filename:.+}", _handle_static)
    app.router.add_get("/{filename:.+}", _handle_static)
    return app


async def start_webserver(host: str, port: int) -> web.AppRunner:
    """Start the aiohttp web server and return the runner (for later cleanup)."""
    try:
        from web_config import WEB_ENABLED
        if not WEB_ENABLED:
            _log.info("Web server disabled via web_config.WEB_ENABLED=False")
            return None
    except ImportError:
        pass

    app = _make_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    _log.info(f"Web player running on http://{host}:{port}")
    return runner
