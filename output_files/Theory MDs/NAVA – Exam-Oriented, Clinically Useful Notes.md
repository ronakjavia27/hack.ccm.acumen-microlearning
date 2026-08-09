
## NAVA 

**Neurally Adjusted Ventilatory Assist (NAVA)** is a proportional, patient-triggered and patient-cycled mode of ventilation that uses the **electrical activity of the diaphragm (EAdi/Edi)** to drive ventilator support in real time. [^1_1][^1_2][^1_3]

***

## 1. Definition \& Core Concept

- **NAVA** = ventilator delivers pressure **proportional** to the **integral of EAdi** during each breath. [^1_4][^1_3]
- The ventilator is:
    - **Triggered** by increase in EAdi (neural trigger)
    - **Cycled off** when EAdi falls to ~70% of its peak
    - **Proportional** throughout inspiration (not just at start) [^1_3][^1_5]
- Patient controls:
    - Respiratory rate
    - Inspiratory time (Ti)
    - Tidal volume (via effort)
    - Flow pattern
Ventilator only **assists** in proportion to neural drive. [^1_6][^1_7]

***

## 2. Physiological Rationale (Why NAVA?)

NAVA is designed to **restore normal neuro-mechanical coupling** between respiratory centers and the ventilator.

### 2.1. Normal Physiology

- Respiratory centers → phrenic nerve → diaphragm contraction → negative intrathoracic pressure → airflow.
- In normal breathing, **neural output** determines:
    - When to breathe
    - How hard to breathe
    - How long to inspire


### 2.2. Problems with Conventional Modes

In pressure/flow-triggered modes (PSV, SIMV, PRVC):

- **Trigger delay**: ventilator detects pressure/flow change **after** diaphragm starts contracting.
- **Cycle-off mismatch**: fixed flow or time criteria may not match neural end of inspiration.
- **Over/under-assistance**: fixed pressure support doesn’t adapt breath-to-breath to changing demand.
- **Leaks and intrinsic PEEP**: degrade triggering and cycling, especially in NIV and pediatrics. [^1_4][^1_8][^1_9]

Consequences:

- Patient–ventilator asynchrony
- Increased work of breathing or diaphragm unloading
- Potential for VIDD (ventilator-induced diaphragm dysfunction) or excessive load


### 2.3. How NAVA Fixes This

- Uses **EAdi** as the control signal → “neural trigger” and “neural cycle”.
- Ventilator assistance starts **before** mechanical movement (pre-contraction neural signal). [^1_6][^1_10]
- Support is **proportional** to neural drive throughout inspiration → matches demand dynamically.
- Independent of:
    - Leaks
    - Circuit mechanics
    - Intrinsic PEEP
    - Lung mechanics changes (within limits) [^1_11][^1_8]

Net effect: **better synchrony, more physiologic breathing, protection against both over- and under-assistance.** [^1_4][^1_3][^1_9]

***

## 3. Working Principle \& Signal Processing

### 3.1. EAdi Catheter

- Specialized **nasogastric/orogastric tube** with:
    - Array of **electrodes** at distal end (commonly 9 electrodes / 8 pairs). [^1_12]
- Positioned in **esophagus at diaphragm level**.
- Detects **crural diaphragm EMG** (EAdi) in µV. [^1_1][^1_13]

Signal processing (simplified):

1. Multiple electrode pairs record EMG.
2. Cross-correlation identifies diaphragm position relative to electrode array.
3. Signals above and below diaphragm (opposite phase) are subtracted → “double-subtracted” signal.
4. Root-mean-square of center + double-subtracted signals → **EAdi**.
5. EAdi sampled every ~16 ms (>60 times/sec). [^1_1][^1_13][^1_12]

### 3.2. How Pressure is Generated

Inspiratory airway pressure above PEEP:

$$
P_{\text{aw,insp}} = \text{NAVA level} \times (\text{EAdi}_{\text{peak}} - \text{EAdi}_{\text{min}}) + \text{PEEP}
$$

- **NAVA level** = gain (cmH₂O/µV), set by clinician. [^1_5][^1_7]
- **ΔEAdi** = patient’s neural drive for that breath.
- Pressure is updated continuously during inspiration, not just at start. [^1_13][^1_7]

Thus:

- Higher drive → higher ΔEAdi → higher pressure.
- Same NAVA level → same proportionality between neural output and pressure.

***

## 4. Starting NAVA – Practical Steps

### 4.1. Prerequisites

- Patient must have:
    - Intact **respiratory drive** (not apneic, not deeply sedated/paralyzed).
    - Intact **phrenic nerve–diaphragm pathway**.
- NAVA-capable ventilator (e.g., Servo-i/n, Servo-u).
- NAVA catheter (EAdi catheter).


### 4.2. Catheter Placement

1. Insert NAVA catheter via nose or mouth like an NG tube.
2. Advance to stomach (check by usual NG methods: auscultation, X-ray if needed).
3. Withdraw slowly while observing **EAdi signal** on ventilator:
    - Look for clear, cardiac-artifact-free EAdi waveform.
    - Optimal position: maximal EAdi with minimal ECG interference. [^1_10][^1_12]
4. Confirm position:
    - Ventilator often has a **positioning tool** (signal quality indicator).
    - Chest X-ray can confirm tip position if uncertain.

### 4.3. Initial Settings

Typical starting approach (adult; adapt per unit protocol):

- **Mode**: NAVA
- **PEEP**: as per lung-protective strategy.
- **FiO₂**: as needed.
- **NAVA level**:
    - Start around **1–2 cmH₂O/µV**.
    - Adjust to achieve:
        - Comfortable breathing pattern
        - Acceptable tidal volume
        - Reduced but not abolished EAdi (avoid complete unloading). [^1_10][^1_7]
- **Back-up ventilation**:
    - Set minimum rate and/or pressure control in case of apnea or signal loss. [^1_10]
- **Pressure limit**:
    - Set upper pressure alarm/limit to avoid excessive PIP.


### 4.4. Titration of NAVA Level

Goal: balance between:

- **Too low**: patient works too hard, high EAdi, fatigue.
- **Too high**: over-assistance, low EAdi, diaphragm inactivity.

Practical titration:

- Observe:
    - EAdi waveform (peak values, pattern)
    - Respiratory rate, tidal volume
    - Patient comfort, accessory muscle use
    - ABG (pH, PaCO₂, PaO₂)
- Adjust NAVA level in small steps (e.g., 0.2–0.5 cmH₂O/µV).
- Aim for:
    - Reduced but present EAdi (not near zero unless full support intended).
    - Stable gases, comfortable patient. [^1_10][^1_7]

***

## 5. Interpreting the EAdi Waveform

Key points for exams and bedside:

- **Baseline EAdi**: should be near zero at end-expiration.
- **EAdi peak**: reflects neural inspiratory drive.
- **Shape**:
    - Smooth, phasic bursts → good neural signal.
    - Erratic, noisy, or constant high signal → artifact, poor positioning, or high drive.
- **Trends**:
    - Rising EAdi over time → increased drive (pain, anxiety, hypoxemia, acidosis, increased load).
    - Falling EAdi → improved condition or over-assistance / sedation.

Many units use EAdi as a **monitor of respiratory drive** even when not on NAVA.

***

## 6. Troubleshooting Common Problems

### 6.1. No or Poor EAdi Signal

Possible causes:

- Catheter malposition (too high/low in esophagus or stomach).
- Disconnection or faulty catheter.
- Very low respiratory drive (deep sedation, neuromuscular blockade, central apnea).
- Severe diaphragmatic dysfunction or phrenic nerve injury.

Actions:

- Check catheter position; reposition using ventilator’s positioning tool.
- Reduce sedation if excessive.
- Confirm patient has spontaneous effort.
- Replace catheter if suspected fault.
- Use back-up ventilation if no reliable EAdi.


### 6.2. Excessive Cardiac Artifact

- EAdi trace shows QRS-like spikes.
- Often due to catheter too close to heart.

Actions:

- Slightly advance or withdraw catheter to optimize signal.
- Use ventilator’s filtering/positioning algorithms.


### 6.3. Asynchrony Despite NAVA

Rare but possible:

- Check for:
    - Secretions, bronchospasm, kinked tube.
    - Inappropriate NAVA level (too low or too high).
    - Patient distress (pain, agitation).
- Optimize NAVA level, treat underlying cause, consider alternative mode if severe.


### 6.4. High EAdi with Distress

Indicates high neural drive:

- Causes: hypoxemia, hypercapnia, acidosis, pain, anxiety, increased load (stiff lungs, high resistance).
- Actions:
    - Optimize oxygenation/ventilation.
    - Treat underlying pathology.
    - Reassess NAVA level (may need higher support or different strategy).

***

## 7. Advantages (Pros)

- **Superior patient–ventilator synchrony**:
    - Neural trigger and neural cycle.
    - Less trigger delay, less premature/late cycling. [^1_4][^1_3][^1_9]
- **Proportional support**:
    - Matches breath-by-breath demand.
    - Reduces risk of over- and under-assistance. [^1_11][^1_5]
- **Preserves physiologic breathing variability**:
    - Natural variability in rate, Ti, VT maintained. [^1_11][^1_8]
- **Less affected by leaks and intrinsic PEEP**:
    - Useful in NIV, pediatrics, and patients with high intrinsic PEEP (COPD). [^1_8]
- **Potential lung- and diaphragm-protective effects**:
    - Avoids excessive unloading → may reduce VIDD.
    - Maintains some diaphragmatic activity while reducing fatigue. [^1_3]
- **May reduce sedation requirements**:
    - Better comfort, less fighting the ventilator. [^1_14][^1_10]

***

## 8. Limitations \& Disadvantages (Cons)

- **Requires intact respiratory drive and phrenic–diaphragm pathway**:
    - Not suitable for apneic, deeply sedated, or paralyzed patients. [^1_14]
- **Technical requirements**:
    - Special catheter and NAVA-capable ventilator.
    - Need for training and familiarity.
- **Signal issues**:
    - Artifact from cardiac activity, movement, poor positioning.
    - Occasional loss of signal requiring fallback to conventional mode.
- **Limited outcome data in adults**:
    - Strong physiologic and synchrony benefits demonstrated.
    - Clear mortality/ventilator-free day benefit in adults not definitively proven in large RCTs (as of current evidence). [^1_8][^1_9]
- **Cost and availability**:
    - More expensive than standard modes; not universally available.

***

## 9. NAVA vs Conventional Modes – Quick Exam Table

| Feature | Conventional (e.g., PSV, SIMV) | NAVA |
| :-- | :-- | :-- |
| Trigger | Pressure or flow | Electrical activity of diaphragm (EAdi) |
| Cycle-off | Flow/time/pressure based | EAdi fall to ~70% of peak |
| Support pattern | Fixed or limited proportional | Continuously proportional to EAdi |
| Effect of leaks | Impairs triggering/cycling | Minimal effect |
| Effect of intrinsic PEEP | Can cause trigger delay/failure | Less affected |
| Breathing variability | Often reduced | Preserved |
| Patient control | Partial (rate, effort) | Full (rate, Ti, VT, flow pattern) |
| Need for special hardware | No | Yes (EAdi catheter + NAVA ventilator) |
| Best suited for | Most patients | Patients with spontaneous drive, especially with asynchrony, NIV, pediatrics |


***

## 10. Clinical Pearls (High-Yield for Exams \& ICU)

- NAVA is a **proportional assist mode** driven by **neural output**, not airway mechanics.
- Key equation to remember:

$$
P_{\text{insp}} = \text{NAVA level} \times \Delta \text{EAdi} + \text{PEEP}
$$
- Ideal candidate: patient with **spontaneous drive** but significant **asynchrony** or high work of breathing.
- Use EAdi trend as a **monitor of respiratory drive** even outside NAVA.
- If EAdi is very low or absent → think: deep sedation, paralysis, apnea, catheter issue.
- NAVA does **not** guarantee lung protection by itself; you still need appropriate PEEP, VT limits, and overall strategy.

***


<span style="display:none">[^1_15]</span>

<div align="center">⁂</div>

[^1_1]: https://www.ncbi.nlm.nih.gov/books/NBK572111/

[^1_2]: https://en.wikipedia.org/wiki/Neurally_adjusted_ventilatory_assist

[^1_3]: https://pmc.ncbi.nlm.nih.gov/articles/PMC9000024/

[^1_4]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4727498/

[^1_5]: https://pmc.ncbi.nlm.nih.gov/articles/PMC7417783/

[^1_6]: http://www.mchrt.ca/uploads/1/2/0/8/120815073/mch_picu_nava_protocol_may_12.2022.pdf

[^1_7]: http://www.rtsupport.org/orientdisplay/nava

[^1_8]: https://ccforum.biomedcentral.com/articles/10.1186/cc11297

[^1_9]: https://www.frontiersin.org/journals/medicine/articles/10.3389/fmed.2022.814245/full

[^1_10]: https://www.youtube.com/watch?v=T6tlda_MElU

[^1_11]: https://www.scielo.br/j/rbti/a/LbmdBTyzSCZrsJHbk9N8mQG/?format=pdf\&lang=en

[^1_12]: https://link.springer.com/article/10.1007/s00134-013-2953-5

[^1_13]: https://journals.sagepub.com/doi/pdf/10.1177/175114371301400409

[^1_14]: https://journals.lww.com/ccmjournal/abstract/2013/12001/1170__neurally_adjusted_ventilatory_assist.1122.aspx

[^1_15]: https://aneskey.com/neurally-adjusted-ventilatory-assist/

