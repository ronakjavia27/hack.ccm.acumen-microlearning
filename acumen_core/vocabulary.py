"""
vocabulary.py - Controlled vocabulary management for specialties and article types.
"""

import os
from acumen_core.config import SPECIALTIES_FILE, ARTICLE_TYPES_FILE

DEFAULT_SPECIALTIES = [
    "Cardiology", "Neurology", "Nephrology", "Pulmonology",
    "Gastroenterology", "Infectious Diseases", "Rheumatology",
    "Immunology", "Sepsis", "Toxicology", "Hepatology",
    "Oncology", "Hematology", "Other", "Multisystem",
    "Nutrition", "Trauma", "Surgery", "Endocrinology",
    "Obstetrics and Gynecology",
]

DEFAULT_TYPES = ["Guideline", "Review", "Meta-analysis", "Trial", "Other"]


def load_allowed_vocabulary(file_path, default_list):
    """Load vocabulary from file, creating with defaults if missing."""
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("\n".join(default_list))
        return default_list
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def build_specialty_map(allowed):
    """Build lookup map from lowercase/alias keys to canonical specialty names."""
    m = {s.lower(): s for s in allowed}
    m.update({
        "infectious_disease": m.get("infectious diseases", "Infectious Diseases"),
        "multi_system": m.get("multisystem", "Multisystem"),
        "multisystem": m.get("multisystem", "Multisystem"),
        "obstetrics_and_gynecology": m.get("obstetrics and gynecology", "Obstetrics and Gynecology"),
        "cardio": m.get("cardiology", "Cardiology"),
        "cardiovascular": m.get("cardiology", "Cardiology"),
        "neuro": m.get("neurology", "Neurology"),
        "nephro": m.get("nephrology", "Nephrology"),
        "pulmo": m.get("pulmonology", "Pulmonology"),
        "gi": m.get("gastroenterology", "Gastroenterology"),
        "heme": m.get("hematology", "Hematology"),
        "onc": m.get("oncology", "Oncology"),
    })
    return m


def normalize_specialty(specialty_list, spec_map):
    """Normalize specialty from LLM output to canonical name."""
    if not isinstance(specialty_list, list) or not specialty_list:
        return "Other"
    raw = str(specialty_list[0]).strip().lower().replace("_", " ").replace("-", " ")
    mapped = spec_map.get(raw, "Other")
    if mapped == "Other":
        raw_orig = str(specialty_list[0]).strip().lower()
        mapped = spec_map.get(raw_orig, "Other")
    return "".join(x for x in str(mapped) if x.isalnum() or x in "._- ").strip()


def normalize_type(payload, allowed_types):
    """Normalize article type from payload, returns canonical type string."""
    low_types = {}
    for t in allowed_types:
        low_types[t.lower().replace("_", "-").replace(" ", "-")] = t
    doc_type = (payload.get("doc_type") or "").lower()
    if doc_type == "guideline":
        payload["article_subtype"] = "Guideline"
        return "Guideline"
    subtype = (payload.get("article_subtype") or "").strip()
    normalized = subtype.lower().replace("_", "-").replace(" ", "-")
    if normalized in low_types:
        payload["article_subtype"] = low_types[normalized]
        return low_types[normalized]
    payload["article_subtype"] = "Other"
    return "Other"


def get_allowed_specialties():
    return load_allowed_vocabulary(SPECIALTIES_FILE, DEFAULT_SPECIALTIES)


def get_allowed_types():
    return load_allowed_vocabulary(ARTICLE_TYPES_FILE, DEFAULT_TYPES)
