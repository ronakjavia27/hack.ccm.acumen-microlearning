"""
llm.py - Unified LLM execution with provider fallback and chunking.
Supports: OpenRouter, Gemini.
"""

import os
import re
import json
import time
from copy import deepcopy

from acumen_core.config import (
    PRIMARY_GEMINI_API_KEY,
    BACKUP_GEMINI_API_KEY,
    OPENROUTER_SUMMARY_MODEL,
    OPENROUTER_SUMMARY_FALLBACK,
    OPENROUTER_PEARLS_MODEL,
    OPENROUTER_PEARLS_FALLBACK,
    GEMINI_SUMMARY_MODEL,
    GEMINI_PEARLS_MODEL,
    GEMINI_VISION_MODEL,
    SUBTOPIC_LLM_MODEL,
    GEMINI_SUBTOPIC_MODEL,
    SUBTOPIC_TEMPERATURE,
    SUBTOPIC_MAX_TOKENS,
    TEMPERATURE_EXTRACTION,
    TEMPERATURE_PEARLS,
    MAX_TOKENS_EXTRACTION,
    MAX_TOKENS_PEARLS,
    MAX_RETRIES,
    RETRY_DELAY,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


def _get_gemini_client():
    """Get primary Gemini client."""
    if not PRIMARY_GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=PRIMARY_GEMINI_API_KEY)
    except Exception:
        return None


def _get_backup_gemini_client():
    """Get backup Gemini client."""
    if not BACKUP_GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=BACKUP_GEMINI_API_KEY)
    except Exception:
        return None


# =====================================================================
# CORE API CALL
# =====================================================================
def call_chat_api(client, model, system_prompt, user_content, temperature=0.3, max_tokens=16384):
    """
    Unified chat API call for OpenAI-compatible (OpenRouter) endpoints.
    Returns parsed dict (if JSON mode) or str (if text mode).
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    kwargs = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    response = client.chat.completions.create(**kwargs)
    raw = response.choices[0].message.content
    if raw is None or raw.strip() == "":
        raise ValueError("Empty response from model")

    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
    raw = re.sub(r'\n?\s*```$', '', raw)

    return json.loads(raw)


def call_gemini_api(client, model, system_prompt, prompt_parts, temperature=0.3):
    """Call Gemini with file/multipart prompt. Returns parsed dict."""
    try:
        from google.genai import types
    except Exception:
        raise RuntimeError("google-genai not installed")

    config = types.GenerateContentConfig(
        system_instruction=system_prompt,
        temperature=temperature,
        response_mime_type="application/json",
    )
    response = client.models.generate_content(
        model=model,
        contents=prompt_parts,
        config=config,
    )
    raw = response.text.strip()
    raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
    raw = re.sub(r'\n?\s*```$', '', raw)
    return json.loads(raw)


def call_gemini_vision(image, prompt):
    """Call Gemini Vision for image/figure transcription."""
    api_key = PRIMARY_GEMINI_API_KEY or BACKUP_GEMINI_API_KEY
    if not api_key:
        return ""
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=GEMINI_VISION_MODEL,
            contents=[prompt, image],
        )
        return response.text.strip()
    except Exception:
        return ""


# =====================================================================
# RETRY HELPERS
# =====================================================================
def _is_retryable(error):
    """Check if an error is worth retrying."""
    msg = str(error).lower()
    if 'timeout' in msg or 'timed out' in msg:
        return True
    if 'rate limit' in msg or '429' in msg or 'resource_exhausted' in msg:
        return True
    if '503' in msg or '502' in msg or 'service unavailable' in msg:
        return True
    if 'internal server' in msg or '500' in msg:
        return True
    if 'empty response' in msg:
        return True
    return False


# =====================================================================
# EXECUTION WITH FALLBACK - OpenRouter (Pass 1 summary extraction)
# =====================================================================
def execute_with_fallback(
    system_prompt,
    user_content,
    category_tag,
    max_retries=None,
    retry_delay=None,
):
    """
    Pass 1 summary extraction via OpenRouter (primary -> fallback model).
    Returns parsed JSON dict.
    """
    from acumen_core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
    max_retries = max_retries or MAX_RETRIES
    retry_delay = retry_delay or RETRY_DELAY
    last_error = None

    client = _get_openrouter_client()
    if not client:
        raise RuntimeError("OpenRouter client not available (check OPENROUTER_API_KEY)")

    models = [OPENROUTER_SUMMARY_MODEL, OPENROUTER_SUMMARY_FALLBACK]
    for model in models:
        for attempt in range(max_retries):
            try:
                print(f"    OpenRouter: {model} (attempt {attempt + 1}/{max_retries})")
                return call_openrouter_api(
                    client, model, system_prompt, user_content,
                    temperature=TEMPERATURE_EXTRACTION,
                    max_tokens=MAX_TOKENS_EXTRACTION,
                )
            except json.JSONDecodeError as e:
                last_error = e
                print(f"    [X] JSON parse error: {e}")
                break
            except Exception as e:
                last_error = e
                if _is_retryable(e) and attempt < max_retries - 1:
                    wait = retry_delay * (attempt + 1)
                    print(f"    [!] {e}")
                    print(f"    Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"    [X] OpenRouter {model} failed: {e}")
                    break

    raise last_error or RuntimeError("OpenRouter models exhausted")


def execute_with_gemini(
    system_prompt,
    user_content,
    category_tag,
    max_retries=None,
    retry_delay=None,
):
    """
    Gemini-only extraction with retry and backup fallback.
    Uses GEMINI_SUMMARY_MODEL primary, backup key retries same model.
    Returns parsed JSON dict.
    """
    max_retries = max_retries or MAX_RETRIES
    retry_delay = retry_delay or RETRY_DELAY
    last_error = None

    primary_client = _get_gemini_client()
    backup_client = _get_backup_gemini_client()
    model = GEMINI_SUMMARY_MODEL

    if primary_client:
        for attempt in range(max_retries):
            try:
                print(f"    Gemini: {model} (attempt {attempt + 1}/{max_retries})")
                return call_gemini_api(
                    primary_client, model, system_prompt, [user_content],
                    temperature=TEMPERATURE_EXTRACTION,
                )
            except json.JSONDecodeError as e:
                last_error = e
                print(f"    [X] JSON parse error: {e}")
                break
            except Exception as e:
                last_error = e
                if _is_retryable(e) and attempt < max_retries - 1:
                    wait = retry_delay * (attempt + 1)
                    print(f"    [!] {e}")
                    print(f"    Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"    [X] Gemini primary failed: {e}")
                    break

    # Fallback to backup Gemini key
    if backup_client:
        for attempt in range(max_retries):
            try:
                print(f"    Gemini Backup: {model} (attempt {attempt + 1}/{max_retries})")
                return call_gemini_api(
                    backup_client, model, system_prompt, [user_content],
                    temperature=TEMPERATURE_EXTRACTION,
                )
            except json.JSONDecodeError as e:
                last_error = e
                print(f"    [X] JSON parse error: {e}")
                break
            except Exception as e:
                last_error = e
                if _is_retryable(e) and attempt < max_retries - 1:
                    wait = retry_delay * (attempt + 1)
                    time.sleep(wait)
                else:
                    print(f"    [X] Gemini backup failed: {e}")
                    break

    raise last_error or RuntimeError("Gemini models exhausted")


def execute_pearl_extraction(markdown_text, file_name="", llm="openrouter"):
    """
    Separate Pass 2: Extract clinical pearls.

    Provider-aware:
      llm="openrouter" (default) -> OpenRouter, [OPENROUTER_PEARLS_MODEL, OPENROUTER_PEARLS_FALLBACK]
      llm="gemini"               -> Gemini, GEMINI_PEARLS_MODEL
    Returns list of pearl dicts.
    """
    pearl_system_prompt = """You are an expert critical care clinician and medical educator. Extract high-yield, evidence-based clinical pearls from the summarized medical text provided. Each pearl must meet these criteria:

1. Directly impacts clinical decision-making, bedside management, or exam-level reasoning
2. Specific and concrete: thresholds, cutoffs, dosing ranges, timing, risk modifiers, diagnostic criteria, prognostic markers, or management algorithms
3. Traceable to evidence when present (RCTs, meta-analyses, strong guideline recommendations)
4. Avoid generic statements like "always assess level of evidence" or "more research is needed"
5. Capture practice-changing points, nuances (subgroups, exceptions, contraindications), and clear if-then conditions
6. Each pearl: 1-3 sentences, maximally information-dense, self-contained
7. Include exact numbers, doses, thresholds, or effect sizes where available

Return a JSON object with a "pearls" key containing an array of objects, each with "text" (the pearl) and "topic" (1-3 comma-separated keywords).

Example:
{"pearls": [{"text": "Start broad-spectrum antibiotics within 1 hour for septic shock (SSC 2026, strong recommendation, moderate quality evidence).", "topic": "sepsis, antibiotics"}]}

Output ONLY valid JSON. No preamble, no markdown fences, no commentary."""

    user_content = f"Extract clinical pearls from this summary:\n\n{markdown_text[:8000]}"
    last_error = None

    if llm == "gemini":
        client = _get_gemini_client()
        backup_client = _get_backup_gemini_client()
        model = GEMINI_PEARLS_MODEL
        if client:
            for attempt in range(MAX_RETRIES):
                try:
                    print(f"    Pearls (Gemini): {model} (attempt {attempt + 1}/{MAX_RETRIES})")
                    result = call_gemini_api(
                        client, model, pearl_system_prompt, [user_content],
                        temperature=TEMPERATURE_PEARLS,
                    )
                    if result and isinstance(result, dict) and "pearls" in result:
                        return result["pearls"]
                    return result if isinstance(result, list) else []
                except json.JSONDecodeError as e:
                    last_error = e
                    print(f"    [X] Pearl JSON parse error: {e}")
                    break
                except Exception as e:
                    last_error = e
                    if _is_retryable(e) and attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                    else:
                        print(f"    [X] Pearl extraction {model} failed: {e}")
                        break
        if backup_client:
            for attempt in range(MAX_RETRIES):
                try:
                    print(f"    Pearls (Gemini Backup): {model} (attempt {attempt + 1}/{MAX_RETRIES})")
                    result = call_gemini_api(
                        backup_client, model, pearl_system_prompt, [user_content],
                        temperature=TEMPERATURE_PEARLS,
                    )
                    if result and isinstance(result, dict) and "pearls" in result:
                        return result["pearls"]
                    return result if isinstance(result, list) else []
                except json.JSONDecodeError as e:
                    last_error = e
                    print(f"    [X] Pearl JSON parse error: {e}")
                    break
                except Exception as e:
                    last_error = e
                    if _is_retryable(e) and attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                    else:
                        print(f"    [X] Pearl extraction {model} failed: {e}")
                        break
    else:
        client = _get_openrouter_client()
        if not client:
            raise RuntimeError("OpenRouter client not available (check OPENROUTER_API_KEY)")
        models = [OPENROUTER_PEARLS_MODEL, OPENROUTER_PEARLS_FALLBACK]
        for model in models:
            for attempt in range(MAX_RETRIES):
                try:
                    print(f"    Pearls: {model} (attempt {attempt + 1}/{MAX_RETRIES})")
                    result = call_openrouter_api(
                        client, model, pearl_system_prompt, user_content,
                        temperature=TEMPERATURE_PEARLS,
                        max_tokens=MAX_TOKENS_PEARLS,
                    )
                    if result and isinstance(result, dict) and "pearls" in result:
                        return result["pearls"]
                    return result if isinstance(result, list) else []
                except json.JSONDecodeError as e:
                    last_error = e
                    print(f"    [X] Pearl JSON parse error: {e}")
                    break
                except Exception as e:
                    last_error = e
                    if _is_retryable(e) and attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                    else:
                        print(f"    [X] Pearl extraction {model} failed: {e}")
                        break

    raise last_error or RuntimeError("Pearl extraction failed - no providers available")


def classify_subtopic(system, context, llm="openrouter"):
    """
    Pass 1.5: Classify the exact subtopic for a summary's system.

    Provider-aware:
      llm="openrouter" (default) -> OpenRouter, SUBTOPIC_LLM_MODEL (openai/gpt-oss-20b)
      llm="gemini"               -> Gemini, GEMINI_SUBTOPIC_MODEL (gemini-3.1-flash-lite)

    context: paper title / one-line summary / key points used as classifier input.
    Returns: exact subtopic string from the vocab, or system name if no vocab/failure.
    """
    from acumen_core.subtopics_config import get_subtopics_for_system, format_subtopics_for_prompt

    valid_subtopics = get_subtopics_for_system(system)
    if not valid_subtopics:
        return system

    vocab_listing = format_subtopics_for_prompt(system)
    system_prompt = """You are a medical content librarian. Given the paper context and the target specialty, select the SINGLE most appropriate subtopic from the provided list.

Rules:
1. Choose exactly ONE subtopic from the list. Pick the closest match.
2. If no listed subtopic fits, choose the closest general/summary option available.
3. Return a JSON object: {"subtopic": "<exact subtopic string from list>"}
4. Output ONLY valid JSON. No preamble, no markdown fences, no commentary."""

    user_content = f"Target specialty: {system}\n\nValid subtopics for this specialty:\n{vocab_listing}\n\nPaper context:\n{context[:6000]}\n\nSelect the single best subtopic."

    last_error = None

    if llm == "gemini":
        client = _get_gemini_client()
        backup_client = _get_backup_gemini_client()
        model = GEMINI_SUBTOPIC_MODEL
        if client:
            for attempt in range(MAX_RETRIES):
                try:
                    print(f"    Subtopic (Gemini): {model} (attempt {attempt + 1}/{MAX_RETRIES})")
                    result = call_gemini_api(
                        client, model, system_prompt, [user_content],
                        temperature=SUBTOPIC_TEMPERATURE,
                    )
                    chosen = (result or {}).get("subtopic", "").strip()
                    if chosen in valid_subtopics:
                        return chosen
                    print(f"    [X] Subtopic not in vocab: '{chosen}'")
                    break
                except json.JSONDecodeError as e:
                    last_error = e
                    print(f"    [X] Subtopic JSON parse error: {e}")
                    break
                except Exception as e:
                    last_error = e
                    if _is_retryable(e) and attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                    else:
                        print(f"    [X] Subtopic classify {model} failed: {e}")
                        break
        if backup_client:
            for attempt in range(MAX_RETRIES):
                try:
                    print(f"    Subtopic (Gemini Backup): {model} (attempt {attempt + 1}/{MAX_RETRIES})")
                    result = call_gemini_api(
                        backup_client, model, system_prompt, [user_content],
                        temperature=SUBTOPIC_TEMPERATURE,
                    )
                    chosen = (result or {}).get("subtopic", "").strip()
                    if chosen in valid_subtopics:
                        return chosen
                    print(f"    [X] Subtopic not in vocab: '{chosen}'")
                    break
                except json.JSONDecodeError as e:
                    last_error = e
                    print(f"    [X] Subtopic JSON parse error: {e}")
                    break
                except Exception as e:
                    last_error = e
                    if _is_retryable(e) and attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                    else:
                        print(f"    [X] Subtopic classify {model} failed: {e}")
                        break
    else:
        client = _get_openrouter_client()
        if not client:
            raise RuntimeError("OpenRouter client not available (check OPENROUTER_API_KEY)")
        model = SUBTOPIC_LLM_MODEL
        for attempt in range(MAX_RETRIES):
            try:
                print(f"    Subtopic: {model} (attempt {attempt + 1}/{MAX_RETRIES})")
                result = call_openrouter_api(
                    client, model, system_prompt, user_content,
                    temperature=SUBTOPIC_TEMPERATURE,
                    max_tokens=SUBTOPIC_MAX_TOKENS,
                )
                chosen = (result or {}).get("subtopic", "").strip()
                if chosen in valid_subtopics:
                    return chosen
                print(f"    [X] Subtopic not in vocab: '{chosen}'")
                break
            except json.JSONDecodeError as e:
                last_error = e
                print(f"    [X] Subtopic JSON parse error: {e}")
                break
            except Exception as e:
                last_error = e
                if _is_retryable(e) and attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY * (attempt + 1))
                else:
                    print(f"    [X] Subtopic classify {model} failed: {e}")
                    break

    if last_error:
        print(f"    [~] Subtopic classification failed ({last_error}); using system name: {system}")
    return system


# =====================================================================
# CHUNKING & MERGE
# =====================================================================
# =====================================================================
# OPENROUTER / FLASHCARD EXECUTION
# =====================================================================

def _get_openrouter_client():
    """Get OpenRouter OpenAI-compatible client."""
    from acumen_core.config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL
    if not OPENROUTER_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL)
    except Exception:
        return None


def call_openrouter_api(client, model, system_prompt, user_content, temperature=0.2, max_tokens=8192, json_mode=True):
    """
    Call OpenRouter (OpenAI-compatible). Returns parsed dict (json_mode=True) or raw text.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]

    kwargs = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(**kwargs)
    raw = response.choices[0].message.content
    if raw is None or raw.strip() == "":
        raise ValueError("Empty response from model")

    raw = raw.strip()
    raw = re.sub(r'^```(?:json)?\s*\n?', '', raw)
    raw = re.sub(r'\n?\s*```$', '', raw)

    if json_mode:
        return json.loads(raw)
    return raw


def execute_with_openrouter(
    system_prompt,
    user_content,
    max_retries=None,
    retry_delay=None,
):
    """
    Execute via OpenRouter with retries.
    Returns parsed JSON dict.
    """
    from acumen_core.config import (
        OPENROUTER_MODEL,
        TEMPERATURE_FLASHCARDS,
        MAX_TOKENS_FLASHCARDS,
        MAX_RETRIES,
        RETRY_DELAY,
    )
    max_retries = max_retries or MAX_RETRIES
    retry_delay = retry_delay or RETRY_DELAY
    last_error = None

    client = _get_openrouter_client()
    if not client:
        raise RuntimeError("OpenRouter client not available (check OPENROUTER_API_KEY)")

    model = OPENROUTER_MODEL
    for attempt in range(max_retries):
        try:
            print(f"    OpenRouter: {model} (attempt {attempt + 1}/{max_retries})")
            return call_openrouter_api(
                client, model, system_prompt, user_content,
                temperature=TEMPERATURE_FLASHCARDS,
                max_tokens=MAX_TOKENS_FLASHCARDS,
            )
        except json.JSONDecodeError as e:
            last_error = e
            print(f"    [X] JSON parse error: {e}")
            break
        except Exception as e:
            last_error = e
            if _is_retryable(e) and attempt < max_retries - 1:
                wait = retry_delay * (attempt + 1)
                print(f"    [!] {e}")
                print(f"    Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"    [X] OpenRouter failed: {e}")
                break

    raise last_error or RuntimeError("OpenRouter exhausted")


def execute_with_openrouter_text(
    system_prompt,
    user_content,
    max_retries=None,
    retry_delay=None,
):
    """
    Execute via OpenRouter with TEXT output (no JSON mode).
    Returns raw text string.
    """
    from acumen_core.config import (
        OPENROUTER_MODEL,
        TEMPERATURE_FLASHCARDS,
        MAX_TOKENS_FLASHCARDS,
        MAX_RETRIES,
        RETRY_DELAY,
    )
    max_retries = max_retries or MAX_RETRIES
    retry_delay = retry_delay or RETRY_DELAY
    last_error = None

    client = _get_openrouter_client()
    if not client:
        raise RuntimeError("OpenRouter client not available (check OPENROUTER_API_KEY)")

    model = OPENROUTER_MODEL
    for attempt in range(max_retries):
        try:
            print(f"    OpenRouter Text: {model} (attempt {attempt + 1}/{max_retries})")
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ]
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=TEMPERATURE_FLASHCARDS,
                max_tokens=MAX_TOKENS_FLASHCARDS,
            )
            raw = response.choices[0].message.content
            if raw is None or raw.strip() == "":
                raise ValueError("Empty response from model")
            return raw.strip()
        except Exception as e:
            last_error = e
            if _is_retryable(e) and attempt < max_retries - 1:
                wait = retry_delay * (attempt + 1)
                print(f"    [!] {e}")
                print(f"    Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"    [X] OpenRouter Text failed: {e}")
                break

    raise last_error or RuntimeError("OpenRouter text exhausted")


def execute_openai_compat(
    system_prompt,
    user_content,
    api_key=None,
    model=None,
    base_url=None,
    temperature=0.2,
    max_tokens=8192,
    json_mode=True,
    max_retries=None,
    retry_delay=None,
):
    """
    Execute via any OpenAI-compatible endpoint (OpenRouter, Together, local servers...)
    with explicit api_key/model/base_url overrides. json_mode=True returns a parsed dict.

    Falls back to config defaults when api_key/model/base_url are omitted.
    """
    from acumen_core.config import (
        OPENROUTER_API_KEY,
        OPENROUTER_MODEL,
        OPENROUTER_BASE_URL,
        MAX_RETRIES,
        RETRY_DELAY,
    )
    key = api_key or OPENROUTER_API_KEY
    if not key:
        raise RuntimeError("No API key: pass --api-key or set OPENROUTER_API_KEY")
    endpoint = base_url or OPENROUTER_BASE_URL
    mdl = model or OPENROUTER_MODEL
    max_retries = max_retries or MAX_RETRIES
    retry_delay = retry_delay or RETRY_DELAY
    last_error = None

    from openai import OpenAI
    client = OpenAI(api_key=key, base_url=endpoint)
    for attempt in range(max_retries):
        try:
            print(f"    Compat[{mdl}]: {endpoint} (attempt {attempt + 1}/{max_retries})")
            return call_openrouter_api(
                client, mdl, system_prompt, user_content,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
            )
        except json.JSONDecodeError as e:
            last_error = e
            print(f"    [X] JSON parse error: {e}")
            break
        except Exception as e:
            last_error = e
            if _is_retryable(e) and attempt < max_retries - 1:
                wait = retry_delay * (attempt + 1)
                print(f"    [!] {e}")
                print(f"    Retrying in {wait}s...")
                time.sleep(wait)
            else:
                print(f"    [X] Compat call failed: {e}")
                break

    raise last_error or RuntimeError("OpenAI-compat call exhausted")


def chunk_text(text, chunk_size=None, overlap=None):
    """Split text at paragraph boundaries. Each chunk <= chunk_size with overlap."""
    chunk_size = chunk_size or CHUNK_SIZE
    overlap = overlap or CHUNK_OVERLAP

    if len(text) <= chunk_size:
        return [text]

    result = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end >= len(text):
            result.append(text[start:])
            break
        boundary = text.rfind('\n\n', start, end)
        if boundary == -1 or (boundary - start) < chunk_size // 4:
            boundary = text.rfind('\n', start, end)
            if boundary == -1 or (boundary - start) < chunk_size // 4:
                boundary = text.rfind(' ', start, end)
                if boundary == -1:
                    boundary = end
        chunk = text[start:boundary]
        result.append(chunk)
        start = max(boundary - overlap, boundary - chunk_size // 4)
    return result


def merge_chunks_programmatically(results):
    """Merge multiple chunk extraction outputs without an extra API call."""
    if not results:
        return None
    if len(results) == 1:
        return deepcopy(results[0])

    merged = deepcopy(results[0])

    for chunk_result in results[1:]:
        existing_sections = merged.get("sections", [])
        offset = len(existing_sections)
        for s in chunk_result.get("sections", []):
            s["order"] = s.get("order", 0) + offset
            existing_sections.append(s)

        existing_blocks = merged.get("recommendation_blocks", [])
        offset = len(existing_blocks)
        for b in chunk_result.get("recommendation_blocks", []):
            b["order"] = b.get("order", 0) + offset
            existing_blocks.append(b)

        existing_steps = merged.get("bedside_protocol", [])
        offset = len(existing_steps)
        for s in chunk_result.get("bedside_protocol", []):
            s["step"] = s.get("step", 0) + offset
            existing_steps.append(s)

        existing_pearls = merged.setdefault("key_pearls", [])
        seen = set(p.strip().lower() for p in existing_pearls)
        for p in chunk_result.get("key_pearls", []):
            key = p.strip().lower()
            if key and key not in seen:
                existing_pearls.append(p)
                seen.add(key)

        existing_tags = merged.setdefault("tags", [])
        seen_tags = set(t.strip().lower() for t in existing_tags)
        for t in chunk_result.get("tags", []):
            key = t.strip().lower()
            if key and key not in seen_tags:
                existing_tags.append(t)
                seen_tags.add(key)

        sl_existing = merged.get("strengths_limitations", "") or ""
        sl_chunk = chunk_result.get("strengths_limitations", "") or ""
        if sl_chunk and sl_chunk not in sl_existing:
            merged["strengths_limitations"] = (sl_existing + "\n" + sl_chunk).strip()

    return merged
