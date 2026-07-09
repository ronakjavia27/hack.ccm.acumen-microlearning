#!/usr/bin/env python3
"""
esbicm_parser.py — ESBICM Trial PDF → Structured JSON Pipeline
===============================================================
Parses "Recent and Landmark Trials in Critical Care by ESBICM (1st Edition)" PDF into:
  1. output_files/esbicm_trials/{system}/{subtopic}/{trial-slug}.json  (trial data)
  2. output_files/esbicm_trials_index.json                             (lightweight trial index)
  3. output_files/esbicm_specialty_subtopic_mapping.json                (hierarchical display schema)

Usage:
  python esbicm_parser.py [--pdf-path PATH] [--debug] [--max-trials N]
"""

import os, sys, re, json, argparse
from datetime import datetime

try:
    import fitz
except ImportError:
    print("PyMuPDF (fitz) required. Install: pip install pymupdf")
    sys.exit(1)

PDF_PATH = os.path.join(os.environ.get("USERPROFILE", ""), "Downloads",
                        "Recent_and_Landmarks_Trials_in_Critical_Care_by_ESBICM_1st_edition.pdf")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BASE = os.path.join(SCRIPT_DIR, "output_files")
TRIALS_DIR = os.path.join(OUTPUT_BASE, "esbicm_trials")
TRIALS_INDEX_FILE = os.path.join(OUTPUT_BASE, "esbicm_trials_index.json")
SYSTEM_SUBTOPIC_FILE = os.path.join(OUTPUT_BASE, "esbicm_specialty_subtopic_mapping.json")

HEADER_FOOTER_PATTERNS = [
    re.compile(r"^Recent and Landmark Trials in Critical Care \| esbicm\.org/trials\s*$"),
    re.compile(r"^Educational Society of Bedside Intensive Care Medicne \(ESBICM\)\s*$"),
    re.compile(r"^\d+\s*$"),
]

SECTION_HEADING_PATTERNS = [
    (1, r"^\d+\.\s*Publication Details"),
    (2, r"^\d+\.\s*Keywords"),
    (3, r"^\d+\.\s*The Clinical Question"),
    (4, r"^\d+\.\s*Background and Rationale"),
    (5, r"^\d+\.\s*Study Design and Methods"),
    (6, r"^\d+\.\s*Key Results"),
    (7, r"^\d+\.\s*Medical Statistics"),
    (8, r"^\d+\.\s*Strengths of the Study"),
    (9, r"^\d+\.\s*Limitations and Weaknesses"),
    (10, r"^\d+\.\s*Conclusion of the Authors"),
    (11, r"^\d+\.\s*To Summarize"),
    (12, r"^\d+\.\s*Context and Related Studies"),
    (13, r"^\d+\.\s*Unresolved Questions"),
    (14, r"^\d+\.\s*External Links"),
    (15, r"^\d+\.\s*Framework for Critical Appraisal"),
    (16, r"^\d+\.\s*Disclaimer and Contact"),
]

SECTION_NAMES = {
    1: "Publication Details",
    2: "Keywords",
    3: "The Clinical Question",
    4: "Background and Rationale",
    5: "Study Design and Methods",
    6: "Key Results",
    7: "Medical Statistics",
    8: "Strengths of the Study",
    9: "Limitations and Weaknesses",
    10: "Conclusion of the Authors",
    11: "To Summarize",
    12: "Context and Related Studies",
    13: "Unresolved Questions & Future Directions",
    14: "External Links",
    15: "Framework for Critical Appraisal",
    16: "Disclaimer and Contact",
}


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def strip_header_footer(text):
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        s = line.strip()
        if any(p.match(s) for p in HEADER_FOOTER_PATTERNS):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


def normalize_ws(text):
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def find_section_boundaries(text):
    boundaries = []
    for sec_id, pat_str in SECTION_HEADING_PATTERNS:
        for m in re.finditer(pat_str, text, re.MULTILINE):
            boundaries.append((sec_id, m.start()))
    boundaries.sort(key=lambda x: x[1])
    return boundaries


def simple_clean_line(line):
    return line.strip().lstrip('\u2022').lstrip('\u2023').lstrip('-').lstrip('\u2026').strip()


# ══════════════════════════════════════════════════════════════════
# SPECIALTY MAPPING (pages 14-26)
# ══════════════════════════════════════════════════════════════════
def build_specialty_mapping(doc):
    full_text = ""
    for idx in range(13, 26):
        if idx < len(doc):
            full_text += doc[idx].get_text() + "\n"
    full_text = strip_header_footer(full_text)

    lines = full_text.split('\n')
    systems = {}
    current_system = None
    current_subtopic = None
    pending_bullet = False  # Track when bullet is on its own line

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            pending_bullet = False
            continue
        if re.match(r'^[xvi]+\s*$', line.lower()):
            pending_bullet = False
            continue
        if 'Trials Organised' in line or 'organizational clarity' in line:
            continue

        sm = re.match(r'^(\d+)\.\s+(.+)$', line)
        if sm:
            current_system = sm.group(2).strip()
            systems[current_system] = {"subtopics": {}, "trials": []}
            current_subtopic = None
            pending_bullet = False
            continue

        if current_system and line.startswith('This section covers'):
            systems[current_system]["description"] = line
            pending_bullet = False
            continue

        is_bullet_line = line.startswith('\u2022') or line.startswith('•') or line == '\u2022' or line == '•'
        is_nobullet_trial_line = False

        if is_bullet_line:
            # Check if the bullet line also has content
            content_after_bullet = line.lstrip('\u2022').lstrip('•').strip()
            if content_after_bullet:
                trial_text = content_after_bullet
            else:
                pending_bullet = True
                continue
        elif pending_bullet:
            trial_text = line
            pending_bullet = False
            is_nobullet_trial_line = True
        else:
            pending_bullet = False
            # Check for subtopic headers
            if current_system and line and not line.startswith('- '):
                if len(line) < 60 and re.match(r'^[A-Za-z\s&,/]+$', line) and not re.search(r'\(\d{4}\)', line):
                    current_subtopic = line.strip()
                    if current_subtopic not in systems[current_system]["subtopics"]:
                        systems[current_system]["subtopics"][current_subtopic] = []
                    continue
            continue

        # Process trial text (from bullet line with content, or from pending bullet + next line)
        trial_match = re.match(r'^([A-Za-z0-9][A-Za-z0-9\s&/-]+?)\s*\(', trial_text)
        if trial_match:
            name = trial_match.group(1).strip()
            if name and len(name) < 60:
                if current_subtopic and name not in systems[current_system]["subtopics"].get(current_subtopic, []):
                    systems[current_system]["subtopics"][current_subtopic].append(name)
                if name not in systems[current_system]["trials"]:
                    systems[current_system]["trials"].append(name)
                continue
        trial_match2 = re.match(r'^([A-Za-z0-9][A-Za-z0-9\s&/-]+?)\s*:', trial_text)
        if trial_match2:
            name = trial_match2.group(1).strip()
            if name and len(name) < 60:
                if current_subtopic and name not in systems[current_system]["subtopics"].get(current_subtopic, []):
                    systems[current_system]["subtopics"][current_subtopic].append(name)
                if name not in systems[current_system]["trials"]:
                    systems[current_system]["trials"].append(name)

    return systems


# ══════════════════════════════════════════════════════════════════
# TOC MAPPING (pages 27-33)
# ══════════════════════════════════════════════════════════════════
def build_toc_mapping(doc):
    toc_text = ""
    for idx in range(26, 33):
        if idx < len(doc):
            toc_text += doc[idx].get_text() + "\n"

    lines = toc_text.split('\n')
    # Filter to name/page entries only (skip headers, roman numerals)
    entries = []
    for line in lines:
        s = line.strip()
        if not s or s.startswith('Trials in') or s.startswith('Trial Name') or s.startswith('Page Number'):
            continue
        if re.match(r'^[xvi]+$', s.lower()):
            continue
        entries.append(s)

    trials = []
    i = 0
    while i < len(entries):
        name = entries[i].rstrip('.')
        # Look ahead for the page number
        if i + 1 < len(entries) and re.match(r'^\d+$', entries[i + 1]):
            page = int(entries[i + 1])
            i += 2
        else:
            page = None
            i += 1
        if name:
            trials.append({"name": name, "page": page})

    toc_names = {}
    page_to_trial = {}
    for t in trials:
        if t["name"] and t["page"] is not None:
            key = t["name"].lower()
            toc_names[key] = t["page"]
            if t["page"] not in page_to_trial:
                page_to_trial[t["page"]] = []
            page_to_trial[t["page"]].append(t["name"])
    return toc_names, page_to_trial


def get_trial_page_ranges(doc, page_to_trial):
    book_offset = 34
    trial_pages = {}
    for book_page, names in page_to_trial.items():
        pdf_idx = book_page + book_offset - 1
        if 0 <= pdf_idx < len(doc):
            trial_pages[pdf_idx] = names[0]
    sorted_indices = sorted(trial_pages.keys())
    ranges = []
    for i, start_idx in enumerate(sorted_indices):
        name = trial_pages[start_idx]
        if i + 1 < len(sorted_indices):
            end_idx = sorted_indices[i + 1] - 1
        else:
            end_idx = len(doc) - 1
        if end_idx >= start_idx:
            ranges.append({"trial_name": name, "start_page": start_idx, "end_page": end_idx})
    return ranges


# ══════════════════════════════════════════════════════════════════
# TRIAL PARSING
# ══════════════════════════════════════════════════════════════════
def extract_trial_header(text):
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    trial_name = ""
    one_liner = ""
    investigators = ""
    collecting_one_liner = False
    standalone_year = ""
    for i, line in enumerate(lines):
        if any(p.match(line) for p in HEADER_FOOTER_PATTERNS):
            continue
        if re.match(r'^\d+\.\s*Publication Details', line):
            break

        # Skip standalone "(2023)" lines - they're just the year on its own line
        if re.match(r'^\(\d{4}\)$', line.strip()):
            standalone_year = line.strip()
            continue

        # Trial name detection: line with year (e.g. "Name (2023)")
        if not trial_name and re.search(r'\(\d{4}\)', line) and not line.startswith('"') and not line.startswith('•'):
            trial_name = line
            continue

        # If trial name has no year yet, check lines before the one-liner
        if not trial_name and not line.startswith('"') and not line.startswith('•') and not line.startswith('('):
            if re.match(r'^[A-Z][A-Za-z0-9\s/:,-]+$', line) and len(line) > 15:
                trial_name = line

        # One-liner in quotes (may span lines)
        if line.startswith('"') and line.endswith('"'):
            one_liner = line.strip('"')
            collecting_one_liner = False
            continue
        if line.startswith('"') and not line.endswith('"') and not collecting_one_liner:
            one_liner = line.lstrip('"')
            collecting_one_liner = True
            continue
        if collecting_one_liner:
            if line.endswith('"'):
                one_liner += " " + line.rstrip('"')
                collecting_one_liner = False
            else:
                one_liner += " " + line
            continue

        # Line with bullet and "Investigators" or "Trial" text
        if line.startswith('•') and ('investigator' in line.lower() or 'trial' in line.lower()):
            investigators = line.lstrip('•').strip()
            continue
        # Also catch line without bullet that mentions investigators
        if not investigators and not line.startswith('"') and ('investigator' in line.lower() or 'trial investigators' in line.lower()):
            investigators = line.strip()

    # Append standalone year to trial name if needed
    if trial_name and standalone_year and '(' not in trial_name and not re.search(r'\d{4}', trial_name):
        trial_name = trial_name + ' ' + standalone_year

    return trial_name, one_liner, investigators


def extract_publication_details(text):
    details = {}
    raw_lines = text.split('\n')
    # Group lines by bullet points
    groups = []
    current = []
    for raw_line in raw_lines:
        line = raw_line.strip()
        if line.startswith('•') or line.startswith('\u2022'):
            if current:
                groups.append('\n'.join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        groups.append('\n'.join(current))

    for section in groups:
        m = re.match(r'^[•\u2022]\s*([A-Za-z /-]+?):\s*(.*)', section, re.DOTALL)
        if m:
            key = m.group(1).strip().lower().replace(' ', '_')
            val = m.group(2).strip().replace('\n', ' ').strip()
            details[key] = val

    pub_text = details.get('published', '')
    journal = ''
    jm = re.search(r'in\s+(.+?)(?:\.|$)', pub_text)
    if jm:
        journal = jm.group(1).strip().rstrip('.')
    # Also extract DOI from citation if not a separate field
    doi = details.get('doi', '')
    if not doi and 'citation' in details:
        dm = re.search(r'DOI:\s*(\S+)', details['citation'])
        if dm:
            doi = dm.group(1)

    return {
        'trial_title': details.get('trial_title', ''),
        'citation': details.get('citation', ''),
        'doi': doi,
        'published': pub_text,
        'journal': journal,
        'primary_author': details.get('author', ''),
        'funding': details.get('funding', ''),
    }


def extract_keywords_from_section(text):
    for line in text.split('\n'):
        s = simple_clean_line(line)
        if s and not re.match(r'^\d+\.', s):
            return [k.strip() for k in s.split(',')]
    return []


def extract_pico(text):
    pico = {}
    pm = re.search(r'In\s+(.+?)\s*\(Population\)', text)
    if pm: pico['population'] = pm.group(1).strip()
    im = re.search(r'(?:does|dose)\s+a\s+(.+?)\s*\(Intervention\)', text)
    if im: pico['intervention'] = im.group(1).strip()
    cm = re.search(r'compared\s+to\s+(.+?)\s*\(Comparison\)', text)
    if cm: pico['comparison'] = cm.group(1).strip()
    om = re.search(r'(.+?)\s*\(Outcome\)', text)
    if om: pico['outcome'] = om.group(1).strip()
    return pico


def extract_sample_size(text):
    m = re.search(r'(\d[\d,]*)\s*patients?\s+were\s+randomized', text, re.IGNORECASE)
    if m: return int(m.group(1).replace(',', ''))
    m = re.search(r'sample\s+size\s+of\s+(\d[\d,]*)', text, re.IGNORECASE)
    if m: return int(m.group(1).replace(',', ''))
    return None


def extract_key_stats(text):
    stats = {}
    pm = re.search(r'[pP]\s*[=<>]\s*([0-9.]+)', text)
    if pm: stats['p_value'] = pm.group(1)
    om = re.search(r'(?:OR|odds\s+ratio)[:\s]+([0-9.]+)\s*\(?\s*95%\s*CI[:\s]+([0-9.]+\s*to\s*[0-9.]+)', text, re.IGNORECASE)
    if om: stats['odds_ratio'] = {'value': om.group(1), 'ci': om.group(2)}
    hm = re.search(r'(?:HR|hazard\s+ratio)[:\s]+([0-9.]+)\s*\(?\s*95%\s*CI[:\s]+([0-9.]+\s*to\s*[0-9.]+)', text, re.IGNORECASE)
    if hm: stats['hazard_ratio'] = {'value': hm.group(1), 'ci': hm.group(2)}
    return stats


def determine_result(text):
    t = text.lower()
    if re.search(r'no\s+significant\s+difference', t): return "Negative/Neutral"
    if re.search(r'did\s+not\s+(reduce|improve|decrease)', t) and re.search(r'p\s*[=>]\s*0\.0[5-9]', t): return "Negative"
    if re.search(r'(benefit|improved|reduced|superior)', t) and re.search(r'p\s*[<]\s*0\.0[0-5]', t): return "Positive"
    return "Neutral"


def parse_trial(full_text):
    text = strip_header_footer(full_text)
    text = normalize_ws(text)

    trial_name, one_liner, investigators = extract_trial_header(text)
    boundaries = find_section_boundaries(text)
    if not boundaries:
        return None, f"No sections found"

    sections = {}
    for idx, (sec_id, start_pos) in enumerate(boundaries):
        end_pos = boundaries[idx + 1][1] if idx + 1 < len(boundaries) else len(text)
        raw = text[start_pos:end_pos].strip()

        first_nl = raw.find('\n')
        if first_nl > 0:
            first_line = raw[:first_nl].strip()
            if re.match(r'^\d+\.', first_line):
                raw = raw[first_nl:].strip()

        sec_name = SECTION_NAMES.get(sec_id, f"Section {sec_id}")
        sec_data = {"id": sec_id, "heading": sec_name, "content": raw}

        if sec_id == 1: sec_data["structured"] = extract_publication_details(raw)
        elif sec_id == 2: sec_data["keywords"] = extract_keywords_from_section(raw)
        elif sec_id == 3: sec_data["pico"] = extract_pico(raw)
        elif sec_id == 6:
            sec_data["sample_size"] = extract_sample_size(raw)
            sec_data["key_stats"] = extract_key_stats(raw)

        if sec_id != 16:
            sections[str(sec_id)] = sec_data

    pub = sections.get("1", {}).get("structured", {})
    sample = sections.get("6", {}).get("sample_size")

    return {
        "trial_name": trial_name,
        "one_liner": one_liner or "",
        "investigators": investigators or "",
        "sections": sections,
        "metadata": {
            "doi": pub.get("doi", ""),
            "journal": pub.get("journal", ""),
            "primary_author": pub.get("primary_author", ""),
            "trial_title": pub.get("trial_title", ""),
            "citation": pub.get("citation", ""),
            "published": pub.get("published", ""),
            "funding": pub.get("funding", ""),
            "sample_size": extract_sample_size(sections.get("5", {}).get("content", "")),
            "key_stats": sections.get("6", {}).get("key_stats", {}),
            "keywords": sections.get("2", {}).get("keywords", []),
            "result_category": determine_result(text),
        }
    }, None


def _match_trial_names(name_from_mapping, names_to_check):
    """Check if a trial name from the mapping matches any of the names_to_check."""
    tl = name_from_mapping.lower()
    t_short = re.sub(r'\s*\(.*?\)', '', tl).strip()
    t_short = re.sub(r'\s*:.*$', '', t_short).strip()
    for n in names_to_check:
        if not n or len(n) < 2:
            continue
        # Exact match (case-insensitive)
        if n == tl or n == t_short:
            return True
        # Prefix match: mapping name starts with our name OR our name starts with mapping name (min 4 chars)
        if len(n) >= 4 and len(tl) >= 4:
            if tl.startswith(n) or n.startswith(tl):
                return True
        if t_short and len(n) >= 4 and len(t_short) >= 4:
            if t_short.startswith(n) or n.startswith(t_short):
                return True
        # Word-boundary match: our name appears as a whole word in mapping name (min 4 chars)
        if len(n) >= 4 and len(tl) >= 4:
            if re.search(r'\b' + re.escape(n) + r'\b', tl):
                return True
    return False


def map_trial_to_system(trial_name, specialty_mapping):
    """Map trial to system/subtopic. Try exact match and substring match both ways."""
    names_to_check = [trial_name.lower().strip()]
    # Short name without parenthetical year/author
    if '(' in trial_name:
        before_paren = trial_name.split('(')[0].strip().lower()
        if before_paren:
            names_to_check.append(before_paren)
    # Very short version (just the first word if it's a short acronym)
    first_word = trial_name.split()[0].lower().strip(':,;.') if trial_name.split() else ''
    if first_word and len(first_word) >= 2 and first_word not in names_to_check:
        names_to_check.append(first_word)

    for sys_name, sys_data in specialty_mapping.items():
        # Check subtopic trials first (more specific)
        for sub_name, trial_list in sys_data.get("subtopics", {}).items():
            for t in trial_list:
                if _match_trial_names(t, names_to_check):
                    return sys_name, sub_name
        # Then check flat trials list (for systems without subtopics)
        subtopic_hint = None
        for t in sys_data.get("trials", []):
            if _match_trial_names(t, names_to_check):
                # Found match without subtopic - try to infer from nearby subtopics
                for sub_name, trial_list in sys_data.get("subtopics", {}).items():
                    if t in trial_list:
                        return sys_name, sub_name
                return sys_name, subtopic_hint if subtopic_hint else "General"
    return None, None


def extract_year(trial_data, toc_name):
    """Extract year from multiple sources."""
    # From TOC name: "3mg (2013)"
    ym = re.search(r'\((\d{4})\)', toc_name)
    if ym: return int(ym.group(1))
    # From parsed trial name
    parsed_name = trial_data.get("trial_name", "")
    ym = re.search(r'\((\d{4})\)', parsed_name)
    if ym: return int(ym.group(1))
    # From published field
    md = trial_data.get("metadata", {})
    pub = md.get("published", "")
    ym = re.search(r'(\d{4})', pub)
    if ym: return int(ym.group(1))
    return None


def create_trial_json(trial_data, toc_name, system_name, subtopic_name):
    md = trial_data.get("metadata", {})
    # Use the full parsed trial name if available, otherwise TOC name
    display_name = trial_data.get("trial_name", "") or toc_name
    slug = slugify(toc_name)
    year = extract_year(trial_data, toc_name)

    secs = []
    for sid in sorted(trial_data.get("sections", {}).keys(), key=int):
       secs.append(trial_data["sections"][sid])

    kr = trial_data.get("sections", {}).get("6", {})
    result_summary = kr.get("content", "")[:400] if kr else ""

    all_text = ' '.join(str(v.get("content", "")) for v in trial_data.get("sections", {}).values())
    trial_type = "RCT"
    if "observational" in all_text.lower(): trial_type = "Observational"
    elif "meta-analysis" in all_text.lower(): trial_type = "Meta-analysis"
    elif "before-and-after" in all_text.lower(): trial_type = "Before-After Study"

    return {
        "id": slugify(toc_name),
        "doc_type": "esbicm_trial",
        "slug": slugify(toc_name),
        "trial_name": display_name,
        "toc_name": toc_name,
        "one_liner": trial_data.get("one_liner", ""),
        "investigators": trial_data.get("investigators", ""),
        "year": year,
        "specialty": system_name or "Uncategorized",
        "subtopic": subtopic_name or "General",
        "journal": md.get("journal", ""),
        "primary_author": md.get("primary_author", ""),
        "doi": md.get("doi", ""),
        "trial_title": md.get("trial_title", ""),
        "citation": md.get("citation", ""),
        "published": md.get("published", ""),
        "funding": md.get("funding", ""),
        "trial_type": trial_type,
        "article_subtype": "rct" if trial_type == "RCT" else "observational",
        "evidence_level": "high-quality RCT" if trial_type == "RCT" else "observational",
        "sample_size": md.get("sample_size"),
        "key_stats": md.get("key_stats", {}),
        "result_category": md.get("result_category", "Neutral"),
        "result_summary": result_summary,
        "keywords": md.get("keywords", []),
        "sections": secs,
        "added_date": datetime.now().strftime("%Y-%m-%d")
    }


# ══════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(description="Parse ESBICM Trials PDF into structured JSON")
    parser.add_argument("--pdf", default=PDF_PATH)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--max-trials", type=int, default=0)
    parser.add_argument("--output-dir", default=OUTPUT_BASE)
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"PDF not found: {args.pdf}")
        sys.exit(1)

    print(f"Opening PDF: {args.pdf}")
    doc = fitz.open(args.pdf)
    print(f"Total pages: {doc.page_count}")

    os.makedirs(os.path.join(args.output_dir, "esbicm_trials"), exist_ok=True)

    print("\n=== Step 1: Building specialty/subtopic mapping (pages 14-26) ===")
    specialty_map = build_specialty_mapping(doc)
    print(f"  Systems found: {len(specialty_map)}")

    print("\n=== Step 2: Building table of contents (pages 27-33) ===")
    toc_names, page_to_trial = build_toc_mapping(doc)
    print(f"  ToC entries: {len(toc_names)}")

    print("\n=== Step 3: Mapping trial page ranges ===")
    trial_ranges = get_trial_page_ranges(doc, page_to_trial)
    print(f"  Trial ranges: {len(trial_ranges)}")

    print("\n=== Step 4: Parsing trials ===")
    trials_index = []
    processed = 0

    for tri in trial_ranges:
        if args.max_trials and processed >= args.max_trials:
            break

        name = tri["trial_name"]
        start, end = tri["start_page"], tri["end_page"]
        if args.debug:
            print(f"\n  [{processed + 1}] {name} (pages {start+1}-{end+1})")

        text = ""
        for idx in range(start, end + 1):
            text += strip_header_footer(doc[idx].get_text()) + "\n"
        text = normalize_ws(text)

        if "Support Us" in text and "Our Mission" in text:
            if args.debug: print("    SKIP: Support Us page")
            continue
        if len(text.strip()) < 200:
            if args.debug: print(f"    SKIP: too short ({len(text)} chars)")
            continue

        parsed, err = parse_trial(text)
        if err:
            if args.debug: print(f"    ERROR: {err}")
            continue
        if not parsed.get("trial_name"):
            if args.debug: print("    No trial name found")
            continue

        # Map using both parsed full name and TOC name
        sys_name, sub_name = map_trial_to_system(parsed["trial_name"], specialty_map)
        if not sys_name:
            sys_name, sub_name = map_trial_to_system(name, specialty_map)

        trial_json = create_trial_json(parsed, name, sys_name, sub_name)

        sys_dir = re.sub(r'[<>:"/\\|?*]', '_', sys_name or "Uncategorized").strip() or "Uncategorized"
        sub_dir = re.sub(r'[<>:"/\\|?*]', '_', sub_name or "General").strip() or "General"
        out_dir = os.path.join(args.output_dir, "esbicm_trials", sys_dir, sub_dir)
        os.makedirs(out_dir, exist_ok=True)

        fpath = os.path.join(out_dir, f"{trial_json['slug']}.json")
        with open(fpath, 'w', encoding='utf-8') as f:
            json.dump(trial_json, f, indent=2, ensure_ascii=False)

        trials_index.append({
            "trial_name": trial_json["trial_name"],
            "toc_name": name,
            "slug": trial_json["slug"],
            "specialty": sys_name or "",
            "subtopic": sub_name or "",
            "primary_author": trial_json.get("primary_author", ""),
            "journal": trial_json.get("journal", ""),
            "year": trial_json.get("year"),
            "doi": trial_json.get("doi", ""),
            "one_liner": trial_json.get("one_liner", ""),
            "result_category": trial_json.get("result_category", ""),
            "trial_type": trial_json.get("trial_type", ""),
            "sample_size": trial_json.get("sample_size"),
            "file_path": os.path.relpath(fpath, args.output_dir).replace('\\', '/'),
            "date_parsed": datetime.now().strftime("%Y-%m-%d")
        })

        processed += 1
        if processed % 10 == 0:
            print(f"  Processed {processed} trials...")

    print(f"\n  Total trials processed: {processed}")

    print("\n=== Step 5: Saving trials index ===")
    with open(TRIALS_INDEX_FILE, 'w', encoding='utf-8') as f:
        json.dump(trials_index, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {TRIALS_INDEX_FILE} ({len(trials_index)} entries)")

    print("\n=== Step 6: Saving system/subtopic mapping ===")
    display = []
    for sname, sdata in specialty_map.items():
        display.append({
            "specialty": sname,
            "description": sdata.get("description", ""),
            "subtopics": list(sdata.get("subtopics", {}).keys()),
            "total_trials": len(sdata.get("trials", [])),
        })
    with open(SYSTEM_SUBTOPIC_FILE, 'w', encoding='utf-8') as f:
        json.dump(display, f, indent=2, ensure_ascii=False)
    print(f"  Saved: {SYSTEM_SUBTOPIC_FILE} ({len(display)} systems)")

    doc.close()
    print(f"\n{'='*60}")
    print(f"  Done! Outputs in: {os.path.join(args.output_dir, 'esbicm_trials')}/")
    print(f"  Index: {TRIALS_INDEX_FILE}")
    print(f"  Mapping: {SYSTEM_SUBTOPIC_FILE}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()