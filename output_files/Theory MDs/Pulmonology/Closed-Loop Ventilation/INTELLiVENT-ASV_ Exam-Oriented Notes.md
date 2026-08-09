
## INTELLiVENT-ASV

**INTELLiVENT-ASV** is a **full closed-loop ventilation mode** that automatically adjusts **RR, VT, Ti, PEEP, and FiO₂** based on real-time physiological inputs (PetCO₂, SpO₂, lung mechanics, spontaneous effort) to achieve clinician-set **oxygenation and ventilation targets**. [^1_1][^1_2][^1_3] It is the evolution of **Adaptive Support Ventilation (ASV)** with added **automated oxygenation and weaning control**. [^1_4][^1_5]

***

## Definition \& Core Concept

- **Full closed-loop ventilation**: Ventilator continuously adjusts all major parameters without operator intervention. [^1_2][^1_6]
- **Dual control**: Simultaneously manages **ventilation (CO₂ elimination)** and **oxygenation (SpO₂)**. [^1_2][^1_7]
- **Single-mode ventilation**: Can be used from **intubation to extubation** without switching modes. [^1_3][^1_7]
- **Target-driven**: Clinician sets **PetCO₂** and **SpO₂** target ranges; machine does the rest. [^1_4][^1_3]

***

## Classification

| Feature | INTELLiVENT-ASV |
| :-- | :-- |
| **Type** | Closed-loop, dual-control mode |
| **Based on** | Adaptive Support Ventilation (ASV) |
| **Control variables** | RR, VT, Ti, PEEP, FiO₂ |
| **Feedback inputs** | PetCO₂, SpO₂, lung mechanics, spontaneous breaths |
| **Patient type** | Passive and active (adult/pediatric ≥7 kg) |
| **Availability** | Hamilton C3, C6, G5, T1, S1 (not available in US) |

[^1_1][^1_2][^1_8]

***

## How It Works: The 3 Controllers

INTELLiVENT-ASV has **three independent closed-loop controllers**: [^1_3][^1_7]

### 1. **MinVol Controller (Ventilation/CO₂)**

- **Target**: PetCO₂ (end-tidal CO₂)
- **Adjusts**: **Respiratory rate (RR)** and **tidal volume (VT)**
- **Mechanism**: Uses **minimal work of breathing** principle (Otis equation)
- **Equation basis**:

$$
\text{Optimal RR} = \frac{\sqrt{1 + 4 \cdot \pi^2 \cdot f_{\text{opt}}^2 \cdot \tau^2} - 1}{2 \cdot \pi^2 \cdot \tau}
$$

Where τ = time constant of respiratory system [^1_5][^1_9]
- **Lung protection**: Limits VT to **4–8 mL/kg IBW**, keeps **driving pressure <15 cmH₂O** [^1_10][^1_9]


### 2. **Oxygen Controller (Oxygenation)**

- **Target**: SpO₂ (pulse oximetry)
- **Adjusts**: **FiO₂** and **PEEP**
- **Mechanism**:
    - First adjusts **FiO₂** to reach SpO₂ target
    - If FiO₂ >0.6, starts increasing **PEEP**
    - Prevents hyperoxia (SpO₂ > target upper limit) [^1_7][^1_11]
- **PEEP titration**: Based on **SpO₂ response**, not fixed PEEP table


### 3. **PEEP Controller (Lung Protection)**

- **Independent PEEP adjustment** based on:
    - **Driving pressure (ΔP = Pplat – PEEP)**
    - **Mechanical power**
    - **Lung mechanics (compliance, resistance)**
- **Goal**: Minimize **VILI** by keeping ΔP low [^1_9][^1_7]

***

## Setup Workflow (4 Steps)

1. **Enter patient basics**:
    - Sex, height → calculates **ideal body weight (IBW)**
    - Select **lung condition**: Normal, ARDS, COPD/hypercapnia, Brain injury [^1_4][^1_3]
2. **Set targets**:
    - **PetCO₂**: e.g., 35–45 mmHg (normal), 45–55 mmHg (COPD)
    - **SpO₂**: e.g., 92–96% (normal), 88–92% (COPD) [^1_4][^1_3]
3. **Start ventilation**:
    - Machine automatically adjusts **RR, VT, FiO₂, PEEP** breath-by-breath [^1_3]
4. **Fine-tune (optional)**:
    - Any controller can be set to **manual** if needed [^1_3]

***

## Key Features

### **1. Automatic Transition: Passive ↔ Active**

- Detects **spontaneous breathing effort**
- Seamlessly switches from **controlled** to **assisted** ventilation
- No need to change mode (e.g., PCV → PSV) [^1_1][^1_2]


### **2. Quick Wean (Automated Weaning Protocol)**

- **Progressive reduction** of pressure support
- **Readiness-to-wean screening** (spontaneous RR, VT, etCO₂ stability)
- Can perform **automated SBTs** at set intervals
- Promotes **early extubation** [^1_12][^1_4][^1_9]


### **3. Lung-Protective Strategies**

- **VT limitation**: 4–8 mL/kg IBW
- **Driving pressure control**: <15 cmH₂O
- **Mechanical power monitoring**
- **Dynamic Lung visualization** for real-time mechanics [^1_2][^1_10][^1_9]


### **4. Visual Decision Support**

- **Ventilation Cockpit**: Shows targets vs. actual values
- **Dynamic Lung**: Real-time compliance, resistance, ΔP
- **Horizon graphs**: Trend data over time [^1_12][^1_2]

***

## Clinical Indications

| Condition | PetCO₂ Target | SpO₂ Target | Special Considerations |
| :-- | :-- | :-- | :-- |
| **Normal lungs** | 35–45 mmHg | 92–96% | Standard settings |
| **ARDS** | 35–45 mmHg | 88–95% | Low VT, higher PEEP |
| **COPD/Chronic hypercapnia** | 45–55 mmHg | 88–92% | Accept higher CO₂ |
| **Brain injury** | 30–35 mmHg | 94–98% | Avoid hypercapnia |
| **Post-cardiac surgery** | 35–45 mmHg | 92–96% | Standard |

[^1_4][^1_3][^1_7]

***

## Advantages

- **Reduces workload**: Fewer manual adjustments [^1_2][^1_6]
- **Consistent lung protection**: Automated VT, ΔP, MP limits [^1_10][^1_9]
- **Faster weaning**: Quick Wean protocol [^1_12][^1_9]
- **Single mode**: No need to switch between PCV, PSV, SIMV [^1_7]
- **Safe**: As effective as conventional modes for VT and oxygenation control [^1_10][^1_6]

***

## Limitations \& Controversies

- **No outcome superiority**: RCTs show **no reduction** in ventilation duration or mortality vs. conventional modes [^1_10]
- **Not available in USA**: Regulatory restrictions [^1_4][^1_2]
- **Requires reliable monitoring**: Needs accurate **PetCO₂** and **SpO₂** [^1_6]
- **Cost**: Optional software feature (enterprise pricing) [^1_2]
- **Learning curve**: Clinicians must understand **closed-loop logic** [^1_8]

***

## Evidence Summary

| Study | Design | Findings |
| :-- | :-- | :-- |
| **Bialais et al. (2014)** | RCT, ICU | Safe, effective for VT and oxygenation titration [^1_3][^1_6] |
| **Systematic Review (2021)** | 10 RCTs, meta-analysis | - As safe as conventional modes<br>- No superiority in weaning time or mortality<br>- Effective for lung-protective VT [^1_10] |
| **Feasibility Study (2013)** | Prospective | Automated FiO₂, PEEP, %MV adjustments feasible and safe [^1_6] |


***

## Exam Pearls \& MCQ Points

- **INTELLiVENT-ASV = ASV + automated O₂ + automated weaning** [^1_4][^1_5]
- **Three controllers**: MinVol (CO₂), Oxygen (SpO₂), PEEP (lung protection) [^1_3][^1_7]
- **Targets**: PetCO₂ and SpO₂ (not VT or RR) [^1_4][^1_3]
- **Lung protection**: VT 4–8 mL/kg, ΔP <15 cmH₂O [^1_10][^1_9]
- **Quick Wean**: Automated SBT and pressure support reduction [^1_12][^1_9]
- **Not superior** to conventional modes in RCTs (outcome-wise) [^1_10]
- **Not available in USA** [^1_4][^1_2]

***

## Comparison: INTELLiVENT-ASV vs. ASV vs. Conventional Modes

| Feature | INTELLiVENT-ASV | ASV | Conventional (PCV/PSV) |
| :-- | :-- | :-- | :-- |
| **Closed-loop** | Full (CO₂ + O₂) | Partial (CO₂ only) | None |
| **Adjusts** | RR, VT, Ti, PEEP, FiO₂ | RR, VT, Ti | Manual |
| **Targets** | PetCO₂, SpO₂ | MinVol (VT) | Set by clinician |
| **Weaning** | Automated (Quick Wean) | Manual | Manual |
| **Mode switching** | Not needed | Not needed | Required (PCV→PSV) |
| **Lung protection** | Automated ΔP, MP | Automated VT | Manual |

[^1_2][^1_5][^1_7]

***

## Clinical Algorithm (Simplified)

```
Intubation → Enter height/sex/condition → Set PetCO₂ & SpO₂ targets
              ↓
      Start INTELLiVENT-ASV
              ↓
    Machine adjusts RR, VT, FiO₂, PEEP
              ↓
    Monitor: PetCO₂, SpO₂, ΔP, mechanics
              ↓
    Quick Wean activated when ready
              ↓
    Automated SBT → Extubation
```


***

## Key Takeaways for Exams

1. **Full closed-loop**: Only mode that auto-adjusts **both ventilation AND oxygenation** [^1_2][^1_6]
2. **Three controllers**: MinVol, Oxygen, PEEP [^1_3][^1_7]
3. **Target-based**: Set **PetCO₂** and **SpO₂**, not VT or RR [^1_4][^1_3]
4. **Lung-protective**: Auto-limits VT, ΔP, mechanical power [^1_10][^1_9]
5. **Quick Wean**: Automated weaning protocol with SBT [^1_12][^1_9]
6. **Evidence**: Safe, effective, but **no outcome superiority** over conventional modes [^1_10]
7. **Not in USA**: Regulatory restriction [^1_4][^1_2]

***
<span style="display:none">[^1_13][^1_14][^1_15]</span>

<div align="center">⁂</div>

[^1_1]: https://www.hamilton-medical.com/en_AE/Products/Technologies/INTELLiVENT-ASV.html

[^1_2]: https://intuitionlabs.ai/software/pdfs/intellivent-asv.pdf

[^1_3]: https://www.hamilton-medical.com/en/Prehospital-transport/Products/Technologies/INTELLiVENT-ASV.html

[^1_4]: https://www.hamilton-medical.com/en_US/Resource-center/Article-page~knowledge-base~a1be16d7-47c2-4ff0-a004-e3483e800d82~How-ASV-works~.html

[^1_5]: https://www.scribd.com/document/372221320/ASV-Intellivent-Article

[^1_6]: https://pmc.ncbi.nlm.nih.gov/articles/PMC4056360/

[^1_7]: https://pmc.ncbi.nlm.nih.gov/articles/PMC7183105/

[^1_8]: https://www.hamilton-medical.com/dam/jcr:f51b6a06-f5cc-4f8c-8e2c-4f75c0b3c281/INTELLiVENT-ASV-faq-troubleshooting-pocket-guide_en-ELO20220910N.00.pdf

[^1_9]: https://pmc.ncbi.nlm.nih.gov/articles/PMC10257811/

[^1_10]: https://www.tandfonline.com/doi/full/10.1080/17476348.2021.1933450

[^1_11]: https://webview.isho.jp/journal/detail/abs/10.11477/mf.3102200547

[^1_12]: https://www.hamilton-medical.com/dam/jcr:b11285c4-4e45-4848-9621-57d0cbfd5bb4/INTELLiVENT-ASV-HAMILTON-C3_ops-manual_v2.0.x_en_624768.02.pdf

[^1_13]: https://www.youtube.com/watch?v=P1lrr0BrE94

[^1_14]: https://www.hamilton-medical.com/dam/jcr:5f9b4a0c-88f9-453d-bf63-aec83eafafeb/INTELLiVENT-ASV_HAMILTON-G5-S1_quick-guide_en_689499.02.pdf

[^1_15]: https://pmc.ncbi.nlm.nih.gov/articles/PMC6967062/

