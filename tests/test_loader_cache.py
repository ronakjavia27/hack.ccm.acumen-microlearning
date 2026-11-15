"""The content loaders are cached against the files they read."""
import os

import pytest

from webapp import loaders

CACHED = ["load_approved_ledger", "load_pearls", "load_trial_index", "load_flashcard_decks",
          "load_theory_notes", "load_related_links", "load_condensed_trial_index"]


def bump(path, seconds=10):
    """Move a file's mtime so a rewrite is visible even on coarse-grained filesystems."""
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + seconds * 10**9))


# ---------- signature ----------

def test_signature_tracks_adds_changes_and_removals(tmp_path):
    (tmp_path / "a.json").write_text("1")
    d = tmp_path / "dir"
    d.mkdir()
    (d / "b.json").write_text("22")
    paths = [str(tmp_path / "a.json"), str(d), str(tmp_path / "missing.json")]
    first = loaders._file_signature(paths)
    assert first == loaders._file_signature(paths)  # stable while nothing changes
    assert any(p.endswith("missing.json") and m is None for p, m, _ in first)

    (d / "c.json").write_text("3")
    added = loaders._file_signature(paths)
    assert added != first
    (d / "c.json").unlink()
    assert loaders._file_signature(paths) == first
    (d / "b.json").write_text("2222")
    assert loaders._file_signature(paths) != first
    (tmp_path / "missing.json").write_text("now here")
    assert loaders._file_signature(paths) != first


def test_signature_walks_nested_directories(tmp_path):
    nested = tmp_path / "x" / "y"
    nested.mkdir(parents=True)
    before = loaders._file_signature([str(tmp_path)])
    (nested / "deep.md").write_text("hi")
    assert loaders._file_signature([str(tmp_path)]) != before


# ---------- decorator ----------

@pytest.fixture
def counted(tmp_path):
    f = tmp_path / "data.json"
    f.write_text("[1]")
    calls = []

    @loaders._cached_by_files(lambda: [str(f)])
    def load():
        calls.append(1)
        return {"text": f.read_text()}

    load.calls, load.file = calls, f
    return load


def test_cache_hit_reuses_the_same_object_and_skips_the_loader(counted):
    a, b = counted(), counted()
    assert a is b and len(counted.calls) == 1


def test_cache_reloads_when_the_file_changes(counted):
    first = counted()
    counted.file.write_text("[1, 2, 3]")
    bump(counted.file)
    second = counted()
    assert second["text"] == "[1, 2, 3]" and second is not first and len(counted.calls) == 2
    assert counted() is second and len(counted.calls) == 2


def test_a_removed_file_is_not_answered_from_the_cache(counted):
    assert counted()["text"] == "[1]"
    counted.file.unlink()
    with pytest.raises(FileNotFoundError):  # the loader runs again and fails as it always did
        counted()
    counted.file.write_text("[9]")
    assert counted()["text"] == "[9]"
    assert len(counted.calls) == 3


def test_a_result_computed_while_the_file_changed_is_not_cached(tmp_path):
    f = tmp_path / "data.json"
    f.write_text("old")
    calls = []

    @loaders._cached_by_files(lambda: [str(f)])
    def load():
        text = f.read_text()
        calls.append(text)
        if len(calls) == 1:  # the pipeline rewrites the file in the middle of our read
            f.write_text("newer content")
            bump(f)
        return text

    assert load() == "old"
    assert load() == "newer content"  # not served from a cache entry built from half-old data
    assert load() == "newer content" and len(calls) == 2


def test_cache_clear_and_uncached_are_available(counted):
    counted()
    counted.cache_clear()
    counted()
    assert len(counted.calls) == 2
    counted.uncached()
    assert len(counted.calls) == 3


# ---------- the real loaders ----------

@pytest.mark.parametrize("name", CACHED)
def test_every_content_loader_is_cached(name):
    fn = getattr(loaders, name)
    assert callable(fn.cache_clear) and callable(fn.uncached)


def test_loaders_return_the_same_object_until_a_file_changes():
    for name in CACHED:
        fn = getattr(loaders, name)
        fn.cache_clear()
        assert fn() is fn(), name


def test_edited_pearls_file_is_picked_up(tmp_path, monkeypatch):
    p = tmp_path / "pearls.json"
    p.write_text('[{"id": "1", "pearl": "first"}]')
    monkeypatch.setattr(loaders, "PEARLS_JSON", str(p))
    loaders.load_pearls.cache_clear()
    assert [x["pearl"] for x in loaders.load_pearls()] == ["first"]
    p.write_text('[{"id": "1", "pearl": "first"}, {"id": "2", "pearl": "second"}]')
    bump(p)
    assert [x["pearl"] for x in loaders.load_pearls()] == ["first", "second"]
    monkeypatch.undo()
    loaders.load_pearls.cache_clear()


def test_new_condensed_trial_file_is_picked_up(tmp_path, monkeypatch):
    root = tmp_path / "Sepsis"
    root.mkdir()
    (root / "alpha.json").write_text('{"trial_name": "Alpha", "year": "2020"}')
    monkeypatch.setattr(loaders, "CONDENSED_TRIALS_DIR", str(tmp_path))
    loaders.load_condensed_trial_index.cache_clear()
    assert [t["name"] for t in loaders.load_condensed_trial_index()] == ["alpha"]
    (root / "beta.json").write_text('{"trial_name": "Beta"}')
    assert [t["name"] for t in loaders.load_condensed_trial_index()] == ["alpha", "beta"]
    monkeypatch.undo()
    loaders.load_condensed_trial_index.cache_clear()


def test_serving_requests_never_corrupts_the_shared_cache(dev_client):
    """Cached values are shared between requests, so no endpoint may modify what a loader returned."""
    for name in CACHED:
        getattr(loaders, name).cache_clear()
    for path in ("/", "/api/pearls?limit=50", "/api/pearls?q=fluid", "/api/search?q=sepsis", "/api/trials?limit=50",
                 "/api/trials/stats", "/api/condensed-trials", "/"):
        assert dev_client.get(path).status_code == 200, path
    for name in CACHED:
        fn = getattr(loaders, name)
        assert fn() == fn.uncached(), f"{name}: the cached value no longer matches a fresh read of the files"
