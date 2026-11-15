"""The route table is the contract of the portal.

Routes are grouped into routers (webapp/routers/), so their order is not part of the contract; what
must hold is that the set of routes is unchanged and that no route is hidden behind an earlier,
more general one (e.g. /api/admin/users/defaults vs /api/admin/users/{email:path}).
"""
import json
import re
from pathlib import Path

from webapp.app import create_app

EXPECTED = Path(__file__).with_name("expected_routes.json")


def flat_routes(app):
    """Every effective route in matching order. Newer FastAPI keeps included routers as wrappers."""
    def walk(routes):
        for r in routes:
            inner = getattr(r, "original_router", None)
            if inner is not None:
                yield from walk(inner.routes)
            else:
                yield r
    return list(walk(app.routes))


def table(app):
    return [[",".join(sorted(getattr(r, "methods", None) or [])), r.path] for r in flat_routes(app)]


def test_route_set_unchanged():
    assert sorted(table(create_app(google=True))) == sorted(json.loads(EXPECTED.read_text()))


def test_google_routes_only_on_the_google_app():
    google_paths = {p for _, p in table(create_app(google=True))}
    plain_paths = {p for _, p in table(create_app())}
    assert {"/api/auth/google", "/api/auth/google/callback"} <= google_paths
    assert not {"/api/auth/google", "/api/auth/google/callback"} & plain_paths
    assert google_paths - plain_paths == {"/api/auth/google", "/api/auth/google/callback"}


def test_no_route_is_shadowed_by_an_earlier_one():
    routes = [r for r in flat_routes(create_app(google=True)) if getattr(r, "methods", None)]
    shadowed = []
    for j, later in enumerate(routes):
        sample = re.sub(r"\{[^}:]+:path\}", "x/y", later.path)
        sample = re.sub(r"\{[^}]+\}", "x", sample)
        for earlier in routes[:j]:
            if earlier.path != later.path and earlier.methods & later.methods and earlier.path_regex.match(sample):
                shadowed.append(f"{later.path} is hidden by {earlier.path}")
    assert not shadowed, shadowed


def test_shadow_check_would_catch_the_admin_users_ordering_bug():
    """Guard the guard: put the catch-all before the specific route and the check must fail."""
    from fastapi import APIRouter, FastAPI

    router = APIRouter()
    router.put("/api/admin/users/{email:path}")(lambda: None)
    router.put("/api/admin/users/defaults")(lambda: None)
    app = FastAPI()
    app.include_router(router)
    routes = [r for r in flat_routes(app) if getattr(r, "methods", None) and r.path.startswith("/api/admin")]
    later = routes[1]
    assert routes[0].path_regex.match(later.path)  # the catch-all matches the literal path first
