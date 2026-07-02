import os
import json
import time
import argparse
from dotenv import load_dotenv

load_dotenv()

OUTPUT_DIR = "output_files"

SYSTEM_PROMPT = """You are a medical text formatting assistant. Given a clinical summary in unstructured prose, restructure it into a clean, scannable format:

1. Use bullet points for lists of findings, criteria, or items
2. Use numbered steps for protocols or sequential actions
3. Bold key labels like **Strengths**, **Limitations**, **Dose**, **Indication**, **Monitoring**, **Key Point**, **Recommendation** before their content
4. Use ## for major section headings (e.g. ## Key Pearls, ## Bedside Protocol)
5. Preserve ALL medical facts — do not add, remove, or alter content
6. Do NOT use markdown tables unless they were explicitly present
7. Keep the same voice and tense
8. For recommendations, format as: - **[Label]** Statement (Strength, Evidence Grade)
9. If the text already has reasonable bullet/number structure and bold labels, leave it as-is and return it unchanged.

Output ONLY the reformatted text, no explanations."""


def load_json(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def needs_reformat(text):
    """Check if text is likely prose (needs reformatting) vs already structured."""
    if not text or len(text) < 100:
        return False
    # Count bullet points, bold labels, numbered items
    lines = text.split("\n")
    bullet_count = sum(1 for l in lines if l.strip().startswith("- ") or l.strip().startswith("* "))
    bold_count = sum(1 for l in lines if "**" in l)
    numbered_count = sum(1 for l in lines if l.strip() and l.strip()[0].isdigit() and ". " in l[:5])
    structured = bullet_count + bold_count + numbered_count
    # If < 15% of non-empty lines are structured, it's prose
    non_empty = sum(1 for l in lines if l.strip())
    if non_empty == 0:
        return False
    ratio = structured / non_empty
    return ratio < 0.15


def call_together_api(text, api_key, model="openai/gpt-oss-120b"):
    import urllib.request
    import ssl

    url = "https://api.together.xyz/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    ctx = ssl.create_default_context()
    resp = urllib.request.urlopen(req, context=ctx, timeout=120)
    result = json.loads(resp.read().decode("utf-8"))
    return result["choices"][0]["message"]["content"].strip()


def main():
    parser = argparse.ArgumentParser(description="Restructure old summary prose into structured markdown")
    parser.add_argument("--api-key", help="Together API key (defaults to TOGETHER_API_KEY env var)")
    parser.add_argument("--model", default="openai/gpt-oss-120b", help="Together model name")
    parser.add_argument("--dry-run", action="store_true", help="Show which files would be processed without making changes")
    parser.add_argument("--limit", type=int, default=None, help="Max files to process")
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("TOGETHER_API_KEY")
    if not api_key:
        print("ERROR: Provide --api-key or set TOGETHER_API_KEY in .env")
        return

    if not os.path.isdir(OUTPUT_DIR):
        print(f"ERROR: {OUTPUT_DIR} not found")
        return

    # Collect all JSON files
    json_files = []
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for fname in files:
            if fname.endswith(".json"):
                json_files.append(os.path.join(root, fname))

    print(f"Found {len(json_files)} JSON files")

    processed = 0
    skipped = 0
    errors = 0

    for filepath in sorted(json_files):
        if args.limit and processed >= args.limit:
            break

        relpath = os.path.relpath(filepath, OUTPUT_DIR)
        try:
            data = load_json(filepath)
        except Exception as e:
            print(f"  SKIP {relpath}: failed to load ({e})")
            skipped += 1
            continue

        # Check clinical_summary_markdown
        text = data.get("clinical_summary_markdown", "")
        is_old_format = data.get("parsing_notes") == "old_md_schema"

        if not text:
            skipped += 1
            continue

        if not needs_reformat(text):
            skipped += 1
            continue

        print(f"  REFORMAT {relpath} ({len(text)} chars)...", end=" ", flush=True)

        if args.dry_run:
            print("(dry run)")
            processed += 1
            continue

        try:
            reformatted = call_together_api(text, api_key, args.model)
            data["clinical_summary_markdown"] = reformatted
            data["parsing_notes"] = "restructured_via_gpt-oss"
            save_json(filepath, data)
            print(f"OK ({len(reformatted)} chars)")
            processed += 1
            time.sleep(0.5)  # rate limit buffer
        except Exception as e:
            print(f"ERROR: {e}")
            errors += 1
            time.sleep(2)  # back off on error

    print(f"\nDone. Processed: {processed}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    main()
