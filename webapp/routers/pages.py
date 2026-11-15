"""Sign-in page, the logged-in dashboard page and the favicon."""
import os
import re

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse

from acumen_core.vocabulary import build_specialty_map, get_allowed_specialties
from webapp import loaders
from webapp.auth import (
    dev_login_allowed,
    FEATURE_FLAGS,
    get_session_user,
    local_dev_login,
    SESSION_COOKIE_NAME,
    set_session_cookie,
    user_has_feature,
)
from webapp.config import (
    CREDITS_TEXT,
    DISCLAIMER_TEXT,
    ECG_SVG,
    ESBICM_SPEC_COLORS,
    FEEDBACK_FORM_URL,
    SPEC_COLORS,
    SUBSCRIBE_FORM_URL,
    TRIAL_DISCLAIMER_TEXT,
    UNSUBSCRIBE_FORM_URL,
)
from webapp.templating import asset_url, render_template, script_json

router = APIRouter()


# ---- Landing page HTML ----
def _landing_disclaimer(text):
    """The sign-in page shows the portal's disclaimer, minus its closing 'click Proceed' paragraph
    (there is no Proceed button before login)."""
    paragraphs = text.rstrip().split("\n\n")
    if paragraphs and paragraphs[-1].lstrip().startswith('By clicking "Proceed"'):
        paragraphs = paragraphs[:-1]
    return "\n\n".join(paragraphs)


LANDING_DISCLAIMER_TEXT = _landing_disclaimer(DISCLAIMER_TEXT)


def _render_landing(request):
    """Sign-in page. create_app(google=True) sets app.state.google_auth, which switches on the Google section."""
    google = getattr(request.app.state, "google_auth", None)
    return render_template(
        "landing.html",
        google=bool(google),
        css_url=asset_url("css/landing.css"),
        js_url=asset_url("js/landing.js"),
        google_js_url=asset_url("js/google_signin.js"),
        config_json=script_json({"disclaimer_text": LANDING_DISCLAIMER_TEXT, "google": google}),
    )


@router.get("/", response_class=HTMLResponse)
async def render_dashboard(request: Request, response: Response):
    user = get_session_user(request)
    if not user:
        return HTMLResponse(content=_render_landing(request))
    entries = loaders.load_approved_ledger()

    articles_list = []
    systems_set = set()
    types_set = set()
    if entries:
        for idx, entry in enumerate(entries):
            raw_doi = str(entry.get("doi", "")).strip()
            clean_doi_url = "#"
            if raw_doi and raw_doi.lower() not in ["none", "nan", ""]:
                if raw_doi.startswith("http://") or raw_doi.startswith("https://"):
                    clean_doi_url = raw_doi
                else:
                    clean_doi_url = f"https://doi.org/{raw_doi}"
            sys = str(entry.get("system", "General")).strip()
            typ = str(entry.get("type", "Other")).strip()
            systems_set.add(sys)
            types_set.add(typ)
            articles_list.append({
                "id": str(idx),
                "title": str(entry.get("title", "Unknown Title")),
                "authors": str(entry.get("authors", "Unknown Authors")),
                "system": sys,
                "journal": str(entry.get("journal", "Unknown Source")),
                "type": typ,
                "doi": clean_doi_url,
                "file_name": str(entry.get("file_name", "")),
                "date_added": str(entry.get("date_added", "")),
                "year": str(entry.get("year", "")),
                "subtopic": str(entry.get("subtopic", sys)).strip(),
            })

    pearls = loaders.load_pearls()
    trial_index = loaders.load_trial_index()
    trial_specialties = sorted(set(t["specialty"] for t in trial_index))
    condensed_index = loaders.load_condensed_trial_index()
    condensed_systems = sorted(set(c["system"] for c in condensed_index))
    trial_subtopic_map = {}
    for t in trial_index:
        sp = t["specialty"]
        st = t.get("subtopic", "General")
        if sp not in trial_subtopic_map:
            trial_subtopic_map[sp] = set()
        trial_subtopic_map[sp].add(st)
    trial_subtopic_map = {k: sorted(v) for k, v in trial_subtopic_map.items()}
    trial_spec_counts = {}
    for t in trial_index:
        sp = t["specialty"]
        trial_spec_counts[sp] = trial_spec_counts.get(sp, 0) + 1
    trial_result_cats = sorted(set(t["result_category"] for t in trial_index))
    trial_types_list = sorted(set(t["trial_type"] for t in trial_index))

    show_disclaimer = bool(DISCLAIMER_TEXT.strip())

    # Build subtopic map per system (from data + approved subtopics)
    raw_subtopic_map = {}
    for entry in entries:
        sys = entry.get("system", "General").strip()
        st = entry.get("subtopic", sys).strip()
        if sys not in raw_subtopic_map:
            raw_subtopic_map[sys] = set()
        raw_subtopic_map[sys].add(st)
    subtopic_map = {k: sorted(v) for k, v in raw_subtopic_map.items()}

    # Build CSS variable mapping for specialties using canonical vocabulary
    allowed_specialties = get_allowed_specialties()
    spec_map = build_specialty_map(allowed_specialties)

    def canonical_specialty(name):
        """Normalize specialty name to canonical form."""
        return spec_map.get(name.lower(), name)

    spec_css_vars = {}
    spec_css_vars_js = {}
    for s in sorted(systems_set):
        canon = canonical_specialty(s)
        color = SPEC_COLORS.get(canon, "#6B7280")
        var_name = "--spec-" + re.sub(r"[^a-zA-Z0-9]", "", canon.lower())
        spec_css_vars[var_name] = color
        spec_css_vars_js[canon] = var_name

    # Additional colors for specialties not in data but in color map
    for s, c in SPEC_COLORS.items():
        canon = canonical_specialty(s)
        var_name = "--spec-" + re.sub(r"[^a-zA-Z0-9]", "", canon.lower())
        if var_name not in spec_css_vars:
            spec_css_vars[var_name] = c
        if canon not in spec_css_vars_js:
            spec_css_vars_js[canon] = var_name

    spec_css_str = "; ".join(f"{k}:{v}" for k, v in spec_css_vars.items()) + ";"

    type_list = sorted(
        t for t in types_set if t and t.lower() not in ["none", "nan"]
    )

    # Trial CSS vars
    trial_spec_css = {}
    for s in trial_specialties:
        color = ESBICM_SPEC_COLORS.get(s, "#6B7280")
        var_name = "--tspec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower())
        trial_spec_css[var_name] = color
    trial_spec_str = "; ".join(f"{k}:{v}" for k, v in trial_spec_css.items()) + ";"
    trial_spec_vars = {s: "--tspec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower()) for s in trial_specialties}
    condensed_result_cats = sorted(set(t.get("result_category", "") for t in condensed_index if t.get("result_category")))
    condensed_types_list = sorted(set(t.get("trial_type", "") for t in condensed_index if t.get("trial_type")))

    # Theory flashcard decks (unified store) + Theory Topics (markdown notes)
    flashcard_decks = loaders.load_flashcard_decks() if user_has_feature(user, "theory") else []
    theory_notes = loaders.load_theory_notes() if user_has_feature(user, "theory") else []
    THEORY_SPEC_COLORS = {
        "Cardiology": "#C6554B", "Pulmonology": "#3A7CA5", "Neurology": "#6B5B95",
        "Nephrology": "#B08D57", "Gastroenterology": "#14B8A6",
        "Infectious Diseases": "#4F8A6D", "Hematology": "#E11D48",
        "Endocrinology": "#06B6D4", "Trauma": "#DC2626", "Surgery": "#6B7280",
        "Toxicology": "#7C3AED", "Sepsis": "#F97316", "General": "#9333EA",
        "Other": "#9333EA", "Hepatology": "#B45309", "Immunology": "#A855F7",
        "Multisystem": "#0EA5E9", "Nutrition": "#84CC16",
        "Obstetrics And Gynecology": "#DB2777", "Oncology": "#A78BFA",
        "Cardiothoracic": "#0891B2", "Vascular": "#F59E0B",
        "Rheumatology": "#0D9488",
    }
    theory_specs = sorted(
        set(d["specialty"] for d in flashcard_decks)
        | set(n.get("system") for n in theory_notes if n.get("system"))
    )
    theory_spec_css = {}
    for s in theory_specs:
        color = THEORY_SPEC_COLORS.get(s, "#9333EA")
        var_name = "--theory-spec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower())
        theory_spec_css[var_name] = color
    theory_spec_str = "; ".join(f"{k}:{v}" for k, v in theory_spec_css.items()) + ";"
    theory_spec_vars = {
        s: "--theory-spec-" + re.sub(r"[^a-zA-Z0-9]", "", s.lower()) for s in theory_specs
    }
    theory_total_cards = sum(len(d["cards"]) for d in flashcard_decks)
    theory_subtopic_map = {}
    for d in flashcard_decks:
        for t in d.get("subtopics") or []:
            theory_subtopic_map.setdefault(d["specialty"], set()).add(t)
    theory_subtopic_map = {s: sorted(v) for s, v in theory_subtopic_map.items()}

    # Cross-linking data (papers ↔ guidelines ↔ theory ↔ decks) precomputed by acumen_core/linker.py
    related_data = loaders.load_related_links()
    related_meta = {
        "generated_at": related_data.get("generated_at", ""),
        "entity_count": related_data.get("entity_count", 0),
        "loaded": bool(related_data["catalog"]),
    }

    # Compute resolved feature flags for the authenticated user
    user_features = {f: user_has_feature(user, f) for f in FEATURE_FLAGS}
    insights_tag = '<script defer src="/_vercel/insights/script.js"></script>' if os.environ.get("VERCEL") else ''

    boot = {
        "spec_vars": spec_css_vars_js,
        "spec_labels": sorted(spec_css_vars_js),
        "type_list": type_list,
        "articles": articles_list,
        "pearls": pearls,
        "subtopic_map": subtopic_map,
        "show_disclaimer": show_disclaimer,
        "trial_index": trial_index,
        "trial_spec_labels": list(trial_specialties),
        "trial_spec_vars": trial_spec_vars,
        "trial_spec_counts": trial_spec_counts,
        "trial_subtopic_map": trial_subtopic_map,
        "trial_result_cats": trial_result_cats,
        "trial_types_list": trial_types_list,
        "condensed_index": condensed_index,
        "condensed_systems": condensed_systems,
        "condensed_result_cats": condensed_result_cats,
        "condensed_types_list": condensed_types_list,
        "flashcard_decks": flashcard_decks,
        "theory_spec_vars": theory_spec_vars,
        "theory_subtopic_map": theory_subtopic_map,
        "theory_notes": theory_notes,
        "related_catalog": related_data["catalog"],
        "related_index": related_data["index"],
        "related_meta": related_meta,
        "user_features": user_features,
        "user_is_admin": bool(user.get("is_admin")),
        "admin_feature_flags": FEATURE_FLAGS,
        "credits_text": CREDITS_TEXT,
        "trial_disclaimer_text": TRIAL_DISCLAIMER_TEXT,
        "disclaimer_text": DISCLAIMER_TEXT,
        "feedback_form_url": FEEDBACK_FORM_URL,
        "subscribe_form_url": SUBSCRIBE_FORM_URL,
        "unsubscribe_form_url": UNSUBSCRIBE_FORM_URL,
    }
    html = render_template(
        "dashboard.html",
        user=user,
        insights_tag=insights_tag,
        ecg_svg=ECG_SVG,
        css_url=asset_url("css/app.css"),
        js_url=asset_url("js/app.js"),
        boot_json=script_json(boot),
        spec_css_str=spec_css_str,
        trial_spec_str=trial_spec_str,
        theory_spec_str=theory_spec_str,
        theory_notes=theory_notes,
        theory_total_cards=theory_total_cards,
        theory_specs=theory_specs,
        trial_index=trial_index,
        trial_specialties=trial_specialties,
        trial_result_cats=trial_result_cats,
        trial_types_list=trial_types_list,
        can_see_condensed=user_has_feature(user, "condensed_trials"),
        condensed_index=condensed_index,
        condensed_systems=condensed_systems,
        condensed_result_cats=condensed_result_cats,
        condensed_types_list=condensed_types_list,
        feedback_form_url=FEEDBACK_FORM_URL,
    )
    resp = HTMLResponse(content=html)
    resp.headers["Cache-Control"] = "no-store, max-age=0"
    if dev_login_allowed(request) and not request.cookies.get(SESSION_COOKIE_NAME):
        _, dev_sid = local_dev_login()
        set_session_cookie(resp, dev_sid)
    return resp


@router.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)
