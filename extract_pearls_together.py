#!/usr/bin/env python3
"""
extract_pearls_together.py — Extract clinical pearls via Together AI cloud.
Extracts high-yield, evidence-based pearls from structured JSON summaries
using Together AI (openai/gpt-oss-20b primary, openai/gpt-oss-120b fallback),
with rule-based extraction as final fallback.

Features:
  - Strengthened prompt to prevent AI hallucination (pearls must be grounded
    in the source text)
  - Optional consistency check that verifies pearl content overlaps with
    source terms
  - Tracks processed files in pearls_processed.json to avoid rework

Usage:
    python extract_pearls_together.py
    python extract_pearls_together.py --max 5
    python extract_pearls_together.py --consistency-check
    python extract_pearls_together.py --model openai/gpt-oss-120b
"""

import os
import sys
import json
import re
import time
import argparse
from datetime import datetime

from dotenv import load_dotenv

script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')
load_dotenv(dotenv_path=env_path)


# =====================================================================
# CONFIG
# =====================================================================
OUTPUT_DIR = "./output_files"
PEARLS_JSON = "./pearls.json"
PEARLS_TRACKER = "./pearls_processed.json"

TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")
PRIMARY_MODEL = "openai/gpt-oss-20b"
FALLBACK_MODEL = "openai/gpt-oss-120b"

MAX_TOKENS = 8192
TEMPERATURE = 0.1
MAX_PAPERS = 0

# Specialty aliases
SPECIALTIES_ALIASES = {
    "infectious_disease": "Infectious Diseases",
    "infectious diseases": "Infectious Diseases",
    "multi_system": "Multisystem",
    "multisystem": "Multisystem",
    "obstetrics_and_gynecology": "Obstetrics and Gynecology",
    "obstetrics and gynecology": "Obstetrics and Gynecology",
    "cardio": "Cardiology",
    "neuro": "Neurology",
    "nephro": "Nephrology",
    "pulmo": "Pulmonology",
    "gi": "Gastroenterology",
    "heme": "Hematology",
    "onc": "Oncology",
}

TITLE_SPECIALTY_KEYWORDS = {
    "cardiologist": "Cardiology", "cardiology": "Cardiology", "cardiac": "Cardiology",
    "coronary": "Cardiology", "myocardial": "Cardiology", "heart": "Cardiology",
    "arrhythmia": "Cardiology", "ventricular": "Cardiology", "atrial": "Cardiology",
    "aortic": "Cardiology", "mitral": "Cardiology", "valvular": "Cardiology",
    "pericardial": "Cardiology", "defibrillator": "Cardiology", "stent": "Cardiology",
    "angioplasty": "Cardiology", "statin": "Cardiology",
    "neurologist": "Neurology", "neurology": "Neurology", "neurologic": "Neurology",
    "brain": "Neurology", "stroke": "Neurology", "cerebral": "Neurology",
    "intracranial": "Neurology", "cranial": "Neurology", "seizure": "Neurology",
    "epilepsy": "Neurology", "neurocritical": "Neurology", "subarachnoid": "Neurology",
    "intracerebral": "Neurology", "encephalopathy": "Neurology", "spinal": "Neurology",
    "neuromuscular": "Neurology",
    "nephrologist": "Nephrology", "nephrology": "Nephrology", "kidney": "Nephrology",
    "renal": "Nephrology", "dialysis": "Nephrology", "glomerular": "Nephrology",
    "creatinine": "Nephrology",
    "pulmonologist": "Pulmonology", "pulmonology": "Pulmonology", "lung": "Pulmonology",
    "respiratory": "Pulmonology", "pulmonary": "Pulmonology", "airway": "Pulmonology",
    "tracheostomy": "Pulmonology", "bronchoscopy": "Pulmonology", "pleural": "Pulmonology",
    "copd": "Pulmonology",
    "gastroenterologist": "Gastroenterology", "gastroenterology": "Gastroenterology",
    "biliary": "Gastroenterology", "pancreas": "Gastroenterology", "pancreatic": "Gastroenterology",
    "colon": "Gastroenterology", "colonic": "Gastroenterology", "gastric": "Gastroenterology",
    "esophageal": "Gastroenterology", "intestine": "Gastroenterology", "intestinal": "Gastroenterology",
    "hepatologist": "Hepatology", "hepatology": "Hepatology", "cirrhosis": "Hepatology",
    "portal": "Hepatology",
    "infectious": "Infectious Diseases", "tuberculosis": "Infectious Diseases",
    "hiv": "Infectious Diseases", "bacteremia": "Infectious Diseases",
    "antimicrobial": "Infectious Diseases", "fungal": "Infectious Diseases",
    "hematologist": "Hematology", "hematology": "Hematology", "coagulation": "Hematology",
    "thrombosis": "Hematology", "thromboembolism": "Hematology", "anemia": "Hematology",
    "hemoglobin": "Hematology", "platelet": "Hematology", "neutropenia": "Hematology",
    "oncologist": "Oncology", "oncology": "Oncology", "cancer": "Oncology",
    "tumor": "Oncology", "carcinoma": "Oncology", "malignancy": "Oncology",
    "neoplasm": "Oncology", "chemotherapy": "Oncology", "immunotherapy": "Oncology",
    "metastasis": "Oncology",
    "endocrinologist": "Endocrinology", "endocrinology": "Endocrinology",
    "diabetes": "Endocrinology", "thyroid": "Endocrinology", "hormone": "Endocrinology",
    "pituitary": "Endocrinology", "adrenal": "Endocrinology", "glycemic": "Endocrinology",
    "glucose": "Endocrinology", "insulin": "Endocrinology", "cortisol": "Endocrinology",
    "surgeon": "Surgery", "surgery": "Surgery", "surgical": "Surgery",
    "thoracotomy": "Surgery", "laparotomy": "Surgery", "laparoscopic": "Surgery",
    "resection": "Surgery", "bypass": "Surgery", "craniotomy": "Surgery",
    "traumatic": "Trauma", "hemorrhagic shock": "Trauma", "damage control": "Trauma",
    "obstetric": "Obstetrics and Gynecology", "obstetrics": "Obstetrics and Gynecology",
    "gynecology": "Obstetrics and Gynecology", "pregnancy": "Obstetrics and Gynecology",
    "pregnant": "Obstetrics and Gynecology", "fetal": "Obstetrics and Gynecology",
    "maternal": "Obstetrics and Gynecology", "placental": "Obstetrics and Gynecology",
    "preeclampsia": "Obstetrics and Gynecology", "eclampsia": "Obstetrics and Gynecology",
    "postpartum": "Obstetrics and Gynecology",
    "immunologist": "Immunology", "immunology": "Immunology", "autoimmune": "Immunology",
    "immunodeficiency": "Immunology", "immunosuppression": "Immunology",
    "rheumatologist": "Rheumatology", "rheumatology": "Rheumatology", "rheumatic": "Rheumatology",
    "vasculitis": "Rheumatology", "lupus": "Rheumatology", "scleroderma": "Rheumatology",
    "toxicologist": "Toxicology", "toxicology": "Toxicology", "poisoning": "Toxicology",
    "overdose": "Toxicology", "toxin": "Toxicology", "intoxication": "Toxicology",
    "nutritional": "Nutrition", "enteral": "Nutrition", "parenteral": "Nutrition",
    "malnutrition": "Nutrition",
    "septic shock": "Sepsis", "septic": "Sepsis",
}

PEARLS_JSON_FIELDS = [
    "id", "timestamp", "source_paper", "doi",
    "author", "system", "type", "pearl", "remarks", "file_name", "topic"
]

# =====================================================================
# STRENGTHENED PEARL EXTRACTION PROMPT
# Hallucination-proof: explicitly forbids generating content not in source
# =====================================================================
PEARL_PROMPT = """You are an expert critical care clinician. Your task is to EXTRACT high-yield clinical pearls STRICTLY from the provided text below.

CRITICAL — This is an EXTRACTION task, NOT a generation task, each pearl should have some meaninful clinical data, do not blindly quote line from text, working of trial, criteria used in guideline or haphazard information having no bedside clinical bearing:

1. ONLY extract pearls that are DIRECTLY STATED in the provided text. Each pearl must be a close paraphrase of specific sentences found below.
2. If the text does NOT contain a high-yield actionable pearl on a given topic, return {"pearls": []}. Returning nothing is better than fabricating.

Prioritize:
- **Clinical updates** — recent practice changes, new guideline recommendations
- **Practice-changing concepts** — shifts in standard of care, updated thresholds
- **Bedside actionable items** — doses, cutoffs, protocols, diagnostic criteria, management algorithms you can apply immediately

Each pearl must be:
- Specific and concrete (thresholds, cutoffs, dosing ranges, timing, risk modifiers, diagnostic criteria, prognostic markers)
- Self-contained (1-2 sentences, maximally information-dense)
- NOT generic advice or truisms

Deduplicate: if the same finding appears in multiple sections, include it only once.

Return ONLY valid JSON. No preamble, no markdown fences, no commentary.
Format: {"pearls": [{"text": "...", "topic": "..."}]}

If no qualifying pearls can be extracted, return: {"pearls": []}

Each pearl's "topic" should be 1-3 comma-separated keywords specific to the clinical domain."""


# =====================================================================
# SPECIALTY NORMALIZATION
# =====================================================================
def load_specialties_map():
    m = {}
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specialties.txt")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "." not in line:
                    continue
                name = line.split(".", 1)[1].strip()
                m[name.lower()] = name
    m.update({k.lower(): v for k, v in SPECIALTIES_ALIASES.items()})
    return m


def normalize_specialty(specialty_list, spec_map):
    if not isinstance(specialty_list, list) or not specialty_list:
        return "Other"
    raw = str(specialty_list[0]).strip().lower().replace("_", " ").replace("-", " ")
    mapped = spec_map.get(raw, "Other")
    return "".join(x for x in str(mapped) if x.isalnum() or x in "._- ").strip()


def infer_specialty_from_title(title, spec_map):
    if not title:
        return "Other"
    title_lower = title.lower()
    scores = {}
    for keyword, specialty in TITLE_SPECIALTY_KEYWORDS.items():
        if keyword.lower() in title_lower:
            scores[specialty] = scores.get(specialty, 0) + 1
    if not scores:
        return "Other"
    best = max(scores, key=scores.get)
    return spec_map.get(best.lower(), best)


# =====================================================================
# CONSISTENCY CHECK
# =====================================================================
# Numbers with medical units or percentages
NUM_UNIT_PATTERN = re.compile(
    r'\b\d+(?:\.\d+)?\s*(?:mg|mEq|mmHg|cmH2O|%|mcg|g|dL|mL|L|kg|mOsm|mmol|IU|U|hr|min|h|d|wk|mo|y|mg/dL|mg/kg|μg|ng)\b',
    re.IGNORECASE
)


GENERIC_MEDICAL_WORDS = {
    "acute", "chronic", "severe", "clinical", "patient", "patients", "management",
    "treatment", "therapy", "therapeutic", "recommended", "recommendation",
    "guideline", "guidelines", "standard", "criteria", "diagnosis", "diagnostic",
    "prognostic", "assessment", "evaluation", "intervention", "procedure",
    "outcome", "outcomes", "mortality", "survival", "benefit", "benefits",
    "risk", "risks", "factor", "factors", "increase", "decrease", "reduction",
    "significant", "associated", "compared", "evidence", "study", "studies",
    "trial", "trials", "analysis", "meta", "systematic", "review", "literature",
    "data", "results", "effect", "effects", "effective", "efficacy", "safety",
    "dose", "dosing", "dosage", "administer", "administration", "oral", "intravenous",
    "infusion", "bolus", "titrate", "titration", "target", "goal", "goals",
    "optimal", "optimize", "maintain", "maintenance", "monitor", "monitoring",
    "require", "required", "consider", "considered", "indicate", "indicated",
    "suggest", "suggested", "recommend", "support", "supported", "based",
    "according", "following", "including", "during", "before", "after",
    "initial", "early", "late", "prior", "previous", "current", "additional",
    "alternative", "multiple", "various", "common", "frequent", "rare",
    "presence", "absence", "status", "level", "levels", "range", "value",
    "values", "score", "scores", "scale", "grade", "stage", "phase",
    "group", "groups", "cohort", "population", "sample", "size",
    "approach", "strategy", "strategies", "option", "options", "role",
    "important", "critical", "essential", "necessary", "appropriate",
    "overall", "primary", "secondary", "major", "minor", "key", "central",
    "general", "specific", "standard", "routine", "typical", "usual",
    "potential", "possible", "likely", "unlikely", "usually", "often",
    "however", "although", "despite", "addition", "example", "including",
    "well", "also", "may", "can", "will", "must", "should", "could", "would",
    "show", "shown", "demonstrate", "demonstrated", "observe", "observed",
    "report", "reported", "publish", "published", "perform", "performed",
    "undergo", "undergone", "receive", "received", "present", "presented",
    "describe", "described", "identify", "identified",
    "define", "defined", "measure", "measured", "calculate", "calculated",
    "estimate", "estimated", "determine", "determined", "assess", "assessed",
    "evaluate", "evaluated", "compare", "compared", "contrast",
    "respiratory", "ventilation", "ventilator", "oxygenation", "oxygen",
    "pulmonary", "lung", "airway", "cardiac", "cardio", "heart",
    "hemodynamic", "hemodynamics", "circulation", "circulatory",
    "infection", "infections", "sepsis", "septic", "antibiotic", "antibiotics",
    "surgical", "surgery", "operative", "trauma", "injury", "injuries",
    "position", "positioning", "pressure", "volume", "fluid", "fluids",
    "blood", "plasma", "serum", "tissue", "organ", "organs",
    "failure", "dysfunction", "damage", "disorder", "disease",
    "syndrome", "condition", "pathology", "abnormal", "normal",
    "improve", "improvement", "worsen", "worsening", "progress", "progression",
    "prevent", "prevention", "prophylaxis", "reduce", "reducing",
    "source", "control", "tension", "drainage", "manage", "manageable",
    "cornerstone", "achieve", "achieved", "setting", "remain", "remains",
    "ongoing", "until", "unless", "despite", "without", "within",
    "cause", "caused", "leading", "result", "resulting", "related",
    "high", "higher", "low", "lower", "raised", "elevated", "reduced",
    "supportive", "aggressive", "conservative", "standardized",
    "continuously", "concurrently", "simultaneously", "subsequently",
    "intermittent", "continuous", "prolonged", "prolongation",
    "limited", "extended", "expanded", "restricted", "liberal",
    "newborn", "mother", "placental",
    "delivery", "neonatal", "neonate",
    "uterus", "uterine", "cervical",
    "trimester", "amniotic", "umbilical",
    "window", "refractory", "obtain", "obtaining", "suspected",
    "possible", "feasible", "feasibility", "within", "before",
    "start", "starting", "initiate", "initiation", "guide", "guided",
    "prevent", "prevention", "preventing", "further",
    "deterioration", "deteriorate", "worsening", "progression",
    "resuscitation", "resuscitate", "resuscitative",
    "intervention", "interventional", "multidisciplinary",
    "facilitate", "facilitating", "coordinate", "coordinated",
    "collaborative", "multimodal", "multisystem",
}


def extract_source_terms(payload):
    """Extract key medical terms from source payload for consistency checking."""
    all_text = ""

    fields = ["title", "one_line_summary"]
    for f in fields:
        v = payload.get(f, "")
        if isinstance(v, str):
            all_text += " " + v

    for kp in payload.get("key_pearls", []):
        if isinstance(kp, str):
            all_text += " " + kp

    for s in payload.get("sections", []):
        if isinstance(s.get("content"), str):
            all_text += " " + s["content"]

    for b in payload.get("recommendation_blocks", []):
        if isinstance(b.get("narrative"), str):
            all_text += " " + b["narrative"]
        for r in b.get("recommendations", []):
            if isinstance(r.get("statement"), str):
                all_text += " " + r["statement"]

    protocol = payload.get("bedside_protocol", [])
    for step in protocol:
        if isinstance(step.get("action"), str):
            all_text += " " + step["action"]

    dd = payload.get("drugs_doses", [])
    for d in dd:
        for k in ("drug", "dose", "indication"):
            if isinstance(d.get(k), str):
                all_text += " " + d[k]

    # Extract numbers with units (e.g., "80 mmHg", "0.25 mg/kg")
    units = set(NUM_UNIT_PATTERN.findall(all_text))

    # Extract capitalized terms — both single (Levetiracetam, ICP, TBI) and multi-word
    # Single-word caps must not be common English sentence-start words
    caps_single = set(re.findall(r'\b[A-Z][a-z]{3,}\b', all_text))
    caps_single = {t.lower() for t in caps_single
                   if t.lower() not in GENERIC_MEDICAL_WORDS
                   and not re.match(r'^(this|that|these|those|they|them|their|from|with|when|what|which|where|would|could|should|shall|will|hence|thus|then|than|also|both|each|every|other|another|after|before|into|over|under|above|below|between|among|about|while|since|until|during|because|there|here|first|second|third|fourth|fifth|such|some|more|most|only|very|just|now|then|than|had|has|were|was|been|being|done|having|making|taking|given|using|based|used|seen|known|found|shown|called|defined|described|following)$', t.lower())}
    # Multi-word caps (2+ words) — almost always specific
    caps_multi = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,}\b', all_text))
    caps_terms = {t.lower() for t in caps_multi if len(t) > 4} | caps_single

    # Extract standalone specific terms (longer than 4 chars, not in generic list)
    all_lower = set(re.findall(r'\b[a-z]{5,}\b', all_text))
    specific_terms = all_lower - GENERIC_MEDICAL_WORDS

    units_lower = {u.lower() for u in units}

    return units_lower, caps_terms, specific_terms


def check_consistency(pearl_text, source_terms):
    """Check if pearl text shares at least one specific term with source."""
    units, caps, specific = source_terms
    if not units and not caps and not specific:
        return True  # can't check, pass through

    pearl_lower = pearl_text.lower()

    # Check numbers with units (specific — e.g., "80 mmHg" must be in source)
    pearl_units = set(NUM_UNIT_PATTERN.findall(pearl_text))
    pearl_units_lower = {u.lower() for u in pearl_units}
    if pearl_units_lower & units:
        return True

    # Check capitalized medical terms from source (whole-word match)
    for term in caps:
        if re.search(r'\b' + re.escape(term) + r'\b', pearl_lower):
            return True

    # Check specific lowercase terms (require at least 3 matches)
    matches = 0
    for term in specific:
        if term in pearl_lower:
            matches += 1
            if matches >= 3:
                return True

    return False


# =====================================================================
# TRACKER
# =====================================================================
def load_tracker():
    if not os.path.exists(PEARLS_TRACKER):
        return {}
    try:
        with open(PEARLS_TRACKER, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def update_tracker(file_name, count):
    tracker = {}
    if os.path.exists(PEARLS_TRACKER):
        try:
            with open(PEARLS_TRACKER, "r", encoding="utf-8") as f:
                tracker = json.load(f)
        except Exception:
            tracker = {}
    tracker[file_name] = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "mode": "together",
        "count": count
    }
    tmp = PEARLS_TRACKER + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(tracker, f, indent=2)
        os.replace(tmp, PEARLS_TRACKER)
    except Exception:
        pass


# =====================================================================
# JSON HELPERS
# =====================================================================
def _atomic_write_json(file_path, data):
    tmp = file_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, file_path)


def load_existing_papers():
    if not os.path.exists(PEARLS_JSON):
        return set(), 1
    try:
        with open(PEARLS_JSON, "r", encoding="utf-8") as f:
            rows = json.load(f)
        papers = set()
        max_id = 0
        for row in rows:
            src = row.get("source_paper", "").strip()
            if src:
                papers.add(src)
            try:
                max_id = max(max_id, int(row.get("id", 0)))
            except (ValueError, TypeError):
                pass
        return papers, max_id + 1
    except Exception:
        return set(), 1


def append_pearls_to_json(pearls):
    existing_rows = []
    if os.path.exists(PEARLS_JSON):
        try:
            with open(PEARLS_JSON, "r", encoding="utf-8") as f:
                existing_rows = json.load(f)
        except Exception:
            pass

    now_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    all_rows = existing_rows + pearls

    for i, row in enumerate(all_rows):
        out = {}
        for key in PEARLS_JSON_FIELDS:
            val = row.get(key, "")
            if key == "id":
                val = str(i)
            elif key == "timestamp" and not val:
                val = now_ts
            out[key] = str(val) if val is not None else ""
        all_rows[i] = out

    _atomic_write_json(PEARLS_JSON, all_rows)
    return len(all_rows)


# =====================================================================
# AI CALLER
# =====================================================================
def call_together(prompt, model):
    """Call Together AI with primary/fallback models."""
    from together import Together
    client = Together(api_key=TOGETHER_API_KEY)
    models_to_try = [model, FALLBACK_MODEL]
    last_error = None

    for m in models_to_try:
        for attempt in range(2):
            try:
                response = client.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": PEARL_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                    timeout=300
                )
                raw = response.choices[0].message.content
                if raw is None or raw.strip() == "":
                    raise ValueError("Empty response")
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = re.sub(r'^```(?:json)?\s*', '', raw)
                    raw = re.sub(r'\s*```$', '', raw)
                return json.loads(raw)
            except Exception as e:
                last_error = e
                time.sleep(2)
        if len(models_to_try) > 1:
            print(f"    {m} failed, trying fallback model...")
    raise RuntimeError(f"Together AI failed: {last_error}")


# =====================================================================
# LOCAL FALLBACK (rule-based)
# =====================================================================
def extract_local(payload):
    """Rule-based extraction from payload fields."""
    text_parts = []
    for p in payload.get("key_pearls", []):
        if isinstance(p, str):
            text_parts.append(p)
    for s in payload.get("sections", []):
        if isinstance(s.get("content"), str):
            text_parts.append(s["content"])
        for sp in s.get("section_pearls", []):
            if isinstance(sp, str):
                text_parts.append(sp)
    for b in payload.get("recommendation_blocks", []):
        if isinstance(b.get("narrative"), str):
            text_parts.append(b["narrative"])
        for r in b.get("recommendations", []):
            if isinstance(r.get("statement"), str):
                text_parts.append(r["statement"])

    full_text = "\n".join(text_parts)
    lines = full_text.split("\n")
    candidates = []
    seen = set()

    for line in lines:
        s = line.strip()
        if s.startswith("-") or s.startswith("*"):
            content = s.lstrip("-* ").strip()
            if content and len(content) > 20:
                key = content[:80].lower()
                if key not in seen:
                    seen.add(key)
                    candidates.append(content)
        elif any(kw in s.lower() for kw in ["mg", "mmhg", "cmh2o", "%", "p=", "p <", "p<", "ci ", "nnt", "nnh", "rr ", "or ", "hr="]):
            key = s[:80].lower()
            if key not in seen:
                seen.add(key)
                candidates.append(s)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    spec_map = load_specialties_map()
    source = payload.get("title") or payload.get("paper_name", "")
    specialty_list = payload.get("specialty", [])
    system = normalize_specialty(specialty_list, spec_map)
    if system == "Other":
        inferred = infer_specialty_from_title(source, spec_map)
        if inferred != "Other":
            system = inferred
    doi = payload.get("doi", "")
    author = payload.get("authors") or payload.get("primary_authors", "")
    ptype = payload.get("article_subtype") or payload.get("doc_type", "")

    result = []
    for c in candidates[:25]:
        result.append({
            "timestamp": timestamp,
            "source_paper": source,
            "doi": doi,
            "author": author,
            "system": system,
            "type": ptype,
            "pearl": c[:500],
            "remarks": "",
            "file_name": "",
            "topic": ""
        })
    return result


# =====================================================================
# PROMPT BUILDER
# =====================================================================
def build_prompt(payload):
    parts = []

    title = payload.get("title") or payload.get("paper_name", "")
    doc_type = payload.get("doc_type", "")
    subtype = payload.get("article_subtype", "")
    summary = payload.get("one_line_summary", "")
    strengths = payload.get("strengths_limitations", "")

    if title:
        parts.append(f"Title: {title}")
    if doc_type or subtype:
        parts.append(f"Type: {doc_type} / {subtype}")
    if summary:
        parts.append(f"Summary: {summary}")

    key_pearls = payload.get("key_pearls", [])
    if key_pearls:
        parts.append("\nKey Pearls:\n" + "\n".join(f"- {p}" for p in key_pearls))

    sections = payload.get("sections", [])
    for s in sections:
        heading = s.get("heading", "")
        content = s.get("content", "")
        sp = s.get("section_pearls", [])
        block = ""
        if heading:
            block += f"\n## {heading}\n"
        if content:
            block += content + "\n"
        if sp:
            block += "Section Pearls:\n" + "\n".join(f"- {p}" for p in sp) + "\n"
        if block:
            parts.append(block)

    rec_blocks = payload.get("recommendation_blocks", [])
    for b in rec_blocks:
        topic = b.get("topic", "")
        narrative = b.get("narrative", "")
        block = ""
        if topic:
            block += f"\n## {topic}\n"
        if narrative:
            block += narrative + "\n"
        for r in b.get("recommendations", []):
            rid = r.get("rec_id", "")
            stmt = r.get("statement", "")
            strength = r.get("strength", "")
            grade = r.get("evidence_grade", "")
            meta = f" [{strength}, {grade}]" if strength or grade else ""
            if stmt:
                block += f"- {rid}: {stmt}{meta}\n" if rid else f"- {stmt}{meta}\n"
        if block:
            parts.append(block)

    protocol = payload.get("bedside_protocol", [])
    if protocol:
        block = "\nBedside Protocol:\n"
        for step in protocol:
            sn = step.get("step", "")
            stitle = step.get("title", "")
            action = step.get("action", "")
            block += f"Step {sn}: {stitle} -> {action}\n"
        parts.append(block)

    drugs_doses = payload.get("drugs_doses", [])
    if drugs_doses:
        block = "\nDrugs & Doses:\n"
        for dd in drugs_doses:
            drug = dd.get("drug", "")
            dose = dd.get("dose", "")
            indication = dd.get("indication", "")
            adverse = dd.get("adverse_effects", "")
            block += f"- {drug}"
            if dose:
                block += f" | Dose: {dose}"
            if indication:
                block += f" | Indication: {indication}"
            if adverse:
                block += f" | Adverse: {adverse}"
            block += "\n"
        parts.append(block)

    if strengths:
        parts.append(f"\nStrengths & Limitations:\n{strengths}")

    return "\n".join(parts)


# =====================================================================
# MAIN
# =====================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Extract clinical pearls from JSON summaries using Together AI"
    )
    parser.add_argument("--max", type=int, default=None,
                        help="Max papers to process (default: all)")
    parser.add_argument("--limit", type=str, default=None,
                        help="Comma-separated filenames to process (bypasses tracker)")
    parser.add_argument("--model", type=str, default=None,
                        help=f"Together AI model (default: {PRIMARY_MODEL})")
    parser.add_argument("--force-local", action="store_true",
                        help="Skip Together AI, use rule-based extraction only")
    parser.add_argument("--consistency-check", action="store_true",
                        help="Verify each pearl has content overlap with source text")
    args = parser.parse_args()

    if not TOGETHER_API_KEY and not args.force_local:
        print("ERROR: TOGETHER_API_KEY not found in .env. Use --force-local for rule-based extraction.")
        sys.exit(1)

    max_papers = args.max if args.max is not None else MAX_PAPERS
    model = args.model or PRIMARY_MODEL
    limit_files = set(f.strip() for f in args.limit.split(",")) if args.limit else None

    print("[AI] hack.CCM Pearl Extractor (Together AI)")
    print(f"  Model: {model}  |  Fallback: {FALLBACK_MODEL}")

    if args.force_local:
        backend = "local"
        print("  Backend: local (rule-based)")
    else:
        backend = "together"
        print(f"  Backend: Together AI")

    print(f"  Max papers: {'all' if max_papers == 0 else max_papers}")
    if limit_files:
        print(f"  Limit to {len(limit_files)} specific file(s)")
    if args.consistency_check:
        print("  Consistency check: ON")
    print()

    processed_files = load_tracker()
    existing_papers, _ = load_existing_papers()

    json_files = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if not fname.endswith(".json"):
                continue
            if limit_files and fname not in limit_files:
                continue
            json_files.append(os.path.join(root, fname))

    if limit_files:
        found = set(os.path.basename(f) for f in json_files)
        missing = limit_files - found
        if missing:
            print(f"  Warning: {len(missing)} file(s) not found in {OUTPUT_DIR}: {', '.join(sorted(missing))}")

    print(f"  Found {len(json_files)} total JSON files")
    print(f"  Already processed: {len(processed_files)} files")

    to_process = []
    for fpath in json_files:
        fname = os.path.basename(fpath)
        if not limit_files and fname in processed_files:
            continue
        if limit_files and fname in processed_files:
            print(f"  [NOTE] {fname} was already processed — force-processing due to --limit")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                payload = json.load(f)
            paper_name = payload.get("title") or payload.get("paper_name", "")
            if not limit_files and paper_name in existing_papers:
                continue
            to_process.append((fpath, payload, fname))
        except Exception as e:
            print(f"  Skipping {os.path.basename(fpath)}: {e}")
            continue

    if max_papers > 0:
        to_process = to_process[:max_papers]

    print(f"  To process this run: {len(to_process)} files")
    print()

    if not to_process:
        print("[OK] No new files to process. Exiting.")
        return

    spec_map = load_specialties_map()
    total_pearls = 0

    for idx, (fpath, payload, fname) in enumerate(to_process, start=1):
        paper_name = payload.get("title") or payload.get("paper_name", fname)
        print(f"[{idx}/{len(to_process)}] {paper_name}")

        prompt = build_prompt(payload)
        if len(prompt.strip()) < 30:
            print(f"  [SKIP] Skipping (no content)")
            update_tracker(fname, 0)
            continue

        source = payload.get("title") or payload.get("paper_name", "")
        doi = payload.get("doi", "")
        author = payload.get("authors") or payload.get("primary_authors", "")
        specialty_list = payload.get("specialty", [])
        system = normalize_specialty(specialty_list, spec_map)
        if system == "Other":
            inferred = infer_specialty_from_title(source, spec_map)
            if inferred != "Other":
                system = inferred
        ptype = payload.get("article_subtype") or payload.get("doc_type", "")

        # Extract source terms for consistency check
        source_terms = None
        if args.consistency_check:
            source_terms = extract_source_terms(payload)

        try:
            if backend == "together":
                result = call_together(prompt, model)
            else:
                result = extract_local(payload)

            if isinstance(result, dict) and "pearls" in result:
                raw_pearls = result["pearls"]
            elif isinstance(result, list):
                raw_pearls = result
            else:
                print(f"  [SKIP] No pearls extracted (unexpected format)")
                update_tracker(fname, 0)
                continue

            if not raw_pearls or len(raw_pearls) == 0:
                print(f"  [SKIP] No pearls extracted")
                update_tracker(fname, 0)
                continue

        except Exception as e:
            print(f"  [WARN] AI extraction failed: {e}, falling back to local...")
            result = extract_local(payload)
            raw_pearls = result if isinstance(result, list) else result.get("pearls", [])
            if not raw_pearls:
                print(f"  [SKIP] No pearls extracted (local fallback also empty)")
                update_tracker(fname, 0)
                continue

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        dedup_seen = set()
        pearl_rows = []
        consistency_warnings = 0

        for p in raw_pearls[:25]:
            if isinstance(p, dict):
                text = p.get("text", "").strip()
                topic = p.get("topic", "").strip()
            elif isinstance(p, str):
                text = p.strip()
                topic = ""
            else:
                continue

            if len(text) < 15:
                continue

            # Consistency check
            if args.consistency_check and source_terms:
                if not check_consistency(text, source_terms):
                    consistency_warnings += 1
                    if args.consistency_check > 1:  # strict mode — skip
                        if args.consistency_check == 2:
                            print(f"  [CC-SKIP] No source overlap: {text[:80]}...")
                            continue

            key = text[:100].lower()
            if key in dedup_seen:
                continue
            dedup_seen.add(key)

            pearl_rows.append({
                "id": "",
                "timestamp": timestamp,
                "source_paper": source,
                "doi": doi,
                "author": author,
                "system": system,
                "type": ptype,
                "pearl": text[:500],
                "remarks": "",
                "file_name": fname,
                "topic": topic,
            })

        if consistency_warnings > 0:
            print(f"  [CC] {consistency_warnings} pearls had no source term overlap")

        if not pearl_rows:
            print(f"  [SKIP] No new pearls after dedup")
            update_tracker(fname, 0)
            continue

        count = append_pearls_to_json(pearl_rows)
        update_tracker(fname, count)
        total_pearls += count
        print(f"  [OK] {count} pearls saved")

    print()
    print(f"[DONE] {total_pearls} new pearls written to {PEARLS_JSON}")

    try:
        with open(PEARLS_JSON, "r", encoding="utf-8") as f:
            rows = json.load(f)
        if rows and not all(k in rows[0] for k in PEARLS_JSON_FIELDS):
            missing = [k for k in PEARLS_JSON_FIELDS if k not in rows[0]]
            print(f"  [WARN] Missing fields in first row: {missing}")
        else:
            print(f"  [OK] JSON validated: {len(rows)} entries")
    except Exception as e:
        print(f"  [WARN] JSON validation failed: {e}")


if __name__ == "__main__":
    main()
