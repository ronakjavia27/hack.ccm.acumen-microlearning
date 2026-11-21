"""Content Studio tests — offline (fake LLM, temp dirs). Run: python -m pytest tests/test_studio.py -q"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from acumen_core import config  # noqa: E402
from acumen_core import flashcards as fc  # noqa: E402
from acumen_core.studio import checks, generate, intake, items as store, publish, retrieve  # noqa: E402


@pytest.fixture(autouse=True)
def tmp_dirs(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "STUDIO_ITEMS_DIR", str(tmp_path / "studio" / "items"))
    monkeypatch.setattr(config, "STUDIO_INPUT_DIR", str(tmp_path / "studio_input"))
    monkeypatch.setattr(config, "STUDIO_LEDGER_FILE", str(tmp_path / "studio" / "ledger.json"))
    monkeypatch.setattr(config, "THEORY_MDS_DIR", str(tmp_path / "Theory MDs"))
    monkeypatch.setattr(config, "QUESTION_BANK_DIR", str(tmp_path / "question_bank"))
    monkeypatch.setattr(fc, "FLASHCARDS_DIR", str(tmp_path / "flashcards"))
    monkeypatch.setattr(fc, "FLASHCARDS_INDEX_FILE", str(tmp_path / "flashcards_index.json"))
    monkeypatch.setattr(retrieve, "_LIB", retrieve.Library([
        {"id": "pearl:1", "kind": "pearl", "system": "Pulmonology", "title": "ARDSNet low tidal volume",
         "text": "Low tidal volume ventilation 6 mL/kg predicted body weight reduces mortality in ARDS"},
        {"id": "paper:x.json", "kind": "paper", "system": "Cardiology", "title": "Heart failure", "text": "HFrEF LVEF"},
    ]))
    yield tmp_path
    generate.set_llm(None)


# ---- fake LLM ----------------------------------------------------------------

ANSWER = ("## Definition\nARDS is acute hypoxaemic respiratory failure with bilateral opacities. "
          "Berlin criteria: onset within 1 week, bilateral opacities, not fully explained by cardiac failure, "
          "PaO2/FiO2 ≤300 mmHg on PEEP ≥5 cmH2O.\n## Management\n- Low tidal volume 6 mL/kg PBW\n"
          "- Plateau pressure <30 cmH2O\n- Prone positioning for 16 h/day when P/F <150\n") + ("Detail. " * 700)


def pkg_compose(**over):
    base = {"title": "ARDS", "system": "Pulmonology", "subtopic": "ARDS", "answer_md": ANSWER,
            "key_points": ["Berlin criteria", "6 mL/kg", "Prone 16 h"],
            "rubric": [{"point": "Definition", "keywords": ["bilateral"], "marks": 4},
                       {"point": "Management", "keywords": ["6 mL/kg"], "marks": 6}],
            "claims": [{"text": "Tidal volume 6 mL/kg PBW", "basis": "library:pearl:1", "confidence": "high", "high_stakes": True},
                       {"text": "Prone 16 h/day if P/F <150", "basis": "general", "confidence": "high", "high_stakes": True}],
            "uncertainties": []}
    base.update(over)
    return base


DERIVED = {"flashcards": [{"front": "Target tidal volume in ARDS?", "back": "6 mL/kg predicted body weight"},
                          {"front": "When to prone in ARDS?", "back": "P/F <150, for 16 h/day"}],
           "mcqs": [{"stem": "Recommended tidal volume in ARDS ventilation is:", "options": ["4 mL/kg", "6 mL/kg", "10 mL/kg", "12 mL/kg"],
                     "answer": [1], "explanation": "ARDSNet: 6 mL/kg PBW.", "difficulty": 2}]}


def good_verify(**over):
    v = {"overall": 92, "claim_checks": [{"i": 0, "verdict": "supported"}, {"i": 1, "verdict": "supported"}],
         "issues": [], "coverage": {"score": 90, "missing": []}, "summary": "Accurate."}
    v.update(over)
    return v


class FakeLLM:
    def __init__(self, verify_seq=None, blind_seq=None, compose=None, revise=None):
        self.calls = []
        self.verify_seq = list(verify_seq or [good_verify()])
        self.blind_seq = list(blind_seq or [{"answers": [{"i": 0, "chosen": [1], "confidence": "high"}]}])
        self.compose = compose or pkg_compose()
        self.revise = revise

    def __call__(self, role, system, user, max_tokens):
        self.calls.append((role, user))
        if role == "compose":
            return self.compose
        if role == "derive":
            return DERIVED
        if role == "verify":
            return self.verify_seq.pop(0) if len(self.verify_seq) > 1 else self.verify_seq[0]
        if role == "blind":
            return self.blind_seq.pop(0) if len(self.blind_seq) > 1 else self.blind_seq[0]
        if role == "revise":
            return self.revise or {**pkg_compose(), **DERIVED}
        raise AssertionError(role)


# ---- intake --------------------------------------------------------------------

PAPER = """IDCCM 2024 — Paper I
1. Discuss the pathophysiology and management of ARDS. (10 marks)
2. Short note: procalcitonin-guided antibiotic therapy [5]
3. Write about septic shock:
   a) definition
   b) initial management
4. Gram-negative intracellular diplococci in CSF suggest:
   a) S. pneumoniae
   b) N. meningitidis
   c) H. influenzae
   d) Listeria
   Ans: b
"""


def test_split_numbered_and_mcq():
    qs = intake.split_text(PAPER)
    assert len(qs) == 4
    assert qs[0]["options"] is None and intake.detect_marks(qs[0]["raw"]) == 10
    assert intake.detect_marks(qs[1]["raw"]) == 5
    assert qs[2]["options"] is None and "(a) definition" in qs[2]["raw"]      # sub-parts stay in the stem
    assert qs[3]["options"] == ["S. pneumoniae", "N. meningitidis", "H. influenzae", "Listeria"]
    assert qs[3]["given_key"] == [1]


def test_split_paragraphs_and_csv():
    assert len(intake.split_text("Define sepsis\n\nWhat is qSOFA?\n\nExplain lactate clearance")) == 3
    csv_text = "question,marks,system,option_a,option_b,option_c,option_d,answer\n" \
               "What is ARDS?,5,Pulmonology,,,,,\nFirst-line vasopressor in septic shock?,,Sepsis,Dopamine,Norepinephrine,Adrenaline,Vasopressin,B\n"
    rows = intake.split_csv(csv_text)
    assert rows[0]["marks"] == 5 and rows[0]["options"] is None
    assert rows[1]["given_key"] == [1] and len(rows[1]["options"]) == 4


def test_ingest_dedup_and_types():
    r1 = intake.ingest_text(PAPER, "ccm", "CCM/idccm2024.txt", label="IDCCM 2024")
    assert len(r1["new"]) == 4
    r2 = intake.ingest_text("1. Discuss the pathophysiology & management of ARDS (10 marks)", "ccm", "CCM/edic.txt")
    assert r2["new"] == [] and r2["merged"] == [r1["new"][0]]
    it = store.load(r1["new"][0])
    assert it["qtype"] == "long" and it["marks"] == 10 and len(it["sources"]) == 2
    assert store.load(r1["new"][3])["qtype"] == "mcq"


def test_ingest_folder_ledger(tmp_dirs):
    d = tmp_dirs / "studio_input" / "CCM"
    d.mkdir(parents=True)
    (d / "p.txt").write_text(PAPER, encoding="utf-8")
    (tmp_dirs / "studio_input" / "loose.txt").write_text("1. Ignored question here", encoding="utf-8")
    r = intake.ingest_folder()
    assert len(r["new"]) == 4
    assert intake.ingest_folder()["skipped_files"] == ["CCM/p.txt"]


# ---- pipeline ------------------------------------------------------------------------

def _item(q="Discuss the pathophysiology and management of ARDS. (10 marks)"):
    r = intake.ingest_text("1. " + q, "ccm", "t.txt")
    return store.load((r["new"] or r["merged"])[0])


def test_generate_green_and_context_as_hints():
    llm = FakeLLM()
    generate.set_llm(llm)
    it = generate.generate_item(_item())
    assert it["status"] == "generated" and it["triage"] == "green", store.current_version(it)["reasons"]
    v = store.current_version(it)
    assert v["context"][0]["id"] == "pearl:1"
    compose_prompt = next(u for r, u in llm.calls if r == "compose")
    assert "pearl:1" in compose_prompt
    assert "HINTS, not the" in generate.prompts.COMPOSE_SYSTEM          # truth policy present
    assert [r for r, _ in llm.calls] == ["compose", "derive", "verify", "blind"]


def test_incorrect_claim_triggers_revision_then_green():
    bad = good_verify(overall=60, claim_checks=[{"i": 0, "verdict": "incorrect", "comment": "x", "fix": "6 mL/kg"},
                                                {"i": 1, "verdict": "supported"}])
    llm = FakeLLM(verify_seq=[bad, good_verify()])
    generate.set_llm(llm)
    it = generate.generate_item(_item(), max_revisions=1)
    roles = [r for r, _ in llm.calls]
    assert roles.count("revise") == 1 and it["triage"] == "green"
    assert store.current_version(it)["revisions"] == 1
    revise_prompt = next(u for r, u in llm.calls if r == "revise")
    assert "Claim 0 is incorrect" in revise_prompt


def test_blind_mismatch_is_red_without_revisions():
    llm = FakeLLM(blind_seq=[{"answers": [{"i": 0, "chosen": [2], "confidence": "high"}]}])
    generate.set_llm(llm)
    it = generate.generate_item(_item(), max_revisions=0)
    assert it["triage"] == "red"
    assert any("blind solver" in r for r in store.current_version(it)["reasons"])


def test_verifier_failure_is_red_and_llm_error_is_error_status():
    class Boom(FakeLLM):
        def __call__(self, role, *a):
            if role == "verify":
                raise RuntimeError("timeout")
            return super().__call__(role, *a)
    generate.set_llm(Boom())
    it = generate.generate_item(_item(), max_revisions=0)
    assert it["triage"] == "red" and "verify failed" in store.current_version(it)["reasons"][0]

    def dead(role, *a):
        raise RuntimeError("no key")
    generate.set_llm(dead)
    it2 = generate.generate_item(_item("Discuss ventilator-associated pneumonia prevention bundles (10 marks)"))
    assert it2["status"] == "error" and "no key" in it2["error"]


def test_lint_catches_structure_and_numbers():
    item = {"qtype": "short", "marks": 5, "question": "q", "subject": "ccm"}
    pkg = {"answer_md": "Give 6 mL/kg. " * 40, "claims": [], "rubric": [{"marks": 3}],
           "flashcards": [{"front": "TV?", "back": "8 mL/kg"}],
           "mcqs": [{"stem": "Which tidal volume is right?", "options": ["a", "a", "b"], "answer": [5]}]}
    codes = {l["code"] for l in checks.lint(item, pkg)}
    assert {"number_mismatch", "mcq_options", "mcq_dup_options", "mcq_key", "rubric_sum", "no_claims"} <= codes


def test_uploaded_mcq_key_disagreement_is_red():
    r = intake.ingest_text(PAPER, "ccm", "p.txt")
    mcq = store.load(r["new"][3])
    llm = FakeLLM(compose=pkg_compose(answer_md="N. meningitidis explanation " * 30, rubric=[], mcq_key=[0]))
    generate.set_llm(llm)
    it = generate.generate_item(mcq, max_revisions=0)
    assert it["triage"] == "red"
    assert any("Uploaded key" in x for x in store.current_version(it)["reasons"])


# ---- review + publish ---------------------------------------------------------------

def test_approve_publish_republish_unpublish(tmp_dirs):
    generate.set_llm(FakeLLM())
    it = generate.generate_item(_item())
    with pytest.raises(publish.PublishError):
        publish.publish(it)                                   # not approved yet
    publish.approve(it, "Dr R", parts={"mcqs": []})           # skip the MCQ
    it = publish.publish(it)
    pub = it["published"]
    assert it["status"] == "published" and len(pub["flashcard_ids"]) == 2
    md_path = tmp_dirs / "Theory MDs" / pub["theory_rel"]
    text = md_path.read_text(encoding="utf-8")
    assert text.startswith("# ARDS") and "reviewed by Dr R" in text
    meta = json.loads((tmp_dirs / "Theory MDs" / "theory_notes_meta.json").read_text())
    assert meta[pub["theory_rel"]]["source"] == "studio"
    bank = json.loads((tmp_dirs / "question_bank" / "ccm" / "studio.json").read_text())
    assert [q["id"] for q in bank] == [f"{it['id']}-w"] and bank[0]["kind"] == "written_long"
    assert bank[0]["studio"]["reviewed_by"] == "Dr R" and bank[0]["rubric"]
    card = fc.find_card(pub["flashcard_ids"][0])
    assert card and card["source"] == "studio" and card["data"]["studio"]["studio_id"] == it["id"]

    # human edit → approval stale → must re-approve; republish keeps card ids
    old_ids = list(pub["flashcard_ids"])
    v = store.current_version(it)["package"]
    it = generate.human_edit(it, {**v, "flashcards": v["flashcards"][:1]}, "Dr R", "trimmed")
    assert it["status"] == "generated" and it["review"]["stale"]
    with pytest.raises(publish.PublishError):
        publish.publish(it)
    publish.approve(it, "Dr R")
    it = publish.publish(it)
    assert it["published"]["flashcard_ids"] == old_ids[:1]
    assert fc.find_card(old_ids[1]) is None                   # removed card is gone from the store
    assert len(json.loads((tmp_dirs / "question_bank" / "ccm" / "studio.json").read_text())) == 2  # written + 1 MCQ

    it = publish.reject(it, "Dr R", "withdrawn")
    assert it["status"] == "rejected" and it["published"] is None
    assert not md_path.exists() and fc.find_card(old_ids[0]) is None
    assert json.loads((tmp_dirs / "question_bank" / "ccm" / "studio.json").read_text()) == []


def test_approve_green_only_touches_green():
    generate.set_llm(FakeLLM())
    green = generate.generate_item(_item())
    generate.set_llm(FakeLLM(blind_seq=[{"answers": [{"i": 0, "chosen": [3]}]}]))
    r = intake.ingest_text("1. Short note on prone ventilation (5 marks)", "ccm", "t2.txt")
    red = generate.generate_item(store.load(r["new"][0]), max_revisions=0)
    assert red["triage"] == "red"
    assert publish.approve_green("Dr R") == [green["id"]]


def test_revision_request_uses_editor_note():
    llm = FakeLLM()
    generate.set_llm(llm)
    it = generate.generate_item(_item())
    publish.request_revision(it, "Dr R", "Add ECMO criteria")
    it = generate.generate_item(store.load(it["id"]))
    revise_prompt = [u for r, u in llm.calls if r == "revise"][-1]
    assert "Add ECMO criteria" in revise_prompt and len(it["versions"]) == 2


def test_state_machine_blocks_bad_transitions():
    it = _item()
    with pytest.raises(store.TransitionError):
        store.transition(it, "published")


def test_retriever_ranks_relevant_first():
    hits = retrieve.library().search("management of ARDS tidal volume", k=2)
    assert hits[0]["id"] == "pearl:1"


def test_console_api_flow(tmp_dirs):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    import dashboard.storage as dstorage
    dstorage.AUDIT_LOG = tmp_dirs / "audit.log"
    from dashboard.studio_api import router
    app = FastAPI()
    app.include_router(router, prefix="/console")
    c = TestClient(app)
    r = c.post("/console/api/studio/ingest-text", json={"subject": "ccm", "text": PAPER, "label": "IDCCM"})
    assert r.status_code == 200 and len(r.json()["new"]) == 4
    rows = c.get("/console/api/studio/items?status=queued").json()
    assert len(rows) == 4
    generate.set_llm(FakeLLM())
    iid = next(x["id"] for x in rows if x["qtype"] == "long")
    generate.generate_item(store.load(iid))
    assert c.post(f"/console/api/studio/items/{iid}/approve", json={"by": "Dr R"}).status_code == 200
    pub = c.post(f"/console/api/studio/items/{iid}/publish").json()
    assert pub["question_ids"] and c.get("/console/api/studio/summary").json()["counts"]["published"] == 1
    assert c.get("/console/studio").status_code == 200
