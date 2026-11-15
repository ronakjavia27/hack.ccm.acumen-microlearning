"""webapp/boot.py: the data the dashboard page is built from."""
import pytest

from webapp import boot, loaders


def test_css_var_names():
    assert boot._css_var("--spec-", "Infectious Diseases") == "--spec-infectiousdiseases"
    assert boot._css_var("--tspec-", "Trauma, Hemorrhage & VTE") == "--tspec-traumahemorrhagevte"


def test_css_declarations():
    assert boot._css_declarations({"--a": "#111", "--b": "#222"}) == "--a:#111; --b:#222;"
    assert boot._css_declarations({}) == ";"


@pytest.mark.parametrize("raw,expected", [
    ("10.1000/xyz", "https://doi.org/10.1000/xyz"), (" 10.1000/xyz ", "https://doi.org/10.1000/xyz"),
    ("https://doi.org/10.1/a", "https://doi.org/10.1/a"), ("http://example.org/x", "http://example.org/x"),
    ("", "#"), ("None", "#"), ("nan", "#"), ("  ", "#"), ("NaN", "#"),
])
def test_doi_url(raw, expected):
    assert boot._doi_url(raw) == expected


def test_articles_defaults_and_collected_sets():
    articles, systems, types = boot._articles([
        {"title": "T1", "system": " Sepsis ", "type": "RCT", "doi": "10.1/a", "file_name": "a.json", "year": 2021},
        {"system": "Cardiology"},
    ])
    assert [a["id"] for a in articles] == ["0", "1"]
    assert articles[0] == {"id": "0", "title": "T1", "authors": "Unknown Authors", "system": "Sepsis", "journal": "Unknown Source",
                           "type": "RCT", "doi": "https://doi.org/10.1/a", "file_name": "a.json", "date_added": "", "year": "2021",
                           "subtopic": "Sepsis"}
    assert articles[1]["title"] == "Unknown Title" and articles[1]["type"] == "Other" and articles[1]["doi"] == "#"
    assert systems == {"Sepsis", "Cardiology"} and types == {"RCT", "Other"}
    assert boot._articles(None) == ([], set(), set()) and boot._articles([]) == ([], set(), set())


def test_subtopic_map_is_sorted_per_system():
    entries = [{"system": "Sepsis", "subtopic": "Shock"}, {"system": "Sepsis", "subtopic": "Antibiotics"},
               {"system": "Sepsis ", "subtopic": " Shock "}, {"system": "Trauma"}]
    assert boot._subtopic_map(entries) == {"Sepsis": ["Antibiotics", "Shock"], "Trauma": ["Trauma"]}


def test_specialty_colours_include_unused_specialties_and_are_deterministic():
    css, js = boot._specialty_colours({"Sepsis", "Cardiology"})
    assert "--spec-sepsis" in css and "--spec-cardiology" in css
    assert js["Sepsis"] == "--spec-sepsis"
    # specialties that only exist in the colour map are still present
    assert len(js) >= 20
    assert boot._specialty_colours({"Sepsis", "Cardiology"}) == (css, js)
    # data order first (sorted), then the rest of the colour map
    assert list(css)[:2] == ["--spec-cardiology", "--spec-sepsis"]


def test_trial_summary():
    index = [
        {"specialty": "Sepsis", "subtopic": "Shock", "result_category": "Positive", "trial_type": "RCT"},
        {"specialty": "Sepsis", "subtopic": "Fluids", "result_category": "Neutral", "trial_type": "RCT"},
        {"specialty": "ARDS", "result_category": "Positive", "trial_type": "Meta-analysis"},
    ]
    s = boot._trial_summary(index)
    assert s["specialties"] == ["ARDS", "Sepsis"]
    assert s["spec_counts"] == {"Sepsis": 2, "ARDS": 1}
    assert s["subtopic_map"] == {"Sepsis": ["Fluids", "Shock"], "ARDS": ["General"]}
    assert s["result_cats"] == ["Neutral", "Positive"] and s["types"] == ["Meta-analysis", "RCT"]
    assert s["spec_vars"] == {"ARDS": "--tspec-ards", "Sepsis": "--tspec-sepsis"}
    assert set(s["colours"]) == {"--tspec-ards", "--tspec-sepsis"}
    assert boot._trial_summary([])["specialties"] == []


def test_condensed_summary_ignores_empty_values():
    s = boot._condensed_summary([{"system": "B", "result_category": "Positive", "trial_type": ""},
                                 {"system": "A", "result_category": "", "trial_type": "RCT"}])
    assert s == {"systems": ["A", "B"], "result_cats": ["Positive"], "types": ["RCT"]}


def test_theory_summary():
    decks = [{"specialty": "Sepsis", "cards": [1, 2, 3], "subtopics": ["fluids", "pressors"]},
             {"specialty": "Sepsis", "cards": [1], "subtopics": ["fluids"]}, {"specialty": "ARDS", "cards": [], "subtopics": None}]
    notes = [{"system": "Trauma"}, {"system": ""}, {}]
    s = boot._theory_summary(decks, notes)
    assert s["specs"] == ["ARDS", "Sepsis", "Trauma"] and s["total_cards"] == 4
    assert s["subtopic_map"] == {"Sepsis": ["fluids", "pressors"]}
    assert s["spec_vars"]["Sepsis"] == "--theory-spec-sepsis" and "--theory-spec-trauma" in s["colours"]
    empty = boot._theory_summary([], [])
    assert empty == {"specs": [], "colours": {}, "spec_vars": {}, "subtopic_map": {}, "total_cards": 0}


@pytest.fixture
def tiny_site(monkeypatch):
    monkeypatch.setattr(loaders, "load_approved_ledger", lambda: [{"title": "P", "system": "Sepsis", "type": "RCT", "file_name": "p.json"}])
    monkeypatch.setattr(loaders, "load_pearls", lambda: [{"id": "1", "pearl": "x"}])
    monkeypatch.setattr(loaders, "load_trial_index", lambda: [{"specialty": "Sepsis", "result_category": "Positive", "trial_type": "RCT"}])
    monkeypatch.setattr(loaders, "load_condensed_trial_index", lambda: [{"system": "Sepsis", "name": "n"}])
    monkeypatch.setattr(loaders, "load_flashcard_decks", lambda: [{"specialty": "Sepsis", "cards": [1, 2], "subtopics": ["t"]}])
    monkeypatch.setattr(loaders, "load_theory_notes", lambda: [{"system": "Sepsis"}])
    monkeypatch.setattr(loaders, "load_related_links", lambda: {"catalog": [], "index": {}, "generated_at": "", "entity_count": 0})


def test_page_for_a_user_without_theory_has_no_theory_data(tiny_site):
    b, ctx = boot.build_dashboard_page({"email": "u@x.co", "features": {}})
    assert b["flashcard_decks"] == [] and b["theory_notes"] == [] and ctx["theory_specs"] == [] and ctx["theory_total_cards"] == 0
    assert b["user_is_admin"] is False and ctx["can_see_condensed"] is False
    assert b["related_meta"] == {"generated_at": "", "entity_count": 0, "loaded": False}


def test_page_for_a_user_with_theory_and_condensed(tiny_site):
    user = {"email": "u@x.co", "features": {"theory": True, "condensed_trials": True}}
    b, ctx = boot.build_dashboard_page(user)
    assert len(b["flashcard_decks"]) == 1 and ctx["theory_total_cards"] == 2 and ctx["theory_specs"] == ["Sepsis"]
    assert ctx["can_see_condensed"] is True and ctx["condensed_systems"] == ["Sepsis"]
    assert b["user_features"]["theory"] is True and b["user_features"]["bookmarks"] is True


def test_admin_sees_everything(tiny_site):
    b, ctx = boot.build_dashboard_page({"email": "a@x.co", "is_admin": True})
    assert b["user_is_admin"] is True and ctx["can_see_condensed"] is True and all(b["user_features"].values())
    assert b["admin_feature_flags"] == list(b["user_features"])


def test_context_and_boot_agree(tiny_site):
    b, ctx = boot.build_dashboard_page({"email": "a@x.co", "is_admin": True})
    assert ctx["trial_specialties"] == b["trial_spec_labels"] and ctx["trial_result_cats"] == b["trial_result_cats"]
    assert ctx["condensed_index"] is b["condensed_index"] and ctx["trial_index"] is b["trial_index"]
    assert ctx["spec_css_str"].endswith(";") and "--spec-sepsis:" in ctx["spec_css_str"]
