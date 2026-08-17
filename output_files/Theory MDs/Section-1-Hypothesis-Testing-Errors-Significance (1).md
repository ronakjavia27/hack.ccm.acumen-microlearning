# SECTION 1: HYPOTHESIS TESTING, ERRORS & SIGNIFICANCE
### Plain-Language Edition — DrNB / DM Critical Care Medicine

---

## Running Scenario (used throughout this section)

You're running a trial: **a new sedation protocol vs. standard care, 100 ICU patients per arm.** Ventilator-free days are higher with the new protocol — average **18 days vs. 15 days.** You run the numbers and get **p = 0.03.**

Every chapter below builds on this same trial, one concept at a time.

---

# Chapter 1: The P-value

## 1. Definition & Mathematical Core

**What p = 0.03 actually means, step by step:**
1. Pretend, just for a moment, that the new protocol does absolutely nothing — no better than standard care.
2. In that pretend world, ask: "If I reran this exact trial hundreds of times with truly no real difference between the arms, how often would I see a gap this big (3 extra ventilator-free days) just from the play of chance?"
3. The answer here: about 3% of the time.
4. Because that's rare enough to raise an eyebrow, you lean toward thinking the difference is probably real — not just noise.

That's the whole idea. Everything below is the formal packaging of that one thought.

**The exam notation (same idea, different clothes):**
$$p = P_{H_0}(|T| \geq |t_{obs}|)$$
1. $H_0$ = the "pretend nothing is happening" world (the null hypothesis)
2. $T$ = the test statistic you'd expect to see in that pretend world
3. $t_{obs}$ = the test statistic you actually got

**The decision rule:**
- Before the trial starts, pick a cutoff $\alpha$ (usually 0.05) — your "how rare is rare enough to matter" line
- If $p \leq \alpha$ → you reject the "pretend nothing is happening" world
- This only works honestly if these were fixed **before** you saw the data:
  1. The statistical model
  2. The population analyzed
  3. The outcome definition
  4. The primary comparison

**What a p-value is NOT:**
- ❌ Not the probability that the sedation protocol does nothing
- ❌ Not the probability the protocol works
- ❌ Not a measure of how big or how clinically useful the 3-day difference is

## 2. Key Concepts, Principles & Assumptions

p = 0.03 tells you the 3-day gap is unlikely to be pure chance. It tells you **nothing** about whether 3 extra ventilator-free days actually changes what patients and families care about — mortality, function, time home. That's a separate clinical judgment.

**Why 0.05 isn't a real cliff edge:**
- If your trial had come back p = 0.052 instead of 0.03, would those 3 extra ventilator-free days suddenly become meaningless? No.
- p = 0.049 and p = 0.051 tell almost the same story — convention just slaps different labels on them.

**The 4 misreadings that lose marks:**

| Wrong belief | Why it's wrong |
|---|---|
| "p = 0.03 means 3% chance the protocol doesn't work" | p makes no claim about the protocol — only about the data, *assuming* it truly did nothing |
| "p > 0.05 next time would mean the protocol is useless" | Might just mean the next trial was too small to detect the same real difference |
| "A tiny p-value means a big effect" | A huge trial (5,000/arm) could turn a clinically trivial 0.3-day difference into p < 0.05 |
| "A wide, non-significant CI proves no effect" | The interval may still comfortably include a clinically important benefit |

**The multiplicity trap:** this all only holds if you looked **once**, at the outcome you pre-specified, at the time you said you would. Peeking repeatedly, swapping outcomes, or spotlighting a subgroup after the fact breaks it silently (→ Chapter 4).

**Memory hook:** P = **P**lausibility under the null — not **P**robability it's true.

## 3. Visual / ASCII Schematic
```
Observed ICU trial result
          |
          v
Was the primary hypothesis & analysis PRE-SPECIFIED?
     | yes                           | no / unclear
     v                                v
Read p-value + CI together      Treat as exploratory —
     |                          multiplicity/selection bias
     v                          may explain the result
p <= alpha? --yes--> Reject H0. Report EFFECT SIZE + CI.
     |
     no
     v
Do NOT say "no effect."
Ask instead: does the CI rule out a clinically important difference?
```

## 4. Landmark ICU Clinical Anchor — ANDROMEDA-SHOCK

**The comparison:** capillary refill time-targeted resuscitation vs. lactate-targeted resuscitation in septic shock.

| Metric | Value |
|---|---|
| 28-day mortality, capillary refill arm | 34.9% |
| 28-day mortality, lactate arm | 43.4% |
| Absolute difference | 8.5 percentage points |
| p-value | 0.06 |
| Hazard ratio CI | crosses 1 |

**The lesson:** an 8.5-point mortality difference doesn't become meaningless because p missed 0.05 by 0.01. The honest reading: the data are compatible with **all three**, simultaneously — a real meaningful benefit, no effect, or small harm. You can't rule out any of the three, and you can't declare a winner either.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. One calibrated decision rule — as long as the model and comparison were fixed in advance
2. Puts continuous, binary, and time-to-event outcomes on the same evidentiary scale
3. Can anchor a trial's stopping rules, if built into a pre-specified alpha-spending plan

**Examiner traps:**
1. "The p-value is the probability the treatment works" — that's a Bayesian question, not what p answers
2. "Not significant, so no clinical importance" — always report ARR, NNT/NNH, and CI alongside p
3. "Non-significant superiority = equivalence" — equivalence and non-inferiority need their own pre-specified margins
4. Letting a significant secondary outcome outweigh a non-significant primary one, without checking multiplicity

## 6. Theory Exam Summary Box
> 1. p-value = P(data this extreme | $H_0$ true) — **not** P($H_0$ true)
> 2. 0.05 is a convention, not a biological truth — p = 0.06 ≠ proof of no effect
> 3. Always read p alongside effect size, CI, pre-specification, and clinical consequence

---

# Chapter 2: Z-Score and Standard Error

## 1. Definition & Mathematical Core

**Back to the sedation trial.** Ventilator-free days averaged 18 in the new-protocol group and 15 in standard care. How did that turn into p = 0.03? The bridge is the **Z-score.**

**Step by step:**
1. First, how much do individual patients naturally differ from each other? Some patients get 2 ventilator-free days, some get 26 — that spread is the **standard deviation (SD)**, and it's a property of sick patients, not of your trial.
2. But you don't care about one patient — you care how much your **trial's average** would wobble if you reran it with a different random 100 patients. That wobble is the **standard error (SE)**, and unlike SD, it shrinks as you enroll more patients.
3. The **Z-score** is just: how many SEs apart are your two averages?
4. That Z-score gets converted into the p-value using the normal (bell-curve) distribution.

**The formulas:**
$$z = \frac{x - \mu}{\sigma} \qquad Z = \frac{\bar{x} - \mu_0}{SE(\bar{x})} \qquad SE(\bar{x}) = \frac{s}{\sqrt{n}}$$
1. $\mu$, $\sigma$ = the population mean and SD
2. $\bar{x}$ = your sample's mean; $\mu_0$ = the mean under $H_0$
3. $s$ = the sample SD; $n$ = the sample size

**95% CI:** $\hat{\theta} \pm 1.96 \times SE(\hat{\theta})$

## 2. Key Concepts, Principles & Assumptions

**The single most-confused pair in vivas:**

| | What it measures | Shrinks with bigger $n$? |
|---|---|---|
| **SD** | Patient-to-patient variability | ❌ No — it's a biological fact |
| **SE** | Uncertainty in your trial's *estimate* | ✅ Yes — roughly by $1/\sqrt{n}$ |

**Why this matters:** enroll enough patients and your SE shrinks toward zero — meaning even a **clinically trivial** average difference can generate a large Z-score and a tiny p-value. Big trial ≠ big effect. It just means you can detect smaller effects with confidence.

**When the normal-distribution shortcut breaks down:**
1. **Small samples with unknown population SD** → use the *t*-distribution instead of Z (wider tails, accounts for the extra uncertainty of estimating SD from few patients)
2. **Rare binary events** (e.g., severe hypoglycemia) → need exact or model-based methods, not normal approximations
3. **Clustered or repeated data** (cluster-randomized trials, repeated ICU measurements) → violates the "independent observations" assumption underneath SE
4. **Informative missingness** — e.g., a PaO2/FiO2 ratio measured only in patients who haven't yet died or been extubated — quietly distorts what SE is even estimating

**Memory hook:** SD = spread among patients (fixed by biology). SE = spread if you reran the trial (shrinks as you enroll more).

## 3. Visual / ASCII Schematic
```
Population outcome distribution (e.g., ICU ventilator-free days)
             mean = mu                    SD = sigma  (wide — patient variability)
                 |<---------- spread ---------->|
             ________/\________

Sampling distribution of the TRIAL MEAN
             mean = mu                    SE = s/sqrt(n)  (narrow — shrinks with n)
                    |<--- narrow --->|
                  ________/\________

Observed difference / SE  --->  Z statistic  --->  p-value
```

## 4. Landmark ICU Clinical Anchor — NICE-SUGAR

| Metric | Value |
|---|---|
| Patients randomized | 6,104 |
| 90-day mortality, intensive glucose control | 27.5% |
| 90-day mortality, conventional control | 24.9% |
| Odds ratio | 1.14 (95% CI 1.02–1.28) |
| p-value | 0.02 |

**The lesson:** because the sample was so large, the SE was small enough to detect a **modest but real** absolute difference (~2.6 percentage points). A smaller trial could easily have missed this. The p-value alone didn't settle practice — the absolute mortality increase, the precision, a severe-hypoglycemia signal, and biological plausibility all had to line up together.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Puts values and effect estimates on one standard scale, enabling normal-theory tests and CIs
2. Makes explicit why larger, independent samples buy you precision
3. Lets you interpret lab deviations quickly against a known reference distribution

**Examiner traps:**
1. Confusing SD with SE — SD describes patients, SE describes your estimate's uncertainty
2. Using a Z-test blindly on small samples, sparse binary outcomes, or skewed biomarkers (e.g., lactate) without checking the model first
3. Treating one patient's Z-score as a diagnosis — reference range, timing, assay, and illness trajectory all matter
4. Assuming a bigger $n$ fixes everything — it narrows the CI, but it cannot correct bias from non-random missingness, competing death, or protocol deviations

## 6. Theory Exam Summary Box
> 1. SD = variability between patients; SE = uncertainty in your estimate — never confuse the two
> 2. SE shrinks with $\sqrt{n}$; a huge trial can make a trivial effect "significant"
> 3. Small samples, rare events, and clustered data all break the plain normal-theory Z approach

---

# Chapter 3: Type I & Type II Errors, Power, and Sample Size

## 1. Definition & Mathematical Core

**Continuing the scenario:** suppose your sedation trial had instead come back p = 0.24 — even though, in the real world, the protocol genuinely does help, just by less than you assumed when planning your sample size. You've just risked a **Type II error.**

**Think of it as a smoke alarm:**
1. **Type I error ($\alpha$)** — the alarm goes off, but there's no fire. You declare a real difference when there isn't one. A false alarm.
2. **Type II error ($\beta$)** — the house is on fire, but the alarm stays silent. You conclude "no difference" when a real effect exists. A missed alarm.
3. **Power ($1-\beta$)** — the alarm's sensitivity: given a real fire of a certain size, how likely is your trial to actually detect it?

**The 2×2 truth table:**

| | $H_0$ actually true | $H_0$ actually false |
|---|---|---|
| **You reject $H_0$** | Type I error ($\alpha$) | Correct — true positive |
| **You fail to reject $H_0$** | Correct — true negative | Type II error ($\beta$) |

**What drives power:**
1. Effect size — bigger true differences are easier to detect
2. Variability — noisier outcomes need bigger samples
3. $\alpha$ — a stricter threshold lowers power at a fixed $n$
4. Sample size — more patients → smaller SE (Chapter 2) → more power

## 2. Key Concepts, Principles & Assumptions

An underpowered trial isn't evidence of "no effect" — it's a smoke alarm with a dying battery. It may simply be incapable of hearing a real, moderate-sized fire.

**Why "non-significant" ≠ "no effect":**
1. A trial powered to detect a 10-point mortality difference may completely miss a real 5-point difference
2. Slow recruitment, early termination, or a smaller-than-planned sample all quietly erode power without you being told
3. The correct read of an underpowered "negative" trial: *"we couldn't rule out a clinically important effect,"* not *"there is no effect"*

**Memory hook:** Type I = crying wolf. Type II = missing the wolf. Power = how good your ears are.

## 3. Visual / ASCII Schematic
```
                     TRUTH
              No real effect | Real effect exists
             ----------------|--------------------
Trial says   |  Type I error |  Correct           |
"significant"|     (alpha)   |  (true positive)   |
             |----------------|--------------------|
Trial says   |  Correct       |  Type II error     |
"not sig."   |  (true neg.)   |     (beta)         |
             ----------------------------------------
                                    ^
                          Power = 1 - beta
                     (your trial's chance of catching
                      a real effect, if one exists)
```

## 4. Landmark ICU Clinical Anchor — CORTICUS

**The story:** CORTICUS tested hydrocortisone in septic shock, but recruitment was slow, and the trial closed well short of its originally planned sample size.

**The consequence:** with fewer patients than planned, CORTICUS had limited power to detect anything but a large effect on 28-day mortality. It reported no significant mortality difference between hydrocortisone and placebo — but this doesn't prove steroids don't work in septic shock. It may simply mean the trial never had the numbers to find a real, moderate-sized effect.

**Why this matters for your exam:** this is exactly why later, adequately powered trials (e.g., ADRENAL) were still needed before the field could draw firmer conclusions about steroids in septic shock — an underpowered "negative" trial doesn't close a question, it leaves it open.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Gives you a language for "how confident should I be in a negative result?"
2. Directly informs how many patients a trial needs before it even starts
3. Explains why some "negative" trials get revisited by bigger ones later

**Examiner traps:**
1. Saying an underpowered "negative" trial proves no effect — it proves nothing, either way
2. Forgetting that power is calculated *for a specific effect size* — a trial can be well powered for a large effect and badly powered for a small one
3. Confusing $\alpha$ (your false-alarm rate) with $\beta$ (your missed-alarm rate) — they trade off against each other but are not the same knob
4. Assuming a bigger $n$ always fixes power — recruitment shortfalls, dropout, and crossover all erode the power you calculated on paper

## 6. Theory Exam Summary Box
> 1. Type I ($\alpha$) = false alarm; Type II ($\beta$) = missed alarm; Power = $1-\beta$
> 2. An underpowered "negative" trial means "inconclusive," never "proven no effect"
> 3. Power depends on effect size, variability, $\alpha$, and sample size — and recruitment shortfalls erode it in practice

---

# Chapter 4: Alpha Spending & Multiplicity

## 1. Definition & Mathematical Core

**Continuing the scenario:** imagine your sedation trial has a safety board checking mortality data every 3 months during enrollment, on top of the final analysis. Every extra look is another roll of the dice for hitting p < 0.05 by chance alone — even if the protocol does nothing. Check often enough, and a false positive becomes almost inevitable. That's the **multiplicity problem**, and **alpha spending** is the fix.

**Step by step:**
1. Test 20 truly null hypotheses, each at $\alpha = 0.05$, and by chance alone you'd expect roughly **1 false positive** among them
2. This total false-positive risk across all your looks/tests is the **family-wise error rate (FWER)**
3. **Bonferroni correction** — divide $\alpha$ by the number of tests (simple, but often overly conservative)
4. **False Discovery Rate (FDR)** — controls the *proportion* of false positives among your significant results, less conservative, common in biomarker/genomic studies with many comparisons
5. **Alpha-spending functions** (e.g., O'Brien-Fleming) — pre-specify exactly how much of your total $\alpha$ "budget" you're allowed to spend at each interim look, so your cumulative false-positive risk across the *whole trial* still equals your target (e.g., 0.05)

## 2. Key Concepts, Principles & Assumptions

O'Brien-Fleming boundaries are deliberately very strict early in a trial and looser near the end — this protects against a false-positive stop after only a handful of events, while still allowing a genuinely large effect to stop the trial early and spare future patients an inferior arm.

**The trap even a well-designed alpha-spending plan doesn't fully solve:** trials stopped early for benefit tend to **overestimate** the true effect size. Random noise plus a strict early boundary means you're more likely to stop exactly when the estimate has randomly swung favorable — a phenomenon sometimes called **truncation bias**. The true effect, if the trial had continued, often regresses toward something smaller.

**Memory hook:** every extra look is another lottery ticket for a false positive — alpha spending is the rule that says how many tickets you're allowed to buy, and when.

## 3. Visual / ASCII Schematic
```
Alpha budget across a monitored trial (O'Brien-Fleming style)

Interim look 1  |  tiny slice of alpha  ---> very hard to stop here
Interim look 2  |  slightly bigger slice
Interim look 3  |  bigger still
Final analysis  |  most of the alpha budget spent here

Total alpha spent across ALL looks combined = 0.05 (not 0.05 per look)
```

## 4. Landmark ICU Clinical Anchor — PROWESS and PROWESS-SHOCK

**The story:** PROWESS, testing drotrecogin alfa (activated protein C) in severe sepsis, stopped early after a preplanned interim analysis crossed its efficacy boundary — with a mortality benefit that led to regulatory approval of the drug.

**The reversal:** a required confirmatory trial, PROWESS-SHOCK, later found **no mortality benefit**, and the drug was withdrawn from the market.

**The lesson:** stopping early for benefit, even under a rigorous, pre-specified alpha-spending rule, doesn't guarantee the effect size you saw is the true effect size. It's a textbook example of why regulators and guideline committees treat early-stopped "positive" trials with real caution until confirmed.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Lets you monitor accumulating safety/efficacy data honestly, without inflating your overall false-positive risk
2. Can stop a trial early to spare patients an inferior treatment, when a real large effect emerges
3. Provides a transparent, pre-specified framework auditors and examiners can check you followed

**Examiner traps:**
1. Testing the same outcome at multiple interim looks without any correction — this silently inflates your true $\alpha$ well above 0.05
2. Treating an early-stopped "positive" result as final truth, rather than as an estimate likely to shrink on confirmation
3. Confusing Bonferroni (conservative, simple) with FDR (less conservative, better for many comparisons) — know when each applies
4. Forgetting that alpha-spending governs *repeated looks at one outcome*, while Bonferroni/FDR govern *multiple different outcomes or subgroups* — they solve related but distinct problems

## 6. Theory Exam Summary Box
> 1. More looks or more tests = more chances for a false positive, unless you correct for it
> 2. Alpha-spending (e.g., O'Brien-Fleming) pre-allocates your false-positive budget across interim looks
> 3. Trials stopped early for benefit tend to overestimate the true effect — confirm before you believe it fully

---

# Chapter 5: Confidence Intervals vs. P-values

## 1. Definition & Mathematical Core

**Closing the loop on the scenario:** your sedation trial found p = 0.03 — 18 vs. 15 ventilator-free days. A p-value alone tells you "probably not chance." It says nothing about how big the true effect might be, or how precisely you've measured it. That's what a **confidence interval (CI)** adds — and at the bedside, it's usually the more useful number.

**What a 95% CI actually means:**
1. **The common (wrong) reading:** "there's a 95% chance the true effect is in this range" — this is a Bayesian-sounding statement a frequentist CI doesn't technically make
2. **The technically correct reading:** if you repeated this trial many times, 95% of the calculated intervals would contain the true effect
3. **The practical reading most clinicians actually use:** a range of effect sizes reasonably compatible with your data, given your model's assumptions

**Why width matters:** a narrow CI means a precise estimate; a wide CI means real uncertainty about the size of the effect — even if both give the exact same p-value.

## 2. Key Concepts, Principles & Assumptions

A CI carries everything a p-value carries, plus more:
1. Whether the CI crosses the "line of no effect" (0 for a difference, 1 for a ratio) tells you the same significance information as the p-value threshold
2. The CI's **width and position** additionally tell you the plausible range of effect sizes — information the p-value alone simply doesn't contain

**Two "non-significant" results are not the same thing:**
- A **wide** CI crossing the line of no effect = *"we don't have enough data to know"* (absence of evidence)
- A **narrow** CI tightly hugging the line of no effect = *"we have enough data to be fairly confident there's truly little difference"* (evidence of absence)

Compare ANDROMEDA-SHOCK (Chapter 1) — non-significant with a **wide** CI, genuinely inconclusive — against the landmark trial below, which is non-significant with a **narrow** CI.

**Memory hook:** the p-value tells you *IF* there's likely a real effect. The CI tells you *HOW BIG* — and how sure you are.

## 3. Visual / ASCII Schematic
```
Effect estimate with 95% CI, relative to the "no effect" line

WIDE CI, crosses line       -->  |------------[----o----]------------|
(inconclusive — could be            no effect line (0 or 1)
 large benefit OR large harm)

NARROW CI, crosses line     -->        |---[--o--]---|
(good evidence of little            no effect line (0 or 1)
 to no real difference)

NARROW CI, does NOT cross   -->             |--[--o--]--|
(good evidence of a real                        no effect line
 effect, precisely estimated)
```

## 4. Landmark ICU Clinical Anchor — TTM Trial

| Metric | Value |
|---|---|
| Comparison | Targeted temperature management, 33°C vs. 36°C after cardiac arrest |
| Mortality, 33°C arm | ~50% |
| Mortality, 36°C arm | ~48% |
| Hazard ratio | 1.06 (95% CI 0.89–1.28) |
| p-value | 0.51 |

**The lesson:** both TTM and ANDROMEDA-SHOCK (Chapter 1) came back "non-significant" — but they mean very different things. ANDROMEDA-SHOCK's wide CI left real uncertainty on the table. TTM's tight CI, clustered right around 1, is genuine evidence that 33°C and 36°C perform similarly — a much stronger, more informative kind of "negative" trial.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Communicates precision, not just a binary "significant/not significant" verdict
2. Lets you distinguish a truly inconclusive trial from one that convincingly shows little difference
3. Directly usable for clinical decision-making — you can ask "does even the CI's edge case matter to my patient?"

**Examiner traps:**
1. Saying "95% chance the true value is in this interval" — the correct frequentist reading is about the *procedure*, not this specific interval
2. Treating every non-significant CI as equally uninformative — width matters enormously (see the schematic above)
3. Reporting a p-value without ever reporting the corresponding CI, or vice versa — examiners expect both, together
4. Ignoring the *clinical* significance of an interval's boundaries, even when statistically it excludes zero/one

## 6. Theory Exam Summary Box
> 1. A CI = a range of effect sizes compatible with your data — richer information than a p-value alone
> 2. A wide non-significant CI ("inconclusive") is not the same as a narrow one hugging no-effect ("genuine evidence of no difference")
> 3. Always report p-value and CI together — never one without the other

---

# Section 1 Synthesis — How to Correctly Read Any ICU Trial Result

**Resolving the running scenario, one last time.** Your sedation trial: p = 0.03, ventilator-free days 18 vs. 15, and let's say a 95% CI for the difference of **0.5 to 5.5 days.**

**Walk through the checklist:**
1. **Was the primary outcome pre-specified, and was this your only planned look?** Yes → the p-value and CI can be read at face value (Chapters 1 & 4)
2. **What actually produced that p-value?** The gap between the two averages, scaled by the SE — meaning your sample size directly shaped how easily you could detect this difference (Chapter 2)
3. **Could this be a Type I error?** Possible, but at $\alpha = 0.05$, that's a controlled 5% risk you accepted going in (Chapter 3)
4. **If it had come back non-significant, could it have been a Type II error?** Worth asking whether the trial was even powered to detect a realistic effect size (Chapter 3)
5. **What does the CI actually say?** The true benefit is plausibly anywhere from 0.5 to 5.5 extra ventilator-free days (Chapter 5)
6. **The final, clinical question the statistics can't answer for you:** even at the CI's lower edge — half a day — does that matter to your patients? That judgment is yours, not the p-value's.

```
        READ THE P-VALUE
              |
              v
        READ THE CI ALONGSIDE IT
              |
              v
   Was this pre-specified & the only look?
       | yes                  | no
       v                       v
  Trust the numbers      Treat as exploratory —
       |                 confirm before acting
       v
  Ask: does the CI's WORST-CASE bound
  still matter clinically?
       |
       v
   THAT is your answer — not the p-value alone
```

---

*Continue to Section 2: Tests of Significance & Variable Modeling.*
