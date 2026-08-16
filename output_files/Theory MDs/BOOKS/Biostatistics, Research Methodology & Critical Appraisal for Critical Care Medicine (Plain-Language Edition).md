# Biostatistics, Research Methodology & Critical Appraisal for Critical Care Medicine

## A Comprehensive Guide for DrNB & DM Theory, OSCE, and Table Viva Examinations

---

## TABLE OF CONTENTS

### SECTION 1: HYPOTHESIS TESTING, ERRORS & SIGNIFICANCE
1. P-value: Statistical Definition, Clinical Importance, Threshold Misuse (0.05 Fallacy), Inherent Limitations
2. Z-Score and Standard Error: Calculation, Distribution Properties, Interpretation in Clinical Data
3. Type I (Alpha) and Type II (Beta) Errors: Relationship with Statistical Power (1 − β) and Sample Size
4. Alpha Spending & Multiplicity: Family-Wise Error Rate, Bonferroni Correction, False Discovery Rate (FDR)
5. Confidence Intervals (CI) vs. P-values: Clinical Relevance vs. Statistical Significance, CI Width, Trials Crossing Unity

*Section 1 Recap: Which Test / Which Effect Measure*

### SECTION 2: TESTS OF SIGNIFICANCE & VARIABLE MODELING
6. Tests of Significance: Algorithmic Selection Criteria for Parametric vs. Non-Parametric Tests
7. Student's t-test (Paired & Unpaired) and ANOVA: Indications, Assumptions, ICU Clinical Examples
8. Non-Parametric Alternatives: Mann-Whitney U, Wilcoxon Signed-Rank, Kruskal-Wallis
9. Chi-Square Test: Principle, Degrees of Freedom, Expected Frequency Rules, Fisher's Exact Indications
10. Correlation Coefficient: Pearson vs. Spearman, Linear Associations, Limitations
11. Regression Analysis: Linear vs. Logistic Regression in ICU Severity/Prognostic Scores
12. Univariate vs. Multivariate Analysis: Confounder Adjustment, Collinearity, Model Building
13. Missing Data Handling: Complete-Case Analysis, MAR Assumptions, Multiple Imputation

*Section 2 Recap: Which Test / Which Effect Measure*

### SECTION 3: DIAGNOSTIC TESTING & PROBABILITY
14. Diagnostic Accuracy: Sensitivity, Specificity, PPV, NPV
15. Impact of Disease Prevalence on Predictive Values: Spectrum Bias and Test Utility
16. Likelihood Ratios (LR+, LR−) and Diagnostic Odds Ratio (DOR): Pre- to Post-Test Probability Shifts
17. Bayes' Theorem & Fagan Nomogram: Bedside Critical Care Application
18. ROC Curve: AUROC, Youden's Index, Cutoff Selection

*Section 3 Recap: Which Test / Which Effect Measure*

### SECTION 4: CLINICAL TRIAL DESIGN & EPIDEMIOLOGY
19. RCTs: Core Architecture, Allocation Concealment, Blinding, Run-In Periods
20. Randomization Strategies: Simple, Block, Stratified, Cluster
21. Sample Size Estimation: Determinants and Formulas for Proportions and Continuous Means
22. ITT, Modified ITT, and Per-Protocol Analyses: Strengths and Pitfalls
23. Non-Inferiority and Equivalence Trials: Defining the Margin (Delta), Why Both ITT and PP Are Required
24. Factorial Trials (2×2 Designs): Structure, Efficiency, Interaction Effects
25. Cluster-Randomized and Stepped-Wedge Designs: ICC, Infection-Control Bundle Trials
26. Adaptive Platform Trials: MAMS, Response-Adaptive Randomization, Bayesian Models (REMAP-CAP)

*Section 4 Recap: Which Test / Which Effect Measure*

### SECTION 5: SURVIVAL ANALYSIS, EFFECT SIZES & TIME-TO-EVENT
27. Measures of Association: Risk Ratio, Odds Ratio, Hazard Ratio Compared
28. ARR, RRR, NNT / NNH
29. Kaplan-Meier Survival Analysis: Product-Limit Method, Right-Censoring, Log-Rank Test
30. Cox Proportional Hazards Model: Assumptions, Schoenfeld Residuals, Time-Varying Covariates
31. Competing Risks Analysis: Cumulative Incidence Function vs. Standard Kaplan-Meier
32. Composite Endpoints & Hierarchical Win Ratios: Mortality Competing with Ventilator-Free Days

*Section 5 Recap: Which Test / Which Effect Measure*

### SECTION 6: EVIDENCE SYNTHESIS & SYSTEMATIC APPRAISAL
33. Systematic Reviews & PRISMA: Search Protocols, Screening Pipelines, Quality Scoring
34. Meta-Analysis Mechanics: Fixed- vs. Random-Effects Models, Forest Plot Interpretation
35. Statistical Heterogeneity: Cochran's Q and I²
36. Publication Bias: Funnel Plot Asymmetry, Egger's Regression, Begg's Test
37. Critical Appraisal Pitfalls: Ecological Fallacy, Small-Study Effects, Reverse Causation, Immortal Time Bias
38. Levels of Evidence & GRADE Methodology

*Section 6 Recap: Which Test / Which Effect Measure*

### MASTER VIVA ANNEXURE
A. "Spot the Flaw" Journal Club Checklist (10-Point Rapid Appraisal)
B. Master Decision Trees (ASCII): Which Test of Significance? / Which Effect Measure?
C. 50 High-Yield Rapid-Fire Viva Q&As
D. Glossary of Abbreviations

---
# SECTION 1: HYPOTHESIS TESTING, ERRORS & SIGNIFICANCE

## Chapter 1: P-value—Statistical Definition, Clinical Importance and Threshold Misuse

### 1. Definition & Mathematical Core
A **p-value** tells you how often a result at least this extreme would arise if the null hypothesis (the working assumption of no true treatment effect) were true. For a two-sided test of $H_0$, $p=P_{H_0}(|T|\geq |t_{obs}|)$. Here, $H_0$ is the null hypothesis. $T$ is the random test statistic under $H_0$. $t_{obs}$ is the observed test-statistic value. The p-value is **not** the probability that $H_0$ is true.

Set a significance level (the decision threshold) before the trial. For a pre-specified significance level $\alpha$, reject $H_0$ when $p\leq\alpha$. Here, $\alpha$ is the long-run chance of rejecting a true null hypothesis. This calculation assumes you fixed the statistical model, analysis population, outcome definition, and primary comparison before seeing outcome data.

### 2. Key Concepts, Principles & Assumptions
In this chapter, intensive care unit is abbreviated ICU. The p-value asks one question. “If there were no true treatment effect and the model were correct, how unusual would these data be?” It does not tell you the size of the effect. It does not show clinical benefit, reproducibility, probability of benefit, or trial quality. A p-value near 0.05 is not a biological cliff. Results at 0.049 and 0.051 carry nearly the same evidence. People still too often call one “positive” and the other “negative.”

The common **0.05 fallacy** comes in several forms. $p=0.05$ does not mean a 5% chance that the result is a false positive. $p>0.05$ does not prove equivalence, no benefit, or no harm. A very large trial can give a small p-value for a trivial absolute effect. A clinically important effect can remain statistically uncertain when the confidence interval (CI, the range of effects compatible with the data) is wide. Repeated looks at accumulating mortality data can distort the usual p-value meaning. So can changing outcomes, highlighting selected subgroups, or hiding analyses. You need a pre-specified monitoring or multiplicity plan (a plan for handling many tests).

### 3. Visual / ASCII Schematic
```
Observed ICU trial result
          |
          v
Was the primary hypothesis and analysis pre-specified?
     | yes                              | no / unclear
     v                                  v
Read p-value with its CI          Treat as exploratory;
     |                             multiplicity/selection may dominate
     v
p <= alpha? -------- yes ------> Reject H0; quantify effect and CI
     |
     no
     v
Do NOT say “no effect” --> Ask whether CI excludes important benefit/harm
```

### 4. Landmark ICU Clinical Anchor
In [ANDROMEDA-SHOCK](https://pubmed.ncbi.nlm.nih.gov/30772908/), investigators compared capillary-refill-targeted with lactate-targeted resuscitation in septic shock. The observed 28-day mortality was lower with capillary-refill targeting (34.9% versus 43.4%). The primary comparison had $p=0.06$. Its hazard-ratio confidence interval crossed 1. A hazard ratio compares the rate of an event over time between groups. You should not call the strategies identical. The data fit meaningful benefit, no effect, and small harm. You also should not claim definite mortality benefit from the favourable point estimate. This trial shows why thresholds are fragile. A 0.01 change in p-value does not suddenly alter the clinical plausibility of an 8.5-percentage-point absolute mortality difference.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**
- Gives you a calibrated frequentist decision rule when the null model, sampling plan, and one primary comparison are valid.
- Lets you compare continuous, binary, and time-to-event endpoints on one evidence scale.
- Supports trial monitoring when you build it into a pre-specified alpha-spending framework (a plan that limits false-positive risk across interim looks).

**Clinical limitations / examiner pitfalls**
- Do not translate $p$ as “the probability treatment works” or “the chance result.” You need a Bayesian model (one that combines data with prior assumptions) for that.
- Do not infer clinical importance from statistical significance. Report the absolute risk difference, number needed to treat or harm, and CI.
- Do not call a non-significant superiority result “equivalent.” Equivalence and non-inferiority each need their own margins (the largest acceptable difference) and analyses.
- Do not favour a significant secondary outcome over a non-significant primary outcome without checking multiplicity and the outcome hierarchy.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - $p$ is the probability of data this extreme or more extreme **assuming $H_0$**, not the probability that $H_0$ is true.
> - The 0.05 threshold is a convention; $p=0.06$ is not evidence of no clinically important effect.
> - Interpret every p-value with prespecification, effect size, precision, multiplicity, and clinical consequences.

## Chapter 2: Z-Score and Standard Error—Calculation, Distribution and Clinical Interpretation

### 1. Definition & Mathematical Core
A **z-score** tells you how far a value is from a reference mean (average). It expresses that distance in standard-deviation units. A standard deviation (SD) is the usual spread of individual values around their average. $z=(x-\mu)/\sigma$, where $x$ is the observed value, $\mu$ is the reference population mean, and $\sigma$ is the population standard deviation.

For an estimated mean, the **standard error (SE)** is the uncertainty caused by sampling only some patients. Use the standardized test statistic $Z=(\bar{x}-\mu_0)/SE(\bar{x})$. Here, $\bar{x}$ is the sample mean. $\mu_0$ is the null mean (the mean assumed if there is no true difference). $SE(\bar{x})=s/\sqrt{n}$, with $s$ the sample standard deviation and $n$ the independent sample size.

The central limit theorem says that averages tend to follow a normal distribution (a bell-shaped distribution) in sufficiently large, independent samples. Therefore, $Z$ is approximately standard normal, so $Z\sim N(0,1)$ under $H_0$. Here, H0 is the null hypothesis (the assumption of no real difference). Independent means that one observation does not determine another. A 95% normal-theory confidence interval (CI) is $\hat{\theta}\pm1.96\,SE(\hat{\theta})$, where $\hat{\theta}$ is the estimated parameter and $SE(\hat{\theta})$ is its standard error.

### 2. Key Concepts, Principles & Assumptions
A standard deviation describes **patient-to-patient heterogeneity** (how much individual patients differ). A standard error describes **sampling uncertainty** (how much your estimate would vary across similar samples). Increasing $n$ reduces the standard error roughly with $1/\sqrt{n}$. It does not make critically ill patients less heterogeneous. A large multicentre trial can therefore produce a large z-score for a small mean difference. That difference may still not matter clinically.

For a small sample with an unknown population standard deviation, use the Student $t$ distribution. It has wider tails than the normal distribution because replacing $\sigma$ with $s$ adds uncertainty. Binary outcomes need adequate expected counts before you use normal approximations. For rare events, such as severe hypoglycaemia, exact or model-based methods may be better. A cluster-randomized trial assigns groups, such as hospitals, rather than individual patients. Such clusters can violate simple independence. Repeated measurements, centre effects, and informative death before measurement can do the same. In ventilated patients in an intensive care unit (ICU), the partial-pressure-of-oxygen to inspired-oxygen ratio (PaO2/FiO2) at 72 hours can mislead. Death or liberation from ventilation changes who remains measurable.

### 3. Visual / ASCII Schematic
```
Population outcome distribution (e.g., ICU glucose)
             mean = mu                         SD = sigma
                 |<--------- spread ---------->|
             ________/\________

Sampling distribution of trial mean
             mean = mu                         SE = s/sqrt(n)
                    |<--- narrow --->|
                  ________/\________

Observed difference / SE  --->  Z statistic  --->  normal-tail p-value
```

### 4. Landmark ICU Clinical Anchor
[NICE-SUGAR](https://www.nejm.org/doi/full/10.1056/NEJMoa0810625) randomized 6,104 adults in medical and surgical intensive care units (ICUs). The large sample made the standard errors small enough to identify a modest but clinically important higher 90-day mortality with intensive glucose control. Mortality was 27.5% versus 24.9%, odds ratio 1.14 (95% CI 1.02–1.28; $p=0.02$). An odds ratio compares the odds of an outcome between groups. A z-based p-value alone does not settle practice. The absolute mortality increase, precision, severe-hypoglycaemia signal, biological plausibility, and pragmatic ICU population make this finding clinically persuasive together.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**
- Puts observed values and treatment estimates onto a standard scale. This supports normal-theory tests and confidence intervals.
- Shows clearly why larger independent samples improve precision.
- Helps you interpret laboratory deviations quickly when an appropriate reference distribution exists.

**Clinical limitations / examiner pitfalls**
- Never confuse $SD$ with $SE$. $SD$ describes the spread of patient values. $SE$ describes uncertainty in the estimated mean or effect.
- Do not use a z-test blindly in small samples, sparse binary data, or strongly skewed biomarkers such as lactate. Check the model or transformation first.
- A z-score for one patient is not a diagnosis. Reference range, timing, assay, renal dysfunction, and illness trajectory all matter.
- A larger $n$ narrows the CI. It cannot correct bias from non-random missingness, competing death, or protocol deviations.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - $z=(x-\mu)/\sigma$ standardizes an observation; an effect-test z-score divides the estimated difference by its $SE$.
> - $SE=s/\sqrt n$ falls with sample size, whereas $SD$ reflects biological heterogeneity and does not.
> - Use normal approximations only when distributional and independence assumptions are defensible; otherwise use an appropriate alternative.

## Chapter 3: Type I (Alpha) and Type II (Beta) Errors—Power and Sample Size

### 1. Definition & Mathematical Core
A **Type I error** is a false positive. It happens when you reject a true null hypothesis (the assumption of no real effect). $\alpha=P(\text{reject }H_0\mid H_0\text{ true})$, where $H_0$ is the null hypothesis and $\alpha$ is the pre-specified false-positive probability. A **Type II error** is a false negative. It happens when you do not reject a false null hypothesis. $\beta=P(\text{do not reject }H_0\mid H_1\text{ true})$, where $H_1$ is a specified alternative hypothesis and $\beta$ is the false-negative probability. Statistical power is the chance of detecting a specified real effect. It is $1-\beta$.

For two equal groups comparing proportions, an approximate required sample size per group is
$$
n\approx \frac{\left[z_{1-\alpha/2}\sqrt{2\bar p(1-\bar p)}+z_{1-\beta}\sqrt{p_1(1-p_1)+p_2(1-p_2)}\right]^2}{(p_1-p_2)^2},
$$
where $n$ is sample size per group. $z_q$ is the $q$th standard-normal quantile (a cutoff from the normal distribution). $\bar p=(p_1+p_2)/2$. $p_1$ and $p_2$ are the anticipated event risks in the two groups.

### 2. Key Concepts, Principles & Assumptions
Power is not fixed for a study. It depends on $\alpha$, sample size, allocation ratio, outcome variance, event rate, and planned effect size. The allocation ratio is the number assigned to each group. Outcome variance is the spread of outcome values. It also depends on loss to follow-up, non-adherence, and the analytic method. A standard error (SE) measures sampling uncertainty. A confidence interval (CI) shows the range of effects compatible with the data. With a fixed sample, lowering alpha reduces power. Increasing the sample may restore it. In intensive care unit (ICU) trials, event rates can fall below projections. Changed case mix, earlier source control, or recruitment of less severely ill patients can cause this. Fewer outcome events then leave the trial unable to separate plausible benefit from no effect.

Choose a target difference that is **clinically important and credible**. Do not choose a conveniently large effect. Planning for a 15% absolute mortality reduction is risky if 3–5% would matter and is more plausible. You may then get a falsely reassuring “negative” result. An enormous trial can detect statistically significant but clinically trivial differences. Power calculations cannot fix bias, poor intervention fidelity, cross-over, or an inappropriate endpoint. Intervention fidelity means that the intended treatment was actually delivered. Cross-over means that patients receive the other group’s treatment. An endpoint is the outcome used to judge the intervention.

### 3. Visual / ASCII Schematic
```
Truth                         Trial decision
                         Reject H0          Do not reject H0
H0 true                Type I error          Correct decision
                         probability alpha
H1 true                Correct detection      Type II error
                         probability 1-beta    probability beta

Lower alpha  --->  fewer false positives, but lower power if n is unchanged
Higher n     --->  lower SE, more power for the chosen effect size
```

### 4. Landmark ICU Clinical Anchor
[ADRENAL](https://www.nejm.org/doi/full/10.1056/NEJMoa1705835) planned a large septic-shock trial with 90% power to detect a 5-percentage-point absolute reduction in 90-day mortality. Continuous-infusion hydrocortisone did not reduce the primary mortality outcome versus placebo. Mortality was 27.9% versus 28.8%, odds ratio 0.95, 95% CI 0.82–1.10; $p=0.50$. The large sample and relatively narrow interval make a major mortality benefit less plausible. They do not rule out every smaller benefit or harm. That is the right power-based reading of a neutral primary outcome. Hydrocortisone also improved some non-mortality recovery outcomes.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**
- Makes you specify the outcome, alpha, anticipated control risk, clinically meaningful effect, and acceptable false-negative risk.
- Helps prevent underpowered mortality trials. It also separates precision from statistical significance.
- Supports rational event-driven or adaptive monitoring when you pre-specify and control it. Event-driven means that the trial ends after a target number of events.

**Clinical limitations / examiner pitfalls**
- “No significant difference” does not automatically mean low power. Inspect the CI and the original target effect.
- Post hoc observed power is calculated after seeing the result. It usually restates the p-value and adds little beyond the CI.
- Do not say a trial was powered to show equivalence unless it used an equivalence or non-inferiority margin. That margin defines the largest acceptable loss of efficacy.
- More recruitment cannot correct systematic bias, contamination, outcome misclassification, or inappropriate composite endpoints. A composite endpoint combines several outcomes into one.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - $\alpha$ is false-positive risk; $\beta$ is false-negative risk; power is $1-\beta$ for a specified alternative.
> - Sample size rises as the target effect becomes smaller, event rate falls, alpha becomes stricter, or desired power increases.
> - Interpret a neutral ICU trial through its CI and its planned detectable effect—not by the label “negative.”

## Chapter 4: Alpha Spending and Multiplicity—Family-wise Error, Bonferroni and FDR

### 1. Definition & Mathematical Core
Multiplicity means running more than one statistical test. When $m$ hypotheses are tested, the **family-wise error rate (FWER)** is the chance of at least one false positive in that family of tests. $FWER=P(V\geq1)$, where $V$ is the number of false rejections among the $m$ tests. Under independence with per-test threshold $\alpha_{test}$, $FWER=1-(1-\alpha_{test})^m$. This approaches $m\alpha_{test}$ for small $\alpha_{test}$. Bonferroni control sets $\alpha_{test}=\alpha_{family}/m$, where $\alpha_{family}$ is the desired family-wise threshold.

An interim analysis is a planned check of results before recruitment ends. **Alpha spending** divides a total Type I error budget (false-positive risk) across those checks. $\sum_{k=1}^{K}\alpha_k\leq\alpha$, where $K$ is the number of planned looks and $\alpha_k$ is the amount spent at look $k$. The **false discovery rate (FDR)** is the expected proportion of false discoveries among declared discoveries. $FDR=E[V/R\mid R>0]P(R>0)$, where $R$ is the total number of rejected hypotheses and $E$ is expectation. Unlike FWER, FDR does not target the chance of even one false positive.

### 2. Key Concepts, Principles & Assumptions
In an intensive care unit (ICU) trial, multiplicity can come from outcomes, time points, doses, subgroups, repeated looks, and alternative models. It is not just a problem across separate trials. If you test twenty independent null comparisons at 0.05, chance alone makes at least one apparently significant result likely. Bonferroni is simple and valid even when outcomes are dependent. It can be conservative, especially with correlated outcomes. Holm’s step-down method tests p-values in order and improves power while retaining FWER control. Benjamini–Hochberg FDR procedures help in high-dimensional exploratory work. Examples include biomarker or transcriptomic screening. A q-value is an FDR-adjusted measure used to rank these findings. They do not make any individual discovery certain.

Alpha spending differs from correcting for many endpoints. It controls repeated checks of one primary question during recruitment. Strict early boundaries protect you from claiming benefit after a random early high effect. The final boundary is adjusted in return. A data monitoring committee is an independent group that reviews accumulating trial data. It must follow a pre-specified plan. That plan should state whether benefit, harm, or futility boundaries are binding. A futility boundary marks when more recruitment is unlikely to answer the question.

### 3. Visual / ASCII Schematic
```
One ICU trial, many analyses
   |-- primary 90-d mortality ------------> protected alpha / hierarchy
   |-- 6 secondary outcomes --------------> multiplicity plan required
   |-- 3 shock-type subgroups ------------> interaction tests, exploratory caution
   `-- 4 interim looks -------------------> alpha spending: a1+a2+a3+a4 <= 0.05

Choose error target:
Confirmatory, few outcomes --> FWER (Bonferroni/Holm)
Exploratory, many signals  --> FDR (ranked q-values; validate externally)
```

### 4. Landmark ICU Clinical Anchor
[SOAP II](https://sites.duke.edu/cicu/files/2019/11/SOAP-II-trial.pdf) compared dopamine with norepinephrine in 1,679 patients with shock. Overall 28-day mortality did not differ significantly. Dopamine caused more arrhythmias. The pre-specified cardiogenic-shock subgroup had higher 28-day mortality with dopamine. However, the treatment-by-shock-type interaction was not significant. An interaction is the formal test of whether treatment effects differ between subgroups. The examiner-safe conclusion is that this subgroup signal is clinically concerning and useful for generating a hypothesis. It does not prove that treatment effect differs by shock type. A significant p-value within one subgroup cannot replace a significant interaction. Multiple subgroup comparisons increase false-positive risk.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**
- FWER control protects definitive, guideline-changing claims across a small confirmatory family of hypotheses.
- Alpha spending allows ethical interim monitoring without resetting the 0.05 threshold at every look.
- FDR keeps more signals for broad exploratory biomarker, omics, or hypothesis-generation programmes.

**Clinical limitations / examiner pitfalls**
- Do not apply Bonferroni mechanically to every variable in a coherent primary-outcome model. Define the test family first.
- Do not confuse $FWER$ with FDR. FWER asks about any false positive. FDR asks about the expected proportion among positive findings.
- Do not treat a subgroup p-value as evidence of effect modification. Effect modification means that treatment effect truly differs between subgroups. Test the interaction.
- A lower unadjusted p-value at an interim look may not justify stopping. Use the planned boundary.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Multiplicity inflates Type I error across outcomes, subgroups, models, and repeated looks.
> - Bonferroni uses $\alpha/m$ to control FWER; it controls false positives but may sacrifice power.
> - Alpha spending handles repeated interim looks; FDR is usually better suited to large exploratory signal sets.

## Chapter 5: Confidence Intervals versus P-values—Clinical Relevance, Width and Trials Crossing Unity

### 1. Definition & Mathematical Core
A frequentist 95% **confidence interval (CI)** is a method that captures the true parameter in 95% of intervals across many similar samples. A parameter is the true population value you are trying to estimate. A standard error (SE) measures uncertainty in an estimate from sampling. In a normal approximation, $CI_{95\%}=\hat{\theta}\pm1.96\,SE(\hat{\theta})$, where $\hat{\theta}$ is the estimated effect, $SE(\hat{\theta})$ is its standard error, and 1.96 is the two-sided 97.5th standard-normal quantile.

A risk ratio (RR) compares event risks between groups. An odds ratio (OR) compares outcome odds. A hazard ratio (HR) compares event rates over time. For a relative effect, the null value is **unity**, or no relative difference. $RR=1$, $OR=1$, or $HR=1$, where $RR$ is risk ratio, $OR$ is odds ratio, and $HR$ is hazard ratio. For an absolute risk difference (RD) $RD=p_T-p_C$, the null is $RD=0$, where $p_T$ and $p_C$ are treatment and control event risks. With a matched two-sided test, a 95% CI excluding the null corresponds to $p<0.05$. The CI also shows direction and precision.

### 2. Key Concepts, Principles & Assumptions
The point estimate is your best single estimate under the model. The CI gives the range of values that fit the data and assumptions reasonably well. CI **width** depends on sample size, event count, variability, allocation ratio, and measurement quality. A narrow CI can rule out a clinically important benefit and harm. That gives a persuasive neutral result. A wide CI crossing unity is indeterminate. It can include important benefit and important harm even when its p-value exceeds 0.05.

Use a pre-specified **minimal clinically important difference (MCID)** or decision threshold. The MCID is the smallest effect that would matter to patients or practice. For mortality, the absolute risk difference is often easier to use at the bedside than a relative measure. Baseline risk varies between patient groups. In time-to-event analyses, a single hazard ratio assumes proportional hazards. This means that the relative event rate stays similar over time. A CI may cross unity because there were too few events. It does not show that interventions are equivalent. Intensive care unit is abbreviated ICU in this chapter. Do not read a 95% CI as a “95% probability the true effect lies inside.” That needs a Bayesian prior-and-posterior model.

### 3. Visual / ASCII Schematic
```
Relative-effect forest-plot logic
                 benefit <--- 1.0 (no relative effect) ---> harm
                              |
Trial A:      -----[====*====]-----         CI crosses 1: inconclusive
Trial B:  [===*===]                         CI excludes 1: statistically significant
Trial C:            [---------*---------]  wide CI: imprecise, assess MCID limits

Always add: absolute risk difference + whether CI excludes clinically important benefit/harm
```

### 4. Landmark ICU Clinical Anchor
In [ANDROMEDA-SHOCK](https://pubmed.ncbi.nlm.nih.gov/30772908/), the mortality hazard ratio favoured capillary-refill-targeted resuscitation (0.75). Its 95% CI (0.55–1.02) crossed unity and $p=0.06$. The interval does not meet the usual threshold for statistical significance. It still includes potentially important benefit. It excludes large harm in the direction of the observed effect. This tells you more than calling the result “non-significant.” The absolute risk difference and its CI show uncertainty on both relative and absolute scales.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**
- Shows effect direction, plausible magnitude, and precision. It is usually more clinically useful than p alone.
- Lets you judge whether a trial rules out a benefit or harm large enough to change intensive care unit practice.
- Connects directly to absolute effects, baseline risk, number needed to treat or harm, and MCID.

**Clinical limitations / examiner pitfalls**
- Do not equate a CI crossing 1 with “no difference.” It means that confidence level did not exclude the null.
- Do not infer equivalence from a narrow CI unless it lies wholly within a pre-specified equivalence or non-inferiority margin.
- Do not report only relative effects. Translate them into absolute risk in the relevant ICU population.
- Do not over-interpret precision when model assumptions fail, death causes missing endpoints, or analyses were selectively chosen.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - A 95% CI displays effect size and precision; a two-sided 95% CI excluding the null aligns with $p<0.05$.
> - For RR, OR, and HR the null is 1; for risk difference the null is 0.
> - A CI crossing unity is not proof of no effect—compare its limits with clinically important benefit and harm.

### Section Recap: Which Test / Which Effect Measure
```
Start: What is the inferential question?
|
|-- One pre-specified primary comparison at final analysis
|     |-- Estimate effect + 95% CI first
|     `-- Use p-value versus pre-specified alpha for the formal null test
|
|-- Is the outcome/estimate approximately normal with independent observations?
|     |-- Yes --> z-based normal approximation; report mean difference + SE/CI
|     `-- No / small sample / sparse event --> use an appropriate exact, t, or model-based method
|
|-- Planning a trial?
|     `-- Set alpha, beta, clinically important effect, event rate, attrition --> power/sample size
|
|-- Several outcomes, subgroups, or analyses?
|     |-- Confirmatory family --> control FWER (Bonferroni/Holm)
|     `-- Many exploratory signals --> control FDR; require validation
|
`-- Repeated interim looks at one primary question?
      `-- Use a pre-specified alpha-spending boundary, not repeated unadjusted 0.05 tests
```

Read the CI before the significance label. Whenever you can, quantify benefit, harm, and precision on an absolute scale.

A non-significant result may precisely exclude a meaningful effect. It may also leave an important question unresolved. The interval tells you which applies.

Match the error-control method to the claim. Use strong FWER control for confirmatory decisions. Use FDR for broad exploratory discovery. Use alpha spending for sequential looks.
# SECTION 2: TESTS OF SIGNIFICANCE & VARIABLE MODELING

## Chapter 6: Tests of Significance

### 1. Definition & Mathematical Core
A **test of significance** asks how well your data fit a null hypothesis, $H_0$ (the starting claim of no difference or association). You choose the test before looking at whether a result seems “significant.” Base that choice on the outcome scale, study design, independence, distribution, and sample size. For a two-sided test, the p value is $p=P(|T|\ge|t_{obs}|\mid H_0)$, where $T$ is the test statistic under $H_0$ and $t_{obs}$ is its observed value. The p value is the chance of a result at least this extreme if the null hypothesis were true.

### 2. Key Concepts, Principles & Assumptions
Start with the **estimand** (the exact effect you want to estimate). It may be a difference in means, a difference in medians or ranks, a risk difference, an odds ratio, or an association. Then identify the outcome type. A continuous, roughly Gaussian outcome (a bell-shaped pattern), such as arterial pH, can suit a parametric mean-based method. Clearly skewed continuous data, such as intensive care unit (ICU) length of stay or norepinephrine dose, often need a rank-based method or a justified transformation. Binary outcomes have two categories, such as death or survival. Ordinal outcomes have ordered categories, such as a bedside score.

Next, decide whether measurements are dependent. Values taken from the same patient before and after prone positioning are **paired**. Values from separately randomized treatment arms are **independent**. Ignoring real pairing throws away precision and can give you the wrong standard error (the estimated sampling variability). For more than two independent groups, use ANOVA (analysis of variance) when residual assumptions are credible. Use Kruskal–Wallis when rank-based inference fits better. For categorical outcomes, use chi-square only when expected cell frequencies are adequate. Use Fisher’s exact test for sparse $2\times2$ tables.

Parametric tests do not need every raw value to form a perfect bell shape. Focus on **residuals** (the gaps between observed and model-predicted values). For paired data, focus on the within-pair differences. Look for extreme influential outliers and an implausible variance pattern. With a small sample, inspect histograms, Q–Q plots (plots that compare your data with a normal distribution), and clinical plausibility. Do not rely only on a Shapiro–Wilk normality test. With a large sample, a trivial normality-test p value may not matter clinically. Severe skew can still make the result hard to interpret. Independence comes from the design. A normality test cannot create it.

Predefine one primary endpoint and one primary test. Testing daily SOFA (Sequential Organ Failure Assessment), vasopressor-free days, and PaO$_2$/FiO$_2$ (the arterial oxygen to inspired oxygen ratio) needs a multiplicity plan. The same applies to ICU stay, hospital stay, and mortality. Without a plan, you raise the false-positive risk. A false positive is an apparent effect that is not real. Report an effect estimate and a confidence interval (CI, a range of values compatible with the data). Do not report a p value alone. A non-significant p value does not prove equivalence, no benefit, or an adequately powered trial.

### 3. Visual / ASCII Schematic
```
Clinical question
       |
       +-- Outcome continuous / ordinal? -- yes --> paired observations?
       |                                      |            |
       |                                      |            +-- yes --> normal differences? --> paired t / Wilcoxon
       |                                      |            |
       |                                      |            +-- no  --> independent groups?
       |                                      |                           |
       |                                      |                           +-- 2 --> t test / Mann-Whitney U
       |                                      |                           +-- >2 -> ANOVA / Kruskal-Wallis
       |
       +-- Outcome categorical? ------------ yes --> expected counts adequate?
                                                   |
                                                   +-- yes --> chi-square
                                                   +-- no  --> Fisher's exact (2x2)
```

### 4. Landmark ICU Clinical Anchor
The ARDSNet **ARMA** trial randomized patients with acute lung injury/ARDS (acute respiratory distress syndrome). It compared a lower tidal-volume ventilation strategy with a traditional strategy. It found lower mortality and more ventilator-free days with the lower tidal-volume strategy. The trial shows why you must match the test to the endpoint. Mortality is binary. Ventilator-free days are bounded, often non-normal, and complicated by death. A simple t test may describe that distribution poorly, even when it gives a small p value. Your clinical interpretation must keep death as the competing event (an event that prevents the outcome of interest). A valid randomized comparison does not make every secondary variable suitable for the same statistical test.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** A clear algorithm preserves the estimand. It avoids pseudo-replication (treating linked observations as independent). It also makes the reported CI interpretable.
- **Strengths/indications:** Parametric methods estimate mean differences efficiently when their assumptions are credible. Rank methods tolerate skewed ordinal or continuous data better.
- **Pitfalls:** Do not choose Mann–Whitney just because a normality test is significant. It tests distributions, not automatically medians. You need similarly shaped distributions to interpret it as a median shift.
- **Pitfalls:** An unpaired test on repeated daily SOFA values violates independence. A paired test on different patients in two arms is also wrong.
- **Pitfalls:** “p<0.05” cannot rescue an unplanned outcome, biased measurement, or multiple unadjusted comparisons.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Choose the test from outcome type, number of groups, pairing, and distribution—not from the p value.
> - Inspect residuals/differences and design-based independence before calling a method parametric or non-parametric.
> - Report effect size and CI; non-significance is not equivalence.

## Chapter 7: Student's t-test (paired & unpaired) and ANOVA

### 1. Definition & Mathematical Core
The **unpaired Student’s t-test** compares the population means of two independent groups. A population mean is the average you would expect in the whole target population. The **paired t-test** asks whether the average within-patient difference is zero. For independent groups, $t=(\bar{x}_1-\bar{x}_2)/SE$, where $\bar{x}_1$ and $\bar{x}_2$ are group sample means and $SE$ is the standard error of their difference. For paired data, $t=\bar{d}/(s_d/\sqrt{n})$, where $\bar{d}$ is mean paired difference, $s_d$ is its standard deviation, and $n$ is the number of complete pairs. One-way ANOVA (analysis of variance) compares means across three or more independent groups. It tests $H_0:\mu_1=\mu_2=\cdots=\mu_k$ using $F=MS_B/MS_W$, where $MS_B$ is between-group mean square, $MS_W$ is within-group mean square, $\mu_j$ is population mean in group $j$, and $k$ is the number of groups.

### 2. Key Concepts, Principles & Assumptions
Use an unpaired t-test for one continuous endpoint measured in two independent or randomized groups. For example, compare baseline creatinine in two shock-treatment arms. The classic pooled-variance version assumes independent observations, roughly normal residuals, and equal population variances. **Welch’s t-test** does not assume equal variance. It is usually the safer default when you are unsure about variance equality. Use the paired t-test for matched observations. Examples include pre- and post-recruitment manoeuvre values in one patient or matched donor–recipient data. It assumes pairs are independent of other pairs. It also assumes the *differences* are roughly normal, not each time point separately.

ANOVA extends mean comparison to three or more independent groups. A significant omnibus F test tells you that at least one mean differs. It does not tell you which groups differ. Use a prespecified contrast (a planned comparison) or a multiplicity-adjusted post-hoc comparison, such as Tukey. Choose this after considering the main clinical question and the omnibus result. Repeated measurements from one ICU patient are not a standard one-way ANOVA problem. Their correlation over time needs repeated-measures ANOVA only under restrictive covariance assumptions. A mixed-effects model is usually preferable when trajectories and missing repeated measures matter.

In a small intensive care unit (ICU) study, report the mean difference and 95% confidence interval (CI) with the t or F statistic. If skew is severe, use a transformation, a method less sensitive to extreme values, or a non-parametric method. Do not force normality. A numerical score with few ordered categories is not automatically continuous. Check its distribution and ask what a one-point change means clinically.

### 3. Visual / ASCII Schematic
```
Two values from the SAME patient?   Yes --> compute d = post - pre --> paired t-test
             |
             No
             v
Two independent groups?             Yes --> Welch/unpaired t-test
             |
             No
             v
Three or more independent groups?   Yes --> one-way ANOVA --> planned contrast / adjusted post-hoc test
             |
             No
             v
Repeated patient-time observations?       --> mixed model, not ordinary ANOVA
```

### 4. Landmark ICU Clinical Anchor
In the ACURASYS trial, patients with early moderate-to-severe ARDS (acute respiratory distress syndrome) were randomized to cisatracurium or placebo. Early neuromuscular blockade was associated with improved adjusted 90-day survival in the original study. The two randomized arms contain different patients. A continuous baseline or physiological endpoint measured once between arms therefore needs an **unpaired** comparison, not a paired comparison. If PaO$_2$/FiO$_2$ (the arterial oxygen to inspired oxygen ratio) is measured before and after paralysis in each patient, that within-patient change is paired. Comparing those changes across treatment groups needs a group-by-time analysis or a properly constructed change-score model. The common viva trap is simple: “before and after” does not make the randomized-arm comparison a paired t-test.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** t-tests give a clinically readable mean difference. Welch’s version protects you when variances differ.
- **Strengths/indications:** A paired analysis removes stable between-patient variation. It is more efficient when the pairing is genuine.
- **Pitfalls:** A paired t-test loses an unmatched observation when a pair is incomplete. A mixed model can use more repeated data under stated assumptions.
- **Pitfalls:** ANOVA controls the global type-I error (the chance of a false positive) for the omnibus comparison. It does not control a later unplanned run of pairwise tests.
- **Pitfalls:** Do not judge equal variances by casually comparing standard deviations. Use design knowledge and residual diagnostics. Use Welch ANOVA when appropriate.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Unpaired t: two independent mean values; paired t: mean of within-patient differences.
> - Welch t-test is preferred when equal variance is doubtful; normality concerns residuals or differences.
> - ANOVA answers “any mean differs?”; use planned or multiplicity-adjusted contrasts to locate differences.

## Chapter 8: Non-Parametric Alternatives

### 1. Definition & Mathematical Core
**Non-parametric rank tests** replace raw values with their ordered ranks. They test distributional location under stated conditions. For two independent groups, Mann–Whitney’s statistic is $U_1=n_1n_2+n_1(n_1+1)/2-R_1$, where $n_1$ and $n_2$ are group sample sizes and $R_1$ is the rank sum in group 1. Wilcoxon signed-rank tests the ranks of non-zero paired differences. Kruskal–Wallis uses $H=12\sum_{j=1}^{k}R_j^2/n_j\,/\,[N(N+1)]-3(N+1)$, where $R_j$ is the rank sum in group $j$, $n_j$ is its size, $k$ is number of groups, and $N$ is total sample size.

### 2. Key Concepts, Principles & Assumptions
Use **Mann–Whitney U** for two independent groups when a continuous or ordinal endpoint is clearly skewed, has outliers, or is inherently ordered. It asks whether a randomly selected value from one group tends to exceed a randomly selected value from the other. People often call it a “test of medians.” That claim needs similarly shaped distributions. Without that condition, it detects a broader distributional difference. Report medians, interquartile ranges (IQRs, the middle half of values), a rank-based effect such as probability of superiority, and a suitable confidence interval (CI). Do not present it as a mean difference.

Use **Wilcoxon signed-rank** for paired ordinal or continuous values when paired differences are not suitably normal. It assumes independent pairs and at least ordinal measurement. For a signed-rank location interpretation, it also needs a symmetric distribution of paired differences. It drops zero differences and ranks the absolute non-zero differences. If symmetry seems implausible, use the simpler sign test. The sign test makes fewer distributional assumptions but is less efficient.

Use **Kruskal–Wallis** for three or more independent groups. It is the rank-based counterpart of one-way ANOVA. It gives an omnibus test, not permission for unadjusted pairwise results. If it is positive, use prespecified or multiplicity-adjusted post-hoc comparisons. None of these tests fixes clustering, recurrent measurements, informative death, or confounding. Rank methods do not excuse you from choosing a clinically meaningful effect scale.

### 3. Visual / ASCII Schematic
```
Skewed / ordinal outcome
        |
        +-- two independent arms ----------> Mann-Whitney U
        |
        +-- two measurements per patient --> Wilcoxon signed-rank
        |
        +-- >=3 independent groups -------> Kruskal-Wallis
                                              |
                                              +--> adjusted post-hoc comparisons if needed

Report: median [IQR] + rank/probability effect + CI where available
```

### 4. Landmark ICU Clinical Anchor
The STARRT-AKI trial randomized critically ill adults with severe acute kidney injury to accelerated or standard renal-replacement therapy initiation. It found no reduction in 90-day mortality with the accelerated strategy. More patients in that arm received renal replacement therapy. Intensive care unit (ICU) and hospital stays in this population are usually right-skewed. Death can truncate or alter them. A Mann–Whitney analysis can compare observed stay distributions between independent strategies. It cannot answer a simple “shorter stay” question when early death prevents discharge. In an exam, say that a rank test may describe a secondary stay outcome. You still need a death-aware endpoint or a competing-risk approach for the clinical estimand.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** Rank tests are less sensitive to outliers. They need less restrictive distributional assumptions than mean-based tests.
- **Strengths/indications:** They fit ordered bedside scales and severely skewed doses or duration variables.
- **Pitfalls:** Mann–Whitney tests distributions or stochastic ordering (which group tends to have higher values). It does not automatically test a median difference.
- **Pitfalls:** Wilcoxon signed-rank is paired. It is not the alternative to an unpaired t-test.
- **Pitfalls:** A p value alone hides the size of the effect. A rank-sum result does not prove a clinically relevant mean or median changed.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Mann–Whitney U: two independent skewed/ordinal groups; Wilcoxon signed-rank: paired differences.
> - Kruskal–Wallis is an omnibus rank test for three or more independent groups.
> - Rank methods do not cure confounding, clustering, repeated measures, or death as a competing event.

## Chapter 9: Chi-Square Test

### 1. Definition & Mathematical Core
The **chi-square test** compares the counts you observed with the counts you would expect if two categorical variables were independent. Its statistic is $\chi^2=\sum_{i=1}^{r}\sum_{j=1}^{c}(O_{ij}-E_{ij})^2/E_{ij}$. Here, $O_{ij}$ is the observed count. $E_{ij}=(R_iC_j)/N$ is the expected count for row $i$ and column $j$. $R_i$ is the row total. $C_j$ is the column total. $N$ is the total sample size. Degrees of freedom are $df=(r-1)(c-1)$, where $r$ is rows and $c$ columns.

### 2. Key Concepts, Principles & Assumptions
In a $2\times2$ randomized intensive care unit (ICU) comparison, chi-square asks whether event proportions differ between arms. It assumes patients are independent and categories are mutually exclusive. It also needs an adequate large-sample approximation. A practical rule is that no expected cell frequency should be below 1. No more than 20% of expected cells should be below 5. For a $2\times2$ table, many examiners use at least 5 expected observations in every cell as the simple rule. Calculate expected counts from row and column margins. Do not guess them from observed cell counts.

When data are sparse, use **Fisher’s exact test** for a $2\times2$ table. It holds the margins fixed and calculates the exact tail probability. It suits rare events, small pilot trials, or safety outcomes such as anaphylaxis. It can be conservative. A non-significant exact p value is not reassuring when the confidence interval (CI) is wide. For ordered categories, a trend test may be more efficient than treating categories as unordered names. For repeated outcomes, cluster-randomized designs, or adjusted associations, use methods that model correlation or covariates. A plain chi-square test cannot do that.

Always give the p value with a **risk difference** (the absolute difference in event risk). You can instead give a **risk ratio** (one risk divided by the other). You can also give an **odds ratio** (one group’s odds divided by the other’s). Also report a CI. Chi-square alone gives you no direction, clinical size, or proof of causality. In a randomized trial, allocation and analysis create the causal contrast. The chi-square test does not.

### 3. Visual / ASCII Schematic
```
                         30-day death   Survived   Total
Restrictive transfusion        a            b       a+b
Liberal transfusion            c            d       c+d
Total                          a+c          b+d      N

Expected count E(death, restrictive) = (a+b)(a+c) / N
Here a, b, c, and d are the displayed cell counts; N is the total.

All expected cells adequate? --> Pearson chi-square, df = (2-1)(2-1) = 1
Sparse expected cells? -------> Fisher's exact test
```

### 4. Landmark ICU Clinical Anchor
The TRICC trial randomized euvolemic critically ill adults to restrictive or liberal red-cell transfusion thresholds. In the overall study, the restrictive strategy was not associated with worse 30-day mortality. It used fewer transfusions. Its subgroup findings need cautious interpretation. Mortality is binary, so a $2\times2$ chi-square comparison fits conceptually when event counts are adequate. State the clinical conclusion with an absolute and relative effect plus CI. Do not say only “chi-square significant” or “chi-square non-significant.” If a small subgroup has few deaths, Fisher’s exact test may be mathematically valid. Its evidence will still be imprecise. It does not validate an unplanned subgroup claim.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** It is a simple, transparent comparison of independent categorical outcomes in adequately sized samples.
- **Strengths/indications:** It extends easily beyond $2\times2$ tables and gives clear degrees of freedom.
- **Pitfalls:** The expected-frequency rule concerns **expected** counts, not observed counts. Use Fisher’s exact for sparse $2\times2$ tables.
- **Pitfalls:** A small total sample does not automatically require Fisher’s exact when expected counts are adequate. Fisher’s exact is not a substitute for effect estimates.
- **Pitfalls:** Chi-square cannot adjust for baseline severity, site, or repeated measurements. Use logistic or mixed modelling when those factors matter.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Chi-square compares observed with expected categorical counts; $df=(r-1)(c-1)$.
> - Check independence and expected—not observed—frequencies before applying the approximation.
> - Use Fisher’s exact for sparse $2\times2$ tables and report risk effect measures with CIs.

## Chapter 10: Correlation Coefficient

### 1. Definition & Mathematical Core
A **correlation coefficient** describes how strongly two variables move together and in which direction. It does not estimate a treatment effect or prove causation. Pearson correlation is $r=\sum_{i=1}^{n}(x_i-\bar{x})(y_i-\bar{y})/\sqrt{\sum_{i=1}^{n}(x_i-\bar{x})^2\sum_{i=1}^{n}(y_i-\bar{y})^2}$, where $x_i$ and $y_i$ are paired observations, $\bar{x}$ and $\bar{y}$ their sample means, and $n$ the number of pairs. Spearman’s $\rho_s$ is Pearson correlation calculated on ranks. It is commonly written without ties as $\rho_s=1-6\sum_{i=1}^{n}d_i^2/[n(n^2-1)]$, where $d_i$ is the difference between paired ranks.

### 2. Key Concepts, Principles & Assumptions
Use **Pearson r** for a linear association between two continuous variables. Your scatterplot should be roughly elliptical. Outliers should not dominate the result. Observations must be independent. The original scale must make clinical sense. Pearson is not a normality test. The variables do not need to be perfectly normal. In small samples, its inference relies on bivariate-normal or linear-residual assumptions. Always inspect a scatterplot with a fitted line. Report a confidence interval (CI).

Use **Spearman rho** for a monotonic association. A monotonic relationship keeps moving in one direction, even if it is curved. It helps when a variable is ordinal, the relation is curved but steadily rising or falling, or skew and outliers make Pearson unhelpful. Spearman uses rank order. It can be high for a non-linear monotonic curve. It can be low for a U-shaped relation. A non-significant correlation does not rule out a clinically important threshold effect.

The coefficient ranges from $-1$ to $+1$. Its size has no universal clinical meaning. $r^2$ is the proportion of variation in one variable linearly accounted for by the other in a simple linear model. It is not agreement, calibration (how closely predicted risks match observed risks), or individual predictive accuracy. Two devices can correlate strongly yet differ systematically by 15 mmHg. Use Bland–Altman methods for agreement. Use ROC (receiver operating characteristic) and calibration assessments for prediction. Use multivariable modelling to address confounding (a shared cause that distorts an association).

Repeated daily measures create within-patient correlation. If you pool all lactate and SOFA (Sequential Organ Failure Assessment) values as independent, you can manufacture a narrow CI. You may also create an apparently strong association driven by patient severity. Use repeated-measures correlation or a mixed model when your question follows patients over time.

### 3. Visual / ASCII Schematic
```
Pearson: linear association                 Spearman: monotonic ranks
 y                                           y
 |        *                                  |           *
 |     *                                     |       *
 |   *                                       |    *
 | *                                         |  *
 +---------- x                               +---------- x

Correlation != agreement != causation != validated prediction
```

### 4. Landmark ICU Clinical Anchor
ANDROMEDA-SHOCK randomized septic-shock resuscitation to a peripheral-perfusion target using capillary refill time or to a lactate-targeted strategy. The mortality reduction in the peripheral-perfusion arm did not reach conventional statistical significance in the primary analysis. Lactate and capillary refill may be associated in a dataset. Correlation cannot show that they are interchangeable targets. It also cannot show that a correlation explains a treatment effect. A Spearman coefficient can summarize their monotonic bedside relation when distributions are skewed. The trial question still needs a randomized outcome comparison, not correlation. Do not infer that correlated resuscitation markers must give the same prognosis or treatment response.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** Pearson efficiently summarizes linear continuous association. Spearman handles ordered or skewed monotonic relationships.
- **Strengths/indications:** Scatterplots reveal non-linearity, clusters, leverage points (observations that strongly pull a fitted line), and thresholds hidden by one coefficient.
- **Pitfalls:** Correlation does not imply causality, agreement, calibration, or predictive performance.
- **Pitfalls:** A near-zero Pearson r can coexist with a strong U-shaped relationship. A high r can come from one influential extreme value.
- **Pitfalls:** Do not treat repeated measurements as independent. Do not correlate a variable with a score that already contains it without recognising mathematical coupling.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Pearson measures linear association; Spearman measures rank-based monotonic association.
> - Inspect the scatterplot and CI; select correlation does not establish agreement or causation.
> - Repeated ICU measurements require longitudinal methods, not naïve pooled correlation.

## Chapter 11: Regression Analysis

### 1. Definition & Mathematical Core
**Regression** models an outcome using several predictors while holding the other listed predictors constant. Linear regression for a continuous outcome is $Y_i=\beta_0+\beta_1X_{1i}+\cdots+\beta_pX_{pi}+\varepsilon_i$. Here, $Y_i$ is the outcome for patient $i$. $\beta_0$ is the intercept. $X_{ji}$ is predictor $j$. $\beta_j$ is its conditional mean-change coefficient. $p$ is the number of predictors. $\varepsilon_i$ is residual error. Logistic regression for binary hospital mortality is $\log[p_i/(1-p_i)]=\beta_0+\beta_1X_{1i}+\cdots+\beta_pX_{pi}$, where $p_i$ is the mortality probability. $e^{\beta_j}$ is the adjusted odds ratio (OR) for a one-unit predictor increase, holding other predictors constant.

### 2. Key Concepts, Principles & Assumptions
Choose the model from the outcome. Use linear regression for an approximately continuous outcome with an interpretable conditional mean. Its residuals must behave sensibly. Use logistic regression for binary death, dialysis dependence, or delirium. Linear regression needs independent observations and a linear conditional mean. It also needs homoscedastic residual variance (roughly constant spread of residuals) and no unduly influential observation. Residual normality mainly matters for small-sample inference. Logistic regression needs independent observations and a correctly specified relation on the log-odds scale. It needs enough information or events for the model’s complexity. It also needs no problematic separation, where a predictor perfectly sorts outcomes. Logistic regression does **not** require normally distributed predictors.

In prognostic modelling, separate **discrimination** from **calibration**. Discrimination means separating survivors from non-survivors. You often measure it with the c-statistic (the chance a model gives a higher risk to a case than a non-case). Calibration means that predicted risk agrees with observed risk. A high c-statistic does not guarantee well-calibrated probabilities in a new intensive care unit (ICU) population. Do not arbitrarily turn continuous predictors, such as age, lactate, and creatinine, into categories. Check non-linearity with clinically sensible splines (smooth flexible curves) or transformations. Internal validation with bootstrap or cross-validation estimates optimism (apparent performance that will not repeat). External validation tests whether performance holds across hospitals, eras, and case mix.

APACHE II (Acute Physiology and Chronic Health Evaluation II) combines acute physiology, age, and chronic health information to estimate risk. SAPS II (Simplified Acute Physiology Score II) is also a severity-of-illness score developed for mortality prediction. Both are multivariable risk tools. They are not causal estimates. They do not replace bedside reassessment. SOFA (Sequential Organ Failure Assessment) quantifies organ dysfunction. Its trajectory can give prognostic information. Do not treat a score change as a validated individual mortality probability without a specified, calibrated model.

### 3. Visual / ASCII Schematic
```
Outcome to model
  |
  +-- continuous (e.g., ICU-free days, if mean model defensible) --> Linear regression
  |       report beta: adjusted mean change + residual diagnostics
  |
  +-- binary (e.g., hospital death) ------------------------------> Logistic regression
          report OR = exp(beta), calibration, discrimination, validation

Severity variables --> APACHE II / SAPS II predictors --> predicted mortality
Organ dysfunction --> SOFA trajectory              --> prognosis, not automatic causality
```

### 4. Landmark ICU Clinical Anchor
APACHE II and SAPS II are landmark ICU severity-of-illness systems. They estimate hospital mortality risk from multiple baseline variables. Their development and use illustrate logistic rather than linear regression when death is the endpoint. An APACHE II score helps describe case mix and adjust risk. Two patients with the same score can still have different risks because of diagnosis, treatment, and setting. SOFA was designed to describe sequential organ dysfunction. Using it to predict mortality needs a separately assessed model. In a viva, explain that an odds ratio from a logistic score model is a conditional association. It does not prove that changing a component, such as creatinine, causes the corresponding mortality change.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** Regression estimates adjusted associations. It can produce individual risk estimates when development, validation, and calibration are adequate.
- **Strengths/indications:** It retains continuous predictors and quantifies uncertainty with confidence intervals (CIs). It avoids crude risk-group dichotomization.
- **Pitfalls:** Odds ratios can overstate risk ratios when outcomes are common. Report predicted risks or risk ratios or differences when clinicians need them.
- **Pitfalls:** Selecting variables only by univariate p values creates unstable, biased models. It can also omit known confounders.
- **Pitfalls:** Discrimination alone is not validation. Check calibration, correct for internal optimism, and perform external validation.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Linear regression models a continuous conditional mean; logistic regression models log-odds of a binary outcome.
> - APACHE II/SAPS II are risk-prediction tools; SOFA describes organ dysfunction and needs separate prognostic validation.
> - Assess functional form, overfitting, calibration, discrimination, and external validity.

## Chapter 12: Univariate vs. Multivariate Analysis

### 1. Definition & Mathematical Core
**Univariate analysis** examines one outcome–predictor relation at a time. **Multivariable analysis** estimates an exposure–outcome association while accounting for several covariates (other measured variables). In a logistic model, $\log[p_i/(1-p_i)]=\beta_0+\beta_EE_i+\beta_1C_{1i}+\cdots+\beta_qC_{qi}$. Here, $p_i$ is outcome probability for patient $i$. $\beta_0$ is the intercept. $E_i$ is the exposure. $C_{ji}$ are covariates or confounders. $\beta_E$ is the adjusted log-odds association. $q$ is the number of covariates. A confounder is associated with both exposure and outcome. It is not caused by the exposure. It is not on the causal pathway.

### 2. Key Concepts, Principles & Assumptions
A univariate association can describe your data. In intensive care unit (ICU) observational research, it is rarely a causal estimate. For example, patients receiving renal replacement therapy are often sicker than patients who do not. An unadjusted link between therapy and death can reflect severity, indication, and timing as well as treatment. Choose adjustment variables using clinical knowledge and a causal diagram (a drawing of assumed cause-and-effect links). Measure them before exposure where possible. Do not choose them from p values alone. Do not adjust for mediators, such as post-treatment vasopressor reduction when estimating a fluid strategy’s total effect. A mediator lies on the causal path. Do not adjust for colliders, such as a variable caused by both the exposure and unmeasured severity. That adjustment can introduce bias.

“Multivariate” is often used loosely. Strictly, **multivariable** means one outcome with multiple predictors. **Multivariate** means several outcomes modelled jointly. In an examination answer, state that distinction. Then discuss multivariable regression for confounder adjustment. Randomization balances measured and unmeasured baseline confounders in expectation. Adjustment in a trial can improve precision or address chance imbalance. It does not replace intention-to-treat analysis (analysing patients in their assigned groups).

Check **collinearity** (strong overlap between predictors). APACHE II (Acute Physiology and Chronic Health Evaluation II), SAPS II (Simplified Acute Physiology Score II), SOFA (Sequential Organ Failure Assessment), lactate, and vasopressor dose can all reflect illness severity. High collinearity makes coefficients unstable and widens confidence intervals (CIs). Overall prediction can still look reasonable. Inspect clinical redundancy, correlation matrices, variance-inflation factors, and coefficient stability. Do not include a composite score and all its components without a clear reason. Pre-specify a parsimonious model (one no more complex than needed). Keep continuous variables continuous. Handle non-linearity. Assess interactions only when plausible and adequately powered. Validate performance. A model with many predictors but few events is prone to overfitting (fitting random noise too closely). In the schematic, RRT means renal replacement therapy and AKI means acute kidney injury.

### 3. Visual / ASCII Schematic
```
Observed association: early RRT  ------------------> mortality
                         ^                              ^
                         |                              |
                 AKI severity / shock severity ----------+
                         (confounder)

Build model:
Clinical estimand --> pre-exposure confounders --> functional form --> collinearity check
       --> prespecified interactions --> internal validation --> transparent adjusted effect
```

### 4. Landmark ICU Clinical Anchor
The RECOVERY trial randomized hospitalized patients with coronavirus disease 2019 (COVID-19) to dexamethasone or usual care. It showed a mortality benefit in patients receiving oxygen or invasive mechanical ventilation. It did not show benefit in patients receiving no respiratory support. Random allocation means the primary treatment comparison does not need multivariable adjustment to remove baseline confounding. Respiratory-support subgroup estimates still need prespecification, interaction testing, and caution. Comparing a “significant” ventilated subgroup with a “non-significant” subgroup does not prove effect modification (a true difference in treatment effect between groups). In an observational ICU cohort, disease severity and treatment indication would require a carefully specified multivariable adjustment.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** Multivariable models can adjust measured pre-exposure confounders. They can improve precision in a randomized trial.
- **Strengths/indications:** Transparent model building shows effect modification, non-linearity, and uncertainty better than a series of univariate p values.
- **Pitfalls:** Statistical adjustment cannot remove unmeasured confounding, reverse causation, immortal-time bias (a period when an outcome cannot occur), or a poorly defined exposure.
- **Pitfalls:** Do not include post-exposure mediators or colliders. Do not choose “confounders” only because their univariate p value is below 0.05.
- **Pitfalls:** Collinearity widens CIs and destabilizes individual coefficients. Blindly deleting the variable with the largest p value does not fix it.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Univariate describes one association; multivariable models one outcome with several predictors.
> - Adjust pre-exposure confounders selected from clinical/causal knowledge, not only statistical screening.
> - Check collinearity, overfitting, functional form, interactions, and residual confounding.

## Chapter 13: Missing Data Handling

### 1. Definition & Mathematical Core
**Missing-data handling** sets out how you represent absent values, why they may be absent, and how replacement uncertainty enters your analysis. Let $R_i=1$ if a value $Y_i$ is observed and $R_i=0$ if it is missing. Missing completely at random (MCAR) means $P(R_i\mid Y_i,X_i)=P(R_i)$. Missing at random (MAR) means $P(R_i\mid Y_i,X_i)=P(R_i\mid X_i)$. Missing not at random (MNAR) means missingness still depends on unobserved $Y_i$ after observed covariates $X_i$. In multiple imputation, estimates combine as $\bar{Q}=m^{-1}\sum_{l=1}^{m}Q_l$ and $T=\bar{U}+(1+1/m)B$. Here, $m$ is the number of imputed datasets. $Q_l$ is the estimate in dataset $l$. $\bar{U}$ is the mean within-imputation variance. $B$ is the between-imputation variance. $T$ is the total variance.

### 2. Key Concepts, Principles & Assumptions
Start by counting and displaying missing values by variable, treatment arm, time, centre, and outcome status. A test may be absent because the patient improved. A lactate may be absent because the patient died. A laboratory result may simply be unavailable. These patterns have different causes and clinical meanings. Never silently convert a missing value into normal, zero, or “no event.” For a composite severity score, state whether a missing component prevents calculation. State whether a validated scoring rule assigns a value. An ad hoc substitute can bias severity adjustment and prognosis.

**Complete-case analysis** uses only patients with all required data. It is simple and transparent. It is unbiased only under MCAR or more restrictive conditions that fit the analysis. In intensive care unit (ICU) data, MCAR is uncommon. Sicker patients may have more tests. Moribund patients may have fewer later measurements because they died. Under plausible MAR, multiple imputation can reduce bias and preserve precision. The imputation model should include the outcome, exposure, missingness predictors, auxiliary variables (useful extra variables), non-linearities, interactions, and the design structure. Impute within treatment arms or include arm appropriately when effects may differ. Do not impute a post-randomization outcome and call the result definitive without sensitivity analyses.

You cannot verify MNAR from observed data alone. When you report an estimated effect, a confidence interval (CI) shows its uncertainty. Use clinically anchored sensitivity analyses. Examples include delta-adjusted imputation and best- or worst-plausible-case analyses. Mortality follow-up should be extremely complete. Report any missing vital status and explore its possible effect. With repeated biomarkers, death is not ordinary missingness. It is a competing event or truncation by death. Imputing biomarker values after death is usually nonsensical.

### 3. Visual / ASCII Schematic
```
Value missing?
    |
    +-- Why / pattern documented? --> by arm, time, site, outcome
    |
    +-- plausibly MCAR --> complete case may be acceptable (state loss of precision)
    |
    +-- plausibly MAR  --> multiple imputation + complete-case sensitivity analysis
    |
    +-- possibly MNAR  --> delta/pattern-mixture sensitivity analysis
    |
    +-- death before measurement --> do NOT impute a post-death biomarker value
```

### 4. Landmark ICU Clinical Anchor
The ADRENAL trial randomized patients with septic shock to continuous hydrocortisone or placebo. It found no significant difference in 90-day all-cause mortality. Hydrocortisone hastened resolution of shock. Its mortality endpoint shows why you must state follow-up completeness and the intention-to-treat denominator. A complete-case analysis of a secondary day-7 SOFA (Sequential Organ Failure Assessment) value could be biased. Death or early discharge may cause the missing values disproportionately. Multiple imputation may suit an intermittently missing baseline laboratory value under MAR. It is not a mechanical answer for a post-death SOFA measurement. Your analysis must preserve the endpoint’s clinical meaning.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** Complete-case analysis is reproducible and can be valid under MCAR. Multiple imputation retains information and carries imputation uncertainty forward under MAR.
- **Strengths/indications:** Sensitivity analyses expose unverifiable MNAR assumptions rather than hiding them.
- **Pitfalls:** “Missing at random” does not mean values are randomly scattered. It means missingness no longer depends on the unobserved value after accounting for observed information.
- **Pitfalls:** Single mean imputation understates variance, weakens associations, and falsely increases certainty.
- **Pitfalls:** Imputation cannot fix informative death, unmeasured missingness predictors, or a poorly defined endpoint. Report the amount, reasons, method, and sensitivity analysis.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Describe missingness before modelling: amount, pattern, reason, and relation to arm/outcome.
> - Complete case is credible mainly under MCAR; multiple imputation targets MAR and must include outcome/predictors.
> - MNAR needs sensitivity analysis; never impute post-death physiological values as ordinary missing data.

### Section Recap: Which Test / Which Effect Measure
```
START: Specify outcome, groups, and whether measurements are paired
 |
 +-- Continuous / ordinal outcome
 |    |
 |    +-- 2 groups
 |    |    |
 |    |    +-- paired --> normal paired differences? -- yes --> paired t-test (mean difference, 95% CI)
 |    |    |                                           no  --> Wilcoxon signed-rank (rank/median-oriented summary)
 |    |    |
 |    |    +-- independent --> approximately normal residuals? -- yes --> Welch/unpaired t-test (mean difference)
 |    |                                                        no  --> Mann-Whitney U (rank/probability effect)
 |    |
 |    +-- >=3 independent groups --> assumptions credible? -- yes --> ANOVA (mean contrasts)
 |                                                         no  --> Kruskal-Wallis (rank comparison)
 |
 +-- Categorical binary outcome --> expected cell counts adequate? -- yes --> chi-square (risk difference/RR/OR)
 |                                                             no  --> Fisher's exact for sparse 2x2 (risk effect + CI)
 |
 +-- Two variables, no treatment contrast --> linear continuous association? --> Pearson r
                                           --> monotonic / ordinal association? --> Spearman rho
 |
 +-- Outcome requires adjustment/prediction --> continuous --> linear regression (adjusted beta)
                                         --> binary     --> logistic regression (adjusted OR; calibration/discrimination)
```
Choose the test after you define the estimand. Then check pairing, independence, distribution, and expected counts.
For a clinical trial, report the absolute effect and 95% CI alongside the p value. Use risk measures for binary outcomes. Use mean or rank summaries for continuous outcomes.
Correlation is not agreement, causation, or prediction. Regression adjustment needs a causal plan, a collinearity check, and validation.
For incomplete ICU data, state your MCAR, MAR, or MNAR assumptions. Use sensitivity analyses. Death is not an ordinary missing value that you can impute.
# SECTION 3: DIAGNOSTIC TESTING & PROBABILITY

## Chapter 14: Diagnostic Accuracy: sensitivity, specificity, PPV, NPV

### 1. Definition & Mathematical Core
**Diagnostic accuracy** means how closely an **index test** (the test you are assessing) agrees with a **reference standard** (the best available way to decide whether disease is present). **Sensitivity** is the share of patients with disease who test positive. **Specificity** is the share without disease who test negative. **Positive predictive value (PPV)** is the chance that a positive result means disease. **Negative predictive value (NPV)** is the chance that a negative result means no disease. Procalcitonin (PCT) is a blood biomarker, meaning a measurable substance that may help identify illness.

$$
\mathrm{Sensitivity}=\frac{TP}{TP+FN};\quad \mathrm{Specificity}=\frac{TN}{TN+FP};\quad
\mathrm{PPV}=\frac{TP}{TP+FP};\quad \mathrm{NPV}=\frac{TN}{TN+FN}
$$

Here, $TP$ = true positives, $FN$ = false negatives, $TN$ = true negatives, and $FP$ = false positives. Each classification uses the reference standard as the comparison.

### 2. Key Concepts, Principles & Assumptions
Sensitivity asks, “Of patients who truly have the target condition, how often is the test positive?” You need it when missing disease would be dangerous. Examples include hidden invasive aspergillosis or septic shock that could respond to fluid. Specificity asks the matching question for people without disease. It matters when a false positive could harm the patient. Examples include unnecessary antifungal treatment or a fluid bolus in established pulmonary oedema.

PPV asks about disease after a positive result. NPV asks about no disease after a negative result. Sensitivity and specificity do not change simply because you move populations. PPV and NPV do. They depend on disease prevalence (how common the disease is in the tested group) and on the clinical spectrum (the mix and severity of disease and its mimics). A test can have an excellent NPV in a low-risk emergency group. The same NPV may be unsafe in an intensive care unit (ICU) group with much more severe disease.

A valid study needs a defensible reference standard. Ideally, readers interpret the tests at about the same time and while blinded (unaware of the other result). The study should set its threshold (the cutoff for a positive result) before analysing results. **Incorporation bias** occurs when the index test helps decide the reference diagnosis. **Verification bias** occurs when only patients with positive index tests receive the reference standard. ICU reference standards are often imperfect. For sepsis, clinicians may use cultures, imaging, serial physiology, and response to treatment to decide the diagnosis. That can create circularity, meaning the test helps support the diagnosis used to judge that same test. This is a concern for biomarkers such as PCT.

### 3. Visual / ASCII Schematic
```text
Reference standard                         Disease present   Disease absent
                                          (D+)               (D-)
Index test positive (T+)                  TP                 FP
Index test negative (T-)                  FN                 TN

Illustrative ICU PCT table: 100 patients with suspected sepsis
PCT positive                              30                 12
PCT negative                              10                 48

Sensitivity = 30/(30+10) = 75%            Specificity = 48/(48+12) = 80%
PPV         = 30/(30+12) = 71%            NPV         = 48/(48+10) = 83%
```

These numbers are deliberately illustrative. They are not results from a PCT study. The table shows why you need the denominator, or total group being counted, before interpreting PPV and NPV.

### 4. Landmark ICU Clinical Anchor
The original [BLUE protocol study](https://eoa.umontreal.ca/wp-content/uploads/sites/33/Lichenst_Blue-protocol_Chest-2008.pdf), named for Bedside Lung Ultrasound in Emergency (BLUE), assessed lung ultrasound patterns in acute respiratory failure. It reported that the protocol would have provided the correct diagnosis in 90.5% of cases. In that dataset, diffuse anterior B-lines with lung sliding, called the B-profile, identified haemodynamic pulmonary oedema with 97% sensitivity and 95% specificity. The composite pneumonia profiles had 89% sensitivity and 94% specificity. These figures make a practical point. A profile is not the disease itself. Its performance depends on the acute-respiratory-failure case mix, operator technique, diagnostic definitions, and final reference diagnosis.

At the bedside, interpret a B-profile alongside the whole picture. A low P/F ratio is a low ratio of arterial oxygen pressure to inspired oxygen fraction. In a patient with shock and renal failure, assess focused cardiac ultrasound, venous congestion, ventilator mechanics, and timing. Do not automatically label it cardiogenic oedema in acute respiratory distress syndrome (ARDS). In ARDS, B-lines show interstitial syndrome, meaning excess fluid or tissue in the lung interstitium. They do not prove a hydrostatic mechanism, meaning pressure-driven oedema.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**

- Sensitivity and specificity are easy to understand. They let you compare tests at one fixed threshold.
- PPV and NPV answer direct clinical questions after you receive a result.
- The $2\times2$ table shows every part of apparent test performance. Ask to see it before accepting an “accuracy” claim.

**Examiner pitfalls**

- Do not say PPV is “the chance of a positive test in disease.” That is sensitivity.
- Do not assume a highly sensitive test has a high NPV. Do not assume a highly specific test has a high PPV. Predictive values also depend on prevalence.
- Do not report accuracy $(TP+TN)/N$ alone. If almost nobody has invasive pulmonary aspergillosis, a test can look accurate while missing many real cases.
- Do not apply a profile-level BLUE estimate to one sign. Do not apply a serum PCT result to every ICU phenotype.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
>
> - Sensitivity and specificity start with true disease status. PPV and NPV start with the test result.
> - Rebuild the $2\times2$ table. Identify the reference standard before interpreting “accuracy.”
> - Predictive values depend on the population. ICU case mix can make an imported PPV or NPV misleading.

## Chapter 15: Impact of Disease Prevalence on Predictive Values: spectrum bias and test utility

### 1. Definition & Mathematical Core
**Prevalence** is the pre-test probability (your estimated chance of disease before this result) in the tested population. **Sensitivity** is the share with disease who test positive. **Specificity** is the share without disease who test negative. Prevalence changes positive predictive value (PPV) and negative predictive value (NPV), even when sensitivity and specificity stay the same. **Spectrum bias** means test performance changes because the study and your patient differ in disease severity, alternative diagnoses, or test conditions. Procalcitonin (PCT) is a blood biomarker used as one clue in possible infection. The intensive care unit (ICU) is the high-acuity hospital setting used throughout this chapter.

$$
\pi=\frac{TP+FN}{N};\quad
\mathrm{PPV}=\frac{Se\times\pi}{(Se\times\pi)+(1-Sp)\times(1-\pi)};\quad
\mathrm{NPV}=\frac{Sp\times(1-\pi)}{(1-Se)\times\pi+Sp\times(1-\pi)}
$$

Here, $\pi$ = disease prevalence (pre-test probability), $N$ = all tested patients, $Se$ = sensitivity, $Sp$ = specificity, $TP$ = true positives, and $FN$ = false negatives.

### 2. Key Concepts, Principles & Assumptions
When prevalence is low, most tested patients do not have the disease. Even a small false-positive rate can then make up much of the positive-result group. PPV falls. When prevalence is high, many more patients truly have disease. False negatives then occur in a larger group, so a negative result is less reassuring and NPV falls. Bayes’ theorem, the rule for updating probability after a result, is not failing. You are testing a different population.

Spectrum bias matters greatly in ICU diagnostic research. PCT may separate bacterial sepsis from selected non-infectious systemic inflammation in one study group. It can perform differently after major surgery, trauma, cardiogenic shock, prolonged resuscitation, renal dysfunction, or early infection. Galactomannan, a fungal cell-wall test, also performs differently in neutropenic angioinvasive disease and in non-neutropenic ICU disease that mainly affects the airways. Choosing healthy controls instead of patients with realistic mimics can falsely improve specificity. It can also inflate the apparent area under the receiver-operating-characteristic curve (AUROC). AUROC measures how well a test separates cases from non-cases.

**Test utility** means whether a result changes what you should do. A useful result moves probability across an action threshold (the probability at which your next action changes). It may move the patient below a testing or exclusion threshold. It may move the patient above a treatment threshold. Or it may leave an intermediate zone where you need imaging, repeat sampling, or monitoring. Utility also depends on turnaround time, invasiveness, cost, and the harm caused by an error.

### 3. Visual / ASCII Schematic
```text
Same test performance: sensitivity 77%, specificity 79%

Low-prevalence setting (π = 10%)        Higher-prevalence setting (π = 50%)
PPV = 29%                               PPV = 79%
NPV = 97%                               NPV = 78%

Interpretation:
positive PCT in low-risk group  -> often needs corroboration
negative PCT in high-risk ICU   -> cannot by itself exclude sepsis
```

These calculations use the sensitivity and specificity above only to show the effect of prevalence. They are not universal decision thresholds.

### 4. Landmark ICU Clinical Anchor
A systematic review combines results from several studies. In 30 studies and 3,244 critically ill patients, [Wacker and colleagues](https://europepmc.org/article/med/23375419) reported combined PCT sensitivity of 0.77 and specificity of 0.79. The AUROC was 0.85 for separating sepsis from non-infectious systemic inflammatory response syndrome (SIRS). The studies had substantial heterogeneity, meaning their results differed more than expected by chance alone. With a 10% pre-test probability, those figures give a PPV of about 29% and an NPV of about 97%. With a 50% pre-test probability, PPV rises to about 79% and NPV falls to about 78%. The same assay result therefore means very different things in a low-risk post-operative patient and in a deteriorating patient with vasopressor-dependent shock.

The D-dimer pathway shows the same point in practice. The [2019 ESC pulmonary embolism guideline](https://publications.ersnet.org/content/erj/54/3/1901647), from the European Society of Cardiology (ESC), recommends D-dimer. D-dimer is a blood marker of clot breakdown. Use it to exclude pulmonary embolism with low or intermediate clinical probability and an appropriate sensitive assay. It does not recommend this approach in high clinical probability. A normal result then does not safely exclude disease. D-dimer also works less efficiently in hospitalised or inflamed ICU populations. Background elevation lowers specificity.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**

- Prevalence-aware predictive values support patient-level counselling and action.
- Spectrum analysis checks whether a study looks like your intended ICU population.
- Threshold thinking stops indiscriminate biomarker ordering.

**Examiner pitfalls**

- Do not call prevalence a property of the assay. It is a property of the tested population at a defined point in the pathway.
- Do not carry PPV or NPV from a case-control study, which deliberately selects cases and controls, into a general ICU.
- Do not use a positive D-dimer to rule in pulmonary embolism in septic, post-operative, or malignant disease.
- Do not mistake spectrum bias for random error. It is a systematic threat to external validity, meaning whether study findings apply to other patients.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
>
> - When prevalence falls, PPV falls and NPV rises. When prevalence rises, the reverse occurs.
> - Spectrum bias occurs when disease severity, mimics, or test conditions differ from those in your target ICU patient.
> - Order a test only when a plausible result can cross an exclusion, imaging, or treatment threshold.

## Chapter 16: Likelihood Ratios (LR+, LR−) and Diagnostic Odds Ratio (DOR): pre- to post-test probability shifts

### 1. Definition & Mathematical Core
**Likelihood ratios (LRs)** show how much a specific result changes disease odds. **Odds** compare the chance of disease with the chance of no disease. **Diagnostic odds ratio (DOR)** compares the odds of a positive test in patients with disease against those without disease. It summarises how well the test separates those groups in one number. **Sensitivity** is the share with disease who test positive. **Specificity** is the share without disease who test negative. Procalcitonin (PCT) is a blood biomarker used as one clue in possible infection. Area under the receiver-operating-characteristic curve (AUROC) measures how well a test separates cases from non-cases. The intensive care unit (ICU) is the high-acuity hospital setting discussed here.

$$
LR^+=\frac{Se}{1-Sp};\quad LR^-=\frac{1-Se}{Sp};\quad
DOR=\frac{LR^+}{LR^-}=\frac{TP\times TN}{FP\times FN}
$$

Here, $LR^+$ = positive likelihood ratio, $LR^-$ = negative likelihood ratio, $Se$ = sensitivity, $Sp$ = specificity, $TP$ = true positives, $TN$ = true negatives, $FP$ = false positives, and $FN$ = false negatives.

### 2. Key Concepts, Principles & Assumptions
An $LR^+$ above 1 raises disease probability. An $LR^-$ below 1 lowers it. The farther either ratio is from 1 in the useful direction, the more information the result gives. As practical rules, $LR^+>10$ usually gives a large rule-in shift. An $LR^-<0.1$ usually gives a large rule-out shift. No LR removes the need to judge pre-test probability or the clinical harm of being wrong.

The DOR is neat mathematically because it combines both LRs. In a standard diagnostic cohort, it does not depend on prevalence. It does not tell you the direction of usefulness. A DOR of 20 does not show whether the test mainly rules in, rules out, or does both. Separate LRs are therefore better for bedside decisions. In a meta-analysis, which combines studies, sensitivity and specificity often move together because studies use different thresholds. Pooling them separately without a hierarchical diagnostic model, which accounts for this linked variation between studies, can mislead.

You may multiply sequential LRs only when tests add **conditionally independent** information. This means that, once you know disease status, one result does not predict the other. This often fails in ICU care. PCT, fever, neutrophilia (a raised neutrophil white-cell count), and Sequential Organ Failure Assessment (SOFA) deterioration can all reflect the same inflammatory process. Multiplying their published LRs without validation makes you too certain.

### 3. Visual / ASCII Schematic
```text
Pre-test probability -> convert to odds -> apply result-specific LR -> post-test probability

20% probability -> 0.20/0.80 = 0.25 odds
positive test, LR+ = 10  -> 0.25 x 10   = 2.50 odds -> 71% probability
negative test, LR- = 0.15 -> 0.25 x 0.15 = 0.038 odds ->  4% probability

DOR = LR+ / LR- = 10 / 0.15 = 66.7
```

### 4. Landmark ICU Clinical Anchor
Passive leg raising (PLR) temporarily moves blood from the legs toward the heart. It is a reversible, internal fluid challenge. Read the result through the variable used to measure response. In a [systematic review and meta-analysis of 23 clinical trials](https://pubmed.ncbi.nlm.nih.gov/26741579/), PLR had pooled sensitivity of 86%, specificity of 92%, and summary AUROC of 0.95 for predicting fluid responsiveness. **Fluid responsiveness** means cardiac output rises after a fluid challenge. These combined values give an approximate $LR^+$ of 10.8, $LR^-$ of 0.15, and DOR of 70.6. In a patient with a 20% clinical probability of fluid responsiveness, a properly measured positive PLR can raise probability to roughly 73%. A negative result lowers it to roughly 4%.

The same review found that PLR measured with a flow variable, such as cardiac output or stroke volume, outperformed PLR measured by pulse-pressure change. Pooled sensitivity was lower when pulse pressure was used. A pulse-pressure rise is not interchangeable with a measured rise in flow. This is especially true with reduced arterial compliance (stiff arteries), spontaneous breathing, right-ventricular dysfunction, or arrhythmia. Fluid responsiveness does not show that fluid will be tolerated. It does not automatically mean you should give a bolus.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**

- LRs turn your pre-test probability into a post-test probability. They travel better between clinical populations than PPV and NPV.
- Separate $LR^+$ and $LR^-$ show whether a test is mainly a rule-in or rule-out tool.
- DOR gives a compact way to compare studies at a common threshold.

**Examiner pitfalls**

- Do not multiply probability directly by an LR. Convert probability to odds first.
- Do not call DOR a risk ratio. Do not derive a patient’s post-test probability from DOR alone.
- Do not multiply correlated bedside tests as though they are independent.
- Do not treat a positive PLR as an indication for fluid. Check congestion, oxygenation, the right ventricle, and the treatment goal.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
>
> - A large $LR^+$ helps rule in. A small $LR^-$ helps rule out. Both update odds, not raw probability.
> - $DOR=LR^+/LR^-$ summarises discrimination. It does not tell you which result is clinically useful.
> - In PLR, measure flow change whenever possible. Pulse-pressure substitutes perform less well diagnostically.

## Chapter 17: Bayes' Theorem & Fagan Nomogram: bedside critical care application

### 1. Definition & Mathematical Core
**Bayes’ theorem** updates one patient’s disease probability. It combines a clinically estimated **pre-test probability** (the chance of disease before this result) with the information in a test result. A **likelihood ratio (LR)** measures how much that result shifts disease odds. **Odds** compare the chance of disease with the chance of no disease. A **Fagan nomogram** is a three-axis graphic that performs the same odds calculation. The intensive care unit (ICU) is the high-acuity hospital setting used in the examples.

$$
O_{\mathrm{pre}}=\frac{p_{\mathrm{pre}}}{1-p_{\mathrm{pre}}};\quad
O_{\mathrm{post}}=O_{\mathrm{pre}}\times LR;\quad
p_{\mathrm{post}}=\frac{O_{\mathrm{post}}}{1+O_{\mathrm{post}}}
$$

Here, $p_{\mathrm{pre}}$ = pre-test probability and $O_{\mathrm{pre}}$ = pre-test odds. $LR$ = the result-specific likelihood ratio. Use $LR^+$ for a positive result and $LR^-$ for a negative result. $O_{\mathrm{post}}$ = post-test odds and $p_{\mathrm{post}}$ = post-test probability.

### 2. Key Concepts, Principles & Assumptions
Pre-test probability is not a free-floating guess. In ICU practice, build it from the patient’s trajectory, host factors, examination, source assessment, microbiology, imaging, local epidemiology, and measured physiology. Estimate it *before* you see the index-test result, meaning the test being assessed. Otherwise you count the same evidence twice. You can use a validated score, a closely matched cohort, or calibrated clinical judgement. **Calibrated clinical judgement** means an estimate that has been checked against real outcomes over time.

A Fagan nomogram has three vertical axes. The left axis is pre-test probability. The middle axis is the LR. The right axis is post-test probability. Draw a straight line from the first axis through the second. Then read the third. This helps in a viva because you can show Bayesian updating without doing arithmetic. The calculations and nomogram are equivalent, as described in the [Fagan nomogram review](https://pmc.ncbi.nlm.nih.gov/articles/PMC4744617/).

Bayesian updating assumes the chosen LR fits your patient’s population, specimen, assay, threshold, and reference standard. It also assumes you have not counted the pre-test evidence and test evidence twice. A post-test probability is not a treatment order. Compare it with a decision threshold, which weighs treatment benefit and harm against further testing, delay, and diagnostic error.

### 3. Visual / ASCII Schematic
```text
Fagan construction

left axis                   middle axis                    right axis
pre-test probability        likelihood ratio               post-test probability
       50%       -----------       LR+ 3.67       -----------       79%
       50%       -----------       LR- 0.29       -----------       23%

Arithmetic check:
50% -> odds 1.0
positive: 1.0 x 3.67 = 3.67 odds -> 3.67/4.67 = 79%
negative: 1.0 x 0.29 = 0.29 odds -> 0.29/1.29 = 23%
```

### 4. Landmark ICU Clinical Anchor
Suppose bedside assessment gives a 50% probability of sepsis rather than sterile inflammation. [Wacker et al.](https://europepmc.org/article/med/23375419/) reported combined procalcitonin (PCT) sensitivity of 0.77 and specificity of 0.79. These figures give $LR^+=0.77/(1-0.79)=3.67$ and $LR^-=(1-0.77)/0.79=0.29$. The Fagan update is about 79% after a positive result. It is about 23% after a negative result. Neither result crosses a universal “sepsis excluded” threshold in a critically ill patient. Cultures, source-control assessment, serial examination, organ-failure assessment, and appropriate early antimicrobials still matter.

The same logic prevents overdiagnosis of invasive pulmonary aspergillosis. In a critically ill chronic obstructive pulmonary disease (COPD) cohort, bronchoalveolar lavage (BAL) galactomannan at a 0.5 optical-density cutoff had reported sensitivity of 88% and specificity of 87%. Serum galactomannan sensitivity was only 42% in that setting, as summarised in an [ICU aspergillosis review](https://pmc.ncbi.nlm.nih.gov/articles/PMC7176220/). A positive BAL test means more when host factors, compatible computed tomography (CT) findings, and bronchoscopy context give a meaningful pre-test probability. In a low-risk ventilated population, imperfect specificity can make many positive results false positives. BAL galactomannan should change your estimate. It should not replace integrated clinical adjudication, meaning the final diagnosis based on all relevant evidence.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**

- Bayes’ theorem makes your starting clinical assessment visible. It stops binary thinking.
- A Fagan nomogram gives a quick visual estimate when you have an LR and pre-test probability.
- The framework fits ICU action thresholds: exclude, investigate, treat, or reassess.

**Examiner pitfalls**

- Do not put sensitivity or specificity straight into the odds equation. Derive or obtain the right LR first.
- Do not equate pre-test probability with disease prevalence unless the patient really resembles the study population before testing.
- Do not let a biomarker “rule out” sepsis when the negative post-test probability remains above your action threshold.
- Do not apply serum galactomannan results from neutropenia, a low neutrophil count, to non-neutropenic ICU disease without checking specimen type and spectrum.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
>
> - Convert probability to odds. Multiply by the result-specific LR. Then convert odds back to probability.
> - The Fagan nomogram is Bayes’ theorem shown as a three-axis straight-line tool.
> - Compare post-test probability with an action threshold. No biomarker replaces source assessment and serial reassessment.

## Chapter 18: ROC Curve: AUROC, Youden's Index, cutoff selection

### 1. Definition & Mathematical Core
A **receiver-operating-characteristic (ROC) curve** plots sensitivity against $1-\mathrm{specificity}$ at every possible threshold, or cutoff. **Sensitivity** is the share with disease who test positive. **Specificity** is the share without disease who test negative. A continuous test can take many numeric values. An ordinal test has ordered categories. **Area under the ROC curve (AUROC)** is the chance that a randomly chosen case gets a higher test value than a randomly chosen non-case. **Youden’s Index** identifies the threshold that gives the largest combined sensitivity and specificity. The intensive care unit (ICU) is the high-acuity setting discussed in this chapter.

$$
J=Se+Sp-1;\quad 0\leq AUROC\leq1
$$

Here, $J$ = Youden’s Index, $Se$ = sensitivity at a stated cutoff, $Sp$ = specificity at that cutoff, and $AUROC$ = area under the ROC curve. A false positive is a positive result in someone without disease. A false negative is a negative result in someone with disease. An AUROC of $0.5$ means no discrimination, meaning the test cannot separate cases from non-cases. An AUROC of $1.0$ means perfect discrimination.

### 2. Key Concepts, Principles & Assumptions
Each ROC point represents one threshold. Lowering a procalcitonin (PCT), ferritin, or galactomannan cutoff usually raises sensitivity and lowers specificity. Raising the cutoff does the opposite. Ferritin is an iron-storage protein that also rises with inflammation. Galactomannan is a fungal cell-wall test. AUROC measures rank discrimination across thresholds. It does not measure calibration, meaning whether predicted risks match observed risks. It also does not measure prevalence, clinical utility, or whether one cutoff is safe. Two tests can have similar AUROCs yet perform very differently at the cutoff that matters clinically.

Youden’s Index selects the point furthest from the no-discrimination diagonal. It gives false positives and false negatives equal weight. That may not suit critical care. For a possibly fatal but treatable diagnosis, a lower cutoff may be reasonable even if it creates more false positives. For a toxic or invasive intervention, you may value specificity more. Choose a cutoff using assay precision, biological plausibility, external validation, and the effect of crossing a treatment threshold. **External validation** means checking the cutoff in a new patient group.

You can compare ROC results only when outcomes, time windows, and patient populations match. A **prognostic** AUROC predicts a future outcome, such as death. It is not diagnostic accuracy for sepsis. The P/F ratio, the ratio of arterial oxygen pressure to inspired oxygen fraction, measures oxygenation impairment in acute respiratory distress syndrome (ARDS) classification. Do not present it as a stand-alone ROC-derived diagnostic test for the mechanism of hypoxaemia.

### 3. Visual / ASCII Schematic
```text
Sensitivity
1.0 |          .  high sensitivity / low threshold
    |       .
    |    .        ROC curve
    |  .
0.5 | . . . . . . . . . . . . . . . . . . . .  no-discrimination line
    |
0.0 +------------------------------------------------ Specificity
    0.0                                              1.0

For each cutoff: J = sensitivity + specificity - 1
Choose cutoff only after considering false-negative and false-positive harm.
```

### 4. Landmark ICU Clinical Anchor
The [Sepsis-3 derivation and validation analysis by Seymour et al.](https://jamanetwork.com/journals/jama/fullarticle/2492875) shows both the value and limit of AUROC. In validation-cohort ICU encounters with suspected infection, mortality discrimination was higher for Sequential Organ Failure Assessment (SOFA). Its AUROC was 0.74, 95% confidence interval (CI) 0.73–0.76. Quick SOFA (qSOFA) had an AUROC of 0.66, 95% CI 0.64–0.68. Systemic inflammatory response syndrome (SIRS) had an AUROC of 0.64. SOFA had higher mortality discrimination than qSOFA and SIRS. Outside the ICU, qSOFA discriminated in-hospital mortality better than SOFA and SIRS. Its AUROC was 0.81 versus 0.79 and 0.76, respectively. These results describe prognostic discrimination. They do not prove that qSOFA is a sensitive diagnostic screen for infection or sepsis. qSOFA should prompt an organ-dysfunction assessment. It is not a rule-out test.

Cutoff optimisation can inform practice but can be fragile. In one ICU cohort assessed for haemophagocytic lymphohistiocytosis (HLH), [ferritin 9,083 μg/L](https://pmc.ncbi.nlm.nih.gov/articles/PMC7245825/) was the single-criterion cutoff with 92.5% sensitivity and 91.9% specificity. This is a useful hypothesis-generating threshold in hyperinflammatory critical illness. Ferritin is still non-specific. Diagnosing HLH requires the broader clinical pattern and structured criteria. Do not treat a cutoff selected in one cohort as a universal ICU rule.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
**Strengths / indications**

- ROC analysis shows the sensitivity-specificity trade-off across all thresholds.
- AUROC lets you compare overall discrimination when outcomes and populations match.
- Youden’s Index gives a clear, reproducible candidate cutoff.

**Examiner pitfalls**

- Do not say “AUROC is accuracy.” It measures discrimination, not calibration, benefit, or decision utility.
- Do not automatically choose the highest Youden cutoff when missing disease harms more than a false positive.
- Do not compare AUROCs from different settings or endpoints as though they are interchangeable.
- Do not call qSOFA a diagnostic test for sepsis. Do not use P/F ratio alone to decide why a patient has hypoxaemic respiratory failure.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
>
> - ROC curves show threshold trade-offs. AUROC measures rank discrimination across all thresholds.
> - $J=Se+Sp-1$ selects a cutoff that weights both error types equally. It may not be the best clinical cutoff.
> - qSOFA and SOFA AUROC work describes prognostic discrimination. Diagnosis and treatment still need clinical context.

### Section Recap: Which Test / Which Effect Measure
```text
Suspected ICU diagnosis
|
|-- First: estimate pre-test probability from phenotype, trajectory, and setting
|    |
|    |-- Need to describe a binary test at one threshold?
|    |    |     -> 2x2 table: sensitivity, specificity, PPV, NPV
|    |
|    |-- Need patient-level probability shift after a result?
|    |    |     -> LR+ or LR- -> Bayes odds calculation / Fagan nomogram
|    |
|    |-- Comparing overall discrimination or selecting a continuous-test cutoff?
|    |    |     -> ROC curve, AUROC, then Youden's Index only if error costs are equal
|    |
|    |-- Applying a study to this patient?
|          -> Check prevalence, spectrum, specimen, threshold, reference standard
|
`-- Post-test probability
     |-- below exclusion threshold -> withhold/stop targeted work-up when safe
     |-- intermediate -> repeat, image, sample, or monitor
     `-- above treatment threshold -> treat or obtain decisive confirmation as appropriate
```

Sensitivity and specificity describe a test at one threshold. PPV and NPV also depend on prevalence.  
Likelihood ratios are the best bridge from pre-test to post-test probability. Use them only when the study population matches your patient.  
AUROC does not choose treatment. Choose a cutoff based on the harm of false negatives and false positives.  
In every ICU setting, update the post-test probability as physiology, imaging, microbiology, and treatment response change.
# SECTION 4: CLINICAL TRIAL DESIGN & EPIDEMIOLOGY

## Chapter 19: RCTs: Core Architecture, Allocation Concealment, Blinding, Run-In Periods

### 1. Definition & Mathematical Core
A **randomized controlled trial (RCT)** assigns eligible people to planned treatments by chance. This makes the groups similar at baseline, apart from random differences. Its usual cause-and-effect target is the average treatment effect (ATE). $ATE=E[Y(1)-Y(0)]$, where $Y(1)$ and $Y(0)$ are a participant’s potential outcomes under experimental and control treatment, respectively, and $E$ denotes the population mean.

For a binary outcome (an outcome with two options, such as death or survival), the intention-to-treat (ITT) risk difference (RD) is $RD=p_E-p_C$. Here, $p_E$ is event risk in the experimental allocation group. $p_C$ is event risk in the control allocation group. A confidence interval (CI) shows the range of effect sizes compatible with the data. Randomization cannot fix biased outcome assessment. It also cannot fix unequal extra treatments, missing outcome data, or exclusions after randomization.

### 2. Key Concepts, Principles & Assumptions
Your trial needs a target population and clear eligibility criteria. It also needs a meaningful intervention and comparator. Set the primary outcome and analysis plan before recruitment. Then randomize, follow patients up, and analyse them in their assigned groups. Decide eligibility before allocation. Otherwise, recruiters may consciously or unconsciously select patients based on the next assignment.

**Allocation concealment** keeps the random sequence hidden *before* enrolment. Use central web or telephone randomization, or an independent pharmacy. Do not use transparent envelopes, alternation, date of birth, or an open block list. Concealment prevents selection bias (systematic differences caused by who gets recruited into each group). **Blinding** keeps treatment allocation hidden *after* allocation. You may blind patients, bedside clinicians, outcome assessors, data analysts, or adjudicators. Blinding matters most for subjective intensive care unit (ICU) outcomes. Examples include delirium, readiness for extubation, and withdrawal of life support. You usually cannot blind prone positioning, extracorporeal membrane oxygenation (ECMO), or fluid strategy. An open-label trial can still be credible when allocation is concealed and mortality follow-up is complete.

A **run-in period** is a phase before randomization. You can use it to confirm eligibility, stabilize treatment, train sites, or identify patients unable to follow the regimen. It can reduce avoidable variation. It can also make the randomized sample less representative if you exclude patients who cannot tolerate or follow treatment. Report these exclusions separately from losses after randomization. Randomization needs a valid, unpredictable sequence and correct implementation. It also assumes one patient’s treatment does not affect another’s, unless you use a cluster design. Measure outcomes in comparable ways across groups.

### 3. Visual / ASCII Schematic
```
Screen ICU population
       |
Eligible + consent -> optional pre-randomization run-in
       |                    |
       |              failures reported, NOT analysed as randomized
       v
Concealed central allocation
       |
  +----+----+
  |         |
Experimental  Control
  |         |
Blinding where feasible; equal follow-up; blinded adjudication
  +----+----+
       |
Analyse assigned groups (ITT) -> effect estimate + CI
```

### 4. Landmark ICU Clinical Anchor
**PROSEVA** was a multicentre, parallel-group trial of early prolonged prone positioning in severe acute respiratory distress syndrome (ARDS). It used central computer-generated allocation stratified by ICU. This properly separates recruitment from knowledge of allocation. Bedside staff could not realistically be blinded because they had to prone patients. Mortality is, however, a relatively objective endpoint. The trial demonstrated lower 28-day and 90-day mortality with early prone positioning in its selected severe-ARDS population ([PROSEVA trial summary](https://criticalcarereviews.com/foundational-trials/proseva)). Do not conclude that unblinded clinicians invalidate an RCT. When blinding is impossible, use objective outcomes, strict co-intervention protocols, concealed allocation, and complete outcome assessment.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** Randomization balances known and unknown baseline prognostic factors on average. Concealment limits selection bias. Blinding limits performance bias (different care because staff know allocation) and detection bias (different outcome assessment because assessors know allocation).
- **Clinical limitations:** Narrow ARDS or shock eligibility, delayed consent, and run-in exclusions can limit external validity (how well results apply to usual patients). Crossovers reduce the difference between treatments actually received.
- **Examiner traps:** Allocation concealment is not blinding. A random sequence is useless if recruiters can predict it. An open-label mortality RCT is not automatically biased. Excluding patients *after* randomization breaks the randomized comparison.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Randomization supports causal inference only when allocation is concealed and follow-up is comparable.
> - Concealment prevents pre-allocation selection bias; blinding prevents post-allocation performance/detection bias.
> - Run-in improves adherence but can reduce generalizability and must occur before randomization.

## Chapter 20: Randomization Strategies: Simple, Block, Stratified, Cluster

### 1. Definition & Mathematical Core
A randomization strategy sets the probability and method for assigning each eligible unit to a treatment. Under equal simple randomization, $P(A_i=1)=P(A_i=0)=0.5$. $A_i$ is the allocated arm for participant $i$. The realized group sizes and covariate balance vary by chance.

In a stratum (a subgroup defined before randomization) $s$, a useful balance metric is $D_s=n_{Es}-n_{Cs}$. $n_{Es}$ and $n_{Cs}$ are the numbers assigned to experimental and control arms in stratum $s$. Random permuted blocks limit $D_s$ while you recruit. Stratification aims to balance important prognostic subgroups.

### 2. Key Concepts, Principles & Assumptions
**Simple randomization** works well for large, quickly recruiting trials. It remains unpredictable. In a small intensive care unit (ICU) trial, chance can still produce temporary group imbalance. **Permuted-block randomization** balances assignments within blocks of size $b$. Use variable, concealed block sizes, especially in open-label trials. A fixed block of four can reveal the final assignment. A block is not a cluster.

**Stratified randomization** uses separate randomization lists for a few important prognostic variables. Common choices are site and illness severity. This is useful in multicentre acute respiratory distress syndrome (ARDS) trials because case mix and local practice vary. Too many strata create near-empty cells and defeat the purpose. If you need to balance several covariates, use minimization with a random component. Prespecify stratification variables. Usually include them in the adjusted analysis too.

**Cluster randomization** assigns groups, such as ICUs, hospitals, or time periods, rather than individual patients. Use it when a policy affects everyone in a unit. Examples include saline versus balanced-crystalloid policy, an antimicrobial-stewardship pathway, or a ventilator bundle. It makes the trial workable. It also means patients within one cluster are correlated, so the analysis must allow for this.

### 3. Visual / ASCII Schematic
```
Individual intervention, little contamination?
        |
        +-- Yes --> Large trial: SIMPLE randomization
        |            Small/slow trial: VARIABLE PERMUTED BLOCKS
        |            Major prognostic factor/site: STRATIFY or MINIMIZE
        |
        +-- No, policy spills across patients --> CLUSTER randomize ICU/hospital

Fixed blocks + open allocation list = predictable sequence = selection bias
```

### 4. Landmark ICU Clinical Anchor
In **ADRENAL**, patients with mechanically ventilated septic shock were centrally assigned to continuous-infusion hydrocortisone or placebo. The trial used a web-based minimization/randomization process. It was stratified by site and operative versus non-operative admission. Patients and clinicians were blinded ([ADRENAL statistical analysis plan](https://clinicaltrialsalliance.org.au/wp-content/uploads/2025/01/ADRENAL-SAP_ANZICS-CTG.pdf)). This balanced factors likely to affect prognosis while keeping assignment unpredictable. The trial did not show a mortality reduction at 90 days. Its allocation method makes imbalance in site practice or admission type an unlikely explanation.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** Simple randomization is maximally unpredictable. Blocks maintain numerical balance. Stratification balances strong prognostic factors. Cluster allocation limits contamination (spillover of an intervention into the comparison group).
- **Clinical limitations:** Too much stratification makes round-the-clock ICU enrolment harder. Predictable blocks threaten concealment. Cluster designs need more patients and more participating units.
- **Examiner traps:** Stratification alone is not adjustment. Balanced baseline variables cannot correct unequal protocol adherence. Do not analyse a cluster trial as though every patient were independent.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Use simple randomization when sample size is large; use concealed variable blocks when balance is needed during enrolment.
> - Stratify sparingly on powerful prognostic factors such as site or admission category.
> - Randomize clusters when the intervention is a unit-wide policy or contamination is unavoidable.

## Chapter 21: Sample Size Estimation: Determinants and Formulas for Proportions and Continuous Means

### 1. Definition & Mathematical Core
Sample size is the number of evaluable participants you need to detect a planned clinically important effect. You choose the type-I error (a false positive) and power (the chance of detecting a real effect). For equal-sized groups and a two-sided binary comparison, an approximation is
$$
n=\frac{\left[z_{1-\alpha/2}\sqrt{2\bar p(1-\bar p)}+z_{1-\beta}\sqrt{p_E(1-p_E)+p_C(1-p_C)}\right]^2}{(p_E-p_C)^2},
$$
Here, $n$ is participants per group. $z_q$ is the standard-normal quantile at probability $q$. $\alpha$ is type-I error and $1-\beta$ is power. $p_E$ and $p_C$ are expected experimental and control event risks. $\bar p=(p_E+p_C)/2$.

For a continuous endpoint (a measurement on a scale, such as mean ventilator-free days) with common standard deviation (SD), $$n=\frac{2\sigma^2(z_{1-\alpha/2}+z_{1-\beta})^2}{\delta^2},$$ $\sigma$ is the assumed within-group standard deviation. $\delta$ is the target mean difference. Increase recruitment for expected attrition (patients whose outcomes will be unavailable): $n_{recruit}=n/(1-L)$, where $L$ is expected loss proportion.

### 2. Key Concepts, Principles & Assumptions
Do not choose a sample size from the desired $P$ value alone. Choose one primary endpoint. Estimate the baseline event rate or standard deviation from a similar population. State the **minimum clinically important difference**. State sidedness too. This means whether you test one direction or both. Specify power, allocation ratio, and expected non-adherence or loss. Account for multiple testing and interim monitoring. Multiple testing means extra false-positive risk from several tests. Interim monitoring means planned looks at trial data before the end. In intensive care unit (ICU) mortality trials, you need far more patients when control mortality is lower than expected. You also need more patients when the target absolute reduction is small. Ventilator-free days can be non-normal. Death also complicates their meaning. Define that endpoint carefully and often use simulation rather than a naïve normal approximation.

The formulas assume independent observations and valid variance assumptions. They also assume accurate nuisance parameters (inputs such as control risk), equal allocation, and a conventional fixed design. Unequal allocation, clustering, covariate adjustment, repeated measures, non-inferiority, and group-sequential monitoring change the calculation. A well-powered trial can still chase a clinically trivial effect. A negative underpowered trial cannot show there is no benefit.

### 3. Visual / ASCII Schematic
```
Choose primary outcome and estimand
            |
Control risk / SD ----> Clinically important delta
            |                    |
alpha, power, sidedness, allocation, losses, clustering/interims
            |
        Calculate n
            |
Sensitivity analysis: optimistic / plausible / pessimistic assumptions
```

### 4. Landmark ICU Clinical Anchor
**ANDROMEDA-SHOCK** compared a peripheral-perfusion-targeted resuscitation strategy with lactate-targeted resuscitation in early septic shock. Its planned sample assumed a large, clinically important absolute mortality difference. The enrolled trial did not reach conventional statistical significance for its primary mortality outcome. The direction favoured the peripheral-perfusion strategy ([trial record](https://clinicaltrials.gov/study/NCT03078777)). The assumed control risk and effect size decide what question your trial can answer. Planning for a large benefit makes a trial feasible. It leaves limited power for smaller benefits that may still matter clinically.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** It forces you to state a clinical target. It protects against a trial that is too small to help. Sensitivity analyses show how much the result depends on assumptions.
- **Clinical limitations:** ICU mortality, crossover, competing risks (events that prevent the outcome of interest), and centre variation make historical control rates unstable. Plan for losses before recruitment, not after it.
- **Examiner traps:** $n$ is normally **per group** in the displayed formulas. Power is $1-\beta$, not $\beta$. A non-significant result does not prove the true effect is zero. Do not power a trial from a post hoc observed effect.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Base sample size on the primary endpoint, plausible control risk/SD, and a clinically meaningful effect.
> - Smaller target effects, higher power, lower alpha, attrition, clustering, and interim looks generally increase recruitment.
> - A negative underpowered trial is inconclusive, not evidence of equivalence.

## Chapter 22: ITT, Modified ITT, and Per-Protocol Analyses: Strengths and Pitfalls

### 1. Definition & Mathematical Core
**Intention-to-treat (ITT)** compares patients by their random assignment. It does this regardless of adherence, crossover (switching to the other treatment), or treatment received. The ITT estimand is the exact treatment effect your analysis aims to estimate. For a binary outcome, it is $RD_{ITT}=P(Y=1\mid A=1)-P(Y=1\mid A=0)$. Here, $Y$ is the observed outcome and $A$ is randomized allocation.

**Modified ITT (mITT)** excludes a prespecified group after randomization. This often includes patients never dosed, later found ineligible, or lacking a baseline measurement. **Per-protocol (PP)** compares patients who adhered sufficiently to their assigned protocol. If $R=1$ denotes protocol adherence, a naïve contrast is $P(Y=1\mid A=1,R=1)-P(Y=1\mid A=0,R=1)$. Randomization no longer protects this comparison because $R$ occurs after allocation.

### 2. Key Concepts, Principles & Assumptions
ITT keeps the benefit of randomization. It estimates the effect of a treatment **policy**. It is usually the least biased primary analysis for superiority trials. Keep outcome data when a patient stops hydrocortisone, receives rescue extracorporeal membrane oxygenation (ECMO), or departs from a fluid protocol. ITT has a trade-off. Widespread non-adherence or rescue treatment in the control group reduces the contrast between the treatments actually delivered.

mITT is reasonable only when exclusions are prespecified, objective, rare, balanced, and biologically defensible. “Received at least one dose” can be dangerous in septic shock. Death before dosing contains prognostic information and may differ between groups. PP asks a different question that depends on adherence. It is vulnerable to survivor bias (including only people who lived long enough to adhere). It is also vulnerable to confounding by severity and informative censoring (loss of follow-up related to prognosis). A credible PP estimate needs a prespecified adherence definition. It also needs methods such as inverse-probability weighting. This gives more weight to patients who resemble those lost or non-adherent. Instrumental-variable approaches use random assignment to estimate the effect of treatment received. PP is not just a second unadjusted table.

### 3. Visual / ASCII Schematic
```
Randomized --------------> ITT: analyse all by assigned arm
     |
     +--> never received / ineligible after randomization
     |          |
     |          +--> mITT only if exclusion is prespecified and unbiased
     |
     +--> crossed over / non-adherent
                |
                +--> PP: selection after randomization; supportive, not automatically causal
```

### 4. Landmark ICU Clinical Anchor
In **EOLIA**, patients with very severe acute respiratory distress syndrome (ARDS) were assigned to immediate venovenous extracorporeal membrane oxygenation (ECMO) or conventional management. Control-arm crossover to rescue ECMO was allowed for refractory hypoxaemia. A substantial minority crossed over. The primary ITT comparison therefore estimates an *early-ECMO strategy with rescue ECMO available* versus conventional management with rescue ECMO. It does not estimate the biological efficacy of ECMO with perfect treatment separation. Sixty-day mortality directionally favoured early ECMO but did not reach conventional statistical significance ([EOLIA report](https://criticalcare.cooperhealth.org/fellows/wp-content/uploads/sites/4/2019/07/EOLIA-TRIAL.pdf)). If you exclude the sick control patients who crossed over, conventional care can look deceptively better in PP analysis. Crossover is not a reason to abandon ITT.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** ITT preserves baseline comparability and estimates real-world policy effectiveness. PP describes how faithfully treatment was delivered. It can help when you present it alongside ITT.
- **Clinical limitations:** Rescue therapy and non-adherence can hide a biological efficacy signal. mITT definitions vary across ICU trials, so read the protocol.
- **Examiner traps:** ITT means “as randomized,” not “as treated.” mITT is not a universally standard population. PP does not become less biased just because it removes crossovers.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - ITT is the default primary analysis for superiority because it preserves randomization.
> - mITT must be prespecified and justified; post-randomization exclusions risk bias.
> - PP estimates are selection-prone and should complement, not replace, a transparent ITT analysis.

## Chapter 23: Non-Inferiority and Equivalence Trials: Defining the Margin (Delta), Why Both ITT and PP Are Required

### 1. Definition & Mathematical Core
A **non-inferiority (NI)** trial asks whether a new treatment is not unacceptably worse than an effective active control. You set the maximum acceptable loss in advance as the margin $\Delta$. For an adverse binary outcome, use $D=p_N-p_C$. $p_N$ and $p_C$ are event risks with new and control treatment. You conclude NI when the upper confidence bound for $D$ is less than $\Delta$. A confidence interval (CI) provides this bound. $\Delta>0$ is the largest clinically acceptable excess risk.

An **equivalence** trial asks whether effects stay within both acceptable limits: $-\Delta_L< D < \Delta_U$, where $\Delta_L$ and $\Delta_U$ are lower and upper clinically acceptable differences. A two-sided $100(1-2\alpha)\%$ confidence interval must sit completely inside the equivalence interval.

### 2. Key Concepts, Principles & Assumptions
Do not choose the margin after seeing the outcomes. It must retain a clinically credible portion of the active control’s proven benefit over placebo or historical care. It must also allow for uncertainty in that evidence. Patients and clinicians must accept the trade-off. If continuous renal replacement therapy (CRRT) benefits a particular indication, an NI sustained low-efficiency dialysis (SLED) trial must state the loss you would accept. This may be loss of haemodynamic stability, solute control, renal recovery, or survival. The reason might be lower cost or easier delivery. A wide margin can label an ineffective treatment acceptable.

NI also needs **assay sensitivity**. This means the trial could detect a difference if one really exists. The patients, control delivery, adherence, endpoints, and follow-up must resemble the earlier evidence. This is the constancy assumption. A non-significant superiority test does not prove NI. Crossover, non-adherence, and missing data often make groups look more alike. They can produce false NI. Regulators and methodologists therefore expect consistent ITT and PP analyses. ITT preserves allocation, but can be conservative for superiority and anti-conservative for NI. PP has selection bias, but tests treatment separation. If the analyses disagree, treat that as a warning. Do not simply select the favourable result.

### 3. Visual / ASCII Schematic
```
Bad outcome difference D = risk(new) - risk(control)

<---- new better ----|---- no difference ----|---- unacceptable worse ---->
                    0                       Delta

95% CI wholly left of Delta        -> non-inferior
95% CI crosses Delta               -> NI not shown
95% CI wholly within -Delta to +Delta -> equivalent (if both bounds used)
```

### 4. Landmark ICU Clinical Anchor
The SLED-versus-CRRT acute kidney injury (AKI) literature is a useful warning. It does not show that the treatments are interchangeable. Comparative intensive care unit (ICU) cohorts found no clear adjusted mortality difference. Their confidence intervals were wide enough to allow important benefit or harm ([SLED versus CRRT cohort](https://pmc.ncbi.nlm.nih.gov/articles/PMC4522955/)). You need a prospectively justified $\Delta$, valid active-control assumptions, and a confidence interval fully within the margin. Without them, “no significant difference” is **not** non-inferiority. Interpret transfusion-threshold randomized controlled trials (RCTs) such as TRICC or HEMOTION by their prespecified superiority hypotheses. A non-significant superiority test does not establish that two thresholds are clinically equivalent.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** It lets you evaluate a simpler, safer, cheaper, or more available therapy. This works when a modest loss of efficacy may be acceptable. Confidence intervals directly answer the margin question.
- **Clinical limitations:** Control benefit and constancy may be uncertain as ICU care changes. Margins may be ethically contentious. Adherence and rescue therapy threaten assay sensitivity.
- **Examiner traps:** NI is one-sided in clinical interpretation, even when you report a two-sided confidence interval (CI). Failing to prove superiority is not NI. Equivalence requires ruling out meaningful benefit and meaningful harm. Report both ITT and PP.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Define Delta prospectively from preserved active-control benefit and clinical acceptability.
> - For harm-oriented risk differences, NI requires the upper CI bound to remain below Delta.
> - Concordant ITT and PP analyses are required because non-adherence can falsely favour NI.

## Chapter 24: Factorial Trials (2×2 Designs): Structure, Efficiency, Interaction Effects

### 1. Definition & Mathematical Core
A **2×2 factorial randomized controlled trial (RCT)** assigns each participant to one level of intervention A and one level of intervention B. This creates four groups: $A+B+$, $A+B-$, $A-B+$, and $A-B-$. A linear factorial model estimates the separate and combined effects. $E(Y)=\beta_0+\beta_AA+\beta_BB+\beta_{AB}(A\times B)$. $Y$ is the outcome. $A$ and $B$ are treatment indicators. $\beta_A$ and $\beta_B$ are main effects. $\beta_{AB}$ is the interaction effect.

The main effect of A averages A’s outcome across both levels of B. This is efficient when the effect of A is reasonably similar across B assignments. Check that assumption with the interaction term.

### 2. Key Concepts, Principles & Assumptions
Factorial trials answer two independent treatment questions in one patient group. Use one when both interventions can be delivered at the same time. Neither treatment should stop the other being given. In septic shock, you could randomize insulin target and extra fludrocortisone at the same time. Each participant then informs both main-effect comparisons. You may need far fewer patients than for two separate RCTs.

A strong interaction reduces this efficiency. An interaction means the effect of one treatment changes depending on the other. For example, restrictive glucose control may be harmful only with one corticosteroid regimen. An average glucose effect could then hide the important clinical difference. Prespecify biologically plausible interactions. Power the trial realistically when detecting an interaction is a main aim. Do not hunt indiscriminately through subgroups. The participant remains the unit of analysis. Balance co-interventions, adherence, and timing for both factors. A factorial design is more than a four-arm trial. Its analysis uses the crossed structure.

### 3. Visual / ASCII Schematic
```
                         Factor B
                    B+                 B-
Factor A  A+   A+B+ group          A+B- group
          A-   A-B+ group          A-B- group

Main effect A: compare all A+ vs all A-
Main effect B: compare all B+ vs all B-
Interaction: does effect of A differ between B+ and B-?
```

### 4. Landmark ICU Clinical Anchor
**COIITSS** (Corticosteroids and Intensive Insulin Therapy for Septic Shock) used a genuine multicentre 2×2 factorial design. It crossed intensive versus conventional glucose control with fludrocortisone versus no fludrocortisone. All patients received hydrocortisone for septic shock ([COIITSS trial synopsis](https://www.thebottomline.org.uk/summaries/icm/coiitss/)). The design answered two treatment questions without needing two separate septic-shock cohorts. It found no clear mortality advantage from intensive insulin therapy or from added fludrocortisone in that setting. When appraising it, identify the planned main effects. Then ask whether the trial credibly assessed an A×B interaction. Four groups alone do not validate pooled main-effect conclusions.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** It tests two interventions efficiently. It shares recruitment, control patients, and infrastructure. It can identify synergism (a combined effect greater than expected) or antagonism (one treatment weakening another).
- **Clinical limitations:** Interaction can reduce power and make results harder to interpret. A burdensome combination may reduce adherence. Eligibility must suit both treatment questions.
- **Examiner traps:** Factorial does not mean every four-cell comparison has enough power. Main effects average across the other factor. A non-significant interaction does not prove that no clinically important interaction exists.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - A 2×2 factorial design randomizes two interventions simultaneously, creating four cells.
> - Main effects are efficient only when interaction is absent or clinically negligible.
> - Prespecify and interpret the A×B interaction; do not treat factorial data as an unplanned four-arm trial.

## Chapter 25: Cluster-Randomized and Stepped-Wedge Designs: ICC, Infection-Control Bundle Trials

### 1. Definition & Mathematical Core
A **cluster-randomized trial** assigns groups, such as intensive care units (ICUs), rather than individual patients. Outcomes within one group are correlated. The design effect (DE) is $DE=1+(m-1)\rho$. $m$ is mean cluster size. $\rho$ is the intracluster correlation coefficient (ICC), the correlation between two patients from the same cluster. The approximate effective individual sample size is $N_{eff}=N/DE$, where $N$ is total enrolled patients.

A **stepped-wedge cluster randomized controlled trial (RCT)** starts every cluster in the control condition. Clusters then move to the intervention in randomly allocated time periods. With $Y_{ijk}$ representing outcome for patient $i$ in cluster $j$ during period $k$, analyses include both cluster and period terms to separate intervention effect from secular time trends.

### 2. Key Concepts, Principles & Assumptions
Cluster allocation prevents contamination when clinicians cannot apply competing unit-wide policies to adjacent patients. It suits order-set changes, catheter-care bundles, surveillance practices, and a default balanced-fluid policy. You pay for this with less information. Even a small ICC can greatly increase the needed sample when each ICU contributes many patients. The number of clusters drives precision more than the total number of patients. Use mixed-effects models that allow for ICU-level differences. You can also use generalized estimating equations (GEE), which adjust for within-ICU correlation. Use confidence intervals that account for clustering.

In a stepped wedge, every ICU eventually receives the intervention. This can make an infection-control bundle easier to accept when staff think it will help. The central problem is **secular confounding**. This means calendar-time changes occur alongside rollout. Staffing, pathogen prevalence, ventilation practice, or a pandemic wave may change during the trial. Use a randomized sequence and enough observations before intervention. Include transition or wash-in periods. Adjust explicitly for time period. Do not use this design if the intervention must later be withdrawn. Avoid it when effects are immediate but unstable. It also does not suit urgent outbreak implementation.

### 3. Visual / ASCII Schematic
```
Stepped wedge: each row = ICU cluster; X = intervention
Period          1   2   3   4   5   6
ICU 1           C   X   X   X   X   X
ICU 2           C   C   X   X   X   X
ICU 3           C   C   C   X   X   X
ICU 4           C   C   C   C   X   X

ICC > 0  -> patients in one ICU are partly redundant -> inflate N by DE
```

### 4. Landmark ICU Clinical Anchor
**SMART** assigned participating ICUs in a multiple-crossover cluster design. Units used balanced crystalloids or saline as the default intravenous crystalloid. You could not reliably randomize this policy by individual patient. Stock, order sets, and clinician habits would contaminate the groups. The analysis therefore accounted for the unit and time allocation structure ([SMART trial report](https://www.nejm.org/doi/full/10.1056/NEJMoa1711584)). For a stepped-wedge infection-control example, the **CHORAL** protocol randomizes six ICUs to sequentially stop chlorhexidine prophylaxis. They then implement an oral-care bundle for ventilated patients. All units start with control care ([CHORAL protocol](https://pmc.ncbi.nlm.nih.gov/articles/PMC6814100/)). Its key epidemiological threat is a time-varying change in ventilator-associated infection risk. Simple patient-level confounding is not the main concern.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** It prevents contamination and tests pragmatic ICU policies. It permits staged training and implementation. A stepped wedge gives every cluster eventual access.
- **Clinical limitations:** ICC inflation, few clusters, uneven cluster sizes, secular trends, and delayed intervention effects can determine the result.
- **Examiner traps:** More patients in one ICU cannot replace more ICUs. Never use an ordinary independent two-sample test for clustered observations. A stepped wedge is not automatically ethical or unbiased just because every cluster eventually crosses.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Cluster trials randomize the ICU/hospital and require ICC-aware design and analysis.
> - $DE=1+(m-1)\rho$ explains why many correlated patients add less information than expected.
> - Stepped-wedge analyses must adjust for calendar period and account for transition effects.

## Chapter 26: Adaptive Platform Trials: MAMS, Response-Adaptive Randomization, Bayesian Models (REMAP-CAP)

### 1. Definition & Mathematical Core
An **adaptive platform trial** is a long-running master protocol. It tests multiple interventions. It uses planned changes based on accumulating data. It can add or retire trial arms. In a Bayesian model, the posterior is $p(\theta\mid D)\propto p(D\mid\theta)p(\theta)$. The posterior is your updated belief after seeing the data. $\theta$ is the treatment-effect parameter and $D$ is observed trial data. $p(\theta)$ is the prior distribution, or what you believed before seeing these data. $p(D\mid\theta)$ is the likelihood, or how compatible the data are with possible effects.

A decision rule might declare superiority when $P(\theta>0\mid D)>c_S$. It might declare futility when $P(\theta>\theta_{min}\mid D)<c_F$. $c_S$ and $c_F$ are prespecified probability thresholds. $\theta_{min}$ is the minimum worthwhile effect. **Multi-arm multi-stage (MAMS)** designs compare several arms with a common control at scheduled interim stages. Response-adaptive randomization (RAR) changes future allocation probabilities using prespecified evidence rules.

### 2. Key Concepts, Principles & Assumptions
“Adaptive” does not mean you can make it up as you go. Prespecify adaptations, endpoints, borrowing rules, multiplicity control, and operating characteristics. Operating characteristics describe how the design behaves across many simulated trials. Simulate the design extensively before recruitment. MAMS can stop futile or inferior arms early. It shares a contemporaneous control (patients enrolled in the same period). This improves efficiency in a fast-changing syndrome such as severe COVID-19. A platform keeps its infrastructure while new treatment domains enter.

RAR may give later patients a higher chance of receiving arms with favourable posterior results. It complicates balance over calendar time, estimation, communication, and logistics. It is not automatically more ethical. Early random variation can change later allocation. Consent language must explain this clearly. Bayesian hierarchical models can partly pool related groups or interventions. This can increase precision. Their prior assumptions and borrowing rules must be transparent. Contemporaneous controls matter when survival changes with proning, steroid uptake, vaccination, or intensive care unit (ICU) strain. Historical controls from a different period are especially risky.

### 3. Visual / ASCII Schematic
```
Master protocol / common data platform
          |
Domain 1: A vs control ----> interim Bayesian/MAMS rule ----> continue / stop / graduate
Domain 2: B vs control ----> interim Bayesian/MAMS rule ----> continue / stop / graduate
Domain 3: add new arm ---------------------------------------> enter platform
          |
Prespecified RAR weights may alter future allocation, with time-stratified analysis
```

### 4. Landmark ICU Clinical Anchor
**REMAP-CAP** is an international randomized embedded multifactorial adaptive platform for severe community-acquired pneumonia and pandemic respiratory illness. It randomizes patients across treatment **domains**. This lets investigators evaluate several interventions and planned interactions at once. Bayesian models support frequent analyses and stopping decisions. In selected periods, they also support response-adaptive allocation ([REMAP-CAP design paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC7328186/)). During COVID-19, the platform produced domain-specific conclusions. It accounted for patient strata and changing care. Do not reduce its success to “Bayesian equals faster.” Its credibility depends on planned decision thresholds, governance, contemporaneous comparisons, and clear reporting of arm availability by site and time.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** It tests multiple therapies efficiently. It shares infrastructure and control information. It stops futile arms earlier. It can respond during an epidemic.
- **Clinical limitations:** Complex simulations, data delays, changing standards of care, non-concurrent controls, and unequal arm availability can threaten interpretation.
- **Examiner traps:** MAMS is not always response-adaptive. A Bayesian posterior probability is not a frequentist $P$ value. Adaptive randomization does not remove the need for concealment, a prespecified analysis, or independent oversight.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Platform trials use a master protocol to add, stop, and compare multiple interventions over time.
> - MAMS uses interim stage decisions; RAR changes future allocation probabilities; both require prospective simulation.
> - REMAP-CAP couples multifactorial domains with Bayesian decision rules and contemporaneous ICU comparisons.

### Section Recap: Which Test / Which Effect Measure
```
Choose a trial design
|
+-- One patient-level intervention; minimal contamination?
|   |
|   +-- Superiority question --> Individually randomized parallel RCT
|   |      Effect: RD/RR/OR for binary outcome; MD for continuous outcome; HR for time-to-event
|   |
|   +-- New therapy acceptable if not clinically worse? --> Non-inferiority RCT
|   |      Measure: CI for D = risk(new)-risk(control) against prespecified Delta
|   |
|   +-- Need to exclude meaningful benefit AND harm? --> Equivalence RCT
|          Measure: CI wholly inside (-Delta, +Delta)
|
+-- Two independently deliverable interventions? --> 2x2 factorial RCT
|      Effects: main effects A and B; test A×B interaction
|
+-- Unit-wide policy/bundle; contamination unavoidable? --> Cluster RCT
|      Measure/model: ICC-aware mixed model or GEE; inflate by DE = 1+(m-1)rho
|      |
|      +-- Phased, randomized roll-out to all units? --> Stepped-wedge cluster RCT
|             Include cluster and calendar-period effects
|
+-- Multiple interventions/arms expected to enter or leave? --> Adaptive platform / MAMS
       Measure: prespecified Bayesian posterior probabilities or stagewise decision statistics
```
For a superiority policy question, use **ITT** as the main estimand. Show PP as a supportive efficacy analysis when adherence matters. Use a CI, not a non-significant $P$ value, to judge non-inferiority, equivalence, and precision. In cluster trials, ICUs or hospitals are the scarce independent units. In adaptive platforms, preserve contemporaneous controls and predeclare every adaptation.
# SECTION 5: SURVIVAL ANALYSIS, EFFECT SIZES & TIME-TO-EVENT

## Chapter 27: Measures of Association: Risk Ratio, Odds Ratio, Hazard Ratio Compared

### 1. Definition & Mathematical Core
A **risk ratio (RR)** compares the chance of an outcome by a stated time. An **odds ratio (OR)** compares the odds of an outcome. A **hazard ratio (HR)** compares event rates at each instant among patients who have not yet had the event. For a binary endpoint (an outcome with two possibilities), let $a$ and $b$ be events and non-events in the treatment group. Let $c$ and $d$ be events and non-events in the control group. Then

$$RR=\frac{R_T}{R_C}=\frac{a/(a+b)}{c/(c+d)}, \qquad OR=\frac{a/b}{c/d}=\frac{ad}{bc}.$$ 

Here, $R_T$ and $R_C$ are the treatment and control risks. For time-to-event data, $HR(t)=h_T(t)/h_C(t)$, where $h_T(t)$ and $h_C(t)$ are the treatment and control hazards at time $t$. Each hazard is conditional on being alive and event-free immediately before $t$. An HR usually comes from a statistical model. An RR compares observed risks at a chosen time point.

**Absolute risk reduction (ARR)** is the difference between the two group risks. **Number needed to treat (NNT)** is the number treated to prevent one event. Kaplan–Meier (KM) estimates survival over time. A Cox model estimates HRs from time-to-event data. The examples use intensive care unit (ICU) outcomes.

### 2. Key Concepts, Principles & Assumptions
RR and OR answer different questions, even when you calculate both from the same $2\times2$ table. RR is usually easiest to explain for 28-day mortality. For example, $RR=0.80$ means cumulative mortality was 20% lower relative to the control group. OR suits logistic regression (a model for yes/no outcomes), case-control studies, and matched analyses. It is **not** a risk ratio. When an outcome is common, as in severe acute respiratory distress syndrome (ARDS) mortality, an OR farther from 1 looks more dramatic than the RR. OR approximates RR only when the event is rare.

HR uses when events happen. It also handles unequal follow-up and independent right-censoring (when follow-up ends for reasons unrelated to a patient’s future event risk). It is not the ratio of 28-day death risks. You also cannot call it a “percent reduction in mortality” without qualification. **Proportional hazards (PH)** means the relative hazard stays constant over time. Crossing survival curves can break that assumption. Early procedure-related harm followed by later benefit can also make one HR misleading. State the time horizon and absolute risks. Also report the 95% confidence interval (CI, a range of effect sizes compatible with the data) and the analysis population with every relative measure.

| Measure | Data/denominator | Main interpretation | Best use | Principal trap |
|---|---|---|---|---|
| **RR** | Events / everyone randomized in each group at a fixed time | Ratio of cumulative risks | Randomized controlled trial (RCT) binary endpoint, e.g. day-28 mortality | Can hide the absolute baseline risk |
| **OR** | Events / non-events | Ratio of odds | Logistic regression; case-control study | Often mistaken for RR when the outcome is common |
| **HR** | Event times and risk sets (the patients still able to have the event) | Ratio of instantaneous hazards | Censored time-to-death data | Not a risk ratio; you must assess PH |

### 3. Visual / ASCII Schematic
```text
                 Fixed 28-day endpoint?
                         |
             +-----------+-----------+
             |                       |
            Yes                      No / censoring
             |                       |
       Report risk + RR          Kaplan–Meier / Cox
             |                       |
      Also ARR and NNT          Report HR + survival at time t
             |
   Logistic regression used? ----> adjusted OR (label it OR)

Common outcome: OR 0.60 does NOT imply RR 0.60.
```

### 4. Landmark ICU Clinical Anchor
In **SOAP II**, 1,679 patients with shock were randomized to dopamine or norepinephrine. The prespecified 28-day mortality comparison reported an OR of 1.17 for dopamine versus norepinephrine (95% CI 0.97–1.42). There was no statistically significant mortality difference. Arrhythmias (abnormal heart rhythms) were more frequent with dopamine ([SOAP II summary and reanalysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC11385121/)). This is an examiner-grade reminder to label the measure correctly. The OR describes the odds of death by day 28. It does not give the ratio of death risks or a time-to-death HR. Mortality was common, so you cannot translate the OR into “17% higher risk.” Its CI includes 1. It is compatible with modest benefit or harm on the odds scale. Interpret the clinically important excess arrhythmia outcome separately on an absolute scale.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** RR is intuitive and you can convert it directly to absolute risk reduction (ARR). OR allows adjusted logistic models and case-control inference. HR uses event timing and censoring efficiently.
- **Report absolute effects:** A favourable RR can still mean very little when baseline mortality is low. Give the control risk and ARR, not the RR alone.
- **Do not equate measures:** As event incidence rises, OR becomes more extreme than RR. HR does not imply the same absolute risk difference at every time.
- **Do not call an HR “survival benefit” without its time horizon and PH assessment.**
- A non-proportional treatment effect needs time-varying HRs, restricted mean survival time (RMST, average event-free survival over a stated period), or landmark risks.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - **RR** compares fixed-time risks; pair it with ARR and baseline risk.
> - **OR** compares odds and overstates relative magnitude for common ICU outcomes.
> - **HR** compares conditional event rates over time; it is validly summarized by one number only when PH is plausible.

## Chapter 28: ARR, RRR, NNT / NNH: Formulas, Worked ICU Example

### 1. Definition & Mathematical Core
**Absolute risk reduction (ARR)** is how much treatment lowers risk. **Relative risk reduction (RRR)** expresses that fall as a proportion of the control risk. The **risk ratio (RR)** is treatment risk divided by control risk. **Number needed to treat (NNT)** is the number of patients you need to treat to prevent one beneficial outcome. With $R_C$ as control-event risk and $R_T$ as treatment-event risk at a stated horizon,

$$ARR=R_C-R_T, \qquad RR=\frac{R_T}{R_C}, \qquad RRR=1-RR=\frac{R_C-R_T}{R_C}, \qquad NNT=\frac{1}{ARR}.$$ 

For a harmful event, $ARI=R_T-R_C$ is **absolute risk increase (ARI)**. $NNH=1/ARI$ is the **number needed to harm (NNH)**, or the number treated for one extra harmful event. Use proportions rather than percentages in these formulas. Round NNT and NNH **up** to the next whole patient. Always state the follow-up time. The worked example below uses acute respiratory distress syndrome (ARDS).

### 2. Key Concepts, Principles & Assumptions
ARR answers the bedside question. It tells you how many fewer deaths, renal-replacement starts, or reintubations occur per 100 treated patients. RRR travels poorly between populations because it leaves out baseline risk. A treatment with the same RR gives a larger ARR in high-risk septic shock than in low-risk postoperative intensive care unit (ICU) patients. That larger ARR gives a smaller NNT. NNT is not a fixed property of a treatment. It also cannot replace its confidence interval (CI).

NNT assumes a comparable population, treatment strategy, outcome definition, and time horizon. For time-to-event outcomes with censoring (follow-up ending before the event is observed), $1/ARR$ makes sense only after you estimate risks at a fixed time. That might be 28 or 90 days. A Kaplan–Meier estimate is a survival probability that accounts for censoring. An NNT made by subtracting two Kaplan–Meier risks must name that time. If the CI for ARR crosses zero, its reciprocal breaks apart mathematically. Report the ARR CI directly. Do not force a misleading single NNT interval.

### 3. Visual / ASCII Schematic
```text
                Day-28 mortality in severe ARDS

                 Death      Alive       Total
Prone              38        199         237   RT = 38/237 = 0.160
Supine             75        154         229   RC = 75/229 = 0.328

ARR = 0.328 - 0.160 = 0.168  = 16.8 fewer deaths / 100 treated
RRR = 0.168 / 0.328 = 0.512  = 51.2%
NNT = 1 / 0.168 = 5.95  --> round up to 6
```

### 4. Landmark ICU Clinical Anchor
The **PROSEVA** trial randomized adults with early severe ARDS to prolonged prone sessions or supine ventilation. Day-28 mortality was 16.0% with prone positioning and 32.8% with supine positioning ([trial report](https://www.nejm.org/doi/full/10.1056/NEJMoa1214103/)). Thus $ARR=0.328-0.160=0.168$ (16.8 percentage points), $RR=0.488$, $RRR=51.2\%$, and $NNT=5.95$, conventionally reported as **NNT 6 to prevent one day-28 death**. This is a large treatment effect in a selected high-risk severe-ARDS group receiving lung-protective ventilation. Do not automatically apply it to less severe hypoxaemia, late proning, or units that cannot safely provide long prone sessions. The study also showed that survival curves and HRs add time-to-event information. NNT is an absolute summary at one fixed time. It does not replace survival analysis.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** ARR and NNT communicate absolute benefit. NNH makes you balance benefit against harm, such as mortality benefit versus proning-related adverse events.
- **Use the correct direction:** For death, lower is better and $ARR=R_C-R_T$. For ventilator-free survival, define the favourable event before calculating NNT.
- **Never derive NNT from an OR.** Convert to risks only when justified. State the assumed baseline risk.
- **Avoid false precision:** “NNT 6 at 28 days” is interpretable. “NNT 5.95” is not. A negative ARR means harm. Express it as ARI/NNH.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - $ARR=R_C-R_T$; it is the most decision-relevant effect measure.
> - $RRR=ARR/R_C$ and can appear impressive despite a small ARR.
> - NNT/NNH require a population, outcome, and time horizon; round upward and report uncertainty.

## Chapter 29: Kaplan-Meier Survival Analysis: Product-Limit Method, Right-Censoring, Log-Rank Test

### 1. Definition & Mathematical Core
The **Kaplan–Meier (KM) estimator** is a non-parametric (not based on an assumed distribution shape) product-limit estimate of survival probability. A product-limit estimate multiplies conditional survival probabilities at each event time. It includes right-censored observations, where follow-up stops before you observe the event. At ordered event times $t_j$, with $d_j$ events and $n_j$ individuals event-free and uncensored immediately before $t_j$,

$$\widehat S(t)=\prod_{t_j\leq t}\left(1-\frac{d_j}{n_j}\right).$$

Here, $\widehat S(t)$ is the estimated probability of staying event-free beyond time $t$. A **log-rank test** compares observed and expected events between groups across all event times. Its null hypothesis says the survival functions are equal.

### 2. Key Concepts, Principles & Assumptions
When a death occurs, the KM curve steps down. When a patient is right-censored, the curve does not fall. The patient simply leaves later risk sets. Censoring happens when follow-up ends, consent is withdrawn, or outcome status becomes unknown before the event. Valid inference needs **non-informative censoring** after accounting for measured information. In plain terms, a patient censored at day 12 should have the same future prognosis as similar patients still observed. You cannot casually censor intensive care unit (ICU) discharge for ICU-acquired infection. Discharge stops later observation and is a competing event (an event that prevents the outcome of interest), not ordinary censoring.

The log-rank test gives roughly equal weight to event times under proportional hazards (PH). It works best when hazards are proportional. It gives you a P value, not the clinical size of an effect. Show the KM plot with numbers at risk. Report survival at useful landmarks, such as day 28 and day 90. Add a hazard ratio (HR) or risk difference with a confidence interval (CI) when appropriate. Median survival is the time by which half the group has had the event. You often cannot estimate it in intensive care unit (ICU) trials because fewer than half of patients die. Do not invent a median just because you have shown a KM curve.

### 3. Visual / ASCII Schematic
```text
Survival probability
1.00 | treatment  ────────────┐
     |                         └─────
     | control    ───────┐
     |                   └──────────
0.00 +----+----+----+----+---- time
      0   7   14   28   90 days

| = death/event produces a step down
+ = right-censored: no drop; removed from later risk sets
Log-rank: compares observed versus expected deaths at every step.
```

### 4. Landmark ICU Clinical Anchor
**EOLIA** studied early venovenous extracorporeal membrane oxygenation (ECMO, a machine that oxygenates blood outside the body) in very severe acute respiratory distress syndrome (ARDS). It compared early ECMO with conventional management. Rescue ECMO was allowed for refractory hypoxaemia (oxygen levels that remain dangerously low despite treatment). The primary 60-day mortality comparison favoured early ECMO directionally but did not reach conventional statistical significance ([EOLIA report](https://www.nejm.org/doi/full/10.1056/NEJMoa1800385/)). Survival curves help here because they show when deaths occur. They also show the shrinking number still at risk and whether early separation lasts. The curve cannot fix an open-label design with clinically important rescue crossover. Read it with the trial’s intention-to-treat (patients analysed in their randomized groups) fixed-horizon analysis. In a board answer, say that KM describes observed time to death under censoring. The causal treatment estimate still comes from the randomized comparison.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** It handles unequal follow-up. It shows event timing. It estimates survival at clinically useful time points.
- **Report numbers at risk and censor marks.** A dramatic-looking tail based on few survivors is unstable.
- **Do not treat competing events as non-informative censoring.** For ventilator-associated pneumonia (VAP), alive ICU discharge makes later ICU VAP impossible. Use a cumulative-incidence approach.
- **Do not equate a non-significant log-rank P value with no effect.** Inspect the CI and power (the chance of detecting a real effect). Log-rank may miss an effect when hazards are not proportional.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - KM survival is a product of conditional survival probabilities at event times.
> - Right-censored patients contribute follow-up until censoring; they do not create a curve drop.
> - Log-rank tests equality of survival curves but does not quantify effect size or solve competing risks.

## Chapter 30: Cox Proportional Hazards Model: Assumptions, Schoenfeld Residuals, and Time-Varying Covariates

### 1. Definition & Mathematical Core
The **Cox proportional-hazards model** links covariates (patient or treatment characteristics) to the hazard. It does not assume a particular shape for the baseline hazard:

$$h(t\mid \mathbf X)=h_0(t)\exp(\beta_1X_1+\cdots+\beta_pX_p), \qquad HR_k=\exp(\beta_k).$$

Here, $h(t\mid\mathbf X)$ is the hazard at time $t$ for covariate vector $\mathbf X$. $h_0(t)$ is the baseline hazard. $X_k$ is covariate $k$. $\beta_k$ is its log-hazard coefficient. $p$ is the number of covariates. $HR_k$ is the adjusted hazard ratio (HR) for a one-unit rise in $X_k$, while holding other covariates fixed. A 95% confidence interval (CI) gives the compatible range of values.

### 2. Key Concepts, Principles & Assumptions
The key assumption is **proportional hazards (PH)**. The HR for two covariate patterns must remain constant during follow-up. The model also needs correctly specified covariate forms. It needs independent censoring after accounting for covariates. It also needs event timing recorded precisely enough for the question. Cox regression estimates association. In a randomized trial, a treatment-only Cox model preserves the randomization. A prespecified adjusted model can improve precision.

**Schoenfeld residuals** check PH. At an event time, the residual is the observed covariate value minus the value expected from the weighted risk set. With PH, scaled residuals should not show a pattern over time. Inspect both a global test and plots for each covariate. A significant time trend suggests that the HR changes over time. It does not automatically make the study bad. Plan the response in advance. Options include a treatment-by-$\log(t)$ interaction, piecewise HRs, a flexible parametric survival model, restricted mean survival time (RMST, average survival time up to a chosen limit), or landmark risks.

A **time-varying covariate** has a value $X(t)$ that changes during follow-up. Examples include vasopressor dose, daily Sequential Organ Failure Assessment (SOFA) score, or onset of ventilator-associated pneumonia (VAP). Update it only using information available before time $t$. Calling “received tracheostomy” a baseline yes/no covariate creates immortal-time bias. Patients must survive long enough to receive it. A **time-varying coefficient** allows the effect itself to change. $\beta_k(t)$ then replaces constant $\beta_k$.

### 3. Visual / ASCII Schematic
```text
Cox model workflow

Define time zero --> define event/censoring --> prespecify covariates
        |                                            |
        +------------------> fit Cox model <---------+
                                 |
                    HR = exp(beta), 95% CI
                                 |
              PH diagnostics: Schoenfeld residuals
                         /                 \
                  no time trend          time trend
                       |                    |
                report constant HR    beta(t), piecewise HR,
                                     RMST, or landmark risks
```

### 4. Landmark ICU Clinical Anchor
The **ART trial** compared a recruitment manoeuvre plus compliance-titrated positive end-expiratory pressure (PEEP) with a low-PEEP strategy in moderate-to-severe acute respiratory distress syndrome (ARDS). Its time-to-death analysis used Cox modelling. The recruitment/titrated-PEEP strategy was associated with higher 28-day mortality (HR 1.20, 95% CI 1.01–1.42) ([ART publication](https://jamanetwork.com/journals/jama/fullarticle/2667441/)). This gives a useful way to read an HR. Among patients alive at a given time, the estimated instantaneous death rate was higher with the experimental strategy. It does **not** mean every patient’s absolute death probability rose by 20%. It also does not prove the effect stayed constant without PH diagnostics. In a formal appraisal, check the analysis time origin. Check centre stratification or clustering, prespecified adjustment, missing-data handling, and graphical or Schoenfeld PH assessment. Only then decide whether one adjusted HR is an adequate treatment summary.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** It uses censoring and event timing. It can include several prognostic covariates. It yields adjusted HRs with CIs.
- **PH is not optional.** Inspect log-minus-log curves and Schoenfeld residual plots. A non-significant test with few events does not prove PH.
- **Do not overadjust randomized treatment effects** for post-randomization mediators. Achieved driving pressure is one example. Adjusting for it can block part of the treatment pathway and introduce bias.
- **Time-dependent exposures require correct risk-set coding.** VAP, renal replacement therapy (RRT) initiation, and tracheostomy cannot be assigned at admission just because they happen later.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Cox regression estimates $HR=\exp(\beta)$ while leaving the baseline hazard unspecified.
> - The proportional-hazards assumption means the relative hazard is constant over time; assess it with Schoenfeld residuals.
> - Distinguish a covariate changing over time, $X(t)$, from an effect changing over time, $\beta(t)$.

## Chapter 31: Competing Risks Analysis: Cumulative Incidence Function (Fine-Gray) vs. Standard Kaplan-Meier

### 1. Definition & Mathematical Core
A **competing risk** is an event that makes the event you care about impossible. For intensive care unit (ICU)-acquired ventilator-associated pneumonia (VAP), death and alive ICU discharge before VAP prevent later VAP during that ICU admission. The **cumulative incidence function (CIF)** is the actual probability of a specified event by a given time. For cause $k$ it is

$$F_k(t)=P(T\leq t,J=k)=\int_0^t S(u^-)\,d\Lambda_k(u).$$

Here, $T$ is time to the first event of any type. $J$ is the event type. $k$ denotes VAP. $S(u^-)$ is the probability of no event of any type just before time $u$. $\Lambda_k(u)$ is the cause-$k$ cumulative hazard. Fine–Gray regression models the subdistribution hazard $\tilde h_k(t\mid\mathbf X)=\tilde h_{0k}(t)\exp(\boldsymbol\gamma^T\mathbf X)$, where $\tilde h_{0k}(t)$ is the baseline subdistribution hazard. $\mathbf X$ is the covariate vector. $\boldsymbol\gamma$ is the coefficient vector. $\exp(\gamma)$ is a subdistribution hazard ratio (sHR).

### 2. Key Concepts, Principles & Assumptions
Standard Kaplan–Meier (KM) for “time to VAP” censors patients at discharge or death. It answers a hypothetical net-risk question. It asks what VAP incidence would be if censored patients stayed at risk and had the same prognosis as patients who remained. That is not the observed ICU risk when most patients leave ICU before VAP. As a result, $1-\widehat S_{KM}(t)$ usually **overestimates** the true probability of VAP.

Use the Aalen–Johansen estimator (a method that estimates CIF while retaining competing events) to describe the absolute probability of VAP. Use cause-specific Cox regression for an etiologic question. That asks whether an exposure changes the instantaneous VAP rate among patients currently alive, in ICU, and VAP-free. Use Fine–Gray for a prognostic or policy question. That asks how an exposure changes cumulative VAP occurrence along the real ICU pathway, including indirect effects through death and discharge. The sHR is not a conventional hazard ratio (HR). Do not read it as a biological rate ratio. Both models need appropriate covariate forms and independent administrative loss to follow-up. Their proportional versions also assume constant relative cause-specific or subdistribution effects over time.

### 3. Visual / ASCII Schematic
```text
At ICU admission, VAP-free and ventilated
                 |
      +----------+-----------+
      |          |           |
     VAP       Death      ICU discharge
   (event)  (competing)   (competing)
      |
  CIF_VAP(t) = actual probability of VAP by day t

Incorrect for absolute VAP risk:
KM: death/discharge --> ordinary censoring --> inflated 1 - S_KM(t)
```

### 4. Landmark ICU Clinical Anchor
A large ICU surveillance analysis by **Wolkewitz and colleagues** studied 109,216 admissions. It treated death without nosocomial bacteraemia and ICU discharge without infection as competing events. It compared event-specific rate models with Fine–Gray cumulative-risk models ([Critical Care study](https://pmc.ncbi.nlm.nih.gov/articles/PMC4056071/)). The endpoint was nosocomial bacteraemia rather than VAP. The underlying logic is the same for ventilator-associated events. Discharge ends the chance to diagnose ICU VAP. Death ends it permanently. The investigators showed that an exposure can appear to have opposite associations with daily infection rate and cumulative infection probability. This happens when the exposure changes discharge or death hazards. If your ICU compares VAP-prevention bundles, show CIFs for VAP, death, and discharge. Do not claim a KM “VAP incidence” after censoring death and discharge.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** CIF estimates observed event probability. Fine–Gray allows prognostic covariate modelling. Cause-specific hazards help explain mechanisms.
- **State the estimand (the precise effect you want to estimate):** “Effect on VAP rate among patients still at risk” differs from “effect on probability of VAP by day 28.”
- **Do not censor competing death/discharge as though non-informative** when reporting absolute ICU infection incidence.
- **Do not call sHR an ordinary HR.** Fine–Gray keeps a weighted representation of patients with competing events in the risk set. That is mathematically useful but not intuitively clinical.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Death and ICU discharge are competing events for ICU-acquired VAP.
> - KM complement overestimates actual VAP probability when competing events are censored.
> - Use CIF/Fine–Gray for cumulative risk and cause-specific Cox for an event-rate/etiologic question.

## Chapter 32: Composite Endpoints & Hierarchical Win Ratios: Mortality Competing with Ventilator-Free Days; Days-Alive-and-Free Endpoints

### 1. Definition & Mathematical Core
A **composite endpoint** combines clinically different outcomes into one analysis. A **hierarchical win ratio (WR)** keeps their order of clinical priority. For 28-day ventilator-free days (VFD, days alive and off invasive ventilation), let $\tau=28$ days. Let $D$ indicate death by $\tau$ ($D=1$ if dead). Let $V$ be days of invasive ventilation before final successful liberation. A common definition is

$$VFD_{28}=\begin{cases}0,&D=1\ \text{or still invasively ventilated at }\tau,\\ \tau-V,&D=0\ \text{and successfully liberated before }\tau.\end{cases}$$

For all prioritized cross-group patient pairs, $WR=W/L$, where $W$ is number of treatment wins and $L$ is number of treatment losses. Compare each pair for mortality first. Only if mortality is tied do you compare VFD or another lower-priority outcome.

### 2. Key Concepts, Principles & Assumptions
VFDs recognise that getting off the ventilator quickly is not a success if the patient dies. The usual zero score has a problem. It gives the same value to death before day 28 and survival while continuously ventilated. Those are clinically different paths. Prespecify reintubation rules, the definition of successful liberation, and the observation window. Successful liberation commonly means sustained unassisted breathing. Also specify how you handle death after extubation. The distribution has many zeros and is strongly skewed. A mean difference or an ordinary Poisson model can therefore mislead.

Days-alive-and-free endpoints use the same approach for vasopressor-free, renal-replacement-free, delirium-free, or intensive care unit (ICU)-free days. They work only when every component matters to patients and points in the same clinical direction. One count quietly makes a value judgment about death versus the nonfatal state. A hierarchy makes that judgment visible. Compare death first. Then compare ventilator duration among survivors. The result is a relative priority-based effect, not “days gained.” Ties can be common. Stratified or matched WR designs should account for key baseline risk factors. Pairwise comparisons need a prespecified tie rule and consistent follow-up.

### 3. Visual / ASCII Schematic
```text
Hierarchical pair: treatment patient vs control patient

1. Who survives to day 28?
   treatment survives / control dies  --> treatment WIN
   treatment dies / control survives  --> treatment LOSS
   both same survival status          --> go to step 2

2. Among comparable survivors: more VFD_28?
   more --> WIN       fewer --> LOSS       equal --> TIE

WR = total treatment WINS / total treatment LOSSES
```

### 4. Landmark ICU Clinical Anchor
The **ARDSNet ARMA** low-tidal-volume trial is a useful anchor. It reported both mortality and VFD-related outcomes. That raises the key question of how to value survival against ventilator liberation. A recent critical-care methods study reanalysed ARMA, ACURASYS, LIVE, and COVIDICUS data. It used VFD distributions, competing-risk approaches, multistate models, and win ratios. It notes that VFDs traditionally assign zero to patients dying by day 28. It also notes that hierarchical alive-and-ventilator-free approaches compare death before ventilation duration ([methods study](https://pmc.ncbi.nlm.nih.gov/articles/PMC12180158/)). The same literature identifies **Novack et al.** as proposing an alive-and-ventilator-free hierarchical composite for acute respiratory distress syndrome (ARDS). This is a modern analytic proposal. It does not permit you to retrospectively replace a trial’s prespecified primary endpoint. The debate is principled. VFD may improve while mortality does not change. A composite can also hide whether benefit came from survival, earlier liberation, or an arbitrary scoring rule.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths/indications:** It can improve efficiency when mortality and recovery both matter. It stops a nonfatal benefit being valued above death. WR makes the hierarchy clear.
- **Always present components separately:** Report mortality, ventilation duration among survivors, VFD distribution, and the composite effect.
- **Do not interpret VFD=0 as a homogeneous outcome.** It may mean death, prolonged ventilation, or failed liberation/reintubation.
- **Avoid post hoc hierarchy selection.** Set the ordering, time window, and tie definition before examining outcome data. Otherwise the apparent win ratio is vulnerable to selective analysis.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - VFDs combine survival and liberation but their zeros mix death with persistent ventilation.
> - A hierarchical win ratio compares mortality first, then VFDs or another recovery outcome among ties.
> - Composite results require transparent component reporting and a prespecified clinical hierarchy.

### Section Recap: Which Test / Which Effect Measure
```text
Choose the clinical estimand
|
+-- Fixed binary outcome at a stated day (e.g. day-28 death)?
|     +-- Report risk in each arm + RR + ARR; derive NNT/NNH when useful
|     +-- Logistic adjusted analysis needed? Report adjusted OR, never relabel as RR
|
+-- Time to one event with ordinary independent censoring?
|     +-- Plot Kaplan–Meier with numbers at risk
|     +-- Compare curves: log-rank; estimate effect: Cox HR only after PH assessment
|     +-- PH violated? Time-varying HR / landmark risks / RMST rather than one HR
|
+-- Time to event with death or ICU discharge preventing it (e.g. VAP)?
|     +-- Describe probability: CIF (Aalen–Johansen); compare CIFs
|     +-- Prognostic cumulative risk: Fine–Gray sHR
|     +-- Etiologic event rate while still at risk: cause-specific HR
|
+-- Mortality and recovery are jointly important (e.g. VFDs)?
      +-- Prespecify days-alive-and-free definition and report components
      +-- If mortality must dominate: hierarchical win ratio / multistate approach
```

Report **absolute risks** whenever you give a relative measure. State the time origin, horizon, censoring and competing-event rules, and analysis population. A P value is not an effect size. Attach a CI. For ICU recovery composites, disclose the hierarchy and every component before drawing a treatment conclusion.
# SECTION 6: EVIDENCE SYNTHESIS & SYSTEMATIC APPRAISAL

## Chapter 33: Systematic Reviews & PRISMA

### 1. Definition & Mathematical Core
A **systematic review** answers one focused clinical question through a planned, repeatable process for finding, selecting, judging, and combining studies. You set this process in advance, before you know the results. **PRISMA 2020** (Preferred Reporting Items for Systematic Reviews and Meta-Analyses) tells you how to report that process clearly. It does not itself make a review high quality ([PRISMA 2020](https://www.prisma-statement.org/prisma-2020)). Let $I_j=1$ when record $j$ fulfils all prespecified eligibility criteria and $I_j=0$ otherwise; the included evidence set is $S=\{j:I_j=1\}$. Here $j$ is a retrieved record, $I_j$ is its inclusion indicator, and $S$ is the final study set. Set eligibility before you see results. Use **PICOST**: population, intervention, comparator, outcomes, study design, and timing.

### 2. Key Concepts, Principles & Assumptions
Your protocol states the databases, search dates, controlled vocabulary and free-text terms, language limits, duplicate handling, outcomes, and planned analyses. Register it before the review starts, for example in PROSPERO (an international prospective register of systematic-review protocols). Record any later deviations. Two independent reviewers should screen titles, abstracts, and full texts. A third reviewer resolves disagreements. Screening is not just admin work. A reviewer who knows a trial result may stretch an unclear eligibility rule to include or exclude it.

PRISMA requires a numerical record from identified records to included reports. It also requires reasons for each full-text exclusion. Search several databases. Check trial registries, reference lists, conference material, and completed but unpublished studies. A search that ends before a major intensive care unit (ICU) trial is not merely old. It may give you biased evidence.

Appraisal must match the study design. **RoB 2** (the Cochrane Risk of Bias 2 tool) rates one randomized-trial result as low risk, some concerns, or high risk. It examines bias from randomization, departures from the intended treatment, missing outcomes, outcome measurement, and selective result reporting. Use its signalling questions and domain judgements. Do not invent one total score ([Cochrane RoB 2](https://www.riskofbias.info/welcome/rob-2-0-tool/current-version-of-rob-2)). For cohort and case-control studies, which compare exposed and unexposed groups, use the **Newcastle–Ottawa Scale (NOS)**. It gives stars for selection, comparability, and exposure or outcome measurement. Its total must not hide fatal confounding (mixing up the treatment effect with patient differences) or a time-zero error ([NOS documentation](https://www.ohri.ca/programs/clinical_epidemiology/oxford.asp)). Extract data twice and keep the protocol. Separate each study from each publication so you do not count one ICU cohort twice.

### 3. Visual / ASCII Schematic
```
Protocol: PICOST + outcomes + analysis plan
                 |
Databases / registries / references --> remove duplicates
                 |
      title-abstract screening (2 reviewers)
                 |
        full texts + explicit exclusion reasons
                 |
      included studies --> RoB 2 / NOS --> synthesis
                 |                         |
           PRISMA flow counts       meta-analysis or narrative synthesis
```

### 4. Landmark ICU Clinical Anchor
The corticosteroid question in septic shock shows why you need a living, protocol-led search. In 2018, **ADRENAL** was a large blinded randomized trial. It studied continuous hydrocortisone in mechanically ventilated septic shock and did not show lower 90-day mortality. **APROCCHSS** studied hydrocortisone plus fludrocortisone and reported lower 90-day mortality ([ADRENAL](https://www.nejm.org/doi/full/10.1056/NEJMoa1705835); [APROCCHSS](https://www.nejm.org/doi/full/10.1056/NEJMoa1705716)). A review limited to older, smaller trials can answer a different question. The same is true if it combines hydrocortisone alone with hydrocortisone plus fludrocortisone without a prespecified clinical question. Keep the regimen, shock severity, co-interventions, mortality time point, and risk-of-bias assessment for each trial.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** improves precision; makes searches and exclusions auditable; separates evidence finding from author opinion; can reveal outcome-reporting and duplicate-publication problems.
- **Clinical limitations:** even a thorough search cannot fix biased source studies; 28-day, ICU, hospital, and 90-day mortality are different outcomes; protocol differences may mean you cannot pool studies.
- **Examiner pitfalls:** PRISMA is a reporting checklist, not a quality score. Do not total RoB 2 domains. NOS stars do not prove an observational comparison is free from confounding. Do not screen by results or change eligibility after seeing results.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - PRISMA shows the evidence pathway; a protocol protects it from result-driven decisions.
> - Use RoB 2 domain judgements for randomized trials and design-aware appraisal for observational studies.
> - Pool only studies that answer sufficiently similar PICOST questions.

## Chapter 34: Meta-Analysis Mechanics

### 1. Definition & Mathematical Core
A **meta-analysis** combines numerical study results from studies that answer a sufficiently similar question. It gives each study a weight. Under a fixed-effect model (one shared true effect), $\hat\theta_F=\sum_{i=1}^{k}w_i\hat\theta_i/\sum_{i=1}^{k}w_i$ and $w_i=1/v_i$; under a random-effects model (true effects that vary between studies), $w_i^*=1/(v_i+\tau^2)$. Here $k$ is the number of studies. $\hat\theta_i$ is the effect estimate in study $i$. $v_i$ is its within-study variance, or sampling spread. $\tau^2$ is between-study variance. $\hat\theta_F$ is the fixed-effect pooled estimate. For binary intensive care unit (ICU) mortality, $\theta$ may be a log risk ratio, log odds ratio, or risk difference. The estimand is the exact effect being estimated. Use the same estimand before combining studies.

### 2. Key Concepts, Principles & Assumptions
A fixed-effect model assumes every study is estimating one true effect. Its precision weighting gives more influence to the largest and most precise trial. A random-effects model assumes that true effects differ between studies. It estimates the mean of that spread of true effects. It does not give you permission to pool clinically incompatible studies. Major differences in severity, timing, treatment delivery, or outcome definition can make the average hard to use at the bedside.

Report the effect measure and the 95% confidence interval (**CI**, a range of effects compatible with the data at the stated confidence level). Also report the model, the method used to estimate $\tau^2$, zero-event handling, and planned subgroup and sensitivity analyses. For ratio measures, plot and pool on the log scale, then back-transform. A CI that crosses the line of no effect is compatible with both benefit and harm. It does not prove treatments are equivalent. In a forest plot, square size shows study weight. Horizontal bars show CIs. The diamond shows the pooled estimate and its CI.

### 3. Visual / ASCII Schematic
```
ASCII FOREST PLOT
Outcome: 90-day mortality                 Favours intervention   Favours control
Study                                  RR (95% CI)      0.5       1.0       2.0
Small trial A                           0.72 [0.38,1.36] ---[■]-----|--------
Large trial B                           0.95 [0.82,1.10] ---------[■■■■]-----
Trial C                                 0.88 [0.78,0.99] ----------[■■]------
Fixed/random pooled                     0.90 [0.82,0.99] ----------<◆>-------
                                                   line of no effect = 1.0
```

### 4. Landmark ICU Clinical Anchor
The PRISM investigators combined individual patient data (**IPD**, the original patient-level records) from **ProCESS, ARISE, and ProMISe**. These were three multicentre trials of protocolised early goal-directed therapy (**EGDT**) in septic shock. This IPD meta-analysis aimed to increase power and examine heterogeneity (real differences between study effects). Each contemporary trial had shown no overall survival benefit of EGDT over usual care ([PRISM IPD meta-analysis](https://pubmed.ncbi.nlm.nih.gov/28320242/)). IPD is stronger than adding published summary tables. You can align covariates, eligibility, outcomes, and subgroup definitions while retaining the randomized comparisons. Read its pooled null result in context. Participating systems already gave rapid antibiotics, fluids, vasopressors, and improved usual care. It is not evidence against prompt resuscitation itself.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** improves precision; may settle apparently conflicting trials; IPD permits consistent definitions and credible interaction analyses (tests of whether the treatment effect differs between groups).
- **Clinical limitations:** a pooled average can hide effect modification (a true difference in effect) by acute respiratory distress syndrome (**ARDS**) severity, shock phenotype, timing, or delivery fidelity. Random-effects CIs can look too reassuring when few studies estimate $\tau^2$ poorly.
- **Examiner pitfalls:** fixed effect does not mean “high quality.” Random effects does not “correct heterogeneity.” A diamond on one side of 1 does not prove the result applies to every ventilated or shocked patient.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Fixed effect estimates one common effect; random effects estimates a mean across varying true effects.
> - The forest plot shows each estimate, its CI, its weight, and the pooled diamond.
> - Confirm clinical comparability before interpreting a statistically precise pooled result.

## Chapter 35: Statistical Heterogeneity

### 1. Definition & Mathematical Core
**Statistical heterogeneity** means that observed study effects vary more than you would expect from sampling error, or chance variation from sampling, alone. Cochran’s statistic is $Q=\sum_{i=1}^{k}w_i(\hat\theta_i-\hat\theta_F)^2$ and $I^2=\max\{0,(Q-(k-1))/Q\}\times100\%$. Here $w_i$ is the fixed-effect inverse-variance weight. $\hat\theta_i$ is study $i$’s effect. $\hat\theta_F$ is the fixed-effect pooled effect. $k$ is the number of studies. $Q$ is compared with a chi-square distribution with $k-1$ degrees of freedom. $I^2$ estimates the proportion of observed variation due to heterogeneity rather than chance.

### 2. Key Concepts, Principles & Assumptions
Use the $Q$ test cautiously. With few trials, it has low power, meaning it can miss real inconsistency. With many trials, tiny differences can give a small P value. $I^2$ is uncertain when $k$ is small. It also depends on within-study precision. A high value does not tell you whether the disagreement matters clinically. Describe inconsistency as low, moderate, substantial, or considerable. Do not treat those labels as rigid pass-or-fail bands. Report $\tau^2$. If you use a random-effects model, also report a **prediction interval**. It estimates where the true effect in a comparable future setting may lie.

Look for clinical causes before you focus on statistics. In acute respiratory distress syndrome (**ARDS**), prone-position trials may differ in the PaO$_2$/FiO$_2$ threshold, timing, daily duration, lung-protective ventilation, neuromuscular blockade, and crossover. This ratio divides arterial oxygen pressure by inspired oxygen fraction. Explore prespecified subgroups and a leave-one-out analysis, where you remove one study at a time. Restricting to low-risk-of-bias studies can also help. Treat post hoc explanations, made after you see results, as hypotheses. A non-significant $Q$ test does not prove that studies are identical.

### 3. Visual / ASCII Schematic
```
Is pooling clinically coherent (population, intervention, timing, outcome)?
             | yes                                      | no
             v                                          v
 Estimate Q, I², tau² and prediction interval       Do not force a summary
             |
  Low / explainable inconsistency? ---- no ----> seek prespecified modifiers,
             |                                    sensitivity analyses, narrative synthesis
            yes
             v
 Pool with stated model; interpret the average and its transportability
```

### 4. Landmark ICU Clinical Anchor
Prone-positioning meta-analyses before and after **PROSEVA** show why you must read heterogeneity clinically. Earlier ARDS trials often did not show a mortality benefit. PROSEVA tested early, prolonged sessions in selected severe ARDS and reported lower 28- and 90-day mortality ([PROSEVA](https://pubmed.ncbi.nlm.nih.gov/23688302/)). Later reviews are strongly influenced by this large, protocol-specific trial. Read a pooled benefit as support for the early-prolonged strategy in severe ARDS. Do not apply it to any brief or late prone manoeuvre. A low or moderate $I^2$ cannot remove this treatment-delivery difference.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** identifies inconsistency; directs you to possible effect modifiers (features that change a treatment effect); prediction intervals show uncertainty better than $I^2$ alone.
- **Clinical limitations:** $I^2$ does not tell you the cause of heterogeneity and is unstable with few studies. Subgroup analyses often lack power and are prone to multiplicity (false-positive findings from many comparisons).
- **Examiner pitfalls:** do not treat $I^2=0\%$ as biological uniformity; do not choose random or fixed effects from a P value alone; do not present an unplanned subgroup explanation as confirmation.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - $Q$ tests excess dispersion; $I^2$ describes its proportion, but both are imprecise with few studies.
> - Clinical heterogeneity comes before statistical heterogeneity in appraisal.
> - A prediction interval asks what effect a comparable future ICU might see.

## Chapter 36: Publication Bias

### 1. Definition & Mathematical Core
**Publication bias** means studies are selectively shared or published because of their direction, size, or statistical significance. It is one possible **small-study effect**, where small studies give systematically different estimates from large studies. Egger’s regression is $Z_i=\beta_0+\beta_1P_i+\varepsilon_i$. Here $Z_i=\hat\theta_i/SE_i$ is the standard normal deviate, meaning the effect measured in standard-error units, for study $i$. $P_i=1/SE_i$ is its precision. $\hat\theta_i$ is its effect estimate. $SE_i$ is its standard error. $\beta_0$ is the intercept tested for asymmetry. $\beta_1$ is the slope. $\varepsilon_i$ is the residual. Begg’s test assesses rank correlation, or whether two rankings move together, between effect estimates and their variances.

### 2. Key Concepts, Principles & Assumptions
In an unbiased set of adequately reported studies with similar directions of effect, a funnel plot is roughly symmetrical. This plot places effect against precision. Large precise studies sit near the pooled effect. Small studies scatter more widely. Asymmetry may mean small neutral trials were not published. It may also reflect real small-study differences, poor allocation concealment, early stopping, different case mix, or chance. A funnel plot or a P value cannot diagnose publication bias by itself.

Egger’s test has low power with fewer than about ten studies. It can mislead you with binary outcomes, rare events, or substantial heterogeneity. Begg’s rank test is usually less sensitive. Search registries and protocols. Compare registered outcomes with reported outcomes. Retrieve abstracts and dissertations. Contact investigators where appropriate. “Trim-and-fill” is a sensitivity exercise. It relies on strong symmetry assumptions. It does not turn a biased evidence base into truth.

### 3. Visual / ASCII Schematic
```
                 SE (less precise)
                       ^
                       |       o       o       o
                       |    o     o  |  o      o       missing small,
                       |       o     |     o           unfavourable studies?
                       |         o   |   o
                       |------------|----------------------------> effect
                       |          no effect
                       |             *  *
                       |               *                 high precision
                       +----------------------------------------------->
                 Symmetry is a clue; asymmetry is not a verdict.
```

### 4. Landmark ICU Clinical Anchor
The ADRENAL/APROCCHSS era warns against trying to visually “prove” a corticosteroid mortality effect with a funnel plot. ADRENAL found no reduction in 90-day mortality with hydrocortisone alone. APROCCHSS reported a mortality reduction with hydrocortisone plus fludrocortisone in a different regimen and population ([ADRENAL](https://www.nejm.org/doi/full/10.1056/NEJMoa1705835); [APROCCHSS](https://www.nejm.org/doi/full/10.1056/NEJMoa1705716)). Asymmetry among older, smaller steroid studies may therefore come from regimen and population differences. Selective reporting is another possible explanation. Large modern trials reduce uncertainty. They do not make a funnel-plot test a measure of trial validity.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** makes selective availability a planned concern; complements registry searches and protocol-versus-publication checks; reveals implausible small-study dominance.
- **Clinical limitations:** tests have low power with few studies and are confused by real heterogeneity; a null test does not exclude publication bias.
- **Examiner pitfalls:** do not label every asymmetric funnel as “publication bias.” Do not routinely run Egger’s test in a sparse meta-analysis. Do not use trim-and-fill as the primary analysis. Separate trial quality from selective non-publication.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Funnel asymmetry suggests a small-study effect. It does not diagnose publication bias.
> - Egger tests regression-intercept asymmetry; Begg uses rank correlation.
> - Registry and protocol searches are more persuasive than one asymmetry P value.

## Chapter 37: Critical Appraisal Pitfalls

### 1. Definition & Mathematical Core
**Critical appraisal** asks whether an observed association estimates the causal effect you would have seen under the other treatment strategy. For a treatment started after intensive care unit (ICU) admission, use a time-varying survival model. It updates treatment status over time: $h(t\mid A(t),X)=h_0(t)\exp\{\beta A(t)+\gamma^TX\}$. Here $h(t\mid A(t),X)$ is the hazard, or instantaneous event rate, at time $t$. $h_0(t)$ is baseline hazard. $A(t)$ indicates treatment status at time $t$. $X$ is the vector of baseline confounders, or patient factors linked to both treatment and outcome. $\beta$ is the treatment log-hazard-ratio parameter. $\gamma$ is the vector of confounder coefficients. Coding a future-treated patient as treated from time zero creates **immortal time**: they must survive long enough to receive treatment.

### 2. Key Concepts, Principles & Assumptions
The **ecological fallacy** means wrongly inferring an individual treatment effect from a group-level association. For example, an ICU-level link between proning rate and mortality cannot prove that a particular patient benefits. Severity mix and co-interventions may differ. **Small-study effects** mean small studies give estimates that differ systematically from large studies. Publication bias is only one cause. **Reverse causation** occurs when early deterioration causes the intervention. It can then make the intervention look harmful. For example, late renal replacement therapy (**RRT**, a treatment that replaces failed kidney function) may mark worsening shock rather than cause death.

Immortal-time bias is especially damaging in rescue therapies. Say you label “ECMO patients” as exposed at ICU admission, but cannulation happens later. **ECMO** (extracorporeal membrane oxygenation) patients must survive to cannulation. You then credit all that pre-cannulation survival time to ECMO. Patients not given ECMO may die immediately. This can create a false survival advantage. Define a common time zero. Assign strategies at that time when possible. You can use a justified landmark analysis, which compares those alive at a specified time. You can also model ECMO as time-varying. A **target trial** is the randomized trial you would ideally run. A propensity method, which balances measured baseline differences, cannot fix the wrong time assignment. These methods also need control of measured confounding, positivity (a real chance of each strategy for eligible patients), correct model specification, and proper handling of competing events.

### 3. Visual / ASCII Schematic
```
Naive observational comparison
ICU admission ---- survives 36 h ---- cannulation --> labelled “ECMO” from admission
      |                   |
      |                   +-- this guaranteed survival is immortal time
      +-- early deaths, never eligible for later ECMO --> “no ECMO”

Target-trial logic: common time zero -> eligibility -> treatment strategy -> follow-up
```

### 4. Landmark ICU Clinical Anchor
**CESAR** was a randomized UK trial. It compared referral to an ECMO centre for possible treatment with continued conventional management. It was not a simple comparison of cannulated and non-cannulated patients ([CESAR](https://pubmed.ncbi.nlm.nih.gov/19762075/)). This design avoids a classic observational ECMO error. Survival until transfer or cannulation can be wrongly counted as survival caused by ECMO. This is the usual immortal-time-bias problem in observational ECMO studies. Use time-dependent exposure or carefully emulate a target trial (the trial you would ideally run). Only then can you attribute lower mortality to ECMO rather than selection, transfer eligibility, and survival to cannulation.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** causal diagrams, target-trial emulation, time-varying models, and sensitivity analyses can reveal hidden design errors before you trust regression output.
- **Clinical limitations:** no adjustment removes unmeasured confounding; time-varying treatment may also be affected by time-varying illness severity, causing treatment-confounder feedback.
- **Examiner pitfalls:** an ICU-level correlation is not patient-level causation. Severity-triggered rescue treatment causes reverse causation. A Cox proportional-hazards model with “ever received ECMO” fixed at baseline is biased even with an excellent propensity score.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - Ecological associations cannot be directly translated into individual treatment effects.
> - Small-study effects and reverse causation can explain an association.
> - For delayed ECMO, align time zero and model treatment timing correctly to avoid immortal-time bias.

## Chapter 38: Levels of Evidence & GRADE Methodology

### 1. Definition & Mathematical Core
**GRADE** (Grading of Recommendations Assessment, Development and Evaluation) rates how certain you can be about an effect estimate. It separates certainty from recommendation strength. For a binary benefit outcome, the absolute risk difference is $RD=p_I-p_C$ and the number needed to treat is $NNT=1/|RD|$ when $RD\ne0$. Here $p_I$ is event risk with the intervention. $p_C$ is event risk with the comparator. $RD$ is the absolute risk difference. $NNT$ is the number treated for one additional outcome event. If the absolute risk difference is 0.05, the NNT is 20. You would treat 20 patients to produce one additional outcome event. In intensive care unit (ICU) practice, GRADE panels use absolute effects, not relative effects alone. They also consider patient-important benefits, harms, values, resources, equity, acceptability, and feasibility.

### 2. Key Concepts, Principles & Assumptions
Randomized evidence starts as high-certainty evidence. Observational evidence, from non-randomized studies, starts as low-certainty evidence. You judge certainty **for each outcome**, not for the study as a whole. Start with a population, intervention, comparator, and outcome (**PICO**) question. You can rate certainty down for risk of bias, inconsistency, indirectness, imprecision, and publication bias. You may rarely rate it up for a large effect, a dose response, or plausible residual confounding that would reduce the observed effect. “High” means further research is very unlikely to change confidence materially. “Very low” means the effect estimate is highly uncertain. The evidence hierarchy is a starting point. It is not an automatic verdict.

| GRADE domain | Appraisal question in critical care | Typical downgrading concern |
|---|---|---|
| Risk of bias | Were allocation, follow-up, and reporting trustworthy? | Open-label ventilation co-interventions or missing outcome data |
| Inconsistency | Do effects agree across studies? | Different shock phenotypes or steroid regimens |
| Indirectness | Does evidence match this patient, strategy, and outcome? | Ward sepsis evidence used for refractory ICU shock |
| Imprecision | Does the CI (confidence interval) rule out clinically important benefit and harm? | Few deaths or a wide mortality CI |
| Publication bias | Could unavailable evidence change the estimate? | Small favourable trials with missing registered studies |

### 3. Visual / ASCII Schematic
```
PICO question --> systematic review --> certainty per critical outcome
                                      |
       RoB / inconsistency / indirectness / imprecision / publication bias
                                      |
                  absolute benefits + harms + values + feasibility + equity
                                      |
                  strong recommendation  OR  conditional recommendation
```

### 4. Landmark ICU Clinical Anchor
The **Surviving Sepsis Campaign (SSC) 2021** guideline uses a GRADE-based process. It states recommendation strength and evidence quality separately ([SSC 2021 guideline](https://pmc.ncbi.nlm.nih.gov/articles/PMC8486643/)). “We recommend” means a strong recommendation. “We suggest” means a conditional, or weak, recommendation. Neither phrase simply means high- or low-certainty evidence. Its corticosteroid recommendation for adults with septic shock and an ongoing vasopressor requirement is conditional. This shows how a panel can weigh a likely benefit in shock resolution against mortality uncertainty and adverse effects. One pooled relative risk is not the whole decision.

### 5. Advantages vs. Clinical Limitations / Examiner Pitfalls
- **Strengths:** makes certainty, absolute effects, values, and feasibility clear; stops a statistically significant relative effect from automatically becoming a strong mandate; supports transparent guideline panels.
- **Clinical limitations:** ICUs may judge minimally important effects, resources, and equity differently; GRADE cannot repair sparse or biased trials.
- **Examiner pitfalls:** do not treat a randomized controlled trial (**RCT**) as permanently high certainty. Do not treat “conditional” as ineffective. Do not assume a strong recommendation always has high certainty. State both certainty and recommendation strength.

### 6. Theory Exam Summary Box
> **SUMMARY BOX**
> - GRADE rates certainty per outcome using five main downgrading domains.
> - Recommendation strength also uses absolute effects, harms, values, resources, equity, acceptability, and feasibility.
> - In SSC language, “recommend” is strong and “suggest” is conditional; report both strength and certainty.

### Section Recap: Which Test / Which Effect Measure

```
Meta-analysis submitted for appraisal
|
+-- Was the PICOST question, search, PRISMA flow, and RoB 2/NOS appraisal prespecified?
|      | no --> high concern: inspect protocol, exclusions, and missing studies
|      +-- yes
|
+-- Are effect measures and clinical settings compatible?
|      | no --> narrative/stratified synthesis; do not force a pooled effect
|      +-- yes --> choose RR/OR/RD for binary outcome; HR for time-to-event outcome
|
+-- Common effect plausible?
|      | yes --> fixed-effect estimate (inverse-variance weights)
|      +-- uncertain/varying --> random-effects mean + tau² + prediction interval
|
+-- Is inconsistency important? --> Q (dispersion test) + I² (proportion of variation)
|      | unexplained --> investigate prespecified modifiers / sensitivity analysis
|      +-- acceptable --> interpret forest-plot diamond and CI
|
+-- Are small-study effects credible? --> funnel plot + Egger/Begg (usually >=10 studies)
|      +-- yes/uncertain --> registry search, outcome comparison, cautious certainty rating
|
+-- Is the evidence causal and decision-ready? --> check reverse causation, ecological and
       immortal-time bias; apply GRADE domains before a recommendation
```

Choose the effect measure that matches the outcome and **estimand** (the exact effect you want to estimate). Do not choose the one that looks most dramatic. Use $Q$, $I^2$, funnel plots, Egger’s regression, and Begg’s test as diagnostic aids. They are not binary admission tests. A pooled estimate is clinically credible only after you assess design, timing, comparability, and bias. GRADE then turns certainty and absolute consequences into recommendations. P values alone cannot do that.
# MASTER VIVA ANNEXURE

## A. "Spot the Flaw" Journal Club Checklist

Use this sequence before accepting a dramatic ICU-trial conclusion. At a table viva, state the domain, its consequence for the estimand, and the concrete trial analogue.

1. **Question, population, and estimand — check:** Is the PICO clinically coherent, and is the stated effect a treatment-policy (ITT) effect, a per-protocol effect, or an effect while adherent? **Why it matters:** An elegant analysis cannot rescue a question that enrolls a population unlike the patient in front of you. **Classic ICU-trial example:** **ELAIN** was a single-centre study with an early-RRT trigger and a selected surgical-heavy population; its positive result should not be assumed to transport unchanged to the broader multinational population of **STARRT-AKI**.

2. **Randomisation and allocation concealment — check:** Was the sequence genuinely random and concealed until irrevocable enrolment, with balance in important prognostic factors? **Why it matters:** Foreknowledge of allocation permits selective recruitment and converts chance imbalance into selection bias. **Classic ICU-trial example:** In small single-centre critical-care trials, apparent benefit can coexist with clinically meaningful baseline imbalance despite nominal randomisation; this is one reason large concealed multicentre trials such as **SAFE** carry more protection against selection artefact.

3. **Blinding and objective outcome assessment — check:** Who was blinded—patient, bedside team, adjudicator, statistician—and could knowledge of allocation change co-interventions or event ascertainment? **Why it matters:** Mortality is relatively resistant, but ventilator-free days (VFD), RRT initiation, sedation, extubation, and withdrawal decisions are not. **Classic ICU-trial example:** The **VITAMINS** trial compared open-label vitamin C–based therapy with hydrocortisone alone; clinician-directed outcomes and co-interventions require more caution than an objectively adjudicated mortality endpoint.

4. **Comparator and protocol separation — check:** Did arms receive meaningfully different interventions, at clinically plausible doses and timings, while usual care remained contemporary? **Why it matters:** Contamination or inadequate separation biases toward no difference; an obsolete comparator can exaggerate apparent benefit. **Classic ICU-trial example:** **STARRT-AKI** is interpretable because the accelerated and standard strategies produced clear timing separation, whereas many “early versus late” RRT comparisons are difficult to interpret when substantial crossover narrows exposure contrast.

5. **Primary outcome hierarchy — check:** Is there one prespecified patient-important primary outcome, or a composite dominated by a softer component? **Why it matters:** A positive composite does not establish benefit for each component, especially mortality. **Classic ICU-trial example:** **SMART** used MAKE30, a composite of death, new RRT, or persistent renal dysfunction; interpret the composite and its components rather than saying balanced crystalloids “reduced mortality.”

6. **Follow-up, censoring, and competing risks — check:** Are losses small and balanced, are censoring assumptions plausible, and does death preclude the event of interest? **Why it matters:** Treating death as simple censoring can inflate the apparent incidence of renal recovery, liberation from ventilation, or ICU discharge. **Classic ICU-trial example:** In AKI trials such as **AKIKI** and **STARRT-AKI**, recovery of kidney function is inseparable from the competing risk of death; a Kaplan–Meier recovery curve alone can mislead.

7. **Missing data and analysis population — check:** How much outcome/covariate data are missing, why are they missing, and were multiple imputation and sensitivity analyses prespecified? **Why it matters:** Complete-case analysis is valid only under restrictive assumptions and may preferentially exclude the sickest patients. **Classic ICU-trial example:** ICU biomarker and health-related quality-of-life follow-up studies can lose patients through death and non-response; calling such data “missing at random” without sensitivity analysis is not enough.

8. **Multiplicity, subgroups, and stopping rules — check:** Count outcomes, time points, subgroups, interim looks, and whether correction or a gatekeeping plan was prespecified. **Why it matters:** Repeated opportunities to declare success inflate false-positive probability. **Classic ICU-trial example:** **PROWESS** was stopped early after an apparent mortality benefit with drotrecogin alfa; the later **PROWESS-SHOCK** trial did not confirm a mortality benefit, illustrating why truncated evidence demands restraint.

9. **Precision, clinical importance, and fragility — check:** Read the confidence interval (CI), absolute risk difference, and event counts—not only the p-value. **Why it matters:** A non-significant result may exclude neither important benefit nor important harm, and a statistically significant result may be clinically trivial. **Classic ICU-trial example:** **EOLIA** did not show conventional statistical significance for its primary mortality comparison, but its estimate and uncertainty were compatible with clinically important benefit; heavy crossover also complicates a simplistic “negative trial” verdict.

10. **Generalisability and protocol-era fit — check:** Compare eligibility, centre expertise, co-interventions, and calendar era with current local practice. **Why it matters:** Internal validity answers whether the trial estimate is credible; external validity answers whether it applies to this ICU. **Classic ICU-trial example:** **PROSEVA** established benefit of prolonged prone positioning in carefully selected severe ARDS managed by experienced teams; it is not evidence that any brief or poorly executed prone episode benefits every hypoxaemic patient.

## B. Master Decision Trees (ASCII)

### (i) Which Test of Significance to Use?

```text
WHICH TEST OF SIGNIFICANCE TO USE?
|
+-- What is the outcome being compared?
    |
    +-- Continuous / approximately continuous (e.g., SOFA score, PaO2/FiO2, ICU days)
    |   |
    |   +-- Same participant measured twice, or matched pairs?
    |   |   |
    |   |   +-- Yes
    |   |   |   |
    |   |   |   +-- Differences approximately symmetric/normal? --> Paired t-test
    |   |   |       Otherwise / ordinal / marked skew             --> Wilcoxon signed-rank test
    |   |   |
    |   |   +-- No: independent groups
    |   |       |
    |   |       +-- Two groups
    |   |       |   |
    |   |       |   +-- Approx. normal residuals, independent observations,
    |   |       |       no serious variance problem                --> Independent-samples t-test
    |   |       |       (use Welch t-test when variances differ)
    |   |       |
    |   |       |   +-- Ordinal / skewed / substantial outliers    --> Mann-Whitney U (Wilcoxon rank-sum)
    |   |       |
    |   |       +-- More than two independent groups
    |   |           |
    |   |           +-- Approx. normal residuals, similar variances --> One-way ANOVA
    |   |           +-- Ordinal / skewed                            --> Kruskal-Wallis test
    |   |
    +-- Categorical outcome (e.g., death yes/no, VAP yes/no)
        |
        +-- Paired / matched binary observations? (before-after, matched case-control)
        |   |
        |   +-- Yes --> McNemar test (uses discordant pairs)
        |
        +-- Independent groups
            |
            +-- 2 x 2 table or r x c table
                |
                +-- Expected cell counts adequate (usual rule: all >=5) --> Chi-square test
                |
                +-- Any expected cell count <5 / very sparse data       --> Fisher exact test

REMEMBER: Do not use these simple tests for clustered, repeated, adjusted, or time-to-event data.
Use mixed models/GEE, regression, survival models, or competing-risk methods as appropriate.
```

### (ii) Which Effect Measure to Report?

```text
WHICH EFFECT MEASURE TO REPORT?
|
+-- Is the endpoint binary at a fixed, clinically meaningful time?
|   |   (e.g., 28-day mortality, dialysis dependence at day 90)
|   |
|   +-- Randomised trial or cohort; risks can be estimated
|   |   |
|   |   +-- Report Risk Ratio (RR) for relative comparison
|   |   +-- ALSO report Risk Difference / Absolute Risk Reduction (ARR)
|   |       --> NNT = 1 / ARR only when ARR is beneficial, stable, and time horizon stated
|   |
|   +-- Case-control study, logistic regression, or sampled by outcome
|       --> Odds Ratio (OR); do not call it RR
|       --> If outcome is common, OR can materially overstate the RR away from 1
|
+-- Is time to first event important, with right censoring?
|   |
|   +-- Conventional survival analysis; proportional hazards reasonable
|   |   --> Hazard Ratio (HR) from Cox model + Kaplan-Meier curves / absolute risks at time t
|   |
|   +-- Proportional hazards doubtful
|   |   --> Restricted mean survival time difference, time-varying HR, or survival probabilities
|   |
|   +-- Competing event (e.g., death prevents renal recovery)
|       --> Cumulative incidence function (CIF); cause-specific HR or subdistribution HR,
|           stated explicitly according to the clinical question
|
+-- Are recurrent, prioritised clinical events to be ranked within matched treatment pairs?
|   |   (e.g., death first, then non-fatal events)
|   --> Win Ratio (WR), with explicit hierarchy and handling of unmatched/tied pairs
|
+-- Is the question diagnostic rather than therapeutic?
    --> Sensitivity, specificity, likelihood ratios (LR+ / LR-), AUROC; PPV/NPV only with prevalence

ALWAYS add: numerator/denominator or event risks, CI, time horizon, direction of benefit,
and an absolute measure. A relative measure alone is incomplete at a viva.
```

## C. 50 High-Yield Rapid-Fire Viva Q&As

1. **What does a p-value actually mean?** A p-value is the probability, assuming the null hypothesis and the analysis model are correct, of observing data at least as incompatible with the null as those observed. It is not the probability that the null is true, the probability that the result is due to chance, or the probability that treatment works.

2. **Why is “p < 0.05” not a clinical conclusion?** The threshold is a convention for long-run type I error control, not a boundary between truth and falsehood. Judge the effect size, CI, baseline risk, harms, feasibility, and totality of evidence.

3. **Define type I and type II error in an ICU trial.** A type I error is declaring benefit of an ineffective intervention, for example adopting a sepsis adjunct that only appears beneficial by chance. A type II error is missing a real benefit, often because a mortality trial has too few events or inadequate protocol separation.

4. **What is power, and what does 90% power mean?** Power is the probability of rejecting the null hypothesis when a specified alternative effect is true. Ninety percent power means the planned design has a 90% chance to detect its prespecified target effect at the chosen alpha, not a 90% chance that a positive result is correct.

5. **Why can an underpowered negative trial not prove no effect?** A wide CI may include both clinically important benefit and harm, so absence of statistical significance is evidence of imprecision rather than equivalence. Read what effects the CI excludes before calling an intervention futile.

6. **Why does multiplicity matter in critical-care trials?** Testing many outcomes, time points, subgroups, or interim looks raises the probability of at least one false-positive result. The primary outcome and multiplicity-control plan must be specified before unblinding rather than selected after an attractive signal appears.

7. **What is the difference between FWER and FDR?** Family-wise error rate (FWER) controls the chance of one or more false positives across a family of tests and is appropriate for confirmatory claims. False discovery rate (FDR) controls the expected proportion of false discoveries among declared positives and is more often used in exploratory high-dimensional work.

8. **Why did ANDROMEDA-SHOCK’s p = 0.06 not mean “no effect”?** Its primary 28-day mortality comparison did not cross the conventional 0.05 threshold, so the trial did not establish superiority on that endpoint. The point estimate and CI still required clinical interpretation, and subsequent analyses or secondary endpoints cannot retroactively convert the primary result into definitive proof.

9. **What does a 95% CI mean in frequentist terms?** Under repeated use of the same valid procedure, 95% of such intervals would contain the true parameter. It does not mean there is a 95% probability that this fixed parameter lies inside this particular observed interval.

10. **How do you distinguish statistical from clinical significance?** Statistical significance addresses compatibility of data with a null model, whereas clinical significance asks whether the magnitude is worth changing practice for. A tiny creatinine difference can be statistically significant in a large ICU dataset but irrelevant to dialysis, survival, or patient function.

11. **Why can’t we use standard Chi-square if an expected cell frequency is <5?** The usual Chi-square reference distribution relies on a large-sample approximation that becomes unreliable with sparse expected counts. Use Fisher exact testing for a small independent contingency table, or an appropriate exact/model-based method for more complex sparse data.

12. **When do you use McNemar rather than Chi-square?** Use McNemar for paired binary data, such as the same clinician’s pre- and post-training adherence or matched case-control pairs. It tests the imbalance in discordant pairs, whereas ordinary Chi-square incorrectly treats paired observations as independent.

13. **When is Mann–Whitney preferable to an unpaired t-test?** Use it for independent groups when the outcome is ordinal or continuous with severe skew/outliers that make a mean-based normal model unconvincing. It tests a rank-based distributional contrast, not automatically a difference in medians unless distributional shapes support that interpretation.

14. **Why is “normal data” not the key assumption for a t-test?** The relevant issue is whether the sampling distribution of the mean contrast and model residuals are adequately approximated, with independent observations and appropriate variance handling. Moderate non-normality is often tolerable in large balanced samples; clustering and gross outliers are more dangerous.

15. **What does ANOVA test, and what must follow a significant omnibus test?** One-way ANOVA tests the null hypothesis that all group means are equal. A significant result identifies that at least one differs; prespecified contrasts or multiplicity-adjusted post-hoc comparisons are needed to identify where.

16. **Why is a repeated-measures t-test unsuitable for serial SOFA scores?** It handles only a simple paired contrast and ignores irregular timing, more than two measurements, within-patient correlation, and informative dropout from death. Mixed-effects models or carefully specified longitudinal estimands are usually more defensible.

17. **What is confounding by indication?** In observational ICU care, the sickest patients are often preferentially given ECMO, vasopressors, or early RRT, so treatment status is associated with baseline prognosis. Crude mortality comparisons can therefore make an indicated rescue therapy look harmful even when it is beneficial.

18. **Explain immortal time bias in observational ECMO studies.** A patient assigned to the ECMO group must survive long enough to receive cannulation, creating a pre-cannulation “immortal” period if exposure is classified from baseline. Counting that time as exposed artificially favours ECMO; use time-varying exposure, a landmark design, or target-trial emulation.

19. **What does logistic regression estimate?** Logistic regression models the log odds of a binary outcome conditional on covariates and yields adjusted ORs. When mortality is common, an OR is not a risk ratio and should not be verbally inflated into one.

20. **How would you report an adjusted OR safely?** State the outcome time point, covariates used for adjustment, OR, CI, and the reference group, then give observed or model-based absolute risks when feasible. Do not imply causality from adjustment alone in a non-randomised dataset.

21. **What is overfitting?** Overfitting occurs when a model captures idiosyncratic noise in its development sample, producing optimistic apparent discrimination and unstable coefficients. It is common when few outcome events support many candidate predictors, interactions, or flexible transformations.

22. **Why are stepwise regression p-values unreliable?** Repeated data-driven selection ignores the selection process, inflates apparent significance, and yields unstable models. Prefer prespecified clinically grounded predictors, shrinkage/penalisation, internal validation, and transparent reporting.

23. **What are MCAR, MAR, and MNAR?** Missing completely at random (MCAR) means missingness is unrelated to observed or unobserved values; missing at random (MAR) means it is explainable by observed data; missing not at random (MNAR) depends on unobserved values even after conditioning. Multiple imputation usually relies on MAR, so MNAR sensitivity analysis is essential when that assumption is doubtful.

24. **Why is complete-case analysis risky in ICU datasets?** It discards patients and is unbiased only under restrictive missingness conditions, which may fail when severity, death, or treatment intensity predicts absent measurements. It also reduces precision and can change the target population without acknowledgement.

25. **What is multiple imputation trying to preserve?** It replaces each missing value with several plausible values drawn from an imputation model, analyses each completed dataset, and combines estimates using Rubin’s rules. A credible imputation model includes outcome, treatment, predictors of missingness, and variables related to the missing value.

26. **What does sensitivity measure, and why is it not enough for a diagnostic test?** Sensitivity is the proportion of diseased patients correctly testing positive. Clinical usefulness also requires specificity, likelihood ratios, calibration, consequences of false results, and performance in the intended spectrum of ICU patients.

27. **Why do PPV and NPV change between an ED and an ICU?** Positive and negative predictive values depend directly on pre-test disease prevalence. A test with unchanged sensitivity and specificity can have a much higher PPV in a high-prevalence septic-shock cohort than in an undifferentiated ward population.

28. **What is the advantage of likelihood ratios?** Likelihood ratios update pre-test odds to post-test odds and are less directly dependent on prevalence than predictive values. LR+ is sensitivity divided by one minus specificity, while LR− is one minus sensitivity divided by specificity.

29. **What does AUROC measure?** The AUROC is the probability that a randomly chosen patient with the outcome receives a higher predicted score than a randomly chosen patient without it. It measures discrimination, not calibration, clinical utility, or transportability.

30. **Why can a model with excellent AUROC still be unsafe?** It may systematically overpredict or underpredict risk, particularly after case-mix or treatment changes. Check calibration-in-the-large, calibration slope, clinically relevant thresholds, and external validation.

31. **State Bayes’ theorem in diagnostic language.** Post-test odds equal pre-test odds multiplied by the likelihood ratio. Therefore the same test result should change management differently in a low-risk patient with possible infection and a high-risk patient with refractory septic shock.

32. **Why is randomisation not a guarantee of balanced baseline tables?** Randomisation balances known and unknown prognostic factors on average across repeated trials, not deterministically in every realised sample. Baseline p-values are therefore unhelpful; assess clinical imbalances and prespecify adjusted analyses when appropriate.

33. **What is intention-to-treat (ITT) analysis?** ITT analyses participants in their randomised groups regardless of adherence, crossover, or protocol deviations. It preserves the comparison created by randomisation and usually estimates the effect of assigning a treatment policy.

34. **Why can per-protocol analysis be especially dangerous in non-inferiority trials?** Non-adherence and crossover dilute differences, making treatments look spuriously similar under ITT. Non-inferiority should therefore examine both ITT and carefully defined per-protocol populations, with concordant conclusions increasing credibility.

35. **How is a non-inferiority margin chosen?** It must be clinically acceptable and anchored to reliable evidence of the active control’s benefit over placebo or standard care, while preserving a meaningful fraction of that benefit. It is not chosen because it makes sample size convenient or because a sponsor prefers a favourable result.

36. **What is the correct interpretation when a non-inferiority CI crosses both the margin and zero?** The result is inconclusive: it does not establish non-inferiority and does not establish superiority. The CI permits clinically unacceptable harm as well as possible benefit.

37. **Why is assay sensitivity important in non-inferiority trials?** The trial must be capable of detecting a meaningful difference if one exists; otherwise poor adherence, insensitive outcomes, or protocol failures can produce false non-inferiority. Constancy of the active control effect and high trial conduct quality are central assumptions.

38. **What is a cluster-randomised trial, and what is its key analysis issue?** It randomises groups such as ICUs, hospitals, or time periods rather than individual patients. Patients within clusters are correlated, so analysis and sample size must account for the intracluster correlation coefficient (ICC).

39. **Why is an individual-level analysis of a cluster trial wrong?** Treating correlated patients as independent overstates effective sample size and produces overly narrow CIs and false-positive results. Use cluster-aware mixed models, GEE with robust inference, or appropriate cluster-level methods.

40. **What is an adaptive or MAMS platform trial?** An adaptive trial uses prospectively specified rules to modify aspects such as dropping futile arms or changing randomisation probabilities; MAMS means multi-arm, multi-stage. Validity requires prespecified decision rules, error control, and careful interpretation when the standard of care changes over time.

41. **What does a Kaplan–Meier curve estimate?** It estimates the survivor function for time to a specified event while handling right censoring under assumptions including non-informative censoring. It is appropriate for time-to-death but can misrepresent probability of renal recovery when death is a competing event.

42. **What is the proportional hazards assumption in Cox regression?** It assumes that the hazard ratio between groups is constant over follow-up, conditional on covariates. Inspect plots and time interactions; if hazards cross, report time-varying effects or restricted mean survival time rather than one misleading HR.

43. **Why is the hazard ratio not a risk ratio?** A hazard is an instantaneous event rate among those still event-free, whereas risk is cumulative probability over a stated time. A HR of 0.80 does not mean a 20% absolute or even cumulative relative mortality reduction.

44. **When should you use competing-risk methods?** Use them when an event permanently precludes the target event, such as death before dialysis independence or discharge before ICU delirium assessment. Report the cumulative incidence function and specify whether the model estimates a cause-specific or subdistribution effect.

45. **What is the win ratio, and what is its main vulnerability?** The win ratio compares prioritised outcomes hierarchically in treatment-versus-control pairs, often prioritising death over less severe events. Its result depends on the hierarchy, pairing/comparability rules, and handling of ties, so it must not obscure the individual component outcomes.

46. **Why must a meta-analysis assess heterogeneity before offering a pooled answer?** Pooling assumes studies estimate sufficiently related effects; differences in ARDS severity, co-interventions, timing, and outcome definitions can make one summary clinically misleading. Examine forest plots, direction and magnitude of effects, I², tau-squared, prediction intervals, and prespecified subgroup hypotheses.

47. **What does an I² of 75% mean for your clinical practice?** It suggests that a substantial proportion of observed variation across study estimates is beyond sampling error, but it does not identify the cause or prove that pooling is invalid. Investigate clinical and methodological heterogeneity and use the prediction interval to judge what effect a new ICU might plausibly see.

48. **Why is a random-effects model not an automatic cure for heterogeneity?** It changes the statistical weighting and assumes a distribution of true effects, but it cannot make incomparable populations or biased studies comparable. A random-effects pooled estimate still needs a defensible clinical question and transparent exploration of heterogeneity.

49. **How do you assess publication bias, and what are the limits?** Search trial registries and grey literature, compare protocols with publications, and inspect funnel plots or use small-study-effect tests when enough studies exist. Funnel asymmetry is not proof of publication bias because genuine heterogeneity, chance, and selective methods can produce the same pattern.

50. **What does GRADE add beyond statistical significance?** GRADE rates certainty in an effect estimate by considering risk of bias, inconsistency, indirectness, imprecision, and publication bias, with possible upgrading domains for observational evidence. It separates “an effect is statistically detectable” from “we can make a confident clinical recommendation.”

## D. Glossary of Abbreviations

| Abbreviation | Definition |
|---|---|
| aHR | Adjusted hazard ratio; hazard ratio conditional on specified covariates. |
| AIC | Akaike information criterion; a relative model-fit measure balancing fit against model complexity. |
| AKI | Acute kidney injury. |
| ALT | Average length of stay; a mean duration measure that may be distorted by death and skewness. |
| ANCOVA | Analysis of covariance; regression comparing groups while adjusting for baseline or other covariates. |
| ANOVA | Analysis of variance; test/model for comparing means across more than two groups. |
| AOR | Adjusted odds ratio; OR estimated conditional on covariates in a regression model. |
| APE | Average partial effect; average change in predicted outcome associated with a covariate change. |
| APR | Adjusted prevalence ratio; prevalence ratio adjusted for covariates. |
| ARDS | Acute respiratory distress syndrome. |
| ARR | Absolute risk reduction; control risk minus treatment risk when treatment lowers risk. |
| AST | Average survival time; mean survival over a stated time horizon. |
| AUC | Area under the curve; generic area measure, commonly the area under an ROC curve. |
| AUROC | Area under the receiver-operating-characteristic curve; discrimination measure. |
| BIC | Bayesian information criterion; model-fit measure with a stronger complexity penalty than AIC. |
| BSA | Body surface area. |
| CACE | Complier average causal effect; causal effect among participants who would comply with assigned treatment. |
| CATE | Conditional average treatment effect; treatment effect within a covariate-defined subgroup. |
| CC | Complete-case analysis; analysis restricted to records with complete required data. |
| CCI | Charlson Comorbidity Index; weighted comorbidity score used for risk adjustment. |
| CD | Cumulative distribution; distribution function giving probability up to a value. |
| cHR | Cause-specific hazard ratio; relative instantaneous rate for an event among those free of all events. |
| CI | Confidence interval; interval estimate produced by a stated confidence procedure. |
| CIF | Cumulative incidence function; probability of an event by time *t* in the presence of competing risks. |
| CONSORT | Consolidated Standards of Reporting Trials; reporting guideline for randomised trials. |
| COVID-19 | Coronavirus disease 2019. |
| Cox PH | Cox proportional-hazards model; semiparametric survival regression model. |
| CPP | Cerebral perfusion pressure. |
| CR | Competing risk; event that precludes occurrence of the event of interest. |
| CRF | Case report form. |
| CRO | Contract research organisation. |
| CRT | Cluster-randomised trial. |
| CV | Coefficient of variation; SD divided by mean. |
| DAG | Directed acyclic graph; causal diagram used to identify confounding structures. |
| DCA | Decision-curve analysis; net-benefit evaluation across threshold probabilities. |
| DF | Degrees of freedom; number of independent quantities informing a statistic. |
| DIC | Disseminated intravascular coagulation. |
| DNR | Do not resuscitate order. |
| DOR | Diagnostic odds ratio; odds of positivity in disease divided by odds of positivity without disease. |
| DSMB | Data and Safety Monitoring Board; independent body overseeing accumulating trial safety/data. |
| DVT | Deep-vein thrombosis. |
| ECMO | Extracorporeal membrane oxygenation. |
| EDA | Exploratory data analysis. |
| EMM | Estimated marginal mean; model-derived adjusted group mean. |
| EQ-5D | EuroQol 5-Dimension; health-related quality-of-life instrument. |
| E-value | Minimum strength of unmeasured confounding needed to explain away an observed association on a risk-ratio scale. |
| FDA | United States Food and Drug Administration. |
| FDR | False discovery rate; expected proportion of false positives among declared discoveries. |
| FEV1 | Forced expiratory volume in one second. |
| FIO2 | Fraction of inspired oxygen. |
| FN | False negative. |
| FNR | False-negative rate; 1 minus sensitivity. |
| FP | False positive. |
| FPR | False-positive rate; 1 minus specificity. |
| FWER | Family-wise error rate; probability of at least one false positive in a family of tests. |
| GCS | Glasgow Coma Scale. |
| GEE | Generalised estimating equation; population-averaged regression for correlated observations. |
| GLM | Generalised linear model; regression framework including linear, logistic, and Poisson models. |
| GLMM | Generalised linear mixed model; GLM with random effects for clustered/repeated data. |
| GRADE | Grading of Recommendations Assessment, Development and Evaluation; framework for certainty of evidence and recommendation strength. |
| H0 | Null hypothesis, usually no difference or no association. |
| H1 | Alternative hypothesis. |
| HFNO | High-flow nasal oxygen. |
| HR | Hazard ratio; ratio of instantaneous event rates under model assumptions. |
| HRQoL | Health-related quality of life. |
| HWE | Hardy–Weinberg equilibrium; genotype-frequency equilibrium in a population under stated assumptions. |
| I² | I-squared; proportion of observed meta-analytic variation attributed to heterogeneity rather than sampling error. |
| ICC | Intracluster correlation coefficient; within-cluster outcome correlation. |
| ICH | International Council for Harmonisation. |
| ICM | Intensive care medicine. |
| ICU | Intensive care unit. |
| IDI | Integrated discrimination improvement; a change in average predicted risks for events and non-events. |
| IF | Influence function; quantity used in robust inference and variance estimation. |
| IMV | Invasive mechanical ventilation. |
| INB | Incremental net benefit; monetary summary used in cost-effectiveness analysis. |
| IPD | Individual participant data. |
| IQR | Interquartile range; 25th to 75th percentile range. |
| IRR | Incidence rate ratio; ratio of event rates per person-time. |
| ITT | Intention-to-treat; analysis by randomised assignment regardless of adherence. |
| JAMA | Journal of the American Medical Association. |
| K-M / KM | Kaplan–Meier; estimator/curve for the survivor function with right censoring. |
| LASSO | Least absolute shrinkage and selection operator; penalised regression method. |
| LCI | Lower confidence interval limit. |
| LME | Linear mixed-effects model; regression with fixed and random effects. |
| LOESS | Locally estimated scatterplot smoothing; non-parametric local regression smoother. |
| LOS | Length of stay. |
| LR | Likelihood ratio; probability of a result with disease divided by probability without disease. |
| LR+ | Positive likelihood ratio; sensitivity divided by 1 minus specificity. |
| LR− | Negative likelihood ratio; 1 minus sensitivity divided by specificity. |
| MAMS | Multi-arm, multi-stage; platform/adaptive trial design with multiple arms and interim stages. |
| MAR | Missing at random; missingness conditional on observed data. |
| MCAR | Missing completely at random; missingness unrelated to observed and unobserved data. |
| MCID | Minimal clinically important difference; smallest effect regarded as important to patients/clinicians. |
| MCMC | Markov chain Monte Carlo; simulation method for sampling from probability distributions. |
| MI | Multiple imputation; repeated plausible imputation of missing values with combined inference. |
| MICE | Multivariate imputation by chained equations; common iterative multiple-imputation method. |
| mITT | Modified intention-to-treat; an ITT-like population with a prespecified post-randomisation exclusion. |
| MLE | Maximum likelihood estimation; parameter estimation by maximising likelihood. |
| MMRM | Mixed model for repeated measures; likelihood-based longitudinal model for repeated outcomes. |
| MNAR | Missing not at random; missingness depends on unobserved data after conditioning on observed data. |
| MOF | Multiple organ failure. |
| MR | Missingness rate; proportion of values not observed. |
| MRSA | Meticillin-resistant *Staphylococcus aureus*. |
| MSD | Mean square difference; variance-related quantity in analysis of variance contexts. |
| MSE | Mean squared error; average squared difference between estimate/prediction and target. |
| N | Total sample size. |
| NCP | Non-centrality parameter; parameter governing power under an alternative hypothesis. |
| NEJM | New England Journal of Medicine. |
| NMA | Network meta-analysis; comparison of multiple treatments using direct and indirect evidence. |
| NNH | Number needed to harm; reciprocal of an absolute risk increase over a stated time horizon. |
| NNT | Number needed to treat; reciprocal of ARR over a stated time horizon, rounded appropriately. |
| NPV | Negative predictive value; probability of no disease given a negative test. |
| NS | Not statistically significant; a reporting shorthand that must not imply no clinically important effect. |
| NT-proBNP | N-terminal pro-B-type natriuretic peptide. |
| O2 | Oxygen. |
| OLS | Ordinary least squares; linear-regression estimation minimising squared residuals. |
| OR | Odds ratio; ratio of outcome odds between groups. |
| PaO2/FiO2 | Ratio of arterial oxygen tension to inspired oxygen fraction; oxygenation index used in ARDS. |
| PCC | Proportional change in covariance; a clustering-related covariance summary. |
| PCR | Polymerase chain reaction. |
| PH | Proportional hazards; assumption that hazard ratios remain constant over time. |
| PICO | Population, intervention, comparator, outcome; framework for a focused clinical question. |
| PP | Per-protocol; analysis restricted/adjusted according to adherence to protocol. |
| PPV | Positive predictive value; probability of disease given a positive test. |
| PR | Prevalence ratio; ratio of outcome prevalence between groups. |
| PRISMA | Preferred Reporting Items for Systematic Reviews and Meta-Analyses; reporting guideline. |
| PRO | Patient-reported outcome. |
| PS | Propensity score; probability of treatment conditional on measured covariates. |
| PSM | Propensity-score matching; matching treated and untreated participants by estimated treatment probability. |
| QALY | Quality-adjusted life-year. |
| RCT | Randomised controlled trial. |
| RD | Risk difference; treatment risk minus comparator risk (state direction explicitly). |
| RDS | Respiratory distress syndrome. |
| REML | Restricted maximum likelihood; method for estimating variance components, including meta-analytic heterogeneity. |
| RMST | Restricted mean survival time; expected event-free survival up to a prespecified time horizon. |
| RoB | Risk of bias; systematic deviation from the truth due to study design/conduct/analysis. |
| ROBINS-I | Risk Of Bias In Non-randomized Studies of Interventions; assessment tool. |
| ROC | Receiver-operating-characteristic; sensitivity-versus-1-specificity curve across thresholds. |
| RR | Risk ratio (relative risk); treatment risk divided by comparator risk. |
| RRR | Relative risk reduction; 1 minus RR when treatment lowers risk. |
| RRT | Renal replacement therapy. |
| SAE | Serious adverse event. |
| SAP | Statistical analysis plan; prespecified detailed analytic methods for a study. |
| SAPS | Simplified Acute Physiology Score. |
| SD | Standard deviation; dispersion of individual observations around their mean. |
| SE | Standard error; estimated sampling variability of an estimator. |
| SH | Subdistribution hazard; hazard used in Fine–Gray competing-risk modelling. |
| SHR | Subdistribution hazard ratio; relative subdistribution hazard from Fine–Gray regression. |
| SMD | Standardised mean difference; mean difference divided by a pooled/standardising SD. |
| SOFA | Sequential Organ Failure Assessment score. |
| SOP | Standard operating procedure. |
| SpO2 | Peripheral oxygen saturation. |
| SROC | Summary receiver-operating-characteristic curve; meta-analytic diagnostic-accuracy summary. |
| STARD | Standards for Reporting Diagnostic Accuracy Studies; diagnostic-study reporting guideline. |
| STROBE | Strengthening the Reporting of Observational Studies in Epidemiology; reporting guideline. |
| SUPER | Superiority; trial objective to show a treatment is better than comparator. |
| SUSAR | Suspected unexpected serious adverse reaction. |
| TAVI | Transcatheter aortic valve implantation. |
| TC | Treatment crossover. |
| TE | Treatment effect; contrast in outcome attributable to a treatment under a defined estimand. |
| TEAE | Treatment-emergent adverse event. |
| TN | True negative. |
| TP | True positive. |
| TRIPOD | Transparent Reporting of a multivariable prediction model for Individual Prognosis Or Diagnosis; prediction-model reporting guideline. |
| TTE | Time to event; outcome defined by time until an event occurs. |
| UCI | Upper confidence interval limit. |
| VAP | Ventilator-associated pneumonia. |
| VFD | Ventilator-free days; composite outcome requiring explicit handling of death. |
| VIF | Variance inflation factor; measure of collinearity in regression. |
| WHO | World Health Organization. |
| WMD | Weighted mean difference; meta-analytic pooled mean difference on a common scale. |
| WR | Win ratio; ratio of treatment wins to control wins in prioritised pairwise comparisons. |
