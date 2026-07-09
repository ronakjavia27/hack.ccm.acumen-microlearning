#!/usr/bin/env python3
"""
build_trials_organsystem.py
============================
Creates trials_organsystem.json from PDF pages 14-26.
Captures the full hierarchical structure: system → subtopic → trial entries with descriptions.
Saves to output_files/esbicm_trials/trials_organsystem.json
"""

import os, sys, re, json

try:
    import fitz
except ImportError:
    print("PyMuPDF (fitz) required. Install: pip install pymupdf")
    sys.exit(1)

PDF_PATH = os.path.join(os.environ.get("USERPROFILE", ""), "Downloads",
                        "Recent_and_Landmarks_Trials_in_Critical_Care_by_ESBICM_1st_edition.pdf")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output_files", "esbicm_trials")

HEADER_FOOTER_PATTERNS = [
    re.compile(r"^Recent and Landmark Trials in Critical Care \| esbicm\.org/trials\s*$"),
    re.compile(r"^Educational Society of Bedside Intensive Care Medicne \(ESBICM\)\s*$"),
    re.compile(r"^\d+\s*$"),
]

PAGE_RANGE = (14, 26)  # User-facing page numbers (1-indexed)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[-\s]+', '-', text)
    return text.strip('-')


def strip_hf(text):
    lines = text.split('\n')
    return '\n'.join(l for l in lines if not any(p.match(l.strip()) for p in HEADER_FOOTER_PATTERNS))


def extract_organsystem_structure(doc):
    """
    Parse pages 14-26 into the full hierarchical structure.
    Returns:
    [
        {
            "system": "Sepsis & Septic Shock",
            "description": "This section covers sepsis management...",
            "subtopics": [
                {
                    "subtopic": "Resuscitation & Hemodynamic Targets",
                    "trials": [
                        {
                            "short_name": "ANDROMEDA-SHOCK",
                            "full_entry": "ANDROMEDA-SHOCK (Hernández et al., 2019): Compared a resuscitation strategy...",
                            "author_year": "(Hernández et al., 2019)",
                            "description": "Compared a resuscitation strategy..."
                        },
                        ...
                    ]
                },
                ...
            ]
        },
        ...
    ]
    """
    full_text = ""
    for idx in range(13, 26):
        if idx < len(doc):
            full_text += doc[idx].get_text() + "\n"
    full_text = strip_hf(full_text)

    lines = full_text.split('\n')
    result = []
    current_system = None
    current_subtopic = None
    pending_bullet = False
    accumulated_desc_lines = []  # For multi-line trial descriptions

    def is_subtopic_line(stripped):
        """Check if a line is likely a subtopic header."""
        if not stripped or len(stripped) >= 60:
            return False
        if re.search(r'\d{4}', stripped):  # Has a year
            return False
        if stripped.startswith('(') or stripped.startswith('o ') or stripped.startswith('§') or stripped.startswith('"'):
            return False
        if ':' in stripped:
            return False
        return bool(re.match(r'^[A-Za-z\s&,/()\']+$', stripped))

    def flush_trial():
        """Save the accumulated trial (if any) to the current subtopic."""
        if accumulated_desc_lines and current_system and current_subtopic is not None:
            entry_text = ' '.join(accumulated_desc_lines).strip()
            if entry_text:
                # Extract short name: first alphanumeric word(s) before ( or :
                name_match = re.match(r'^([A-Za-z0-9][A-Za-z0-9\s&/-]+?)\s*[(:]', entry_text)
                if name_match:
                    short_name = name_match.group(1).strip()
                else:
                    short_name = entry_text.split()[0].strip('(') if entry_text.split() else entry_text

                # Extract author/year: find the last parenthetical containing a year
                ay_match = re.search(r'\(([^)]+?\d{4}[^)]*)\)', entry_text)
                author_year = "(" + ay_match.group(1) + ")" if ay_match else ""

                # Description: everything after the first colon
                colon_pos = entry_text.find(':')
                if colon_pos >= 0:
                    desc = entry_text[colon_pos + 1:].strip()
                elif ay_match:
                    desc = entry_text[ay_match.end():].strip().lstrip(':').strip()
                else:
                    desc = entry_text

                trial_obj = {
                    "short_name": short_name,
                    "full_entry": entry_text,
                    "author_year": author_year,
                    "description": desc,
                }
                current_system["subtopics"][-1]["trials"].append(trial_obj)
        accumulated_desc_lines.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if re.match(r'^[xvi]+\s*$', line.lower()):
            continue
        if 'Trials Organised' in line or 'organizational clarity' in line:
            continue

        # System header: "1. Sepsis & Septic Shock"
        sm = re.match(r'^(\d+)\.\s+(.+)$', line)
        if sm:
            flush_trial()
            sys_name = sm.group(2).strip()
            current_system = {
                "system": sys_name,
                "description": "",
                "subtopics": [],
            }
            current_subtopic = None
            result.append(current_system)
            continue

        # Description line
        if current_system and line.startswith('This section covers'):
            current_system["description"] = line
            continue

        # Detect bullet lines
        is_bullet = line.startswith('\u2022') or line.startswith('•')
        bullet_content = line.lstrip('\u2022').lstrip('•').strip() if is_bullet else ""

        if is_bullet and bullet_content:
            flush_trial()
            # Auto-create General subtopic if system has no subtopics yet
            if current_system and current_subtopic is None:
                current_subtopic = {"subtopic": "General", "trials": []}
                current_system["subtopics"].append(current_subtopic)
            accumulated_desc_lines.append(bullet_content)
        elif is_bullet and not bullet_content:
            # Bullet on its own line — next line is the trial
            flush_trial()
            pending_bullet = True
        elif pending_bullet:
            flush_trial()
            # Auto-create General subtopic if system has no subtopics yet
            if current_system and current_subtopic is None:
                current_subtopic = {"subtopic": "General", "trials": []}
                current_system["subtopics"].append(current_subtopic)
            accumulated_desc_lines.append(line)
            pending_bullet = False
        elif not is_bullet and not pending_bullet:
            stripped = line.strip()
            # Check if this line is a subtopic header (even mid-description)
            if is_subtopic_line(stripped) and current_system:
                flush_trial()
                current_subtopic = {
                    "subtopic": stripped,
                    "trials": []
                }
                current_system["subtopics"].append(current_subtopic)
            elif accumulated_desc_lines:
                accumulated_desc_lines.append(line)
            elif current_system:
                if is_subtopic_line(stripped):
                    current_subtopic = {
                        "subtopic": stripped,
                        "trials": []
                    }
                    current_system["subtopics"].append(current_subtopic)

    flush_trial()  # Flush last trial
    return result


def main():
    if not os.path.exists(PDF_PATH):
        print(f"PDF not found: {PDF_PATH}")
        sys.exit(1)

    print(f"Opening PDF: {PDF_PATH}")
    doc = fitz.open(PDF_PATH)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Extracting organ system structure from pages 14-26...")
    data = extract_organsystem_structure(doc)
    doc.close()

    out_path = os.path.join(OUTPUT_DIR, "trials_organsystem.json")
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    total_trials = sum(len(sub.get("trials", [])) for sys_ in data for sub in sys_.get("subtopics", []))
    total_subs = sum(len(sys_.get("subtopics", [])) for sys_ in data)
    print(f"\nSaved: {out_path}")
    print(f"  Systems: {len(data)}")
    print(f"  Subtopics: {total_subs}")
    print(f"  Trials captured: {total_trials}")

    # Print summary
    for sys_ in data:
        print(f"\n  {sys_['system']}:")
        for sub in sys_["subtopics"]:
            names = [t["short_name"] for t in sub["trials"]]
            print(f"    {sub['subtopic']}: {', '.join(names[:5])}{'...' if len(names) > 5 else ''}")


if __name__ == "__main__":
    main()
