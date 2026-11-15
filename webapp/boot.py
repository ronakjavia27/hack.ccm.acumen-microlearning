"""Data preparation for the dashboard page.

build_dashboard_page(user) turns the content files into the two things the page needs:
  * the `boot` payload, which becomes the #boot JSON block read by static/js/app.js, and
  * the template context for the few values the HTML itself shows (counts, <option> lists, CSS colours).
"""
import re

from acumen_core.features import FEATURE_FLAGS
from acumen_core.vocabulary import build_specialty_map, get_allowed_specialties
from webapp import loaders
from webapp.auth import user_has_feature
from webapp.config import (
    CREDITS_TEXT,
    DISCLAIMER_TEXT,
    ESBICM_SPEC_COLORS,
    FEEDBACK_FORM_URL,
    SPEC_COLORS,
    SUBSCRIBE_FORM_URL,
    THEORY_SPEC_COLORS,
    TRIAL_DISCLAIMER_TEXT,
    UNSUBSCRIBE_FORM_URL,
)


def _css_var(prefix, name):
    """CSS custom-property name for a specialty, e.g. ("--spec-", "Infectious Diseases") -> --spec-infectiousdiseases."""
    return prefix + re.sub(r"[^a-zA-Z0-9]", "", name.lower())


def _css_declarations(variables):
    return "; ".join(f"{k}:{v}" for k, v in variables.items()) + ";"


def _doi_url(raw_doi):
    raw_doi = str(raw_doi).strip()
    if raw_doi and raw_doi.lower() not in ["none", "nan", ""]:
        if raw_doi.startswith("http://") or raw_doi.startswith("https://"):
            return raw_doi
        return f"https://doi.org/{raw_doi}"
    return "#"


def _articles(entries):
    """The ledger as the list the page shows, plus the specialties and article types it contains."""
    articles, systems, types = [], set(), set()
    for idx, entry in enumerate(entries or []):
        sys = str(entry.get("system", "General")).strip()
        typ = str(entry.get("type", "Other")).strip()
        systems.add(sys)
        types.add(typ)
        articles.append({
            "id": str(idx),
            "title": str(entry.get("title", "Unknown Title")),
            "authors": str(entry.get("authors", "Unknown Authors")),
            "system": sys,
            "journal": str(entry.get("journal", "Unknown Source")),
            "type": typ,
            "doi": _doi_url(entry.get("doi", "")),
            "file_name": str(entry.get("file_name", "")),
            "date_added": str(entry.get("date_added", "")),
            "year": str(entry.get("year", "")),
            "subtopic": str(entry.get("subtopic", sys)).strip(),
        })
    return articles, systems, types


def _subtopic_map(entries):
    """Subtopics per specialty, from the approved ledger."""
    raw = {}
    for entry in entries:
        sys = entry.get("system", "General").strip()
        st = entry.get("subtopic", sys).strip()
        raw.setdefault(sys, set()).add(st)
    return {k: sorted(v) for k, v in raw.items()}


def _specialty_colours(systems):
    """CSS variables and the specialty -> variable map, for the specialties in the data plus the colour map."""
    spec_map = build_specialty_map(get_allowed_specialties())

    def canonical(name):
        return spec_map.get(name.lower(), name)

    css_vars, js_vars = {}, {}
    for s in sorted(systems):
        canon = canonical(s)
        var_name = _css_var("--spec-", canon)
        css_vars[var_name] = SPEC_COLORS.get(canon, "#6B7280")
        js_vars[canon] = var_name
    # specialties that have a colour but no papers yet
    for s, c in SPEC_COLORS.items():
        canon = canonical(s)
        var_name = _css_var("--spec-", canon)
        if var_name not in css_vars:
            css_vars[var_name] = c
        if canon not in js_vars:
            js_vars[canon] = var_name
    return css_vars, js_vars


def _trial_summary(trial_index):
    """Filter lists and counts for the ESBICM trials view."""
    specialties = sorted(set(t["specialty"] for t in trial_index))
    subtopics = {}
    counts = {}
    for t in trial_index:
        sp = t["specialty"]
        subtopics.setdefault(sp, set()).add(t.get("subtopic", "General"))
        counts[sp] = counts.get(sp, 0) + 1
    return {
        "specialties": specialties,
        "subtopic_map": {k: sorted(v) for k, v in subtopics.items()},
        "spec_counts": counts,
        "result_cats": sorted(set(t["result_category"] for t in trial_index)),
        "types": sorted(set(t["trial_type"] for t in trial_index)),
        "colours": {_css_var("--tspec-", s): ESBICM_SPEC_COLORS.get(s, "#6B7280") for s in specialties},
        "spec_vars": {s: _css_var("--tspec-", s) for s in specialties},
    }


def _condensed_summary(condensed_index):
    return {
        "systems": sorted(set(c["system"] for c in condensed_index)),
        "result_cats": sorted(set(t.get("result_category", "") for t in condensed_index if t.get("result_category"))),
        "types": sorted(set(t.get("trial_type", "") for t in condensed_index if t.get("trial_type"))),
    }


def _theory_summary(decks, notes):
    """Specialties, colours, subtopics and card count for the Theory section."""
    specs = sorted(set(d["specialty"] for d in decks) | set(n.get("system") for n in notes if n.get("system")))
    colours = {_css_var("--theory-spec-", s): THEORY_SPEC_COLORS.get(s, "#9333EA") for s in specs}
    subtopics = {}
    for d in decks:
        for t in d.get("subtopics") or []:
            subtopics.setdefault(d["specialty"], set()).add(t)
    return {
        "specs": specs,
        "colours": colours,
        "spec_vars": {s: _css_var("--theory-spec-", s) for s in specs},
        "subtopic_map": {s: sorted(v) for s, v in subtopics.items()},
        "total_cards": sum(len(d["cards"]) for d in decks),
    }


def build_dashboard_page(user):
    """Return (boot, context) for the dashboard template, for this user."""
    entries = loaders.load_approved_ledger()
    articles, systems, types = _articles(entries)
    pearls = loaders.load_pearls()

    trial_index = loaders.load_trial_index()
    trials = _trial_summary(trial_index)
    condensed_index = loaders.load_condensed_trial_index()
    condensed = _condensed_summary(condensed_index)

    spec_css_vars, spec_js_vars = _specialty_colours(systems)

    can_see_theory = user_has_feature(user, "theory")
    flashcard_decks = loaders.load_flashcard_decks() if can_see_theory else []
    theory_notes = loaders.load_theory_notes() if can_see_theory else []
    theory = _theory_summary(flashcard_decks, theory_notes)

    related = loaders.load_related_links()

    boot = {
        "spec_vars": spec_js_vars,
        "spec_labels": sorted(spec_js_vars),
        "type_list": sorted(t for t in types if t and t.lower() not in ["none", "nan"]),
        "articles": articles,
        "pearls": pearls,
        "subtopic_map": _subtopic_map(entries),
        "show_disclaimer": bool(DISCLAIMER_TEXT.strip()),
        "trial_index": trial_index,
        "trial_spec_labels": list(trials["specialties"]),
        "trial_spec_vars": trials["spec_vars"],
        "trial_spec_counts": trials["spec_counts"],
        "trial_subtopic_map": trials["subtopic_map"],
        "trial_result_cats": trials["result_cats"],
        "trial_types_list": trials["types"],
        "condensed_index": condensed_index,
        "condensed_systems": condensed["systems"],
        "condensed_result_cats": condensed["result_cats"],
        "condensed_types_list": condensed["types"],
        "flashcard_decks": flashcard_decks,
        "theory_spec_vars": theory["spec_vars"],
        "theory_subtopic_map": theory["subtopic_map"],
        "theory_notes": theory_notes,
        "related_catalog": related["catalog"],
        "related_index": related["index"],
        "related_meta": {
            "generated_at": related.get("generated_at", ""),
            "entity_count": related.get("entity_count", 0),
            "loaded": bool(related["catalog"]),
        },
        "user_features": {f: user_has_feature(user, f) for f in FEATURE_FLAGS},
        "user_is_admin": bool(user.get("is_admin")),
        "admin_feature_flags": FEATURE_FLAGS,
        "credits_text": CREDITS_TEXT,
        "trial_disclaimer_text": TRIAL_DISCLAIMER_TEXT,
        "disclaimer_text": DISCLAIMER_TEXT,
        "feedback_form_url": FEEDBACK_FORM_URL,
        "subscribe_form_url": SUBSCRIBE_FORM_URL,
        "unsubscribe_form_url": UNSUBSCRIBE_FORM_URL,
    }
    context = {
        "spec_css_str": _css_declarations(spec_css_vars),
        "trial_spec_str": _css_declarations(trials["colours"]),
        "theory_spec_str": _css_declarations(theory["colours"]),
        "theory_notes": theory_notes,
        "theory_total_cards": theory["total_cards"],
        "theory_specs": theory["specs"],
        "trial_index": trial_index,
        "trial_specialties": trials["specialties"],
        "trial_result_cats": trials["result_cats"],
        "trial_types_list": trials["types"],
        "can_see_condensed": user_has_feature(user, "condensed_trials"),
        "condensed_index": condensed_index,
        "condensed_systems": condensed["systems"],
        "condensed_result_cats": condensed["result_cats"],
        "condensed_types_list": condensed["types"],
        "feedback_form_url": FEEDBACK_FORM_URL,
    }
    return boot, context
