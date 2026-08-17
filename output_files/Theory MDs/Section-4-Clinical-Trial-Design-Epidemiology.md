# SECTION 4: CLINICAL TRIAL DESIGN & EPIDEMIOLOGY
### Plain-Language Edition — DrNB / DM Critical Care Medicine

---

## Running Scenario (used throughout this section)

You're the principal investigator, testing a new sedative — call it **Drug X** — against standard-of-care sedation in mechanically ventilated ICU patients. Across the next 8 chapters, this same trial gets progressively redesigned and scaled up — from a simple two-arm RCT into something closer to how real ICU trials actually get built today.

---

# Chapter 19: RCTs — Core Architecture, Allocation Concealment, Blinding, Run-in Periods

## 1. Definition & Mathematical Core

**Four separate design pieces, often confused with each other:**
1. **Randomization** — the method generating unpredictable, balanced group assignment
2. **Allocation concealment** — hiding the *next* assignment from whoever is enrolling patients, until they've committed the patient to the trial. This happens **before/at** enrollment.
3. **Blinding** — hiding *which* arm a patient landed in, from patients, clinicians, outcome assessors, and analysts. This happens **after** randomization.
4. **Run-in period** — an optional open-label lead-in phase, before formal randomization, used to screen out patients who can't tolerate or won't adhere to the study drug

**Why concealment and blinding are not the same thing:**

| | Allocation concealment | Blinding |
|---|---|---|
| Timing | Before enrollment | After randomization |
| Protects against | Selection bias — a clinician steering a sicker patient away from a particular arm | Performance/detection bias — treatment decisions or outcome assessments influenced by knowing the arm |
| Always achievable? | Yes — even in open-label trials, via central/web-based randomization | No — sometimes impossible (surgery, ECMO, devices) |

## 2. Key Concepts, Principles & Assumptions

**A trial can be open-label (unblinded) and still have perfect allocation concealment** — a web-based central randomization system means no one can predict or manipulate which arm a specific new patient will land in, even if everyone knows the arm afterward. This is exactly the fix used when blinding the treatment itself is impossible: keep concealment airtight, and add **blinded outcome assessment** (an independent adjudication committee, unaware of arm assignment, judging the endpoints) as a substitute for full blinding.

**The run-in period trade-off:** excluding patients who couldn't tolerate an open-label lead-in phase makes your final randomized population healthier and more adherent than the general ICU population you'll eventually treat — this can inflate the trial's apparent efficacy or make results less generalizable to the messier, real-world population you actually manage.

**Memory hook:** *Concealment hides the NEXT assignment. Blinding hides the CURRENT one. You can lose one without losing the other.*

## 3. Visual / ASCII Schematic
```
Screening
    |
    v
Optional RUN-IN period (open-label) --> excludes intolerant/non-adherent
    |                                     patients BEFORE randomization
    v
RANDOMIZATION (allocation concealed --
 enroller cannot predict/see the next assignment)
    |
    v
Delivery of Drug X or standard care (blinded, if possible)
    |
    v
Outcome assessment (blinded adjudication committee,
 even if the treatment itself couldn't be blinded)
```

## 4. Landmark ICU Clinical Anchor — ADRENAL Trial

**The design:** ADRENAL tested hydrocortisone vs. placebo in septic shock — roughly 3,800 patients, double-blind, with allocation concealed through a central randomization system and identical-appearing study vials prepared by a central pharmacy.

**The finding:** no significant difference in 90-day mortality, but faster resolution of shock in the hydrocortisone group.

**The lesson:** even for a drug with physiological effects (like hyperglycemia) that could tip off an alert clinician, meticulous blinding architecture — identical vials, central randomization, blinded outcome adjudication — kept the trial's internal validity intact.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Allocation concealment protects against selection bias, and is achievable in essentially every trial design
2. Blinding, where possible, protects against performance and detection bias
3. Blinded outcome assessment can substitute for full blinding when the treatment itself can't be hidden

**Examiner traps:**
1. Confusing allocation concealment with blinding — they protect against different biases, at different points in time
2. Assuming an open-label trial automatically has poor internal validity — concealment can still be perfect
3. Ignoring how a run-in period changes the generalizability of the final randomized population
4. Forgetting that unblinded trials still need — and can still achieve — blinded outcome adjudication

## 6. Theory Exam Summary Box
> 1. Allocation concealment (before randomization) ≠ blinding (after randomization) — different biases, different timing
> 2. An unblindable trial can still have airtight concealment and blinded outcome assessment
> 3. A run-in period improves internal precision at the cost of generalizability to the real, unselected ICU population

---

# Chapter 20: Randomization Strategies

## 1. Definition & Mathematical Core

**Four strategies, escalating in sophistication:**
1. **Simple randomization** — like a coin flip per patient. Unpredictable, but in smaller trials, chance alone can produce meaningful imbalance (e.g., 65 vs. 35 patients after the first 100)
2. **Block randomization** — randomize in fixed-size blocks (e.g., blocks of 4), guaranteeing near-equal numbers in each arm at any point during enrollment — important because ICU case-mix can drift over calendar time
3. **Stratified randomization** — randomize separately *within* strata defined by a known prognostic factor (e.g., admission diagnosis, APACHE II band), using block randomization inside each stratum, to guarantee balance on that specific factor
4. **Cluster randomization** — randomize entire units (ICUs, wards) rather than individual patients — needed when the intervention can't be delivered to one patient without affecting their neighbors (→ Chapter 25)

## 2. Key Concepts, Principles & Assumptions

**Why block randomization exists at all:** if your trial enrolls over 18 months and ICU case-mix genuinely shifts with season, staffing, or a hospital policy change halfway through, simple randomization could leave you with an imbalanced comparison purely due to *when* patients happened to enroll. Blocking prevents this.

**The trade-off with fixed block sizes:** if staff can work out the block size, they can predict the last one or two assignments in each block — a subtle threat to allocation concealment. The fix is **variable block sizes**, kept unknown to enrolling staff.

**Stratification's limit:** it's most valuable for one or two *strong* prognostic factors. Stratify by too many variables and you create small or empty strata cells, which defeats the purpose and complicates the randomization scheme for little real benefit.

**Memory hook:** *Simple = a coin flip. Block = keeps the coin flip fair over time. Stratified = keeps it fair on a factor you already know matters. Cluster = flips the coin for a whole unit, not one patient.*

## 3. Visual / ASCII Schematic
```
SIMPLE randomization (running balance can drift):
Arm A: ||||   ||   |||||||  |    <- can drift far from 50/50
Arm B: |   |||||   |   ||   |||||||

BLOCK randomization (balance restored every 4 patients):
Block 1: A B B A  | Block 2: B A A B | Block 3: A B A B  ...
         (2 A, 2 B)         (2 A, 2 B)          (2 A, 2 B)

STRATIFIED + BLOCK (separate block randomization per stratum):
High APACHE II stratum:  A B B A | B A A B ...
Low APACHE II stratum:   B A A B | A B B A ...
```

## 4. Landmark ICU Clinical Anchor — PROSEVA Trial

**The design:** PROSEVA (prone vs. supine positioning in severe ARDS) used randomization stratified by study center and vasopressor use, guaranteeing balance on a genuinely important severity marker across both arms.

**The finding:** a clear, convincing 28-day mortality benefit with prone positioning.

**The lesson:** careful stratified randomization is part of *why* PROSEVA's result was so convincing — the trial could confidently attribute the mortality difference to prone positioning itself, not to a chance imbalance in how sick each arm's patients were at baseline.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Block randomization keeps arms balanced even if the trial's population shifts over calendar time
2. Stratification directly protects against chance imbalance on a known, important prognostic factor
3. Cluster randomization makes trials of unit-level interventions possible at all

**Examiner traps:**
1. Using fixed, predictable block sizes without any safeguard against staff guessing upcoming assignments
2. Over-stratifying on too many factors, creating small or empty strata
3. Confusing stratified randomization (patient-level, strata based on a covariate) with cluster randomization (unit-level, no individual randomization at all)
4. Assuming randomization alone guarantees baseline balance — chance imbalance is still possible, especially in smaller trials, which is exactly why the technique matters

## 6. Theory Exam Summary Box
> 1. Block randomization keeps allocation balanced over time; stratified randomization keeps it balanced on a known prognostic factor
> 2. Predictable block sizes threaten allocation concealment — use variable block sizes
> 3. Cluster randomization is a different tool entirely — for interventions that operate at the unit level, not the patient level

---

# Chapter 21: Sample Size Estimation

## 1. Definition & Mathematical Core

**Comparing two proportions** (e.g., mortality rate, Drug X vs. standard care):
$$n_{per\ group} = \frac{(Z_{\alpha/2} + Z_{\beta})^2 \times \big[p_1(1-p_1) + p_2(1-p_2)\big]}{(p_1 - p_2)^2}$$

**Comparing two means** (e.g., ventilator-free days, Drug X vs. standard care):
$$n_{per\ group} = \frac{2(Z_{\alpha/2} + Z_{\beta})^2 \times \sigma^2}{\delta^2}$$

**What each piece controls:**
1. $Z_{\alpha/2}$ — how strict your significance threshold is (stricter → bigger $n$)
2. $Z_{\beta}$ — your desired power (more power → bigger $n$)
3. $\sigma^2$ / the variance term — noisier outcomes need more patients
4. $(p_1-p_2)$ or $\delta$ — the effect size you're trying to detect (smaller true effect → bigger $n$ needed to catch it)

## 2. Key Concepts, Principles & Assumptions

**The single most common way real trials end up underpowered:** picking an overly optimistic effect size, or an inaccurate assumed control-arm event rate, purely to make the required sample size look "achievable" on paper. This doesn't change reality — it just means the finished trial may be powered to detect an effect larger than the one that actually exists (a direct callback to Chapter 3's Type II error risk).

**Two-sided vs. one-sided tests:** a two-sided test (checking for a difference in *either* direction) needs a larger sample than a one-sided test for the same power — and two-sided is the expected default for nearly every confirmatory ICU trial, since a new treatment could plausibly turn out worse, not just better.

**Memory hook:** *Sample size math doesn't create certainty — it just tells you how many patients you need to detect the effect size you assumed. Assume wrong, and the "correct" calculation still leaves you underpowered.*

## 3. Visual / ASCII Schematic
```
Required sample size (per group) vs. assumed effect size

Large assumed effect  ---->  small N needed   (easy to detect)
Moderate assumed effect ---> moderate N needed
Small assumed effect  ---->  LARGE N needed    (hard to detect)

     N required
        |
        |  *
        |    *
        |       *
        |            *
        |________________*_________  effect size
       small                    large
   (the smaller the true effect, the more patients you need
    to reliably tell it apart from chance)
```

## 4. Landmark ICU Clinical Anchor — TTM2 Trial

**The calculation:** TTM2 (hypothermia at 33°C vs. normothermia with early fever control, after cardiac arrest) pre-specified an assumed control-arm mortality, a clinically meaningful absolute risk reduction it aimed to detect, a two-sided $\alpha$ of 0.05, and 90% power — arriving at a target enrollment of roughly **1,900 patients**.

**The lesson:** a trial this large wasn't a matter of throwing resources at the problem — it was the direct mathematical consequence of wanting to reliably detect a realistically modest effect size in a common but heterogeneous post-cardiac-arrest population.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Forces investigators to state, in advance, exactly what effect size they consider clinically meaningful
2. Provides a transparent, checkable justification for a trial's size before it even begins
3. Directly connects to power and Type II error risk, closing the loop from Chapter 3

**Examiner traps:**
1. Backward-engineering the assumed effect size from "what sample size can we realistically recruit," rather than from genuine clinical judgment
2. Using an inaccurate assumed control-arm event rate — even a well-calculated sample size is only as good as this starting assumption
3. Forgetting that a two-sided test needs a larger sample than a one-sided one for the same power
4. Ignoring anticipated dropout/crossover rates, which quietly erode the power a well-calculated $n$ was supposed to provide

## 6. Theory Exam Summary Box
> 1. Required sample size depends on assumed effect size, variability, $\alpha$, and desired power — all pre-specified
> 2. An overly optimistic assumed effect size is the most common real-world cause of underpowered "negative" trials
> 3. Two-sided tests need more patients than one-sided tests for the same power — and are the ICU-trial default

---

# Chapter 22: Intention-to-Treat, Modified ITT, and Per-Protocol Analyses

## 1. Definition & Mathematical Core

**Three ways to decide who counts, and in which group, once your trial has crossover or non-adherence:**
1. **Intention-to-Treat (ITT)** — analyze every randomized patient in the group they were *assigned* to, regardless of what treatment they actually received, crossed over to, or how well they adhered
2. **Per-Protocol (PP)** — analyze only patients who actually received and completed the assigned treatment as intended, excluding major protocol deviations
3. **Modified ITT (mITT)** — a narrower exclusion than full PP: drop only patients who were randomized but never actually *started* the intervention at all (e.g., immediate consent withdrawal, or an urgent contraindication found right after randomization) — everyone else stays, analyzed as assigned

## 2. Key Concepts, Principles & Assumptions

**Why ITT is the default, protected analysis:** it preserves randomization's single most valuable property — balancing both known *and unknown* confounders between arms. The moment you start excluding patients based on what happened *after* randomization (crossover, non-adherence), you risk re-introducing exactly the kind of selection bias randomization was designed to prevent.

**The direction ITT usually biases toward:** in a superiority trial, crossover and non-adherence dilute the true difference between arms, pulling the observed result **toward the null** — making it *harder*, not easier, to show a treatment works. This is honest: it reflects how the treatment performs in real-world practice, imperfect adherence included.

**Why this becomes dangerous in a different trial type:** if ITT dilutes differences toward the null in a superiority trial, imagine what it does in a **non-inferiority** trial, where "no difference" is the result you're hoping for. Diluted-toward-the-null crossover can make a genuinely *worse* treatment look artificially non-inferior — this is exactly why Chapter 23 requires both ITT and PP to agree.

**Memory hook:** *ITT protects the trial's honesty about real-world adherence. PP protects the trial's answer to "does it work when actually taken as prescribed." Neither one alone tells the whole story.*

## 3. Visual / ASCII Schematic
```
Randomized to Drug X ---> some patients cross over to standard care
Randomized to standard care ---> some patients cross over to Drug X

ITT analysis:        group = AS RANDOMIZED     (everyone counted,
                                                 wherever they ended up)
Per-Protocol analysis: group = AS ACTUALLY TREATED, adherent only
                                                 (crossover/non-adherent
                                                  patients EXCLUDED)
Modified ITT:         group = AS RANDOMIZED, minus only those who
                                                 never started treatment at all
```

## 4. Landmark ICU Clinical Anchor — EOLIA Trial

**The design:** EOLIA randomized patients with severe ARDS to early ECMO vs. conventional ventilation (with ECMO available as rescue therapy in the control arm).

**The complication:** a substantial number of control-arm patients ultimately crossed over and received ECMO as rescue therapy. The ITT analysis showed a non-significant mortality difference — but analyses accounting for this crossover suggested a larger apparent benefit of early ECMO.

**The lesson:** this is precisely the scenario Chapter 22 warns about — heavy crossover can obscure a true treatment effect in the primary ITT analysis, which is a large part of why EOLIA's overall conclusion remains genuinely debated rather than settled.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. ITT preserves randomization's protection against both known and unknown confounding
2. PP answers a genuinely useful secondary question: "does this work when actually delivered as intended?"
3. mITT offers a defensible middle ground, when narrowly and transparently pre-specified

**Examiner traps:**
1. Presenting a PP analysis as if it carries the same causal protection as ITT — it doesn't, once non-random exclusions are introduced
2. Assuming ITT always favors finding "no difference" — true for superiority trials, but this is exactly what makes ITT alone insufficient for non-inferiority claims
3. Using mITT without pre-specifying, in the protocol, exactly which patients qualify for exclusion — post-hoc mITT definitions are a serious red flag
4. Reporting only one of the three analyses when the others would change the interpretation, especially in a trial with heavy crossover

## 6. Theory Exam Summary Box
> 1. ITT = analyzed as randomized, regardless of what happened after — the default, protected analysis
> 2. PP = analyzed as actually treated — useful, but loses randomization's protection against confounding
> 3. Heavy crossover (like EOLIA's) can meaningfully change which analysis you'd trust, and why

---

# Chapter 23: Non-Inferiority and Equivalence Trials

## 1. Definition & Mathematical Core

**A different question entirely:** instead of "is the new treatment *better*," a non-inferiority trial asks "is the new treatment *not unacceptably worse* than the established standard" — within a pre-specified margin, $\Delta$ (Delta).

**Choosing $\Delta$ is a clinical judgment, not a statistical one** — typically set conservatively, as a fraction of the standard treatment's own known effect over placebo (historical data), so that even a "non-inferior" result can't secretly mean "barely better than nothing."

**The statistical test looks different from a superiority trial:** you don't need $p < 0.05$ against a null of "no difference." Instead, non-inferiority is declared if the **entire confidence interval** for the difference between arms lies within the pre-specified margin $\Delta$ — the CI's position relative to the margin, not a single p-value, is what matters.

## 2. Key Concepts, Principles & Assumptions

**Why both ITT and PP are mandatory here — directly following from Chapter 22:**
- **ITT alone** can be dangerous: crossover/non-adherence dilutes differences toward the null, which can make a genuinely *inferior* treatment look falsely non-inferior
- **PP alone** can be dangerous too: it excludes exactly the non-adherent or poor-outcome patients whose data might reveal true inferiority

Regulatory guidance requires **both** analyses to reach the same non-inferiority conclusion before it's considered robust — this dual requirement is the direct opposite of superiority trials, where ITT alone is usually sufficient.

**The trap that costs the most marks:** a "non-significant" result from a trial that was designed and powered as a *superiority* trial is **not** evidence of non-inferiority. Non-inferiority requires its own pre-specified margin and its own power calculation — you cannot reinterpret a failed superiority trial as a successful non-inferiority one after the fact.

**Memory hook:** *Superiority asks "is it better?" Non-inferiority asks "is it not unacceptably worse?" — and needs both ITT and PP to agree before you believe it.*

## 3. Visual / ASCII Schematic
```
Non-inferiority margin interpretation zones
(CI for the difference: new treatment minus standard treatment)

          Favors standard <--- 0 ---> Favors new treatment
                    -Delta          0
                     |               |
CI entirely left of -Delta:    CLEARLY INFERIOR
CI crosses -Delta:              INCONCLUSIVE
CI entirely right of -Delta,
   but crosses 0:               NON-INFERIOR (not proven superior)
CI entirely right of -Delta
   AND right of 0:              NON-INFERIOR AND SUPERIOR
```

## 4. Landmark ICU Clinical Anchor — VAP Antibiotic Duration Trial (Chastre et al.)

**The comparison:** 8 days vs. 15 days of antibiotic therapy for ventilator-associated pneumonia.

**The finding:** the shorter 8-day course showed broadly similar mortality and recurrence outcomes to the longer course, with less antibiotic exposure — supporting shorter-duration therapy as an acceptable, not-unacceptably-worse alternative for most patients.

**The lesson:** this is the practical payoff of a well-designed non-inferiority approach in ICU antimicrobial stewardship — accepting a pre-specified margin of "acceptable sameness" in exchange for a genuine, tangible benefit: less antibiotic exposure and less pressure toward resistance.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Lets you formally evaluate treatments valuable for reasons other than superior efficacy — cost, convenience, reduced toxicity, reduced resistance pressure
2. Forces explicit, pre-specified clinical judgment about how much efficacy loss is acceptable
3. The dual ITT-and-PP requirement makes these trials unusually resistant to a specific, well-known form of manipulation

**Examiner traps:**
1. Treating a "failed" superiority trial's non-significant p-value as proof of non-inferiority
2. Setting the non-inferiority margin $\Delta$ too generously (too large), which can let a genuinely worse treatment pass as "non-inferior"
3. Trusting an ITT-only or PP-only non-inferiority conclusion — both are required to agree
4. Forgetting that non-inferiority is not equivalence — equivalence trials require the CI to fall within a margin on *both* sides, a stricter standard

## 6. Theory Exam Summary Box
> 1. Non-inferiority asks "not unacceptably worse," using a pre-specified clinical margin $\Delta$, not a superiority p-value
> 2. Both ITT and PP analyses must agree — either alone can hide true inferiority in opposite ways
> 3. A non-significant superiority trial is not, by itself, evidence of non-inferiority

---

# Chapter 24: Factorial Trials (2×2 Designs)

## 1. Definition & Mathematical Core

**Testing two separate questions in one trial:** randomize patients on **two independent interventions at once** — say, Drug X sedation strategy (yes/no) *and* an early mobilization protocol (yes/no) — creating **4 groups**:

| | Mobilization: yes | Mobilization: no |
|---|---|---|
| **Drug X: yes** | Both | Drug X only |
| **Drug X: no** | Mobilization only | Neither |

**Main effect of Drug X** = the pooled comparison of "any Drug X" (both top-row groups) vs. "no Drug X" (both bottom-row groups), averaged across mobilization status — valid **only if there's no meaningful interaction** between the two factors.

**Interaction effect** = when Drug X's effect genuinely *depends* on whether mobilization was also given (or vice versa). If a real interaction exists, the pooled "main effect" estimates become misleading, and each factor's effect must be reported separately within each level of the other.

## 2. Key Concepts, Principles & Assumptions

**The efficiency that makes this design attractive:** a well-designed 2×2 factorial trial can answer **two research questions** using roughly the same total sample size that a single 2-arm trial would need for one question — a major resource saving in ICU research, where recruitment is slow and expensive.

**The assumption that efficiency quietly depends on:** little-to-no interaction between the two factors. Detecting an interaction reliably requires substantially more patients than detecting either main effect alone — and most factorial trials are **not** powered to reliably rule interaction in or out. This is one of the most common examiner traps in this topic: assuming a factorial trial's main-effect result is safe to interpret without ever checking whether it was adequately powered for interaction.

**When factorial design is a poor choice:** if investigators strongly suspect the two interventions genuinely interact (e.g., biological plausibility that mobilization only helps under lighter sedation), a standard factorial design may need to be specifically — and expensively — powered for that interaction, or abandoned in favor of separate trials.

**Memory hook:** *Factorial trials give you two answers for the price of one — but only if the two questions truly don't talk to each other.*

## 3. Visual / ASCII Schematic
```
                Mobilization: YES      Mobilization: NO
Drug X: YES     Group 1 (n=50)         Group 2 (n=50)    -> Drug X "yes" row
Drug X: NO      Group 3 (n=50)         Group 4 (n=50)    -> Drug X "no" row
                     |                        |
              Mobilization "yes"      Mobilization "no"
                     column                  column

Main effect of Drug X   = (Group1+Group2) vs (Group3+Group4)
Main effect of Mobilization = (Group1+Group3) vs (Group2+Group4)
Interaction check: does Drug X's effect differ between the
                    Mobilization-yes column and the Mobilization-no column?
```

## 4. Landmark ICU Clinical Anchor — FACTT Trial

**The design:** the ARDSnet Fluid and Catheter Treatment Trial (FACTT) used a genuine 2×2 factorial design — randomizing ARDS patients simultaneously to **conservative vs. liberal fluid strategy**, and to **pulmonary artery catheter vs. central venous catheter**–guided management.

**The finding:** conservative fluid management improved lung function and shortened ICU stay without increasing organ failure; catheter type made no significant difference to outcomes.

**The lesson:** FACTT answered two genuinely separate, practically important ICU management questions in a single trial — exactly the efficiency this chapter describes — while still requiring investigators to check that fluid strategy's effect didn't meaningfully depend on which catheter was used.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Answers two independent research questions with roughly one trial's worth of resources
2. Efficient use of a scarce, hard-to-recruit ICU population
3. Can still detect a clinically important interaction, if specifically powered to do so

**Examiner traps:**
1. Reporting main effects without checking (or acknowledging) whether the trial was powered to detect interaction
2. Assuming a factorial design is always more efficient — it isn't, if a genuine interaction exists and goes undetected
3. Confusing a factorial trial's 4 groups with a simple 4-arm trial comparing 4 unrelated treatments — the factorial structure specifically allows pooling across one factor to estimate the other's main effect
4. Ignoring a statistically non-significant but clinically plausible interaction signal, purely because the trial wasn't powered to confirm it

## 6. Theory Exam Summary Box
> 1. A 2×2 factorial design answers 2 questions with roughly the sample size of 1 — provided the two factors don't meaningfully interact
> 2. Most factorial trials are underpowered to detect interaction, even though they can estimate main effects well
> 3. Always ask: was this trial designed to check for interaction, or only to assume it away?

---

# Chapter 25: Cluster-Randomized and Stepped-Wedge Designs

## 1. Definition & Mathematical Core

**Cluster randomization:** randomize entire **units** — ICUs, wards, hospitals — rather than individual patients. Needed whenever an intervention operates at the unit level and can't be given to one patient without inevitably affecting their neighbors (a new sedation order-set, a hand-hygiene campaign, an infection-control bundle).

**The statistical cost of clustering — Intra-cluster correlation (ICC):** patients treated in the same unit tend to resemble each other (shared staff, shared local protocols, shared culture) more than they resemble patients in a different unit. This shrinks your *effective* sample size below the raw patient count.

**The design effect formula quantifies exactly how much:**
$$DEFF = 1 + (m - 1) \times ICC$$
where $m$ = average cluster size. Your required sample size must be multiplied by this design effect to restore the statistical power a naive, unclustered calculation would have overestimated.

**Stepped-wedge design:** every cluster **eventually** receives the intervention, but the **order and timing** of rollout is randomized. Each cluster serves as its own "before" control early on, and "after" intervention data later — useful when withholding a plausibly beneficial intervention from some clusters indefinitely would be logistically or ethically difficult.

## 2. Key Concepts, Principles & Assumptions

**Why ignoring ICC is a serious, common real-world error:** analyzing cluster-randomized data as though it were simple individual-patient randomization makes your results look artificially more precise and more statistically significant than they truly are — directly inflating your real Type I error rate above the stated 5%, often without anyone noticing.

**What stepped-wedge designs must additionally account for:** *time* itself, as a genuine factor. ICU practice, patient case-mix, and background outcomes can drift across the calendar period of a rollout, independent of the intervention — a stepped-wedge analysis has to model this time trend explicitly, or risk crediting the intervention for a change that was happening anyway.

**Memory hook:** *Patients in the same ICU aren't fully independent data points — ICC is the price you pay for that shared environment, and it has to be paid back in your sample size.*

## 3. Visual / ASCII Schematic
```
STEPPED-WEDGE ROLLOUT (rows = clusters, columns = time periods)

              Period 1   Period 2   Period 3   Period 4
Cluster A:    control    INTERVENE  INTERVENE  INTERVENE
Cluster B:    control    control    INTERVENE  INTERVENE
Cluster C:    control    control    control    INTERVENE
Cluster D:    control    control    control    control -> INTERVENE (later)

Every cluster eventually crosses over -- the RANDOM part is WHEN.
Each cluster contributes both "before" and "after" data.
```

## 4. Landmark ICU Clinical Anchor — REDUCE MRSA Trial

**The design:** a cluster-randomized trial comparing three MRSA-prevention strategies — screening and isolation, targeted decolonization, and universal decolonization — with **ICUs themselves**, not individual patients, as the unit of randomization.

**The finding:** universal decolonization significantly reduced MRSA clinical cultures and bloodstream infections compared to screening and isolation.

**The lesson:** this is a textbook cluster-randomized design — the intervention (a unit-wide decolonization protocol) simply couldn't be delivered to one patient without affecting everyone else on that unit, making individual-patient randomization impossible and cluster randomization the only workable option.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Makes trials of genuinely unit-level interventions possible at all
2. Stepped-wedge designs let every cluster eventually benefit, easing ethical and logistical objections to withholding an intervention
3. Can evaluate real-world, system-level implementation rather than an artificial patient-level version of the intervention

**Examiner traps:**
1. Analyzing cluster-randomized data with standard (non-clustered) statistical methods — inflates false-positive risk
2. Forgetting to account for time trends in a stepped-wedge design, crediting the intervention for a secular trend
3. Underestimating required sample size by ignoring the design effect (ICC-driven)
4. Assuming a small number of large clusters behaves statistically like a large number of individual patients — it doesn't; the number of *clusters*, not just patients, drives power

## 6. Theory Exam Summary Box
> 1. Cluster randomization is required whenever an intervention operates at the unit, not the patient, level
> 2. ICC shrinks your effective sample size — the design effect ($1+(m-1)\times ICC$) tells you by how much
> 3. Stepped-wedge designs must model secular time trends explicitly, or risk misattributing a background change to the intervention

---

# Chapter 26: Adaptive Platform Trials

## 1. Definition & Mathematical Core

**A traditional fixed trial:** one question, one comparison, fixed sample size, fixed duration, one final analysis.

**An adaptive platform trial:** a **perpetual trial infrastructure** that can simultaneously test multiple interventions against a shared control, drop underperforming arms early based on pre-specified interim rules, add new candidate treatments as they emerge, and — in some designs — use **response-adaptive randomization** to steer more future patients toward currently better-performing arms. This is typically governed by a **Bayesian** statistical framework, continuously updating the probability that one treatment is superior, rather than waiting for a single fixed end-of-trial p-value.

**Multi-Arm Multi-Stage (MAMS):** several treatment arms run against one shared control; at pre-planned interim looks, arms that are clearly underperforming get dropped, concentrating future recruitment on the most promising remaining candidates.

## 2. Key Concepts, Principles & Assumptions

**Why Bayesian methods fit naturally here:** a trial with no single "final" analysis needs a statistical framework built for continuous updating, not one built around a single fixed hypothesis test — which is exactly what a Bayesian approach provides.

**The trade-off with response-adaptive randomization:** steering patients toward better-performing arms can reduce the number of patients exposed to an inferior treatment over the trial's lifetime — but if standard-of-care itself is drifting over the same period (a real risk during, say, a pandemic), later-enrolled patients can differ systematically from earlier ones, and this time-related confounding has to be modeled explicitly, not assumed away.

**The bigger structural advantage:** a shared, ongoing infrastructure — and crucially, a **shared control arm** — lets one platform answer many sequential questions over years, without needing to recruit a brand-new control group from scratch for every new candidate treatment.

**Memory hook:** *A fixed trial answers one question and closes. A platform trial keeps the door open — new arms in, weak arms out, all sharing one control.*

## 3. Visual / ASCII Schematic
```
ADAPTIVE PLATFORM TRIAL (arms enter/exit over time)

Time  --->    Period 1      Period 2      Period 3      Period 4
Control:      ongoing ------------------------------------------>
Arm A:        active    -->  DROPPED (interim analysis: inferior)
Arm B:        active    -->  active    -->  active     --> active
Arm C:                       NEW ARM ADDED  -->  active --> active
Arm D:                                          NEW ARM ADDED --> active

  Shared control arm runs continuously throughout.
  Bayesian interim analyses decide which arms continue.
```

## 4. Landmark ICU Clinical Anchor — REMAP-CAP

**The design:** a real, ongoing adaptive platform trial testing multiple treatment domains simultaneously — antibiotics, corticosteroids, IL-6 receptor antagonists, anticoagulation strategies, and more — in patients with severe pneumonia, using Bayesian response-adaptive randomization against shared control groups.

**The finding:** during the COVID-19 pandemic, REMAP-CAP identified a mortality benefit from IL-6 receptor antagonists (e.g., tocilizumab) in critically ill patients — a finding reached faster than a traditional fixed-design trial could likely have delivered, because the platform infrastructure and shared control arms were already running.

**The lesson:** this is the real-world payoff of everything in this chapter — a single, evolving infrastructure that could pivot to a novel pandemic pathogen and still deliver a rigorous, statistically sound answer within the outbreak's own timeframe.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Can answer multiple questions, and adapt to new questions, without rebuilding trial infrastructure from scratch each time
2. Bayesian interim monitoring can reduce patient exposure to inferior arms
3. Proved capable of generating practice-changing results within a genuine public health emergency's timeframe

**Examiner traps:**
1. Assuming platform trial results transfer directly to a classic frequentist p-value interpretation — Bayesian outputs (posterior probabilities) answer a related but distinct question
2. Underestimating the complexity of controlling for time-related confounding when standard-of-care itself is evolving mid-trial
3. Treating an early-dropped arm as definitively proven inferior, rather than as "unlikely enough, given the interim data and pre-specified stopping rule, to be worth continued study"
4. Forgetting that response-adaptive randomization, if poorly implemented, can itself introduce bias — it is a powerful tool, not a free efficiency gain

## 6. Theory Exam Summary Box
> 1. Adaptive platform trials test multiple arms against a shared control, adding and dropping arms as evidence accumulates
> 2. Bayesian methods suit this design's continuous, non-final nature better than a single fixed p-value framework
> 3. REMAP-CAP is the real-world proof of concept — rigorous evidence, generated fast enough to matter during a live pandemic

---

# Section 4 Synthesis — Which Trial Design Fits Your Question?

**Resolving the Drug X sedation trial, end to end:**

1. **Basic architecture** — allocation concealed via central randomization, double-blind if feasible, and a decision about whether a run-in period is worth its cost to generalizability (Chapter 19)
2. **How to randomize** — block randomization at minimum, stratified by a known severity marker if the trial is small enough that chance imbalance is a real risk (Chapter 20)
3. **How many patients** — driven by your honestly-assumed control-arm event rate and the smallest effect size that would actually change practice (Chapter 21)
4. **How to analyze inevitable non-adherence** — ITT as your primary, protected analysis; PP as a secondary check (Chapter 22)
5. **What kind of question you're actually asking** — if Drug X is a cheaper generic you're not trying to prove *superior*, just acceptable, this becomes a non-inferiority trial requiring both ITT and PP to agree (Chapter 23)
6. **Could you answer a second question for free?** — pairing Drug X with an unrelated intervention (like mobilization) in a factorial design, if you're confident they won't meaningfully interact (Chapter 24)
7. **Is this actually a unit-level intervention?** — if Drug X is really a protocol/order-set change, individual randomization isn't possible; cluster or stepped-wedge design becomes necessary (Chapter 25)
8. **Do you need to keep asking new questions over time?** — if Drug X is the first of many candidate sedatives you'll want to test over the coming years, a platform trial with a shared control arm may be the more efficient long-term investment (Chapter 26)

```
        WHICH TRIAL DESIGN FITS YOUR QUESTION?
                        |
        Can the intervention be delivered to ONE
        patient without affecting their neighbors?
             | yes                    | no
             v                         v
     Individual RCT              CLUSTER or
     (Ch 19-23)                  STEPPED-WEDGE (Ch 25)
             |
             v
     Testing 2 unrelated questions at once,
     with little expected interaction?
             | yes                    | no
             v                         v
     FACTORIAL (Ch 24)          Standard 2-arm RCT
             |
             v
     Will you keep testing new candidate
     treatments against this control for years?
             | yes                    | no
             v                         v
     ADAPTIVE PLATFORM (Ch 26)    Fixed-duration trial,
                                  as designed in Ch 19-23
```

---

*Continue to Section 5: Survival Analysis, Effect Sizes & Time-to-Event.*
