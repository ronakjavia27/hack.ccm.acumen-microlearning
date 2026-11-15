"""entity_catalog(with_excerpt=False): the portal's cheaper catalog (no content files are read)."""
import pytest

from acumen_core import linking
from webapp import loaders


@pytest.fixture(scope="module")
def full():
    return linking.entity_catalog()


@pytest.fixture(scope="module")
def fast():
    return linking.entity_catalog(with_excerpt=False)


def test_default_still_includes_excerpts_for_the_llm_linker(full):
    assert full and sum(1 for e in full if e["excerpt"]) > len(full) * 0.9


def test_fast_catalog_has_the_same_entities_and_fields_but_no_excerpts(full, fast):
    assert [e["id"] for e in fast] == [e["id"] for e in full]
    strip = lambda e: {k: v for k, v in e.items() if k != "excerpt"}  # noqa: E731
    assert [strip(e) for e in fast] == [strip(e) for e in full]
    assert all(e["excerpt"] == "" for e in fast) and set(fast[0]) == set(full[0])


def test_every_kind_is_covered(fast):
    assert {e["kind"] for e in fast} >= {"paper", "theory", "flashcard_deck"}


def test_related_links_are_identical_to_what_the_full_catalog_would_give(monkeypatch):
    real = linking.entity_catalog
    fast_result = loaders.load_related_links.uncached()
    monkeypatch.setattr(linking, "entity_catalog", lambda with_excerpt=True: real(with_excerpt=True))
    assert loaders.load_related_links.uncached() == fast_result


def test_the_fast_path_reads_no_content_files(monkeypatch):
    opened = []
    real_open = open

    def spy(path, *a, **k):
        opened.append(str(path))
        return real_open(path, *a, **k)

    monkeypatch.setattr("builtins.open", spy)
    linking.summaries_entities(with_excerpt=False)
    linking.theory_entities(with_excerpt=False)
    payloads = [p for p in opened if p.endswith(".json") and "output_files" in p and "sent_summaries" not in p]
    notes = [p for p in opened if "Theory MDs" in p]
    assert not payloads and not notes, (payloads[:2], notes[:2])
