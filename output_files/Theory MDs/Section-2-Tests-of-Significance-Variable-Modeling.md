# SECTION 2: TESTS OF SIGNIFICANCE & VARIABLE MODELING
### Plain-Language Edition — DrNB / DM Critical Care Medicine

---

## Running Scenario (used throughout this section)

You're comparing three strategies for starting **renal replacement therapy (RRT)** in ICU patients with severe acute kidney injury: **early, standard, and delayed initiation** — 60 patients per arm. You're tracking baseline characteristics, ICU length of stay, serum creatinine before and after starting RRT, whether patients end up needing long-term dialysis, and 90-day survival.

Every chapter below picks up a different piece of this same trial.

---

# Chapter 6: Tests of Significance — Choosing the Right One

## 1. Definition & Mathematical Core

**Before you calculate anything, answer 3 questions about the variable you're testing:**
1. Is the outcome **continuous** (creatinine, ICU length of stay) or **categorical** (long-term dialysis: yes/no)?
2. Are you comparing **independent groups** (different patients in each arm) or **paired/repeated measures** (the same patient's creatinine before vs. after RRT)?
3. If continuous — is it **roughly normally distributed**, or **skewed**?

That's it. These three questions ARE the test-selection algorithm. Every test in this section is just the answer to a specific combination of these three.

## 2. Key Concepts, Principles & Assumptions

**The lookup table you'll use for the rest of this section:**

| Outcome type | Groups | Distribution | Test |
|---|---|---|---|
| Continuous | 2 independent | Normal | Unpaired t-test |
| Continuous | 2 independent | Skewed | Mann-Whitney U |
| Continuous | Paired (same patients) | Normal | Paired t-test |
| Continuous | Paired | Skewed | Wilcoxon signed-rank |
| Continuous | 3+ independent | Normal | ANOVA |
| Continuous | 3+ independent | Skewed | Kruskal-Wallis |
| Categorical | 2+ independent | — | Chi-square (or Fisher's exact) |
| Continuous-continuous | — | Normal / Skewed | Pearson / Spearman correlation |

**The most common real-world error:** treating an ordinal score — a 0–4 pain scale, individual APACHE II components — as if it were continuous and normal. It usually isn't, and it usually needs non-parametric handling.

**Memory hook:** *Type, Pairing, Shape — in that order.*

## 3. Visual / ASCII Schematic
```
                    What is the outcome?
                 /                        \
          CATEGORICAL                  CONTINUOUS
              |                              |
       Chi-square /                   Paired or independent?
       Fisher's exact                  /                  \
                              INDEPENDENT              PAIRED
                                  |                        |
                          Normal?  Yes -> t-test    Normal? Yes -> paired t-test
                          No -> Mann-Whitney U       No -> Wilcoxon signed-rank
                                  |
                          3+ groups?
                          Yes, normal -> ANOVA
                          Yes, skewed -> Kruskal-Wallis
```

## 4. Landmark ICU Clinical Anchor — SAFE Trial

**The setup:** the SAFE trial (saline vs. 4% albumin for fluid resuscitation, ~7,000 ICU patients) had a baseline characteristics table mixing every variable type you'll meet at the bedside.

| Variable | Type | Summarized as |
|---|---|---|
| Age | Continuous, roughly normal | Mean ± SD, compared with t-test-type logic |
| APACHE II score | Continuous, skewed | Median (IQR), compared with rank-based methods |
| Sex, admission diagnosis category | Categorical | Proportions, compared with chi-square |

**The lesson:** a single trial's baseline table routinely needs 3 different statistical approaches side by side, purely based on each variable's type and shape — exactly the algorithm from Section 2 above.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. A simple 3-question algorithm covers almost every test you'll be asked about at the table
2. Forces you to actually look at your data's distribution before choosing a test, rather than defaulting to "the one I remember"
3. Prevents the single most common statistical error in ICU papers: mismatched test and data type

**Examiner traps:**
1. Assuming every continuous ICU variable (LOS, lactate, ventilator-free days) is normally distributed — most are skewed
2. Applying a t-test/ANOVA to an ordinal score without checking its distribution first
3. Forgetting that "paired" isn't just "before and after" — matched-pair designs also count
4. Picking chi-square automatically for categorical data without checking expected cell counts (→ Chapter 9)

## 6. Theory Exam Summary Box
> 1. Every test choice reduces to 3 questions: outcome type, paired or not, normal or skewed
> 2. Continuous ICU variables are skewed far more often than trainees assume — check before choosing
> 3. A mismatched test is the single most common statistical error you'll be asked to spot at the table

---

# Chapter 7: Student's t-test (Paired & Unpaired) and ANOVA

## 1. Definition & Mathematical Core

**Comparing mean ICU length of stay, early vs. standard RRT (2 groups, unpaired):**
$$t = \frac{\bar{x}_1 - \bar{x}_2}{SE(\bar{x}_1 - \bar{x}_2)}$$
1. $\bar{x}_1, \bar{x}_2$ = the mean LOS in each arm
2. The denominator is built from both groups' variability and sample sizes (same SE logic as Chapter 2, just for a difference of two means)

**Comparing the same patient's creatinine before vs. after starting RRT (paired):**
$$t = \frac{\bar{d}}{SE(\bar{d})}$$
1. $\bar{d}$ = the mean of each patient's individual before/after **difference**
2. Pairing removes patient-to-patient variability from the comparison entirely — you're only asking "did creatinine change within each patient," which is a more powerful, more precise question

**Extending to all 3 arms at once (ANOVA):**
$$F = \frac{\text{variance between the 3 arms}}{\text{variance within each arm}}$$
A large F means the arms differ from each other by more than patients within an arm naturally differ from one another.

## 2. Key Concepts, Principles & Assumptions

**Why not just run 3 separate t-tests** (early vs. standard, standard vs. delayed, early vs. delayed)? Each test carries its own 5% false-positive risk — run three, and your true chance of at least one false "significant" finding climbs well above 5% (the multiplicity problem from Chapter 4). ANOVA tests all 3 arms together under one controlled 5% risk, then — only if the overall F-test is significant — you run a **post-hoc test** (e.g., Tukey's) to find out which specific pair actually differs.

**Assumptions worth checking:**
1. Roughly normal distribution in each group
2. Roughly equal variance across groups (if not, use Welch's correction)
3. Independent observations — one patient's data point doesn't influence another's

**Memory hook:** *T compares two. F (ANOVA) compares three-or-more, then hands off to a post-hoc test to find the actual culprit pair.*

## 3. Visual / ASCII Schematic
```
UNPAIRED t-test:
  Early arm:    mean_1 -----|
                             }---> compare means directly
  Standard arm: mean_2 -----|

PAIRED t-test:
  Patient 1: before ---> after   (compare the CHANGE, patient-by-patient)
  Patient 2: before ---> after
  Patient 3: before ---> after
                |
                v
        mean of all individual changes

ANOVA (3 arms):
  Early:     |---within-arm spread---|
  Standard:      |---within-arm spread---|
  Delayed:            |---within-arm spread---|
                |
        F = spread BETWEEN arms / spread WITHIN arms
```

## 4. Landmark ICU Clinical Anchor — ProCESS Trial

**The design:** ProCESS randomized septic shock patients to **3 arms** — protocolized early goal-directed therapy, protocolized standard therapy, and usual care — roughly 450 patients per arm.

**The lesson:** whenever a trial like this compares a continuous outcome (organ-dysfunction score, resource use, length of stay) across all three arms at once, this is exactly the setting that calls for ANOVA rather than three separate pairwise t-tests — the same 3-arm structure as your RRT-timing scenario above.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Pairing (paired t-test) dramatically increases power by removing patient-to-patient noise from the comparison
2. ANOVA lets you compare 3+ groups honestly, under one controlled false-positive risk
3. Well understood, widely reported, easy to communicate to a clinical audience

**Examiner traps:**
1. Running multiple unpaired t-tests instead of ANOVA for a 3+ arm trial — this is a classic "spot the flaw" question
2. Using an unpaired test on paired data (or vice versa) — this changes both the answer and the power
3. Reporting a significant ANOVA F-test without a post-hoc test — a significant F only tells you *some* arm differs, not *which*
4. Applying a t-test/ANOVA to visibly skewed ICU data instead of checking distribution first (→ Chapter 8)

## 6. Theory Exam Summary Box
> 1. Unpaired t-test = 2 independent groups; paired t-test = same patients, before vs. after
> 2. ANOVA extends this to 3+ groups under one controlled false-positive risk — not three separate t-tests
> 3. A significant ANOVA needs a post-hoc test to identify which specific pair of arms actually differs

---

# Chapter 8: Non-Parametric Alternatives

## 1. Definition & Mathematical Core

**The problem:** ICU length of stay is almost never a nice bell curve — most patients leave within a week, a few stay for months. That long right tail breaks the t-test's normality assumption.

**The fix — rank the data instead of averaging it:**
1. **Mann-Whitney U** (2 independent groups, e.g., early vs. standard arm LOS): pool every patient's LOS, rank them all from lowest to highest, then compare the *sum of ranks* between the two arms rather than comparing raw means
2. **Wilcoxon signed-rank** (paired data, e.g., each patient's before/after creatinine change): ranks the *size* of each patient's change, ignoring the sign at first, then checks whether positive or negative changes dominate the top ranks
3. **Kruskal-Wallis** (3+ independent groups, e.g., all 3 RRT-timing arms): the rank-based extension of ANOVA — compares rank sums across all arms at once

## 2. Key Concepts, Principles & Assumptions

These tests compare **medians and rank distributions**, not means — which makes them far more robust to outliers and skew. The trade-off: if your data genuinely *is* normally distributed, a non-parametric test is slightly less powerful than its parametric counterpart (it's "throwing away" some information by converting values to ranks).

**A reporting rule that follows directly from this:** once you've used a non-parametric test, report **median (IQR)** — not mean ± SD. Reporting a mean for skewed ICU length-of-stay data is a subtle but common examiner trap, because the mean gets dragged upward by the few very long stays and no longer represents a "typical" patient.

**Memory hook:** *Normal data → compare means. Skewed data → compare ranks, and report medians to match.*

## 3. Visual / ASCII Schematic
```
Skewed ICU length-of-stay distribution (typical, not exceptional):

Frequency
   |  ##
   |  ####
   |  ######
   |  ########_____                    (long right tail —
   |  #####################_______      a few very long stays)
   +----------------------------------> LOS (days)
      most patients here          few outliers here

Mean gets pulled toward the tail. Median does not.
--> report median (IQR); use rank-based tests, not the t-test/ANOVA.
```

## 4. Landmark ICU Clinical Anchor — ARDSnet ARMA Trial

**The trial:** low tidal volume (6 mL/kg) vs. traditional tidal volume (12 mL/kg) ventilation in ARDS.

**The lesson:** ventilator-free days (VFDs) — a routine ICU trial outcome — are classically analyzed with non-parametric methods. Why? Any patient who dies is conventionally assigned 0 VFDs, creating a pile-up of zeros at the floor of the distribution alongside a spread of survivors' values. That's about as far from a normal bell curve as an ICU outcome gets, and it's exactly the kind of variable this chapter is built for.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Make no assumption about the shape of the underlying distribution
2. Robust to outliers — one extreme 200-day ICU stay won't distort a rank-based test the way it would a mean
3. Well suited to the zero-inflated, floor/ceiling-effect outcomes common in critical care (VFDs, days alive and free of organ support)

**Examiner traps:**
1. Assuming non-parametric tests are only a "backup" for small samples — they're the *correct* choice whenever the distribution is skewed, regardless of sample size
2. Reporting mean ± SD alongside a Mann-Whitney/Kruskal-Wallis result — mismatched summary statistic and test
3. Forgetting that Wilcoxon signed-rank needs paired data — using it on two independent groups is a different error in the opposite direction (that's Mann-Whitney's job)
4. Over-interpreting a "median difference" as a magnitude you can act on clinically without also looking at the full distribution shape

## 6. Theory Exam Summary Box
> 1. Skewed data → Mann-Whitney U (2 groups), Wilcoxon signed-rank (paired), Kruskal-Wallis (3+ groups)
> 2. These compare ranks/medians, not means — robust to outliers and skew, slightly less powerful if data is actually normal
> 3. Always report median (IQR) alongside a non-parametric test result, never mean ± SD

---

# Chapter 9: Chi-Square Test & Fisher's Exact Test

## 1. Definition & Mathematical Core

**The question:** does the proportion of patients needing long-term dialysis differ across your 3 RRT-timing arms?

**Step by step:**
1. Build a contingency table — rows for RRT-timing arm, columns for dialysis-dependent (yes/no)
2. Calculate the **expected** count in each cell, if there were truly no association between arm and outcome
3. Compare expected counts to your **observed** counts:
$$\chi^2 = \sum \frac{(O - E)^2}{E}$$
4. Degrees of freedom = (rows − 1) × (columns − 1)
5. A large $\chi^2$ (relative to its degrees of freedom) → the arms differ in their dialysis-dependence rates by more than chance would explain

## 2. Key Concepts, Principles & Assumptions

**The expected-frequency rule that trips people up at the table:** chi-square's math starts to misbehave when any **expected** cell count drops below 5 — typically when your outcome is rare, or a subgroup is small. In that situation, switch to **Fisher's exact test**, which calculates the exact probability of your observed table directly, without relying on the large-sample chi-square approximation.

**Memory hook:** *Cell count under 5 anywhere in the table? Chi-square is off duty — call Fisher's exact.*

## 3. Visual / ASCII Schematic
```
                Long-term dialysis: YES   |   NO
Early RRT              8 (obs) / 6.5 (exp)| 52
Standard RRT            6 (obs) / 6.5 (exp)| 54
Delayed RRT              6 (obs) / 6.5 (exp)| 54
                        --------------------------
                chi-square = sum of (O-E)^2/E across all 6 cells
                df = (3 arms - 1) x (2 outcomes - 1) = 2

If ANY expected cell < 5  --->  use Fisher's exact instead
```

## 4. Landmark ICU Clinical Anchor — SOAP II Trial

**The comparison:** dopamine vs. norepinephrine as the first-line vasopressor in shock.

**The finding:** overall 28-day mortality didn't differ significantly between the two drugs — but arrhythmic events were substantially more common with dopamine, a categorical safety outcome compared with a chi-square-type approach across a large sample.

**The lesson:** a trial can be statistically "negative" on its primary mortality outcome while a categorical safety signal — tested the same basic way — still meaningfully changes which drug you reach for first.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Simple, transparent, and works for any number of categories in either direction of the table
2. Directly answers "is there an association between group and a categorical outcome"
3. Fisher's exact gives you an honest answer even with small or rare-event subgroups

**Examiner traps:**
1. Using standard chi-square when an expected cell count is under 5 — inflates the false-positive risk
2. Confusing a significant chi-square with a *large* or clinically important association — always report the actual proportions and, ideally, an effect measure (Chapter 27) alongside it
3. Applying chi-square to paired/matched categorical data — that needs McNemar's test instead, a different tool for a different design
4. Reading a non-significant chi-square as "no association," without asking whether the subgroup was simply too small to detect one (Chapter 3's Type II error, reappearing here)

## 6. Theory Exam Summary Box
> 1. Chi-square compares observed vs. expected counts across categories: $\sum (O-E)^2/E$
> 2. Any expected cell count under 5 → switch to Fisher's exact test
> 3. A "negative" primary outcome doesn't mean every categorical finding in the same trial is unimportant

---

# Chapter 10: Correlation Coefficient

## 1. Definition & Mathematical Core

**The question:** does baseline serum creatinine correlate with how quickly clinicians actually started RRT?

**Two tools, two situations:**
1. **Pearson correlation ($r$)** — measures the strength of a **straight-line** relationship between two roughly normal continuous variables
2. **Spearman rank correlation ($\rho$)** — measures the strength of a **monotonic** relationship (consistently increasing or decreasing, not necessarily a straight line), using ranks instead of raw values — far more robust to outliers and skew

Both range from −1 (perfect inverse relationship) to +1 (perfect direct relationship), with 0 meaning no linear/monotonic relationship at all.

## 2. Key Concepts, Principles & Assumptions

**Correlation is not causation** — the oldest warning in the book, and still the one examiners return to most, because it's so easy to forget in the middle of a confident-sounding presentation.

**A correlation coefficient alone can also mislead you in quieter ways:**
1. A modest-looking $r$ can still hide a real relationship if it's non-linear — Pearson specifically looks for a *straight line*, and will report a weak correlation even for a strong curved relationship that Spearman would catch
2. Restricting the range of one variable (e.g., only studying patients within a narrow creatinine band) artificially shrinks the apparent correlation
3. A statistically significant correlation with a small $r$ (say, 0.15) may be real, but is rarely strong enough to guide an individual bedside decision

**Memory hook:** *Straight line → Pearson. Any consistent trend, ranked → Spearman. Neither one proves cause.*

## 3. Visual / ASCII Schematic
```
Strong Pearson r (~0.9):        Weak/no correlation (~0.05):
   .    .                         .      .   .
      .    .                    .    .     .
   .     .                        .    .  .
  .    .                        .   .    .
 .   .                             .   .

Non-linear pattern, LOW Pearson r, HIGH Spearman rho:
   .                    .
      .              .
         .        .
            .  .
        (curved but perfectly consistent trend --
         Pearson underestimates this, Spearman catches it)
```

## 4. Landmark ICU Clinical Anchor — Marik's CVP Meta-Analysis

**The question that mattered clinically:** does central venous pressure (CVP) predict whether a patient will respond to a fluid bolus?

**The finding:** the pooled correlation between CVP and fluid responsiveness across the analyzed studies was weak — a correlation coefficient on the order of **0.2**, far too low to guide a real bedside decision.

**The lesson:** this single weak correlation number, quietly reported in a meta-analysis, is a large part of why CVP-targeted fluid management fell out of favor in modern ICU practice. A correlation coefficient isn't just an abstract statistic here — it directly changed how millions of ICU patients are managed.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. A single number that quickly summarizes the strength and direction of a relationship between two continuous variables
2. Spearman's robustness to outliers makes it a safe default for messy real-world ICU data
3. Can flag relationships worth exploring further with regression (Chapter 11)

**Examiner traps:**
1. Saying correlation proves causation — always the first thing an examiner will probe
2. Reporting Pearson's $r$ on visibly skewed or outlier-heavy data without checking whether Spearman would be more honest
3. Treating a statistically significant correlation as automatically clinically useful — check the actual $r$ value and the scatter, not just the p-value
4. Forgetting that a low Pearson $r$ doesn't rule out a strong non-linear relationship

## 6. Theory Exam Summary Box
> 1. Pearson $r$ = strength of a straight-line relationship; Spearman $\rho$ = strength of any consistent (monotonic) trend, via ranks
> 2. Correlation never proves causation — say this out loud at the table before the examiner has to ask
> 3. A weak correlation can still be clinically decisive — CVP's weak link to fluid responsiveness changed real-world practice

---

# Chapter 11: Regression Analysis

## 1. Definition & Mathematical Core

**Two questions, two kinds of regression:**

1. **Linear regression** — predicting a **continuous** outcome (ICU length of stay) from RRT timing plus other predictors:
$$Y = \beta_0 + \beta_1 X_1 + \beta_2 X_2 + \dots + \varepsilon$$
Each $\beta$ tells you how much $Y$ (LOS) changes for a one-unit change in that predictor, holding the others constant.

2. **Logistic regression** — predicting a **binary** outcome (90-day mortality: yes/no) from the same kind of predictors:
$$\log\left(\frac{p}{1-p}\right) = \beta_0 + \beta_1 X_1 + \beta_2 X_2 + \dots$$
Here, each $\beta$ (exponentiated) gives you an **odds ratio** — how the odds of the outcome change per unit of the predictor.

## 2. Key Concepts, Principles & Assumptions

Think of regression as **correlation's more capable sibling**: instead of looking at two variables in isolation, it lets you hold several predictors in the model at once and ask "what's the independent contribution of RRT timing, once I've accounted for age and severity of illness?"

**The trap that costs the most marks:** an odds ratio is **not** the same as a relative risk. They're numerically close when the outcome is rare, but diverge substantially as the outcome becomes common — mortality in severe AKI is common enough that this gap can matter. Always check whether the paper reports OR or RR, and don't casually swap the words in your answer.

**Memory hook:** *Continuous outcome → linear regression, plain coefficients. Binary outcome → logistic regression, odds ratios — and OR ≠ RR.*

## 3. Visual / ASCII Schematic
```
LINEAR REGRESSION (continuous outcome):
LOS (days)
   |            .   .
   |         .    /----- fitted line: LOS = b0 + b1(RRT timing) + b2(age)...
   |      .    /
   |   .    /
   +----------------------------------> predictor (e.g., age)

LOGISTIC REGRESSION (binary outcome):
P(death)
  1 |                    _______
    |                 /
    |              /
    |          /
  0 |______/
    +----------------------------------> predictor
       (S-shaped curve, not a straight line --
        output is a PROBABILITY, coefficients give ODDS RATIOS)
```

## 4. Landmark ICU Clinical Anchor — SMART Trial

**The comparison:** balanced crystalloids (e.g., lactated Ringer's) vs. saline for ICU fluid resuscitation, over 15,000 patients.

**The finding:** balanced crystalloids were associated with a lower rate of major adverse kidney events within 30 days (a composite of death, new RRT, or persistent renal dysfunction) than saline, with an odds ratio around **0.90**, from a regression model adjusted for site.

**The lesson:** this is regression doing exactly the job described above — taking a real-world, multi-site, imperfectly balanced comparison and extracting an adjusted estimate of crystalloid choice's independent association with kidney outcomes.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Lets you estimate one predictor's effect while accounting for several others simultaneously
2. Extends naturally to almost any outcome type (linear for continuous, logistic for binary, and further variants for time-to-event, Chapter 30)
3. Coefficients translate directly into clinically interpretable numbers — a slope, or an odds ratio

**Examiner traps:**
1. Quoting an odds ratio as if it were a relative risk — state clearly which one you mean
2. Building a regression model with more predictors than your data can support (a classic overfitting trap — more on this in Chapter 21, sample size)
3. Assuming a significant regression coefficient proves a causal, bedside-actionable relationship, rather than an adjusted association
4. Forgetting to check the model's underlying assumptions (linearity for linear regression; no perfect separation for logistic regression)

## 6. Theory Exam Summary Box
> 1. Linear regression → continuous outcomes, plain coefficients; logistic regression → binary outcomes, odds ratios
> 2. Regression lets you estimate one predictor's independent contribution while adjusting for others
> 3. Odds ratio ≠ relative risk — the gap widens as the outcome becomes more common

---

# Chapter 12: Univariate vs. Multivariate Analysis

## 1. Definition & Mathematical Core

**Univariate analysis:** look at RRT timing and mortality alone, two variables, nothing else in the model.

**Multivariate analysis:** add covariates — severity of illness, age, comorbidity burden — into the same regression equation, so each predictor's coefficient represents its contribution **after accounting for the others**:
$$\log\left(\frac{p}{1-p}\right) = \beta_0 + \beta_1(\text{RRT timing}) + \beta_2(\text{severity score}) + \beta_3(\text{age}) + \dots$$

## 2. Key Concepts, Principles & Assumptions

**The scenario that makes this chapter matter:** in real ICU practice, sicker patients often get RRT started earlier — not because early RRT is being tested in a clean randomized trial, but because clinicians respond to how sick the patient already looks. Left unadjusted, this creates **confounding by indication**: your univariate comparison might make early RRT look *harmful*, purely because the patients who received it were already the sickest.

**What adjustment does:** a well-built multivariate model can reveal that the raw univariate association was driven almost entirely by baseline severity — once you adjust for it, the timing effect shrinks, disappears, or sometimes even reverses direction.

**A related trap: collinearity.** If two of your predictors are highly correlated with each other (say, two overlapping severity scores), the model can't cleanly separate their individual contributions — coefficients become unstable and hard to interpret, even though the model's overall predictions may still be fine.

**Memory hook:** *Univariate shows you the raw signal. Multivariate tells you whether that signal survives once you stop letting a confounder do the talking.*

## 3. Visual / ASCII Schematic
```
        Baseline severity of illness
              /              \
             v                v
    Early RRT initiation --- ? --- Mortality
      (the "exposure")            (the "outcome")

Severity influences BOTH whether a patient gets early RRT
AND their risk of dying -- that's a confounder.

Univariate:  Early RRT ------------------> Mortality   (biased)
Multivariate: Early RRT --[adjusted for severity]--> Mortality  (cleaner)
```

## 4. Landmark ICU Clinical Anchor — Amato's Driving Pressure Analysis

**The setup:** an individual-patient-data analysis pooling over 3,500 ARDS patients across 9 randomized trials, examining which ventilation variable most strongly predicted survival.

**The univariate-looking picture:** tidal volume and PEEP each show some relationship with outcome on their own.

**The multivariate/mediation finding:** once modeled together, **driving pressure** (tidal volume adjusted for lung compliance) emerged as the ventilation variable most strongly and independently associated with survival — with tidal volume and PEEP's apparent individual effects substantially explained by their relationship to driving pressure.

**The lesson:** this is the textbook demonstration of why the "obvious" univariate predictor isn't always the one that survives proper multivariate modeling.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Multivariate models can unmask confounding that a simple two-variable comparison would miss entirely
2. Lets you ask "independent of X, does Y still matter?" — often the actual clinical question
3. Can reveal which of several correlated variables is the more likely true driver of an outcome

**Examiner traps:**
1. Reporting only the univariate result from an observational study without acknowledging likely confounding by indication
2. Adjusting for so many covariates that the model is overfit relative to the sample size (rule of thumb: roughly 10 outcome events per predictor for logistic regression)
3. Missing collinearity between predictors, leading to unstable, hard-to-trust coefficients
4. Treating a multivariate "independent association" as proof of causation — it reduces confounding, it doesn't eliminate the fundamental limits of observational data

## 6. Theory Exam Summary Box
> 1. Univariate = one predictor alone; multivariate = adjusted for other predictors simultaneously
> 2. Confounding by indication is the single most common reason a univariate ICU finding reverses on adjustment
> 3. Collinear predictors destabilize coefficients even when the model's overall fit still looks fine

---

# Chapter 13: Missing Data Handling

## 1. Definition & Mathematical Core

**The problem:** a handful of your 180 patients are lost to 90-day follow-up — their vital status is simply unknown.

**Two broad approaches:**
1. **Complete-case analysis** — analyze only the patients with complete data, dropping the rest
2. **Multiple imputation** — use the patterns in your *observed* data to generate several plausible values for each missing data point, creating multiple "completed" datasets, analyzing each one separately, then mathematically pooling the results into one final estimate

## 2. Key Concepts, Principles & Assumptions

**The assumption that decides which approach is honest:**
1. **Missing Completely at Random (MCAR)** — the missingness has nothing to do with any variable, observed or not (rare in practice)
2. **Missing at Random (MAR)** — the missingness can be explained by *other observed variables* (e.g., patients transferred to a smaller hospital, itself recorded, were harder to follow up) — multiple imputation works well here
3. **Missing Not at Random (MNAR)** — the missingness depends on the unobserved value itself (e.g., the sickest patients are precisely the ones lost to follow-up, and their unknown vital status is *why* they're missing) — neither complete-case analysis nor standard imputation can fully fix this

**Why complete-case analysis can quietly mislead:** if sicker patients are more likely to be lost to follow-up, simply dropping them doesn't just shrink your sample — it systematically removes exactly the patients whose outcomes would look worse, biasing your result toward an optimistic conclusion.

**Memory hook:** *Complete-case analysis doesn't just lose power — if missingness isn't random, it loses honesty too.*

## 3. Visual / ASCII Schematic
```
Original dataset (some cells missing vital status)
        |
        v
  Multiple Imputation
        |
   -----+-----+-----
   |    |    |     |
 Copy1 Copy2 Copy3 Copy4    (each missing value filled in
   |    |    |     |         with a plausible, slightly
   v    v    v     v         different estimate)
 Analyze each copy separately
        |
        v
   POOL the results into one final estimate + adjusted CI
        |
        v
Compare against complete-case analysis as a sensitivity check
```

## 4. Landmark ICU Clinical Anchor — CLASSIC Trial

**The setup:** a large multi-center trial comparing conservative vs. liberal IV fluid strategies in septic shock, with 90-day mortality as the primary outcome.

**The practical challenge:** in a pragmatic, multi-national ICU trial like this, a small proportion of patients are typically lost to follow-up by day 90 despite best efforts. The standard, defensible approach is multiple imputation under a MAR assumption, with a complete-case analysis reported alongside as a sensitivity check to confirm the conclusions don't depend on how the missing data was handled.

**The lesson:** you don't need to memorize an exact number of missing patients for a trial like this — what an examiner wants to hear is that you understand *why* imputation was the appropriate choice and *how* it should be checked against a simpler complete-case analysis.

## 5. Advantages vs. Clinical Limitations / Examiner Pitfalls

**Strengths:**
1. Multiple imputation preserves your full sample size and statistical power, rather than discarding incomplete cases
2. Uses genuine information from observed variables to make principled estimates, not guesses
3. Reporting both complete-case and imputed results as a sensitivity analysis is a transparent, examiner-approved habit

**Examiner traps:**
1. Assuming missing data is automatically MCAR just because it's inconvenient to think about the alternative
2. Treating multiple imputation as a way to "invent" data that supports your hypothesis — it should be a neutral, pre-specified method, not chosen after seeing which approach gives a better result
3. Using complete-case analysis by default without stating the MCAR/MAR assumption it silently relies on
4. Forgetting that no statistical method — imputation included — can fully fix genuinely MNAR missingness

## 6. Theory Exam Summary Box
> 1. Complete-case analysis is only unbiased if data is missing completely at random — rarely a safe assumption
> 2. Multiple imputation fills gaps using observed-data patterns, analyzes several completed datasets, then pools the results
> 3. Report complete-case and imputed results together as a sensitivity check, not one or the other alone

---

# Section 2 Synthesis — "Which Test Should I Use?"

**Resolving the running scenario, end to end.** You now have every tool needed to analyze the full RRT-timing trial:

1. **Baseline table** (age, APACHE II, sex, comorbidities) → mixed tests by variable type (Chapter 6)
2. **Mean ICU length of stay, early vs. standard** → unpaired t-test, *if* roughly normal (Chapter 7) — but LOS is usually skewed, so in practice → **Mann-Whitney U** (Chapter 8)
3. **Creatinine before vs. after RRT, same patients** → paired t-test if normal, **Wilcoxon signed-rank** if skewed (Chapters 7–8)
4. **All 3 arms compared on LOS at once** → ANOVA if normal, **Kruskal-Wallis** if skewed (Chapters 7–8)
5. **Proportion needing long-term dialysis, across arms** → **chi-square**, or **Fisher's exact** if any expected cell count < 5 (Chapter 9)
6. **Baseline creatinine vs. time-to-RRT** → Pearson or **Spearman correlation** (Chapter 10)
7. **Predicting mortality from RRT timing, adjusted for severity** → **logistic regression** (Chapter 11), ideally **multivariate** rather than univariate, to rule out confounding by indication (Chapter 12)
8. **Patients lost to 90-day follow-up** → **multiple imputation**, with complete-case analysis reported as a sensitivity check (Chapter 13)

```
        WHICH TEST OF SIGNIFICANCE?
                    |
        Continuous or Categorical outcome?
         /                          \
  CATEGORICAL                  CONTINUOUS
      |                              |
Chi-square/Fisher's        Paired or independent, Normal or skewed?
                                     |
              -----------------------------------------------
              |            |             |               |
        Independent,  Independent,   Paired,        Paired,
        Normal        Skewed         Normal         Skewed
              |            |             |               |
          t-test /    Mann-Whitney  Paired t-test   Wilcoxon
          ANOVA(3+)    Kruskal-      / repeated       signed-rank
                       Wallis(3+)    measures
```

---

*Continue to Section 3: Diagnostic Testing & Probability.*
