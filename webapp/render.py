"""Markdown/print rendering and text extraction for summaries."""
import html
import json
import re


def spec_color_from_name(name):
    colors = {
        "Cardiology": "C6554B", "Pulmonology": "3A7CA5", "Infectious Diseases": "4F8A6D",
        "Neurology": "6B5B95", "Nephrology": "B08D57", "Gastroenterology": "10B981",
        "Hematology": "E11D48", "Hepatology": "14B8A6", "Immunology": "A855F7",
        "Sepsis": "F97316", "Trauma": "DC2626", "Endocrinology": "06B6D4",
        "General": "6B7280", "Multisystem": "6366F1",
        "Nutrition": "84CC16", "Obstetrics and Gynecology": "D946EF", "Rheumatology": "0EA5E9",
        "Toxicology": "7C3AED", "Oncology": "059669", "Surgery": "D97706", "Other": "9333EA",
    }
    return colors.get(name, "6B7280")


def bold_labels(text):
    return re.sub(
        r'\b(Strengths|Limitations|Dose|Indication|Adverse effects?|Route|Frequency|'
        r'Duration|Monitoring|Contraindications?|Precautions?|Key Point|Note|Finding|'
        r'Result|Recommendation)\s*:',
        r'**\1:**',
        text
    )


def render_printable(title, meta_html, markdown, kind_label):
    """Standalone, printable HTML page rendering markdown (with KaTeX math).
    Used by /export/print — opens in a new window where the user saves as PDF."""
    esc = html.escape
    page_title = esc(title) if title else "hack.CCM Export"
    html_out = f"""<!DOCTYPE html>
<html lang="en" data-theme="dim">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{page_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"></script>
<style>
  :root {{
    --ink:#F1E4CE; --ink-muted:#C4B18C; --border:#3A3226; --accent:#E8B778;
    --bg-sunk:#241F17; --radius:10px;
  }}
  * {{ box-sizing:border-box; }}
  html, body {{ margin:0; padding:0; }}
  body {{ background:#1F1B14; color:var(--ink); font-family:'Atkinson Hyperlegible',sans-serif; font-size:16px; line-height:1.5; }}
  .toolbar {{ position:fixed; top:0; left:0; right:0; display:flex; align-items:center; gap:10px; padding:10px 18px; background:#14100B; border-bottom:1px solid var(--border); z-index:20; }}
  .toolbar .tag {{ font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; color:var(--ink-muted); }}
  .toolbar .btn {{ margin-left:auto; background:var(--accent); color:#1F1B14; border:none; font:inherit; font-weight:700; padding:8px 16px; border-radius:8px; cursor:pointer; }}
  .doc {{ max-width:880px; margin:70px auto 60px; padding:0 22px; }}
  h1.doc-title {{ font-family:'Space Grotesk',sans-serif; font-size:1.7rem; line-height:1.3; margin:10px 0 6px; }}
  .meta {{ color:var(--ink-muted); font-size:.9rem; margin:0 0 22px; }}
  .article h1, .article h2 {{ font-family:'Space Grotesk',sans-serif; }}
  .article h1 {{ font-size:1.45rem; margin:24px 0 10px; }}
  .article h2 {{ font-size:1.25rem; margin:22px 0 8px; }}
  .article h3 {{ font-size:1.08rem; margin:18px 0 8px; }}
  .article p {{ margin:10px 0; }}
  .article ul, .article ol {{ margin:10px 0; padding-left:26px; }}
  .article li {{ margin:4px 0; }}
  .article code {{ font-family:'JetBrains Mono',monospace; font-size:.86em; background:var(--bg-sunk); border-radius:4px; padding:1px 5px; }}
  .article pre {{ background:var(--bg-sunk); border:1px solid #3A3226; border-radius:10px; padding:12px 14px; overflow:auto; }}
  .article blockquote {{ border-left:3px solid var(--accent); margin:12px 0; padding:4px 14px; color:var(--ink-muted); }}
  .article table {{ border-collapse:collapse; width:100%; margin:14px 0; }}
  .article th, .article td {{ border:1px solid #3A3226; padding:7px 10px; text-align:left; vertical-align:top; }}
  .article th {{ background:var(--bg-sunk); font-weight:700; }}
  .article a {{ color:var(--accent); }}
  .article hr {{ border:none; border-top:1px solid #3A3226; margin:18px 0; }}
  .katex-display {{ margin:14px 0; overflow-x:auto; overflow-y:hidden; }}
  @media print {{
    .toolbar {{ display:none; }}
    body {{ background:#fff !important; color:#111 !important; }}
    .doc {{ margin:0 auto; max-width:none; padding:0; }}
    a {{ color:#111 !important; text-decoration:none; }}
    .article table, .article th, .article td {{ border-color:#888; }}
    .article code {{ background:#f0f0f0; }}
  }}
</style>
</head>
<body>
<div class="toolbar"><span class="badge">hack.CCM &middot; {esc(kind_label or '')}</span><button class="btn" onclick="window.print()">&#128196; Print / Save as PDF</button></div>
<div class="doc">
  <h1>{page_title}</h1>
  <div class="meta">{meta_html or ''}</div>
  <article class="article" id="md-content"></article>
</div>
<script>
  var RAW = {json.dumps(markdown or "", ensure_ascii=False)};
  try {{ document.getElementById('md-content').innerHTML = marked.parse(RAW); }} catch(e){{ document.getElementById('md-content').textContent = RAW; }}
  function renderMath(){{
    try{{ if(window.renderMathInElement){{ renderMathInElement(document.getElementById('md-content'),{{delimiters:[{{left:'$$',right:'$$',display:true}},{{left:'\\\\(',right:'\\\\)',display:false}},{{left:'\\\\[',right:'\\\\]',display:true}}],throwOnError:false,strict:'ignore'}}); }} }}catch(e){{}}
  }}
  renderMath();
  window.addEventListener('load', function(){{ setTimeout(function(){{ window.print(); }}, 600); }});
</script>
</body>
</html>"""
    return html_out


def format_new_schema_as_markdown(payload):
    parts = []
    summary = payload.get("one_line_summary", "")
    if summary:
        parts.append(f"> **One-Line Summary:** {summary}\n")
    pearls = payload.get("key_pearls", [])
    if pearls:
        parts.append("## Key Pearls\n" + "\n".join(f"- {p}" for p in pearls) + "\n")
    sections = payload.get("sections", [])
    if sections:
        for s in sections:
            heading = s.get("heading", "")
            content = s.get("content", "")
            section_pearls = s.get("section_pearls", [])
            block = f"## {heading}\n{content}" if heading else content
            if section_pearls:
                block += "\n\n**Section Pearls:**\n" + "\n".join(f"- {sp}" for sp in section_pearls)
            parts.append(block)
    rec_blocks = payload.get("recommendation_blocks", [])
    if rec_blocks:
        for block in rec_blocks:
            topic = block.get("topic", "")
            narrative = block.get("narrative", "")
            block_parts = [f"## {topic}"] if topic else []
            if narrative:
                block_parts.append(narrative)
            for rec in block.get("recommendations", []):
                rec_id = rec.get("rec_id")
                statement = rec.get("statement", "")
                strength = rec.get("strength")
                evidence_grade = rec.get("evidence_grade")
                label = f"[{rec_id}] " if rec_id else ""
                meta_parts = []
                if strength:
                    meta_parts.append(strength)
                if evidence_grade:
                    meta_parts.append(evidence_grade)
                meta = f" *({', '.join(meta_parts)})*" if meta_parts else ""
                block_parts.append(f"- {label}{statement}{meta}")
            parts.append("\n".join(block_parts))
    protocol = payload.get("bedside_protocol", [])
    if protocol:
        protocol_parts = ["## Bedside Protocol"]
        for step in protocol:
            step_num = step.get("step", "")
            title = step.get("title", "")
            action = step.get("action", "")
            protocol_parts.append(f"**Step {step_num}: {title}**\n\n{action}")
        parts.append("\n\n".join(protocol_parts))
    drugs_doses = payload.get("drugs_doses", [])
    if drugs_doses:
        block = "## Drugs & Doses\n"
        for dd in drugs_doses:
            drug = dd.get("drug", "")
            dose = dd.get("dose", "")
            indication = dd.get("indication", "")
            adverse = dd.get("adverse_effects", "")
            block += f"- **{drug}**"
            if dose:
                block += f"  \n  **Dose:** {dose}"
            if indication:
                block += f"  \n  **Indication:** {indication}"
            if adverse:
                block += f"  \n  **Adverse effects:** {adverse}"
            block += "\n"
        parts.append(block)
    strengths = payload.get("strengths_limitations", "")
    if strengths:
        parts.append(f"## Strengths & Limitations\n{bold_labels(strengths)}")
    return "\n\n".join(parts)


def extract_search_text(payload):
    text_parts = []

    # Paper/guideline format
    text_parts.append(payload.get("paper_name", ""))
    text_parts.append(payload.get("clinical_summary_markdown", ""))
    text_parts.append(payload.get("primary_authors", ""))
    text_parts.append(payload.get("journal_name", ""))
    text_parts.append(payload.get("title", ""))
    authors = payload.get("authors", "")
    if not authors:
        issuing = payload.get("issuing_bodies", [])
        if issuing:
            authors = ", ".join(issuing)
    text_parts.append(authors)
    text_parts.append(payload.get("journal", ""))
    text_parts.append(payload.get("one_line_summary", ""))
    for p in payload.get("key_pearls", []):
        text_parts.append(p)
    secs_array = payload.get("sections", [])
    if isinstance(secs_array, list):
        for s in secs_array:
            if isinstance(s, dict):
                text_parts.append(s.get("heading", ""))
                text_parts.append(s.get("content", ""))
                for sp in s.get("section_pearls", []):
                    text_parts.append(sp)
    text_parts.append(payload.get("consensus_method", ""))
    for b in payload.get("recommendation_blocks", []):
        text_parts.append(b.get("topic", ""))
        text_parts.append(b.get("narrative", ""))
        for r in b.get("recommendations", []):
            text_parts.append(r.get("statement", ""))
    for ib in payload.get("issuing_bodies", []):
        text_parts.append(ib)
    for step in payload.get("bedside_protocol", []):
        text_parts.append(step.get("title", ""))
        text_parts.append(step.get("action", ""))
    text_parts.append(payload.get("strengths_limitations", ""))
    for tag in payload.get("tags", []):
        text_parts.append(tag)

    # Trial format (condensed)
    text_parts.append(payload.get("trial_name", ""))
    text_parts.append(payload.get("trial_title", ""))
    text_parts.append(payload.get("one_liner", ""))
    text_parts.append(payload.get("citation", ""))
    text_parts.append(payload.get("specialty", ""))
    for kw in payload.get("keywords", []):
        text_parts.append(kw)

    # Trial sections (condensed — object with named keys like background, methods, results)
    trial_sec = payload.get("sections", {})
    if isinstance(trial_sec, dict):
        for sec_key, sec_val in trial_sec.items():
            if isinstance(sec_val, str):
                text_parts.append(sec_val)
            elif isinstance(sec_val, dict):
                for sub_val in sec_val.values():
                    if isinstance(sub_val, str):
                        text_parts.append(sub_val)
                    elif isinstance(sub_val, list):
                        for item in sub_val:
                            if isinstance(item, str):
                                text_parts.append(item)
                            elif isinstance(item, dict):
                                for iv in item.values():
                                    if isinstance(iv, str):
                                        text_parts.append(iv)

    return " ".join(text_parts).lower()


def extract_metadata(payload):
    title = payload.get("paper_name") or payload.get("title") or payload.get("trial_name") or payload.get("trial_title", "")
    system = payload.get("system") or ""
    if not system and payload.get("specialty"):
        if isinstance(payload["specialty"], list):
            system = ", ".join(payload["specialty"])
        else:
            system = payload["specialty"]
    article_type = payload.get("type_of_article") or ""
    if not article_type and payload.get("doc_type"):
        article_type = payload["doc_type"]
    if not article_type and payload.get("trial_type"):
        article_type = payload["trial_type"]
    journal = payload.get("journal_name") or payload.get("journal", "")
    if not journal:
        issuing = payload.get("issuing_bodies", [])
        if issuing:
            journal = ", ".join(issuing)
    if not journal:
        journal = "Unknown Journal"
    return title, system, article_type, journal
