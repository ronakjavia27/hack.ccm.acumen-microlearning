# Management of Multidrug-Resistant Gram-Negative Infections in the ICU
### ESBL-E · AmpC-E · CRE · DTR *Pseudomonas* · CRAB · *S. maltophilia* · PDR organisms

> **Primary source:** IDSA 2026 Guidance on the Treatment of Antimicrobial-Resistant Gram-Negative Infections (v5.0, evidence current to March 1, 2026) — supersedes the 2024 (v4.0) document. Supplemented with ICMR (India) surveillance data and treatment guidance, and standard PK/PD dosing principles for critical illness.
> **Scope:** Adult ICU patients. This is a study/reference compilation, not a substitute for ID consultation or local antibiogram-driven policy — both of which the source guidance explicitly recommends.

---

## 0. Framework: Definitions You Must Know

### 0.1 Resistance phenotype classification (Magiorakos et al., *Clin Microbiol Infect* 2012 — still the reference standard)

| Term | Definition |
|---|---|
| **MDR** (multidrug-resistant) | Non-susceptible to ≥1 agent in **≥3** antimicrobial categories |
| **XDR** (extensively drug-resistant) | Non-susceptible to ≥1 agent in **all but ≤2** categories (i.e., susceptible to only 1–2 categories) |
| **PDR** (pandrug-resistant) | Non-susceptible to **all agents in all categories** tested |
| **DTR** (difficult-to-treat resistance — IDSA-specific, applied to *P. aeruginosa*) | Non-susceptible to **all** of: piperacillin-tazobactam, ceftazidime, cefepime, aztreonam, meropenem, imipenem, ciprofloxacin, levofloxacin |

**Key exam point:** DTR is a *clinically actionable* category IDSA created specifically because "MDR/XDR *P. aeruginosa*" was too broad and didn't reliably predict failure of standard agents. DTR = resistant to essentially every conventional first-line option, mandating a newer agent.

### 0.2 Organism definitions used in this document

| Abbreviation | Meaning |
|---|---|
| ESBL-E | Extended-spectrum β-lactamase–producing Enterobacterales (mainly *E. coli*, *K. pneumoniae*, *K. oxytoca*) |
| AmpC-E | Enterobacterales with moderate-to-high risk of clinically significant inducible/derepressed AmpC production |
| CRE | Enterobacterales resistant to ≥1 carbapenem, or carbapenemase-producing |
| CP-CRE | Carbapenemase-producing CRE (KPC / NDM / VIM / IMP / OXA-48-like) — 35–83% of US CRE, and the dominant phenotype in India |
| DTR-PA | *Pseudomonas aeruginosa* with difficult-to-treat resistance |
| CRAB | Carbapenem-resistant *Acinetobacter baumannii* |
| MBL | Metallo-β-lactamase (NDM, VIM, IMP) — zinc-dependent, **not** inhibited by avibactam/vaborbactam/relebactam; only aztreonam among old β-lactams is stable to hydrolysis |

### 0.3 Presumed ESBL / AmpC screening rule of thumb
- *E. coli / K. pneumoniae / K. oxytoca* with **ceftriaxone MIC ≥4 µg/mL** → treat empirically as presumed ESBL-E (routine ESBL phenotype/genotype testing is not universally available or CLSI-mandated).
- *Enterobacter cloacae* complex, *Klebsiella aerogenes*, *Citrobacter freundii* (and, per newer data, *Hafnia alvei*) = **moderate-risk AmpC inducers** — avoid 3rd-gen cephalosporins even if initial susceptibility is reported.
- *Morganella*, *Providencia*, *Serratia* = **low risk** for clinically significant AmpC derepression — treat by susceptibility results.

---

## 1. General ICU Approach — Before You Even Have a Pathogen

```
                         SUSPECTED GRAM-NEGATIVE SEPSIS / ICU INFECTION
                                          |
                 -----------------------------------------------------
                 |                                                   |
       Any MDRO risk factor present?                      No risk factors, low local
       - Prior MDRO colonization/infection (12 mo)          MDRO prevalence
       - Antibiotic exposure in last 90 days                        |
       - Prior carbapenem/BL-BLI use                                v
       - Prolonged ICU stay, device-related infection      Standard empiric regimen per
       - High local unit antibiogram resistance             syndrome (local antibiogram)
       - Recent hospitalization abroad / transfer from
         high-prevalence facility
                 |
                 v
       Broad empiric coverage guided by:
       - Most recent culture/AST from this patient (<12 mo)
       - Local unit-level antibiogram (not hospital-wide)
       - Severity (septic shock → cover CRAB/DTR-PA empirically
         if locally prevalent, until cultures return)
                 |
                 v
          SEND CULTURES + RAPID DIAGNOSTICS
     (blood cultures, site cultures, rapid multiplex PCR /
      carbapenemase gene panels if available — BioFire, Verigene,
      Cepheid Xpert Carba-R)
                 |
                 v
        48–72h: DE-ESCALATE / TARGET THERAPY
        based on organism ID + carbapenemase class + AST
                 |
                 v
        Reassess daily: source control adequate? clinical
        response? duration counted from first ACTIVE agent,
        not from first antibiotic given
```

**Principles that apply across every organism below (IDSA 2026 general suggestions):**
1. All treatment suggestions assume the organism is identified and *in vitro* susceptibility of the chosen agent is demonstrated.
2. When two agents are equally effective, choose based on toxicity, cost, ease of administration, and formulary availability.
3. Duration of therapy for AMR organisms is generally **the same** as for susceptible organisms of the same infection type — resistance itself doesn't mandate a longer course.
4. Transition IV→PO when: pathogen susceptible to an oral agent with good tissue penetration, patient hemodynamically stable, and GI absorption is expected to be adequate.
5. Distinguish **colonization from infection** at every step — this is repeatedly emphasized for CRAB and *S. maltophilia*, where respiratory/wound cultures are frequently colonizers.

---

## 2. ESBL-E (Extended-Spectrum β-Lactamase–Producing Enterobacterales)

CTX-M-15 dominates in the US and India alike. ESBLs hydrolyze penicillins, cephalosporins, and aztreonam but **not** carbapenems, and do not directly affect non-β-lactams (fluoroquinolones, TMP-SMX, aminoglycosides) — though co-resistance is common.

```
                        ESBL-E CONFIRMED / PRESUMED (ceftriaxone MIC ≥4)
                                          |
        --------------------------------------------------------------------
        |                       |                            |
  Uncomplicated cystitis   Pyelonephritis / cUTI       Infection outside urinary tract
        |                       |                      (bacteremia, pneumonia, IAI, SSTI)
        v                       v                            v
  Nitrofurantoin,         TMP-SMX / cipro /            CARBAPENEM (ertapenem OR
  TMP-SMX, single-dose    levofloxacin (if susceptible)  meropenem/imipenem)
  aminoglycoside,             |                            |
  pivmecillinam,          If FQ/TMP-SMX not usable:   Critically ill / hypoalbuminemic?
  gepotidacin, sulopenem      |                        --> prefer MEROPENEM or IMIPENEM
  (all listed alphabetically, v                             over ertapenem (protein-binding
   no hierarchy)          Cefepime-enmetazobactam OR       pharmacokinetics unreliable)
        |                 carbapenem                       |
  Alt: oral fosfomycin        |                        Alt: cefepime-enmetazobactam
  (E. coli only)          Alt: IV fosfomycin (E. coli   Step-down once stable: oral
                           preferred), aminoglycoside,   ciprofloxacin/levofloxacin/
                           pip-tazo (only if not          TMP-SMX if susceptible
                           critically ill, no bacteremia)  (NOT nitrofurantoin, fosfomycin,
                                                            amox-clav, doxycycline, or
                                                            sulopenem for bacteremia)
```

### Key "do NOT" rules for ESBL-E
| Agent | Role |
|---|---|
| **Cefepime** | Avoid for cUTI and invasive ESBL-E infection even if MIC reported susceptible (unreliable AST, clinical trial signal of failure) |
| **Piperacillin-tazobactam** | Not suggested for invasive ESBL-E infection (higher mortality vs meropenem in the MERINO trial); alternative-only for non-critically-ill cUTI without bacteremia |
| **Cephamycins (cefoxitin/cefotetan)** | Not suggested — insufficient outcome data, no optimized dosing |
| **Newer BL-BLIs active against carbapenem-resistant organisms** (ceftazidime-avibactam, meropenem-vaborbactam, imipenem-relebactam, ceftolozane-tazobactam, cefiderocol) | Effective in vitro but **reserve for carbapenem-resistant infections** — don't "spend" them on carbapenem-susceptible ESBL-E |

### Piperacillin-tazobactam empiric-to-ESBL "continuation" rule
If pip-tazo was started empirically for a **uUTI** that turns out to be ESBL-E, and the patient is improving → continue, no change needed (high urinary concentration). This nuance is a favorite exam distractor.

---

## 3. AmpC-E (Enterobacterales at Risk of Inducible AmpC)

```
        Enterobacter cloacae complex / Klebsiella aerogenes /
        Citrobacter freundii / Hafnia alvei recovered
                          |
                          v
        Avoid ceftriaxone/cefotaxime/ceftazidime for INVASIVE
        infection even if reported susceptible
        (~20% develop resistance on therapy via ampC derepression)
                          |
                          v
              Cefepime MIC ≤8 µg/mL (S or SDD)?
                    /                      \
                  YES                       NO
                   |                         |
         CEFEPIME preferred          Carbapenem (ertapenem if not
         (weak inducer + stable       critically ill/CRE; meropenem/
         to AmpC hydrolysis)          imipenem if severe) OR
                                      cefepime-enmetazobactam if
                                      co-ESBL suspected
```

- **Piperacillin-tazobactam: avoid** for invasive infection — tazobactam poorly protects against AmpC hydrolysis.
- **Non-β-lactams** (TMP-SMX, fluoroquinolones, aminoglycosides) are unaffected by AmpC and are good step-down options once susceptibility confirmed.
- Exception for mild, source-controlled infection: if ceftriaxone was already started empirically and the patient is improving, completing the course is reasonable — no forced switch.

---

## 4. CRE (Carbapenem-Resistant Enterobacterales) — Carbapenemase Class Drives Therapy

**This is the single highest-yield area for exam questions.** Treatment is *not* generic "give a carbapenemase inhibitor" — it is enzyme-specific.

```
                              CRE CONFIRMED
                                    |
                    ------------------------------------
                    |                                  |
          Carbapenemase NOT detected           Carbapenemase-producing (send rapid
          (porin loss + ESBL/AmpC               molecular test: KPC / NDM / VIM / IMP /
           hyperproduction)                      OXA-48-like — e.g., Xpert Carba-R, BioFire)
                    |                                  |
     Susceptible to mero/imipenem                      v
     (MIC ≤1) but ERT-resistant?         ------------------------------------------------
          |            |                 |            |            |            |
         YES           NO               KPC          NDM/VIM/IMP   OXA-48-like   Mixed/
          |             |               (serine)      (metallo-    (serine)      unclear
     Extended-infusion   |                 |            β-lactamase)   |
     meropenem/          v                 v              |            v
     imipenem      Newer BL-BLI:    Ceftazidime-           v      Ceftazidime-avibactam
     (standard-    - Ceftazidime-   avibactam OR      Aztreonam-   (avibactam restores
     infusion for    avibactam        Imipenem-        avibactam    activity vs OXA-48
     uUTI only)     - Imipenem-       relebactam OR    (PREFERRED)  since it lacks the
                      relebactam      Meropenem-          |         porin/efflux issues
                    - Meropenem-      vaborbactam      If unavailable:  of MBLs)
                      vaborbactam     (mero-vabor       Ceftazidime-
                      (mild panel     slightly favored  avibactam +
                      preference in   > CAZ-AVI >       AZTREONAM
                      that order)     IMI-REL; CAZ-AVI  (aztreonam evades
                                      ~10% on-therapy   MBL hydrolysis;
                                      resistance vs     avibactam protects
                                      <3% for the        it from co-produced
                                      carbapenem-BLIs)   serine enzymes)
                                                             |
                                                        Alt: Cefiderocol
                                                        (comparative data now
                                                         favor AZA over
                                                         cefiderocol for NDM-E)
                                                             |
                                                     Non-bacteremic/non-UTI alt:
                                                     eravacycline, tigecycline
```

### CRE quick-reference table

| Carbapenemase | Mechanism class | Preferred agent(s) | Notes |
|---|---|---|---|
| **KPC** | Serine (Class A) | Ceftazidime-avibactam, meropenem-vaborbactam, imipenem-relebactam | Meropenem-vaborbactam mildly favored on composite outcome/resistance-emergence data; on-treatment resistance to CAZ-AVI ~10% (Ω-loop mutations) vs <3% for the carbapenem-BLIs |
| **NDM / VIM / IMP (MBL)** | Metallo (Class B) | **Aztreonam-avibactam** (preferred); alt: ceftazidime-avibactam **+ aztreonam** combined | None of KPC-active agents work (avibactam/vaborbactam/relebactam don't inhibit MBLs) |
| **OXA-48-like** | Serine (Class D) | Ceftazidime-avibactam | Avibactam is active; OXA-48 enzymes have weak carbapenemase activity alone but often coexist with porin loss/ESBL |
| **Non-carbapenemase CRE** (porin loss ± ESBL/AmpC amplification) | — | Extended-infusion carbapenem if MIC ≤1; else same newer BL-BLIs as KPC pathway | Confirm true absence of carbapenemase via molecular testing before relying on standard carbapenem |

### New agents added in the 2026 update (awareness for exams)
- **Gepotidacin** (triazaacenaphthylene, oral, DNA gyrase/topoisomerase IV inhibitor) — uUTI only, active against most ESBL-E; limited CRE data.
- **Pivmecillinam** (oral mecillinam prodrug) — uUTI; KPC hydrolyzes mecillinam (avoid if KPC suspected), better activity vs NDM/OXA-48.
- **Oral sulopenem** — thiopenem; uUTI/cUTI step-down only, not for bacteremia.
- **Cefepime-enmetazobactam** — ESBL-E alternative (enmetazobactam's zwitterionic structure improves periplasmic penetration vs tazobactam).
- **IV fosfomycin** — alternative for ESBL-E/CRE cUTI, preferentially *E. coli* (K. pneumoniae often carries *fosA*); watch sodium load in heart failure/renal patients.

---

## 5. DTR *Pseudomonas aeruginosa*

```
                    DTR-PA CONFIRMED (resistant to pip-tazo, ceftazidime,
                    cefepime, aztreonam, meropenem, imipenem, cipro, levo)
                                        |
                          Carbapenemase testing / MBL suspected?
                        (NDM/VIM/IMP — more relevant outside the US;
                         relevant in India given regional MBL prevalence)
                              /                                \
                            YES                                 NO
                             |                                   |
                       CEFIDEROCOL                    Site of infection?
                       (preferred for MBL-                  |
                        producing DTR-PA)         --------------------------
                                                   |                        |
                                              Pneumonia                Non-pneumonia (bacteremia,
                                                   |                     IAI, cUTI, SSTI)
                                                   v                        |
                                     CEFTOLOZANE-TAZOBACTAM                 v
                                     (preferred — comparative        Ceftolozane-tazobactam,
                                      data now favor it over          ceftazidime-avibactam, or
                                      ceftazidime-avibactam            imipenem-relebactam
                                      specifically for pneumonia)      (comparable evidence)
                                                   |
                                     Alt: ceftazidime-avibactam,
                                     imipenem-relebactam (similar
                                     high rate of on-therapy
                                     resistance emergence to
                                     ceftazidime-avibactam)
                                                   |
                                     Alt: cefiderocol (2026 "Game
                                     Changer" trial data now available)
```

### Key DTR-PA points
- **Monotherapy is preferred**, not combination therapy, once *in vitro* susceptibility to cefiderocol, ceftazidime-avibactam, ceftolozane-tazobactam, or imipenem-relebactam is confirmed — combination therapy does **not** improve outcomes and adds toxicity.
- **Nebulized antibiotics**: still not routinely recommended, but the 2026 update *softened* the prior "against" stance — some data suggest improved clinical cure; may be considered adjunctively in refractory pneumonia.
- Resistance emergence on therapy is a real concern with **all** of these newer β-lactams (~20% of isolates on treatment) — repeat cultures/AST if clinical failure occurs.
- A new 2026 question addresses how carbapenemase identification (not just DTR phenotype) should influence Pseudomonas therapy — mirrors the CRE approach (i.e., MBL-producing DTR-PA → cefiderocol, similar logic to NDM-CRE → aztreonam-avibactam).

---

## 6. CRAB (Carbapenem-Resistant *Acinetobacter baumannii*)

**2026 is a genuine paradigm shift here** — read this section carefully; it differs materially from what many 2023–24-trained clinicians still practice.

```
                          CRAB — INVASIVE INFECTION CONFIRMED
                          (colonization vs infection assessed first —
                           respiratory/wound cultures are frequently colonizers)
                                          |
                                Is sulbactam-durlobactam available?
                                /                                  \
                              YES                                   NO
                               |                                     |
              SULBACTAM-DURLOBACTAM                    High-dose ampicillin-sulbactam
              + a background carbapenem                (27 g/day: 18 g ampicillin +
              (meropenem OR imipenem)                    9 g sulbactam) + ≥1 second
              = PREFERRED FIRST-LINE                      active agent (polymyxin B,
              for ALL invasive CRAB                        minocycline, or cefiderocol)
              (highest mortality benefit,                   — used as BRIDGE therapy
               esp. pneumonia/bacteremia)                    until sulbactam-durlobactam
                     |                                         becomes available
                     v
          Resistant to sulbactam-durlobactam?
          (watch for NDM-producing CRAB —
           elevated MICs to sul-dur)
              /                    \
            YES                    NO — continue regimen
             |
             v
       Two non-sulbactam agents
       OR add sulbactam-durlobactam
       to CEFIDEROCOL
```

### CRAB — what changed from the 2024 → 2026 guidance
| 2024 approach | 2026 approach |
|---|---|
| High-dose ampicillin-sulbactam = preferred first-line | **Sulbactam-durlobactam + carbapenem = preferred first-line**; amp-sulbactam demoted to alternative/bridge |
| Combination therapy discussed as a general question | Question on "role of combination therapy" removed — now organized entirely around the sul-dur algorithm |
| Extended-infusion meropenem/imipenem discussed as option | Removed as a standalone option (still used as the *background* partner to sulbactam-durlobactam) |
| Rifamycin combinations discussed | Removed — insufficient support |
| — | New: explicit guidance for **NDM-producing CRAB** (reduced sul-dur susceptibility) |

- **Avoid as CRAB monotherapy:** meropenem, imipenem, rifamycins, nebulized antibiotics (still not routinely recommended, though the "against" language was softened slightly, similar to DTR-PA).
- **Cefiderocol:** use cautiously, generally as part of a combination regimen — it underperformed vs. best-available-therapy in a CRAB subgroup of an earlier RCT (CREDIBLE-CR), though newer 2026 trial data are more favorable.
- **Tigecycline/minocycline:** reasonable second agents; eravacycline not suggested (insufficient data).

---

## 7. *Stenotrophomonas maltophilia*

Intrinsically resistant to carbapenems (chromosomal L1/L2 β-lactamases) — a carbapenem-treated ICU patient who deteriorates should raise suspicion.

```
        S. MALTOPHILIA — INVASIVE INFECTION (not colonization)
                              |
              -----------------------------------------
              |                                        |
        Mild infection                        Moderate–severe infection
              |                                        |
     Monotherapy reasonable:               Preferred (in order):
     high-dose minocycline OR              1. CEFIDEROCOL monotherapy
     TMP-SMX OR levofloxacin                   (± 2nd agent initially)
                                            2. Ceftazidime-avibactam + AZTREONAM
                                            3. Minocycline + 2nd agent
                                            4. TMP-SMX + 2nd agent
                                            5. Levofloxacin + 2nd agent
```

- **Ceftazidime alone: never** — CLSI now advises against even testing ceftazidime for *S. maltophilia*; it is not suggested for treatment.
- Cefiderocol's promotion to preferred is based mainly on susceptibility data and neutropenic-animal models — clinical outcome data remain limited; the 2026 "Game Changer" trial adds some comparative bacteremia data.
- Tigecycline has been **removed** as a suggested combination partner in the current guidance.

---

## 8. PDR / Truly Extensively Resistant Organisms — Salvage Approach

When an isolate tests non-susceptible to essentially everything on the panel (true PDR, or "difficult" XDR where none of the guideline-preferred agents are active/available — a common real-world Indian ICU scenario):

```
                    NO GUIDELINE-PREFERRED AGENT ACTIVE
                                    |
                1. CONFIRM with reference lab / repeat AST
                   (broth microdilution; rule out lab error,
                   especially for colistin — disk diffusion
                   is unreliable for polymyxins)
                                    |
                2. Re-verify SOURCE CONTROL first
                   (drain abscess, remove device/line/catheter —
                   no antibiotic salvage regimen substitutes for this)
                                    |
                3. COMBINATION THERAPY guided by synergy testing
                   where available (checkerboard / time-kill),
                   otherwise 2 agents with different mechanisms:
                   - Polymyxin (colistin or polymyxin B) backbone +
                   - High-dose extended-infusion carbapenem
                     (even if "resistant" — inoculum effect/synergy
                      sometimes restores activity) +/-
                   - Tigecycline / high-dose minocycline (tissue,
                     not blood/urine, infections) +/-
                   - Fosfomycin (IV, if accessible) as add-on
                                    |
                4. Consider agents outside standard panel:
                   - Compassionate use / named-patient access to
                     newest BL-BLIs if not yet on local formulary
                   - Inhaled/nebulized adjuncts for pneumonia
                     (colistin, tobramycin, amikacin) — adjunct
                     ONLY, not monotherapy
                                    |
                5. THERAPEUTIC DRUG MONITORING where available
                   (colistin, vancomycin, aminoglycosides) —
                   critical illness alters volume of distribution
                   and clearance unpredictably
                                    |
                6. Infection prevention: contact precautions,
                   cohorting, active surveillance cultures to
                   prevent onward transmission — treating PDR
                   organisms is as much an IPC problem as a
                   pharmacologic one
                                    |
                7. Early, sustained ID / clinical microbiology
                   consultation — every source above stresses this
```

**Practical Indian-ICU note:** ICMR AMR surveillance data show carbapenem resistance rates far above US figures — imipenem resistance historically reported around **~28% in *E. coli*, ~55% in *K. pneumoniae*, and ~62–87% in *Acinetobacter baumannii*** in ICU isolates (regional and year-to-year variation is large). This changes empiric calculus: many Indian tertiary ICUs empirically cover for CRAB/CRE in septic shock with unknown source, pending cultures, more readily than a typical US algorithm would suggest — always anchor to your **unit-specific antibiogram**, not national averages.

---

## 9. ICU Dosing Quick-Reference (adult, normal renal/hepatic function — verify against your institution's renal dosing nomogram and PK/PD protocol; extended/continuous infusion is preferred for β-lactams in critical illness)

| Agent | Typical adult ICU dose | Infusion notes |
|---|---|---|
| Meropenem (standard MIC-susceptible CRE, extended-infusion) | 2 g IV q8h | Extended infusion over 3h |
| Ceftazidime-avibactam | 2.5 g IV q8h | Infuse over 2h |
| Meropenem-vaborbactam | 4 g IV q8h | Infuse over 3h |
| Imipenem-cilastatin-relebactam | 1.25 g IV q6h | Infuse over 30 min |
| Ceftolozane-tazobactam | 3 g IV q8h (pneumonia dose; lower for UTI) | Infuse over 1h |
| Aztreonam-avibactam | Loading + maintenance per PK/PD nomogram | Population PK-based dosing |
| Cefiderocol | 2 g IV q8h | Infuse over 3h |
| Sulbactam-durlobactam | 1 g/1 g IV q6h | Infuse over 3h, + background carbapenem |
| High-dose ampicillin-sulbactam | 9 g sulbactam/day (27 g total amp-sulb/day) | Divided q6–8h, extended infusion |
| Colistin (colistimethate) | Loading 9 MU once, then 3 MU q8h or 4.5 MU q12h | Target Css,avg 2–2.5 mg/L; TDM if available |
| Polymyxin B | ~2.5 mg/kg/day divided q12h | No renal dose adjustment (non-renally cleared) — better nephrotoxicity profile than colistin for systemic use |
| Minocycline | 200 mg loading, then 100 mg IV/PO q12h | — |
| Tigecycline (high-dose, off-label) | 200 mg loading, then 100 mg IV q12h | Standard FDA dose (100mg load/50mg q12h) is under-dosed for MDR-GNB |

*(Doses above are commonly cited ICU/AMR-guidance figures for teaching purposes — always cross-check against the current IDSA Table 1, your hospital's antimicrobial stewardship dosing card, and renal/hepatic function before prescribing.)*

---

## 10. One-Page Mnemonic Summary

| Organism | First reach for | Reserve for MBL/NDM | Avoid |
|---|---|---|---|
| ESBL-E (invasive) | Carbapenem | — | Cefepime, pip-tazo, cephamycins |
| AmpC-E (invasive) | Cefepime (if MIC ≤8) | — | Ceftriaxone/ceftazidime, pip-tazo |
| CRE — KPC | Ceftazidime-avibactam / mero-vaborbactam / imipenem-relebactam | — | Old carbapenems alone |
| CRE — NDM/VIM/IMP | — | **Aztreonam-avibactam** (or CAZ-AVI + aztreonam) | KPC-active BL-BLIs alone (won't work) |
| CRE — OXA-48 | Ceftazidime-avibactam | — | — |
| DTR-PA (pneumonia) | Ceftolozane-tazobactam | Cefiderocol | Combination therapy (unnecessary) |
| DTR-PA (non-pneumonia) | Ceftolozane-tazobactam / CAZ-AVI / imipenem-relebactam | Cefiderocol | — |
| CRAB | **Sulbactam-durlobactam + carbapenem** | Two non-sulbactam agents, or sul-dur + cefiderocol | Meropenem/imipenem alone, rifamycins |
| *S. maltophilia* | Cefiderocol (moderate–severe) | — | Ceftazidime alone |

---

## References (representative — verify latest versions before citing)

1. Tamma PD, Heil EL, Justo JA, Mathers AJ, Satlin MJ, Bonomo RA. **IDSA 2026 Guidance on the Treatment of Antimicrobial-Resistant Gram-Negative Infections** (v5.0). idsociety.org/practice-guideline/amr-guidance — supersedes *Clin Infect Dis* 2024;ciae403 (v4.0).
2. Magiorakos AP, et al. Multidrug-resistant, extensively drug-resistant and pandrug-resistant bacteria: an international expert proposal for interim standard definitions. *Clin Microbiol Infect* 2012;18(3):268-281.
3. ICMR. **Guidance on Diagnosis & Management of Carbapenem-Resistant Gram-Negative Infections.** Indian Council of Medical Research.
4. ICMR. **Treatment Guidelines for Antimicrobial Use in Common Syndromes** (latest edition). icmr.gov.in.
5. CLSI M100 — Performance Standards for Antimicrobial Susceptibility Testing (updated annually; 2026 breakpoints referenced in current IDSA Table 2).
6. Kadri SS, et al. Difficult-to-treat resistance (DTR) in gram-negative bacteremia — original DTR concept paper, *Clin Infect Dis* 2018.

---

*Compiled for board-exam and clinical reference use. Antimicrobial resistance guidance changes frequently (IDSA explicitly reviews this document quarterly) — confirm against the live IDSA page and your institution's antibiogram before applying to patient care.*
