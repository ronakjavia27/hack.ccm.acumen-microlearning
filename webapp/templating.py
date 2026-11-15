"""Jinja environment, static-asset URLs (content-hashed) and the cache-aware static file handler."""
import hashlib
import json

from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from webapp.config import WEBAPP_DIR


# autoescape stays off on purpose: the page used to be one big f-string, and the markup handed
# to the template (option lists, SVG, <script> tags) is trusted. Data that comes from the
# content files travels through the escaped #boot JSON block instead (see script_json).
_jinja = Environment(
    loader=FileSystemLoader(str(WEBAPP_DIR / "templates")),
    autoescape=False,
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)


def render_template(name, **ctx):
    return _jinja.get_template(name).render(**ctx)


def script_json(obj):
    """JSON for a <script type="application/json"> block. '<', '>' and '&' are written as
    unicode escapes, so data such as a pearl containing "</script>" can never end the tag."""
    return json.dumps(obj).replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


_asset_hashes = {}


def asset_url(rel):
    """/static/<rel>?v=<content hash>: the hash makes the long-lived cache header safe."""
    path = WEBAPP_DIR / "static" / rel
    mtime = path.stat().st_mtime_ns
    cached = _asset_hashes.get(rel)
    if not cached or cached[0] != mtime:
        cached = (mtime, hashlib.sha1(path.read_bytes()).hexdigest()[:10])
        _asset_hashes[rel] = cached
    return f"/static/{rel}?v={cached[1]}"


class AssetFiles(StaticFiles):
    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        if resp.status_code == 200:
            versioned = b"v=" in scope.get("query_string", b"")
            resp.headers["Cache-Control"] = (
                "public, max-age=31536000, immutable" if versioned else "public, max-age=300"
            )
        return resp
