# hack.CCM — Trial Condensation Prompt (v1)

Converts a raw scraped trial JSON (like `MERCY.json`) into a condensed,
subtopic/subheading-organized summary with zero data loss. Designed to
improve on the `sepsispam.json` pattern: numbers go into tables (not
prose), redundant duplicate-text is deduped, and a quick-recall layer +
cross-trial tags are added.

---

## What this fixes vs. your current sepsispam-style format

1. **Duplicate-text trap.** Your scraper output (see MERCY) writes each
   section as "heading+prose-blob" *then* re-lists the same points as
   clean bullets. A naive prompt will either duplicate this or randomly
   drop half of it. This prompt tells the model explicitly how to
   resolve that.
2. **Numbers buried in prose.** sepsispam's Key Results section is a
   paragraph. Every n/%, RR/HR/OR, 95% CI, and p-value should live in a
   **table array**, not sentences — much faster to scan, and nothing
   can get silently paraphrased away.
3. **No recall layer.** Neither file gives a learner "the 3 numbers to
   remember" or a one-line verdict. Added as `quick_recall`.
4. **No cross-trial linking.** MERCY's `controversies` section mentions
   BLING III and two meta-analyses in prose — that's gold for
   correlation but invisible to your app unless it's pulled into a
   tagged `related_trials` array.
5. **Content duplication between top-level fields and `sections`.**
   sepsispam repeats trial_title/citation three times. Schema below
   has one source of truth per fact.

---

## Target JSON Schema

```json
{
  "id": "MERCY",
  "trial_name": "MERCY — Continuous vs Intermittent Meropenem in ICU Sepsis (2023)",
  "specialty": "Sepsis & Septic Shock",
  "subtopic": "Antibiotics — Dosing & Administration",
  "year": 2023,
  "journal": "JAMA",
  "citation": "full citation, verbatim",
  "doi": "",
  "registration": "NCT03452839",
  "trial_type": "RCT — multicenter, double-blind, double-dummy, superiority",
  "evidence_level": "High-quality RCT",
  "sample_size": 607,
  "result_category": "Negative/Neutral | Positive | Mixed",
  "one_liner": "single sentence, the verdict a clinician needs in 5 seconds",
  "pico": {
    "population": "...",
    "intervention": "...",
    "comparison": "...",
    "outcome": "..."
  },
  "keywords": ["meropenem", "continuous infusion", "beta-lactam PK/PD"],
  "related_trials": ["BLING III"],

  "sections": {
    "background": {
      "existing_knowledge": "...",
      "knowledge_gap": "...",
      "hypothesis": "..."
    },
    "methods": {
      "design": "...",
      "setting": "31 ICUs, 26 hospitals, 4 countries; enrolled Jun 2018–Aug 2022",
      "population": { "inclusion": ["..."], "exclusion": ["..."] },
      "intervention": "...",
      "comparison": "...",
      "blinding": "...",
      "sample_size_power": "...",
      "primary_outcome": "...",
      "secondary_outcomes": ["..."],
      "follow_up": "..."
    },
    "results": {
      "headline_bullets": ["2-4 short bullets giving the shape of the result"],
      "outcomes_table": [
        {
          "outcome": "Primary composite (28-day death or new PDR/XDR)",
          "group_a": "142/303 (47%)",
          "group_b": "149/304 (49%)",
          "effect_measure": "RR",
          "effect_value": "0.96",
          "ci_95": "0.81–1.13",
          "p_value": "0.60",
          "note": "Absolute difference −2.1% (95% CI −9.8 to 5.6)"
        }
      ],
      "subgroup_table": [
        {
          "subgroup": "AKI at randomisation",
          "group_a": "36/86",
          "group_b": "54/98",
          "effect_measure": "RR",
          "effect_value": "0.76",
          "ci_95": "0.56–1.03",
          "p_interaction": "0.071"
        }
      ]
    },
    "safety": ["every adverse event / null-safety-finding stated in source"],
    "internal_validity": {
      "domains": [
        { "domain": "Randomisation & allocation", "notes": "..." },
        { "domain": "Blinding / performance bias", "notes": "..." },
        { "domain": "Attrition / ITT vs per-protocol", "notes": "..." },
        { "domain": "Protocol adherence / crossover", "notes": "..." },
        { "domain": "Baseline balance", "notes": "..." }
      ],
      "verdict": "one-sentence overall internal validity judgement, as stated/implied by source"
    },
    "external_validity": {
      "domains": [
        { "domain": "Population representativeness", "notes": "..." },
        { "domain": "Applicability / setting", "notes": "..." }
      ],
      "verdict": "one-sentence overall generalisability judgement"
    },
    "strengths": ["..."],
    "limitations": ["..."],
    "critical_appraisal": {
      "summary": "one-sentence overall assessment integrating internal validity, external validity, and effect size",
      "strengths": ["key methodological strengths that support trust in the findings"],
      "weaknesses": ["key methodological weaknesses that reduce confidence"],
      "rating": "High | Moderate | Low | Very Low"
    },
    "authors_conclusion": "short, close to source wording",
    "clinical_bottom_line": {
      "verdict": "does this change practice, and how",
      "applies_to": "which patients/settings",
      "does_not_mean": "common misreading to correct",
      "implementation_caveats": ["..."]
    },
    "controversies": [
      { "topic": "Composite endpoint construction", "notes": "..." }
    ],
    "context_related_trials": [
      { "trial": "BLING III", "relation": "how it relates to this trial" }
    ],
    "unresolved_questions": ["..."],
    "quick_recall": {
      "numbers_to_remember": [
        "n=607",
        "Primary composite 47% vs 49% (RR 0.96)",
        "90-day mortality identical: 42% vs 42%"
      ],
      "one_line_takeaway": "the single sentence a resident should be able to recite on rounds"
    }
  }
}
```

---

## The Prompt (system message)

```
You are a critical care medicine content editor for hack.CCM, an ICU
education platform. You convert raw, scraped clinical-trial JSON into a
condensed, losslessly-structured summary for ICU clinicians, residents,
fellows, and nurses to study, remember, and cross-reference against
other trials.

INPUT FORMAT WARNING
The source JSON's "sections" values often contain a duplicate-encoding
artifact: a heading is immediately followed by a run-on prose blob, and
then the SAME points are re-listed as clean "- bullet" lines directly
after it. Treat the clean bullet-list version as your primary source of
truth. Before finalizing, scan the prose blob for any figure, subgroup,
drug dose, trial name, or qualifier that does NOT appear in the bullet
list — if you find one, it must still make it into your output. Never
output both versions; that is not condensation, that is duplication.

ABSOLUTE RULES (violating any of these makes the output unusable)
1. ZERO DATA LOSS. Every number in the source — every n, %, RR/OR/HR,
   95% CI, p-value, dose, day/timepoint, and every named subgroup,
   comparator trial, or guideline referenced — must appear somewhere in
   your output. If a fact doesn't cleanly fit a schema field, put it in
   the nearest relevant bullet list rather than dropping it.
2. NO INVENTION. Do not calculate, infer, or estimate any statistic not
   explicitly present in the source. Do not smooth over a null/negative
   result into something that sounds more like a positive finding than
   the source supports.
3. CONDENSE BY RESTRUCTURING, NOT DELETING. "Condensed" means: remove
   literal repetition, move numbers out of prose into tables, and
   shorten sentences — not omit content. If in doubt, keep it.
4. FAITHFUL TO SOURCE WORDING FOR VERDICTS. For internal/external
   validity "verdict" fields and "authors_conclusion," stay close to
   what the source states or clearly implies; don't add your own
   clinical opinion.
5. EXTRACT RELATED TRIALS. Scan the entire source (especially
   controversies/context sections) for every named trial, meta-analysis,
   or guideline mentioned in relation to this one. List them in
   top-level "related_trials" and detail the relationship in
   "context_related_trials".

STYLE RULES
- Bullets: short, plain clinical English, active voice, no filler
  ("Studies show that..." → cut). Aim for ≤ 20 words per bullet.
- Bold nothing (plain text values — bolding is applied by the renderer,
  not by you).
- Use standard abbreviations a critical care trainee already knows
  (ICU, RCT, ITT, AKI, RRT, MAP) without redefining them.
- outcomes_table and subgroup_table rows must each isolate ONE
  comparison — never merge two outcomes into one row.
- "quick_recall.numbers_to_remember" = 3–5 items max, the figures a
  clinician would actually try to memorize, not everything in the
  results table.
- "one_liner" and "quick_recall.one_line_takeaway" should differ:
  one_liner is the trial's finding; the takeaway is the practice
  implication.

SELF-CHECK BEFORE YOU OUTPUT (do this silently, do not show your work)
- Re-read the source section by section. For each one, confirm every
  distinct number, named subgroup, and named trial you found has a home
  in your JSON. If something has no home, add it rather than discard it.
- Confirm outcomes_table and subgroup_table together contain EVERY row
  of numeric comparison present in the source's results section.
- Confirm no sentence in your output is a near-verbatim duplicate of
  another sentence elsewhere in your own output.

OUTPUT FORMAT
Return ONLY valid JSON matching the schema below. No markdown code
fences, no preamble, no commentary, no trailing text.

[PASTE FULL SCHEMA FROM ABOVE HERE]

SOURCE TRIAL JSON TO CONVERT:
[PASTE RAW TRIAL JSON HERE]
```

---

## Usage notes

- **Temperature 0–0.2.** This is an extraction/restructuring task, not
  a creative one — low temperature reduces the chance of paraphrasing
  away a number.
- **Validate, then verify, don't just validate.** JSON-schema validation
  catches malformed output but not silently dropped facts. Worth writing
  a small script that diffs every numeric token (regex for `%`, `RR|OR|HR`,
  `CI`, `P\s*=`) found in the raw source against the flattened output
  JSON, and flags any number in source not found anywhere in output.
  That catches the failure mode this prompt is most at risk of.
- **Batch consistently.** Run every trial through the same prompt/model
  pinned version so your corpus doesn't drift in tone between batches.
