"""
markdown.py - Markdown emphasis enrichment for clinical content fields.
Bold key numbers, units, drug names, and clinical keywords.
"""

import re


def apply_markdown_emphasis(text):
    """Wrap clinical numbers, units, and keywords in bold markdown."""
    if not text:
        return text
    parts = re.split(r'(\*\*[^*]+\*\*)', text)
    for i, part in enumerate(parts):
        if i % 2 == 1:
            continue
        parts[i] = re.sub(
            r'(\d+(?:\.\d+)?)\s*(mg|mcg|g|mL|L|mmHg|cmH2O|%|mmol|mEq|IU|U|kg|hr|min|mg/kg|mcg/kg|mEq/L|mmol/L|mg/dL|IU/kg/hr)\b',
            r'**\1 \2**',
            parts[i], flags=re.IGNORECASE
        )
        parts[i] = re.sub(
            r'\b(significant(?:ly)?|recommended|contraindicated|critical(?:ly)?|essential|pivotal|superior|inferior|equivalent|mandatory|absolute|mortality|survival|prognosis|notable)\b',
            lambda m: f'**{m.group(0)}**',
            parts[i], flags=re.IGNORECASE
        )
    return ''.join(parts)


def enrich_payload_with_markdown(payload):
    """Apply markdown emphasis to all content-bearing fields in payload."""
    for key in ['one_line_summary', 'strengths_limitations']:
        if isinstance(payload.get(key), str):
            payload[key] = apply_markdown_emphasis(payload[key])
    for s in payload.get('sections', []):
        if isinstance(s.get('content'), str):
            s['content'] = apply_markdown_emphasis(s['content'])
        for sp in s.get('section_pearls', []):
            if isinstance(sp, str):
                pass
    for b in payload.get('recommendation_blocks', []):
        if isinstance(b.get('narrative'), str):
            b['narrative'] = apply_markdown_emphasis(b['narrative'])
        for r in b.get('recommendations', []):
            if isinstance(r.get('statement'), str):
                r['statement'] = apply_markdown_emphasis(r['statement'])
    for i, p in enumerate(payload.get('key_pearls', [])):
        if isinstance(p, str):
            payload['key_pearls'][i] = apply_markdown_emphasis(p)
    for step in payload.get('bedside_protocol', []):
        if isinstance(step.get('action'), str):
            step['action'] = apply_markdown_emphasis(step['action'])
    return payload
