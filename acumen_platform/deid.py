"""De-identification gate for the clinical doubts forum.

Policy: posts with any HIGH finding are rejected until the author edits them;
MEDIUM findings are shown as warnings and auto-redacted on save. This is a
safety net, not a guarantee — the author still has to tick the "no patient
identifiers" attestation, and moderators review flagged posts.

Patterns are tuned for Indian + international clinical notes (Aadhaar, UHID,
IPD/OPD numbers, +91 phones, PIN codes) and the HIPAA Safe Harbor identifiers.
Image uploads are disabled until server-side DICOM tag stripping and
burnt-in-text OCR checks exist (see docs/revamp/PLAN.md).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import List

HIGH, MEDIUM = "high", "medium"


@dataclass
class Finding:
    kind: str
    severity: str
    start: int
    end: int
    text: str


_RULES = [
    # kind, severity, regex
    ("email", HIGH, r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    ("aadhaar", HIGH, r"\b[2-9]\d{3}[\s-]?\d{4}[\s-]?\d{4}\b"),
    ("pan", HIGH, r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    ("phone", HIGH, r"(?:\+?91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b"),
    ("phone", HIGH, r"\+\d{1,3}[\s-]?\(?\d{2,4}\)?[\s-]?\d{3,4}[\s-]?\d{3,4}\b"),
    ("record_number", HIGH,
     r"\b(?:MRN|UHID|CR\s?No|IP\s?No|IPD\s?No|OPD\s?No|Reg(?:istration)?\s?No|Hospital\s?No|Case\s?No|Bed\s?No)\.?\s*[:#-]?\s*(?=[A-Z/-]*\d)[A-Z0-9/-]{3,}\b"),
    ("name", HIGH, r"\b(?i:Mr|Mrs|Ms|Miss|Master|Smt|Shri|Sri|Kumari|Baby\s+of)\.?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?"),
    ("name", HIGH, r"\b(?:patient(?:'s)?\s+name|name\s+of\s+(?:the\s+)?patient|pt\s+name)\s*[:\-]?\s*[A-Za-z]+(?:\s+[A-Za-z]+)?", ),
    ("full_date", MEDIUM, r"\b(?:0?[1-9]|[12]\d|3[01])[/.-](?:0?[1-9]|1[0-2])[/.-](?:19|20)\d{2}\b"),
    ("full_date", MEDIUM, r"\b(?:0?[1-9]|[12]\d|3[01])\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s+(?:19|20)\d{2}\b"),
    ("pin_code", MEDIUM, r"\b(?:pin(?:\s?code)?|pincode)\s*[:\-]?\s*\d{6}\b"),
    ("url", MEDIUM, r"\bhttps?://\S+"),
    ("age_over_89", MEDIUM, r"\b(?:9\d|1[01]\d)\s*(?:y(?:ea)?rs?|yo|y/o)\b"),
    ("address", MEDIUM, r"\b(?:r/o|resident\s+of|address\s*[:\-])\s*[A-Za-z0-9 ,.-]{4,40}"),
]
_CASE_SENSITIVE = {"pan"}  # honorific-name rule uses inline (?i:) so the name itself must be Capitalised
_COMPILED = [(k, s, re.compile(p, 0 if (k in _CASE_SENSITIVE or "(?i:" in p) else re.IGNORECASE)) for k, s, p in _RULES]


def scan(text: str) -> List[Finding]:
    found: List[Finding] = []
    taken = []
    for kind, sev, rx in _COMPILED:
        for m in rx.finditer(text or ""):
            if any(m.start() < e and m.end() > s for s, e in taken):
                continue  # earlier (higher-priority) rule already covers this span
            taken.append((m.start(), m.end()))
            found.append(Finding(kind, sev, m.start(), m.end(), m.group(0)))
    return sorted(found, key=lambda f: f.start)


def redact(text: str, findings: List[Finding] = None) -> str:
    findings = scan(text) if findings is None else findings
    out, last = [], 0
    for f in sorted(findings, key=lambda f: f.start):
        out.append(text[last:f.start])
        out.append(f"[{f.kind.upper()}]")
        last = f.end
    out.append(text[last:])
    return "".join(out)


def check(text: str) -> dict:
    fs = scan(text)
    return {
        "ok": not any(f.severity == HIGH for f in fs),
        "findings": [asdict(f) for f in fs],
        "redacted_preview": redact(text, fs),
    }
