"""
flashcards.py - Shared helpers for the flashcard generator pipeline.

Handles:
- Source file parsing (md/txt/pdf/docx/html) -> (title, text)
- LLM conversion prompt + markdown/JSON result parsing
- Sub-topic tagging of decks against the subtopics.txt vocabulary
- Ledger (flashcards_ledger.json) + sha256 helpers for skip-if-unchanged
"""

import hashlib
import json
import os
import re

from .config import (
    FLASHCARDS_LEDGER_FILE,
    THEORY_SPEC_TO_CANONICAL,
    MAX_CARDS_PER_DECK,
)
from .subtopics_config import get_subtopics_for_system
from .tracking import save_json_atomic
SUPPORTED_EXTS = (".md", ".txt", ".pdf", ".docx", ".html", ".htm")

# =====================================================================
# SOURCE FILE PARSING
# =====================================================================

def _read_utf8(path):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _title_from_markdown(text, stem):
    for line in text.split("\n")[:30]:
        s = line.strip()
        if s.startswith("# "):
            return s[2:].strip()
    m = re.match(r"^\*\*(\d+\.?\s*)?([^*]+?)\*\*\s*:?\s*$", text.split("\n")[0].strip() if text.split("\n") else "")
    if m and m.group(2):
        return m.group(2).strip()
    return re.sub(r"^\d+\s*", "", stem).strip()


def extract_md_txt(path):
    text = _read_utf8(path)
    stem = os.path.splitext(os.path.basename(path))[0]
    return _title_from_markdown(text, stem), text.strip()


def extract_pdf(path, ocr_fallback=True):
    from pypdf import PdfReader
    reader = PdfReader(path)
    chunks = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(chunks).strip()
    if ocr_fallback and len(text) < 150:
        try:
            from .ocr import fallback_page_ocr
            text = fallback_page_ocr(path)
        except Exception:
            pass
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"^\d+\s*", "", stem).strip(), text


def extract_docx(path):
    try:
        from docx import Document
    except ImportError:
        raise RuntimeError(
            "python-docx is required for .docx files. Install it with: pip install python-docx"
        )
    doc = Document(path)
    parts = []
    for block in doc.paragraphs:
        t = block.text.strip()
        if t:
            parts.append(t)
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            parts.append(" | ".join(cells))
    stem = os.path.splitext(os.path.basename(path))[0]
    return re.sub(r"^\d+\s*", "", stem).strip(), "\n".join(parts)


def extract_html(path):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(_read_utf8(path), "html.parser")
    title = ""
    if soup.title and soup.title.get_text(strip=True):
        title = soup.title.get_text(strip=True)
    elif soup.h1 and soup.h1.get_text(strip=True):
        title = soup.h1.get_text(strip=True)
    text = soup.get_text("\n", strip=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    return title or re.sub(r"^\d+\s*", "", stem).strip(), text


def parse_source_file(path):
    """Parse a source file -> (title, text). Raises ValueError for unsupported types."""
    ext = os.path.splitext(str(path))[1].lower()
    if ext in (".md", ".txt"):
        return extract_md_txt(path)
    if ext == ".pdf":
        return extract_pdf(path)
    if ext == ".docx":
        return extract_docx(path)
    if ext in (".html", ".htm"):
        return extract_html(path)
    raise ValueError(f"Unsupported file type: {ext}")


# =====================================================================
# LLM CONVERSION (source -> markdown deck)
# =====================================================================

CONVERT_SYSTEM_PROMPT = """You convert medical study material into a markdown flashcard deck.
Rules:
- Each flashcard starts with a line "## " followed by a short card title (one card per section).
- Card body: concise, high-yield study notes. Use tables, bullet lists, and bold key terms where useful. Refine, summarise, and reformat the material — do not copy it verbatim.
- Keep exact numbers, doses, thresholds, and units — never invent or change clinical values. If the source omits a value, omit it too.
- Optional: put a "---" divider inside a card to separate a front (question/prompt) from the back (answer) for flip-mode study. Most cards can omit it.
- Generate 5-12 cards per source chunk (maximum """ + str(MAX_CARDS_PER_DECK) + """).
- Output ONLY the markdown. No preamble, no code fences, no commentary."""


def _extract_markdown(result):
    """Normalize LLM output (str / JSON dict) into a markdown string."""
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        for key in ("markdown", "content", "output", "deck", "text"):
            v = result.get(key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        cards = result.get("cards")
        if isinstance(cards, list) and cards:
            parts = []
            for c in cards:
                if not isinstance(c, dict):
                    continue
                parts.append("## " + str(c.get("subtopic", "Card")).strip() + "\n\n" + str(c.get("content", "")).strip())
            return "\n\n".join(parts)
        for v in result.values():
            if isinstance(v, str) and v.strip():
                return v.strip()
    return ""


def _cards_from_dict(obj, title):
    cards = obj.get("cards") if isinstance(obj, dict) else None
    if isinstance(cards, list) and cards:
        out = []
        for c in cards:
            if not isinstance(c, dict):
                continue
            body = str(c.get("content", "")).strip()
            if not body:
                continue
            out.append({"subtopic": str(c.get("subtopic", "Card")).strip(), "content": body})
        return out
    return []


def _cards_from_markdown(markdown_text, title):
    lines = markdown_text.split("\n")
    card_starts = []
    for i, line in enumerate(lines):
        if line.strip().startswith("## "):
            card_starts.append((i, line.strip()[3:].strip()))
    if not card_starts:
        body = markdown_text.strip()
        if body:
            return [{"subtopic": title, "content": body}]
        return []
    cards = []
    for idx, (start_line, heading) in enumerate(card_starts):
        end_line = card_starts[idx + 1][0] if idx + 1 < len(card_starts) else len(lines)
        body = "\n".join(lines[start_line + 1:end_line]).strip()
        if not body:
            continue
        cards.append({"subtopic": heading, "content": body})
    return cards


def parse_llm_markdown(result, title):
    """Parse LLM output into a list of card dicts {subtopic, content}.
    Accepts markdown text, a JSON string ({"cards": [...]} or {"markdown": "..."}),
    or a parsed dict."""
    if isinstance(result, dict):
        md = _extract_markdown(result)
        if md:
            return _cards_from_markdown(md, title)
        return _cards_from_dict(result, title)
    if not isinstance(result, str):
        return []
    stripped = result.strip()
    if stripped.startswith(("{", "[")):
        try:
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                md = _extract_markdown(obj)
                if md and "cards" not in obj:
                    return _cards_from_markdown(md, title)
                return _cards_from_dict(obj, title)
        except json.JSONDecodeError:
            pass
        m = re.search(r'(\{.*"cards".*\})', stripped, re.DOTALL)
        if m:
            try:
                return _cards_from_dict(json.loads(m.group(1)), title)
            except json.JSONDecodeError:
                pass
    return _cards_from_markdown(stripped, title)


def llm_convert_to_markdown(text, title, llm="openrouter", verbose=False, api_key=None, model=None, base_url=None):
    """Send source text to the LLM, return markdown deck text (or None on failure).

    When api_key or model is given, a direct OpenAI-compatible call is used
    (base_url defaults to OpenRouter). Otherwise the provider chain is used."""
    from .llm import execute_openai_compat, execute_with_fallback, execute_with_gemini, execute_with_openrouter_text

    user_prompt = (
        f"Source title: {title}\n\nSource content:\n{text}\n\n"
        "Generate the flashcard deck in markdown following the rules."
    )
    try:
        if api_key or model:
            result = execute_openai_compat(
                CONVERT_SYSTEM_PROMPT, user_prompt,
                api_key=api_key, model=model, base_url=base_url,
                json_mode=False,
            )
        elif llm == "gemini":
            result = execute_with_gemini(CONVERT_SYSTEM_PROMPT, user_prompt, "flashcards")
        elif llm == "together":
            result = execute_with_fallback(CONVERT_SYSTEM_PROMPT, user_prompt, "flashcards")
        else:
            result = execute_with_openrouter_text(CONVERT_SYSTEM_PROMPT, user_prompt)
        return _extract_markdown(result) or None
    except Exception as e:
        if verbose:
            print(f"    [X] LLM convert failed: {e}")
        return None


# =====================================================================
# SUBTOPIC TAGGING (subtopics.txt vocabulary)
# =====================================================================

TAG_SYSTEM_PROMPT = """You assign subtopics to medical flashcard cards. Use ONLY the exact subtopics from the provided vocabulary — do not invent or rephrase them.
For each card index, pick 1-3 of the valid subtopics that best match the card content.
Return ONLY valid JSON: {{"cards": [{{"index": 0, "tags": ["Exact Subtopic"]}}, ...]}}. Include every card index exactly once. No preamble, no commentary."""


def canonical_systems_for(specialty):
    """THEORY folder abbreviation -> canonical subtopic-vocab systems."""
    return THEORY_SPEC_TO_CANONICAL.get(str(specialty).strip()) or []


def _acronym(phrase):
    words = re.findall(r"[A-Za-z0-9]+", str(phrase))
    if len(words) == 1:
        return words[0].lower()
    return "".join(w[0] for w in words).lower()


def normalize_subtopic(system, candidate):
    """Match an LLM-supplied tag against the vocab for a canonical system.
    Returns the exact vocab entry, or None if no match."""
    cand = str(candidate or "").strip().lstrip("#").strip()
    if not cand:
        return None
    subs = get_subtopics_for_system(system) or []
    cl = cand.lower()
    ca = _acronym(cand)
    for s in subs:
        if s.lower() == cl:
            return s
    for s in subs:
        if cl in s.lower() or s.lower() in cl:
            return s
    for s in subs:
        if ca and (_acronym(s) == ca or re.sub(r"[\s\-&]+", "", s.lower()) == re.sub(r"[\s\-&]+", "", cl)):
            return s
    return None


def tag_deck_with_llm(deck, llm="openrouter", verbose=False, api_key=None, model=None, base_url=None):
    """Tag every card in a deck dict with subtopics from the vocabulary.
    Mutates deck['cards'][i]['tags'] in place. Returns True if tagging ran.

    When api_key or model is given, a direct OpenAI-compatible call is used
    (base_url defaults to OpenRouter). Otherwise the provider chain is used."""
    systems = canonical_systems_for(deck.get("specialty"))
    if not systems:
        if verbose:
            print(f"    [~] No canonical systems for specialty '{deck.get('specialty')}' — skipping tags")
        return False
    vocab = []
    for s in systems:
        for sub in get_subtopics_for_system(s) or []:
            if sub not in vocab:
                vocab.append(sub)
    if not vocab:
        return False

    from .llm import execute_openai_compat, execute_with_fallback, execute_with_gemini, execute_with_openrouter

    cards = deck.get("cards") or []
    if not cards:
        return False

    vocab_str = "\n".join(f"{i+1}. {v}" for i, v in enumerate(vocab))
    system_prompt = TAG_SYSTEM_PROMPT.format(vocab_str=vocab_str, systems=", ".join(systems))
    lines = []
    for i, c in enumerate(cards):
        lines.append(f"[{i}] {c.get('subtopic', '')}\n{(c.get('content') or '')[:800]}")
    user_prompt = "Valid subtopics:\n" + vocab_str + "\n\nCards:\n\n" + "\n\n".join(lines)

    try:
        if api_key or model:
            result = execute_openai_compat(
                system_prompt, user_prompt,
                api_key=api_key, model=model, base_url=base_url,
                json_mode=True,
            )
        elif llm == "gemini":
            result = execute_with_gemini(system_prompt, user_prompt, "flashcards")
        elif llm == "together":
            result = execute_with_fallback(system_prompt, user_prompt, "flashcards")
        else:
            result = execute_with_openrouter(system_prompt, user_prompt)
    except Exception as e:
        if verbose:
            print(f"    [X] LLM tagging failed: {e}")
        return False

    mapping = {}
    if isinstance(result, dict):
        raw_cards = result.get("cards")
    elif isinstance(result, str):
        raw_cards = None
        stripped = result.strip()
        if stripped.startswith(("{", "[")):
            try:
                obj = json.loads(stripped)
                if isinstance(obj, dict):
                    raw_cards = obj.get("cards")
            except json.JSONDecodeError:
                m = re.search(r'(\{.*"cards".*\})', stripped, re.DOTALL)
                if m:
                    try:
                        raw_cards = json.loads(m.group(1)).get("cards")
                    except json.JSONDecodeError:
                        pass
    else:
        raw_cards = None
    for entry in raw_cards or []:
        if not isinstance(entry, dict):
            continue
        try:
            idx = int(entry.get("index"))
        except (TypeError, ValueError):
            continue
        mapping[idx] = entry.get("tags") or []

    tagged = 0
    for i, c in enumerate(cards):
        tags = []
        for cand in mapping.get(i, []):
            norm = None
            for s in systems:
                norm = normalize_subtopic(s, cand)
                if norm:
                    break
            if norm and norm not in tags:
                tags.append(norm)
            if len(tags) >= 3:
                break
        c["tags"] = tags
        if tags:
            tagged += 1
    if verbose:
        print(f"    [i] Tagged {tagged}/{len(cards)} cards")
    return True


# =====================================================================
# LEDGER (skip-if-unchanged)
# =====================================================================

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def load_ledger():
    if not os.path.exists(FLASHCARDS_LEDGER_FILE):
        return {}
    try:
        with open(FLASHCARDS_LEDGER_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, Exception):
        return {}


def save_ledger(ledger):
    save_json_atomic(FLASHCARDS_LEDGER_FILE, ledger)
