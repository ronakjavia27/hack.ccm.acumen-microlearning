# SECTION 5: SURVIVAL ANALYSIS, EFFECT SIZES & TIME-TO-EVENT
### Plain-Language Edition — DrNB / DM Critical Care Medicine

---

## Running Scenario (used throughout this section)

You're studying whether **extended-duration pharmacologic VTE prophylaxis** (continuing anticoagulation for 4 weeks after ICU discharge, instead of stopping it at discharge) reduces venous thromboembolism — 300 critically ill patients per arm. You're tracking time to VTE, time to death, major bleeding events, and, eventually, how to combine all three into one meaningful overall picture.

---

# Chapter 27: Measures of Association — Risk Ratio, Odds Ratio, and Hazard Ratio

## 1. Definition & Mathematical Core

**Three different ways to summarize the same treatment effect:**

1. **Risk Ratio (RR)** — a simple ratio of proportions by a fixed endpoint: "of everyone in each arm, what fraction had a VTE by day 90?" $RR = \frac{\text{risk in extended arm}}{\text{risk in standard arm}}$
2. **Odds Ratio (OR)** — the ratio of odds (not risk) of VTE between arms, the natural output of logistic regression (Chapter 11): $OR = \frac{\text{odds in extended arm}}{\text{odds in standard arm}}$
3. **Hazard Ratio (HR)** — the ratio of the *instantaneous rate* at which VTE is occurring, at any given moment, across the entire follow-up period — accounting for exactly *when* events happened, not just whether they happened by day 90

## 2. Key Concepts, Principles & Assumptions

**What each one actually answers:**

| | Uses timing of events? | Typical source |
|---|---|---|
| RR | No — one fixed timepoint | Simple proportions |
| OR | No — one fixed timepoint | Logistic regression |
| HR | Yes — the whole follow-up curve | Cox regression, Kaplan-Meier/log-rank |

**RR and OR diverge meaningfully when the outcome is common** — and VTE in a high-risk ICU population isn't rare, so this isn't a purely academic distinction (the same OR ≠ RR trap from Chapter 11, reappearing here).

**Why HR is often the preferred summary for time-to-event ICU outcomes:** it uses *every patient's* full follow-up duration — including those who left the study partway through (Chapter 29's censoring) — rather than collapsing everything down to "yes/no by one fixed day." It can also reveal whether a treatment effect is front-loaded, delayed, or consistent across the whole follow-up period, which a single fixed-timepoint RR or OR simply cannot show.

**The assumption HR quietly carries:** proportional hazards — the relative hazard rate between arms stays roughly constant over time (→ Chapter 30).

**Memory hook:** *RR/OR ask "by the end, who had more events?" HR asks "throughout, who was accumulating events faster?"*

## 3. Visual / ASCII Schematic
```
FIXED-TIMEPOINT VIEW (RR/OR):
Day 90 only:  Extended arm: 12/300 VTE   Standard arm: 20/300 VTE
              --------------------------------------------------
              One snapshot, ignores WHEN each VTE occurred

TIME-TO-EVENT VIEW (HR):
Extended arm hazard:  low, roughly flat rate of VTE across all 90 days
Standard arm hazard:  higher, roughly flat rate of VTE across all 90 days
              --------------------------------------------------
              HR = ratio of these two rates, using EVERY day of
              follow-up for EVERY patient, not just the day-90 snapshot
```

## 4. Landmark ICU Clinical Anchor — PROTECT Trial

**The comparison:** dalteparin (low-molecular-weight heparin) vs. unfractionated heparin for VTE prophylaxis in critically ill patients.

**The finding:** the trial's primary outcome, proximal deep vein thrombosis, did not differ significantly between groups — but dalteparin significantly reduced the incidence of pulmonary embolism.

**The lesson:** this single PE-reduction finding could be reported as an RR (proportion by end of follow-up), an OR (from a logistic model), or an HR (if analyzed as time-to-PE) — and depending on how common the underlying PE risk was in this population, these three numbers would not be identical, even though they describe the same underlying benefit.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. RR is intuitive and easy to communicate to patients and colleagues
2. OR is the natural output whenever logistic regression is used to adjust for confounders
3. HR makes full use of time-to-event data, including censored patients, and can reveal how a treatment effect evolves over time

**Examiner traps:**
1. Quoting an OR as if it were an RR, especially for a common outcome — the gap between them widens as the outcome becomes more frequent
2. Using RR/OR for a primary outcome that was actually analyzed as time-to-event — check which measure the trial's own methods section actually reports
3. Interpreting an HR as if it were a simple risk ratio "at every moment" without checking whether proportional hazards actually held (→ Chapter 30)
4. Forgetting that all three of these summarize *relative* effect, not absolute risk — that's Chapter 28's job

## 6. Theory Exam Summary Box
> 1. RR and OR summarize a fixed-timepoint proportion; HR summarizes the whole time-to-event curve
> 2. RR and OR diverge meaningfully once the outcome becomes common — check which one a study actually reports
> 3. HR's efficiency comes with an assumption attached: proportional hazards over the full follow-up period

---

# Chapter 28: Absolute Risk Reduction, Relative Risk Reduction, and NNT/NNH

## 1. Definition & Mathematical Core

**Continuing the PROTECT trial's PE finding** (illustrative, rounded figures): suppose PE occurred in roughly 2.3% of the standard heparin arm and 1.3% of the dalteparin arm.

$$ARR = \text{risk}_{control} - \text{risk}_{treatment} = 2.3\% - 1.3\% = 1.0 \text{ percentage point}$$
$$RRR = \frac{ARR}{\text{risk}_{control}} = \frac{1.0\%}{2.3\%} \approx 43\%$$
$$NNT = \frac{1}{ARR} = \frac{1}{0.01} = 100$$

**The same arithmetic, applied to harm instead of benefit, gives NNH** — for example, if extended prophylaxis increased major bleeding from 2% to 3%, that's an ARR of 1 percentage point in the *harmful* direction, and an NNH of 100 (one additional bleed for every 100 patients treated).

## 2. Key Concepts, Principles & Assumptions

**Why the headline "43% relative reduction" can mislead on its own:** it sounds dramatic, but it's built on a tiny absolute difference — 1 percentage point. The NNT of 100 puts this in honest perspective: you'd need to treat 100 patients with dalteparin instead of standard heparin to prevent a single additional PE. Both numbers are true. Only one of them tells you what to expect for the *next* 100 patients you treat.

**NNT and NNH are meaningless without a stated time frame** — "NNT = 100" over 90 days is a very different claim from "NNT = 100" over 10 years, since events keep accumulating the longer you follow patients. Always ask: over what duration was this NNT calculated?

**The real clinical question this chapter sets up:** if extended prophylaxis has an NNT of 100 to prevent one VTE, but an NNH of 100 to cause one major bleed, is it worth it? That comparison — benefit's NNT against harm's NNH, weighted by how severe each outcome actually is — is the heart of real bedside decision-making, and a favorite examiner question.

**Memory hook:** *RRR is the headline. ARR and NNT are the fine print — and the fine print is what you actually act on.*

## 3. Visual / ASCII Schematic
```
Same data, two ways of presenting it:

RELATIVE (RRR):    Standard arm  ||||||||||||||||||||||  (2.3%)
                    Extended arm  |||||||||||||           (1.3%)
                    "43% relative reduction" -- looks dramatic

ABSOLUTE (ARR/NNT): Standard arm  ..  (2.3 per 100)
                    Extended arm  .   (1.3 per 100)
                    "1 fewer event per 100 patients treated"
                    NNT = 100 -- the honest, actionable number

BENEFIT vs HARM:
    NNT (prevent 1 VTE)  = 100
    NNH (cause 1 bleed)  = 100
    -->  roughly balanced -- severity of each outcome now
         matters more than the raw numbers alone
```

## 4. Landmark ICU Clinical Anchor — PROTECT Trial, Continued

Using the same illustrative PE-reduction figures from Chapter 27: an NNT around 100 to prevent one additional PE with dalteparin over unfractionated heparin. This is precisely the number a clinician actually needs at the bedside — not the relative percentage alone — to weigh against dalteparin's cost, administration burden, and any bleeding signal observed in the same trial.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. ARR and NNT translate an abstract relative effect into a number a clinician can actually act on
2. NNH lets you weigh harm using the exact same, directly comparable arithmetic as NNT
3. Forces an explicit statement of the time frame the benefit or harm was measured over

**Examiner traps:**
1. Reporting RRR alone without ARR — this is the single most common way a modest benefit gets oversold
2. Quoting an NNT without its associated time frame
3. Comparing an NNT for a mild outcome directly against an NNH for a severe one without weighting by clinical severity — 100 prevented minor DVTs is not obviously worth 100 caused major bleeds
4. Calculating NNT from a relative measure (RR) without first confirming the baseline (control-arm) risk it was derived from — the same RR/RRR can produce wildly different NNTs depending on baseline risk

## 6. Theory Exam Summary Box
> 1. ARR = absolute difference in risk; RRR = ARR divided by control-arm risk; NNT = 1/ARR
> 2. A large RRR can hide a tiny ARR and a large NNT — always ask for both
> 3. NNT and NNH use identical arithmetic — compare them directly, weighted by how severe each outcome actually is

---

# Chapter 29: Kaplan-Meier Survival Analysis

## 1. Definition & Mathematical Core

**The upgrade from Chapter 27's fixed-timepoint view:** instead of one proportion at day 90, Kaplan-Meier tracks the probability of remaining **VTE-free** continuously across the *entire* follow-up period, updating the estimate every time an event occurs.

**The product-limit method, step by step:**
1. At each time a VTE event occurs, calculate the conditional probability of remaining event-free through that specific interval, *given* the patient was event-free up to that point
2. Multiply these conditional probabilities together, across every preceding interval, to get the cumulative event-free probability at any given day

**Right-censoring:** a patient discharged alive without a VTE, or one whose follow-up ends before the study closes, is "censored" at the last day they were known to be event-free. They still contribute everything they know up to that point — they just don't count as "event" or "no event, confirmed" beyond it.

**Log-rank test:** compares two KM curves' difference across the *entire* follow-up period, not just at one arbitrary day — the appropriate significance test to pair with a KM plot.

## 2. Key Concepts, Principles & Assumptions

**Why this beats a simple fixed-timepoint proportion:** it uses every patient's actual observed follow-up time, including those censored partway through, rather than discarding their partial information or forcing an artificial "yes/no by day 90" answer.

**The assumption doing quiet work here: non-informative censoring.** Patients who are censored — discharged, lost to follow-up, study ends — must not have a systematically different underlying VTE risk than patients who remain under observation. If sicker patients are disproportionately likely to be censored (or, worse, if death itself is being treated as simple censoring), KM estimates become biased — this is exactly the problem Chapter 31 tackles directly.

**How to read the shape of a KM curve, not just its endpoint:**
- Curves separating **early** → an early treatment effect
- Curves separating **late**, or continuing to diverge → a delayed or cumulative effect
- Curves that **cross** → the treatment effect may not be constant over time, a hint that the proportional hazards assumption (Chapter 30) could be shaky

**Memory hook:** *KM uses every day of every patient's story, not just the last page.*

## 3. Visual / ASCII Schematic
```
Probability event-free
   1.0 |‾‾‾‾‾‾\_________
       |                \___________          <- Extended prophylaxis
       |                            \______
       |‾‾‾\__________                     \__
       |               \______________          <- Standard prophylaxis
       |                               \________
   0.0 |________________________________________
       0                Day                     90
                          ^
                    tick mark = a censored patient (discharged alive,
                    event-free, still counted up to this point)
```

## 4. Landmark ICU Clinical Anchor — PROSEVA Trial, Revisited

**You met this trial in Chapter 20**, for its stratified randomization. Now look at how its actual result was displayed: PROSEVA's Kaplan-Meier curves for prone vs. supine positioning showed survival separating and persisting across the full 28- and 90-day follow-up, with the log-rank test confirming the difference held across the entire curve — not just at one arbitrarily chosen day.

**The lesson:** this is exactly why PROSEVA's result felt so convincing to the field — the benefit wasn't a fragile single-timepoint finding, it was a consistent separation sustained across the whole observation window.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Uses every patient's actual follow-up time, including those censored partway through
2. Visually communicates not just *whether* but *when* a treatment effect emerges
3. The log-rank test pairs naturally with the curve, testing the whole-curve difference honestly

**Examiner traps:**
1. Treating censoring as automatically "safe" without checking whether it's genuinely non-informative
2. Reading only the curves' final endpoint, ignoring valuable information about when they separated
3. Applying standard KM/log-rank when a competing risk (like death) is common enough to bias the estimate (→ Chapter 31)
4. Forgetting that crossing curves are a visual clue the proportional hazards assumption may not hold, before ever formally testing it

## 6. Theory Exam Summary Box
> 1. KM tracks event-free probability continuously, using the product-limit method across all follow-up time
> 2. Right-censored patients still contribute information up to their last known event-free day
> 3. Read the *shape* of the KM curve, not just its endpoint — early vs. late separation tells a different clinical story

---

# Chapter 30: Cox Proportional Hazards Model

## 1. Definition & Mathematical Core

**Extending Kaplan-Meier to adjust for covariates simultaneously** — the same conceptual jump from a simple chi-square to logistic regression (Chapters 9→11), now applied to time-to-event data:

$$h(t) = h_0(t) \times \exp(\beta_1 X_1 + \beta_2 X_2 + \dots)$$

1. $h_0(t)$ = the **baseline hazard** — the shape of risk over time shared by everyone in the model
2. $\exp(\beta)$ for a given covariate = the **hazard ratio** for a one-unit change in that covariate, holding the others constant
3. Covariates shift the hazard proportionally **up or down** — but under this model, the underlying *shape* of risk over time stays the same for every patient, just scaled

## 2. Key Concepts, Principles & Assumptions

**The proportional hazards (PH) assumption, stated plainly:** the hazard ratio between groups must stay roughly constant across the *entire* follow-up period. If a treatment's true effect is strong early and fades later (or the reverse), this assumption breaks down, and a single "average" HR across the whole follow-up can misrepresent both the early and late periods.

**Schoenfeld residuals — the formal check for PH:** this test examines whether the difference between each patient's observed covariate value and the model's expected value, at each event time, shows a systematic trend *over time*. A significant trend for a given covariate is a red flag that PH is violated for that specific variable — not necessarily for the whole model.

**Time-varying covariates — when a predictor itself changes during follow-up:** a patient's mobility status, for instance, may genuinely improve over the ICU stay rather than staying fixed at its baseline value. Cox models can be extended to let such a covariate's *value* update as follow-up progresses, giving a more accurate, dynamic risk estimate than freezing it at admission.

**Memory hook:** *Proportional hazards means the GAP between groups' risk stays proportionally the same over time — Schoenfeld residuals are how you check whether that's actually true, rather than just assuming it.*

## 3. Visual / ASCII Schematic
```
PROPORTIONAL HAZARDS (assumption holds):
Extended arm hazard:   ___/\___/\___/\___    (shape shared)
Standard arm hazard:  ____/\____/\____/\___   (same shape, scaled up)
        --> constant HR across all of follow-up

NON-PROPORTIONAL (assumption violated):
Extended arm hazard:   ___/\_______________    (effect fades late)
Standard arm hazard:  ____/\____/\____/\___
        --> HR is NOT constant -- an "average" HR would mislead
```

## 4. Landmark ICU Clinical Anchor — PREVENT Trial

**The design:** PREVENT tested adding intermittent pneumatic compression (IPC) to pharmacologic prophylaxis, against pharmacologic prophylaxis alone, for preventing proximal DVT in critically ill patients — analyzed with adjusted, time-to-event methods.

**The finding:** adding IPC did not significantly reduce proximal DVT incidence compared to pharmacologic prophylaxis alone.

**The lesson:** even a "negative" trial like this one relies on the same Cox-model machinery described above — adjusting for baseline covariates and modeling the full time-to-event curve, not just a single endpoint proportion, to give the most statistically efficient and honest answer available.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Lets you estimate a covariate-adjusted hazard ratio, extending Kaplan-Meier's simplicity to a multivariate setting
2. Time-varying covariates allow genuinely dynamic, evolving patient status to be modeled accurately
3. The Schoenfeld residuals test gives a concrete, checkable way to validate the model's core assumption

**Examiner traps:**
1. Reporting a single Cox model HR without ever checking the proportional hazards assumption
2. Treating a borderline-significant Schoenfeld residuals test as automatically disqualifying — sometimes a mild violation for one covariate is manageable with stratification or a time-varying term, not a reason to abandon the model
3. Using a fixed baseline value for a covariate that genuinely changes over follow-up, when a time-varying specification would be more accurate
4. Interpreting hazard ratios as if they were simple risk ratios "at every moment" without appreciating what the PH assumption is actually claiming

## 6. Theory Exam Summary Box
> 1. Cox regression estimates covariate-adjusted hazard ratios, assuming proportional hazards over time
> 2. Schoenfeld residuals formally test that assumption — don't just assume it holds
> 3. Time-varying covariates let genuinely evolving patient factors be modeled dynamically, not frozen at baseline

---

# Chapter 31: Competing Risks Analysis

## 1. Definition & Mathematical Core

**The problem hiding inside your own VTE trial:** death is a **competing risk** for VTE — a patient who dies from another cause can no longer go on to develop, or be diagnosed with, a VTE event. Standard Kaplan-Meier treats death as simple censoring, which silently assumes a patient who died would have had the *same* future VTE risk as patients who remained alive and under observation. That assumption is usually false, and it inflates the estimated cumulative incidence of VTE.

**The correct alternative — the Cumulative Incidence Function (CIF):** directly estimates the actual probability of experiencing VTE by a given time, properly accounting for the fact that some patients will die first and can therefore never experience the event of interest.

**The Fine-Gray subdistribution hazard model** is the competing-risks analog of Cox regression — it models covariate effects on the CIF directly, rather than on a cause-specific hazard that ignores the competing event.

## 2. Key Concepts, Principles & Assumptions

**Why naive KM overestimates VTE incidence when death is common:** KM's "1 minus survival" calculation implicitly keeps patients who died "in the running" for the event of interest, redistributing their probability mass as if they were still at risk — which inflates the apparent VTE incidence, especially later in follow-up once a meaningful number of at-risk patients have already died of something else.

**The examiner's favorite question on this topic:** *"When would you use CIF instead of standard KM?"* — whenever a competing event (almost always death, in ICU research) is common enough in your population that treating it as ordinary censoring would meaningfully bias your estimate of the event you actually care about.

**This isn't a VTE-specific quirk — it's a general ICU research issue:** time to extubation (death competes), time to AKI recovery (death competes), time to ICU discharge (death competes). Any outcome where death can preclude the event of interest needs this consideration, and critically ill populations — with their high background mortality — are exactly where it matters most.

**Memory hook:** *If death can stop the clock on your outcome of interest before it happens, you don't have simple censoring — you have a competing risk, and KM alone will lie to you about how big the problem really is.*

## 3. Visual / ASCII Schematic
```
Naive Kaplan-Meier "1 - survival" for VTE (treats death as censoring):
   Cumulative VTE incidence
       |                    ___________  <- OVERESTIMATED
       |              _____/                (death patients
       |         ____/                       still counted as
       |    ____/                            "at risk" of VTE)
       |___/
       +--------------------------------> time

Correct Cumulative Incidence Function (CIF, accounts for death):
       |               ______________  <- lower, more accurate
       |          ____/                  (patients who died are
       |     ____/                        properly removed from
       |____/                             future VTE risk)
       +--------------------------------> time
```

## 4. Landmark ICU Clinical Anchor — Competing-Risk Re-Analyses of ICU VTE-Prevention Data

**The pattern:** methodological re-analyses of critically ill VTE-prevention trial data, using proper competing-risk methods, have generally shown that naive Kaplan-Meier estimates of VTE incidence run higher than the corresponding CIF estimates — precisely because ICU mortality is high enough for death to meaningfully compete with VTE as an outcome.

**The lesson:** this is worth knowing generally, even without memorizing one specific trial's exact numbers — any critical care trial or observational study reporting a Kaplan-Meier-based VTE (or similar) incidence, in a population with substantial mortality, deserves a moment's scrutiny for whether death was handled as a true competing risk or quietly folded into ordinary censoring.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Gives an accurate, unbiased estimate of the true probability of the event of interest in populations with substantial competing mortality
2. The Fine-Gray model extends this to covariate-adjusted analysis, paralleling Cox regression
3. Forces explicit acknowledgment of competing outcomes that a naive analysis would silently ignore

**Examiner traps:**
1. Treating death as ordinary censoring in any ICU population with meaningful mortality — a near-automatic examiner flag
2. Assuming CIF and KM will give similar answers whenever competing-event rates are low — true, but the divergence grows quickly as competing mortality rises, exactly as it does in critical illness
3. Confusing a cause-specific hazard model with a subdistribution (Fine-Gray) hazard model — they answer related but genuinely different questions
4. Applying competing-risk correction only to the headline outcome while leaving secondary time-to-event outcomes analyzed naively

## 6. Theory Exam Summary Box
> 1. Death is a competing risk whenever it can preclude the event of interest — treating it as simple censoring inflates estimated incidence
> 2. The Cumulative Incidence Function (CIF) gives the accurate estimate; Fine-Gray regression extends this to adjusted analysis
> 3. High background mortality is the norm in critical illness — competing risks deserve default consideration, not an afterthought

---

# Chapter 32: Composite Endpoints & Hierarchical Win Ratios

## 1. Definition & Mathematical Core

**A composite endpoint** combines multiple distinct outcomes into one primary endpoint — for instance, "VTE, or major bleeding, or death, by day 28." This increases the overall event rate (helping with statistical power) and captures a broader picture of benefit and risk in a single number. **Its major limitation:** it treats every component event as equally important — statistically, a death and a minor lab-detected DVT count the same.

**A hierarchical win ratio fixes this by ranking, not pooling:**
1. Decide a clinical severity hierarchy in advance — for example, death > VTE > major bleeding > a continuous tie-breaker outcome
2. Compare **every possible pair** of patients, one from each treatment arm
3. Work down the hierarchy for each pair: compare on death first (whoever died "loses" that comparison); if tied on death, move to VTE; if tied on VTE, move to bleeding; if still tied, use a continuous outcome (like days alive and free of organ support) as the final tie-breaker
4. $$\text{Win Ratio} = \frac{\text{total wins}}{\text{total losses}}$$ across all pairwise comparisons

## 2. Key Concepts, Principles & Assumptions

**Why win ratios are gaining ground over flat composite endpoints in ICU trials:** they respect clinical severity by design — a death correctly "outweighs" a non-fatal event in every single paired comparison, rather than being statistically interchangeable with it, as a flat composite would treat it. They can also incorporate a continuous tie-breaker for patients who match on every categorical outcome, extracting genuine additional information a flat composite would simply discard.

**The trade-off:** win ratios are more complex to compute and communicate than a simple composite event rate, and the result can be sensitive to exactly how the hierarchy and tie-breaker outcome were chosen — which is precisely why both must be **pre-specified**, not selected after looking at the data.

**A hierarchical idea you've already met in this book:** REMAP-CAP's use of organ-support-free days (Chapter 26) is a close real-world relative of this idea — death is coded as categorically worse than any finite number of organ-support-free days, so mortality always outranks a merely prolonged ICU course in the resulting ordinal outcome. It isn't formally a "win ratio" analysis, but it shares the same underlying logic: rank severity first, don't just pool events as equivalent.

**Memory hook:** *A flat composite asks "did anything bad happen?" A win ratio asks "when we compare two real patients head-to-head, who actually did worse — and by which outcome, in which order of importance?"*

## 3. Visual / ASCII Schematic
```
HIERARCHICAL PAIRWISE COMPARISON (one pair at a time):

Patient A (extended arm) vs. Patient B (standard arm)
        |
        v
   Did either die?  --- yes, one did ---> that patient LOSES the pair
        | no, tied
        v
   Did either have VTE? --- yes, one did ---> that patient LOSES
        | no, tied
        v
   Did either have major bleeding? --- yes ---> that patient LOSES
        | no, tied
        v
   Compare organ-support-free days (continuous tie-breaker)
        |
        v
   Repeat for EVERY possible pair across both arms
        |
        v
   Win Ratio = total wins / total losses (ties excluded)
```

## 4. Landmark ICU Clinical Anchor — REMAP-CAP, Revisited

**You met this trial in Chapter 26**, for its adaptive platform design. Its use of organ-support-free days as a primary ordinal outcome — where death is assigned the worst possible value, ranked below every finite duration of organ support — is a close conceptual cousin of the hierarchical win-ratio approach described above, even though it isn't identical methodology.

**The lesson:** both approaches solve the same underlying problem — a flat composite or a simple binary mortality outcome alone would either dilute death's importance or throw away valuable information about non-fatal severity. Ranking outcomes by clinical importance, rather than pooling them as equivalent, is the shared idea worth remembering.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Respects clinical severity hierarchy explicitly, rather than treating death and a minor event as statistically equivalent
2. Can extract more information than a flat composite by using a continuous tie-breaker for otherwise-tied pairs
3. Increasingly used in modern critical care trials as composite outcomes have come under more scrutiny

**Examiner traps:**
1. Treating a flat composite endpoint's "positive" result as evidence of benefit on its most severe component (usually death) — always check which component(s) actually drove the composite
2. Choosing or reordering the severity hierarchy after seeing the data — this must be pre-specified
3. Assuming a win ratio result is intuitive to communicate to a non-statistical audience — it typically needs more explanation than a simple event rate
4. Ignoring the "ties" in a win ratio calculation — a design with many ties conveys less information than the win ratio number alone might suggest

## 6. Theory Exam Summary Box
> 1. A flat composite endpoint pools distinct outcomes as equally important — often clinically inaccurate
> 2. A hierarchical win ratio ranks outcomes by severity and compares patients pairwise, respecting that hierarchy
> 3. Pre-specify both the hierarchy and any continuous tie-breaker — never choose them after seeing the results

---

# Section 5 Synthesis — Reading Any Time-to-Event ICU Trial Result

**Resolving the VTE-prophylaxis scenario, end to end:**

1. **The headline comparison** — VTE rates by day 90, reportable as RR, OR, or HR, each answering a subtly different question (Chapter 27)
2. **Putting it in real terms** — ARR and NNT for the benefit, NNH for any bleeding signal, both stated with their time frame (Chapter 28)
3. **The full time course** — Kaplan-Meier curves showing not just whether but *when* the two arms diverge, with the log-rank test confirming it across the whole follow-up (Chapter 29)
4. **Adjusting for who's actually in each arm** — Cox regression for a covariate-adjusted hazard ratio, with the proportional hazards assumption checked via Schoenfeld residuals (Chapter 30)
5. **Accounting for death honestly** — a Cumulative Incidence Function, not naive KM, given how common death is in this population (Chapter 31)
6. **The final, clinically honest answer** — a pre-specified hierarchy (death, then VTE, then bleeding, then organ-support-free days) or win ratio, rather than a flat composite that quietly treats a death and a minor lab finding as the same thing (Chapter 32)

```
        READING ANY TIME-TO-EVENT ICU RESULT
                        |
        Is death common enough in this population to
        compete with the outcome of interest?
             | yes                    | no
             v                         v
     Use CIF, not naive KM        Standard KM/Cox is fine
     (Ch 31)                      (Ch 29-30)
             |                         |
             -------------+-------------
                           v
        Was the primary outcome a composite?
             | yes                    | no
             v                         v
     Check which component      Report RR/OR/HR + ARR/NNT
     actually drove it — was    together (Ch 27-28), with
     it ranked by severity, or  the full KM curve (Ch 29)
     pooled as equivalent?
     (Ch 32)
```

---

*Continue to Section 6: Evidence Synthesis & Systematic Appraisal.*
