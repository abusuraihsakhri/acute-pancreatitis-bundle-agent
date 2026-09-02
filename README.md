# Acute Pancreatitis Clinical Decision Support & Care Bundle System

Production-grade gastroenterology and critical care decision engine implementing international evidence-based guidelines (**IAP/APA, ACG, and Revised Atlanta Classification 2012**) for **severity stratification**, **multiorgan failure scoring**, **goal-directed fluid resuscitation**, and **nutrition/antibiotic bundle management**.

---

## Clinical Frameworks Implemented

### 1. Revised Atlanta Classification 2012 (*Banks et al., Gut 2013*)
- **Mild Acute Pancreatitis**:
  * Absence of organ failure.
  * Absence of local or systemic complications.
  * Resolves within days; managed on the regular floor.
- **Moderately Severe Acute Pancreatitis**:
  * **Transient organ failure** (resolves within 48 hours), **OR**
  * Local complications (acute peripancreatic fluid collection, acute necrotic collection, pseudocyst), **OR**
  * Exacerbation of pre-existing co-morbid disease.
- **Severe Acute Pancreatitis**:
  * **Persistent organ failure** ($\ge 48$ hours), single or multiple organ systems.
  * Mandatory high-dependency / ICU admission.

---

### 2. Bedside Index for Severity in Acute Pancreatitis (BISAP)
Five objective binary criteria evaluated within 24 hours of admission:
- **B**: $\text{BUN} > 25\text{ mg/dL}$ ($8.9\text{ mmol/L}$)
- **I**: Impaired mental status ($\text{GCS} < 15$ or acute disorientation)
- **S**: SIRS criteria $\ge 2$ met
- **A**: Age $> 60$ years
- **P**: Pleural effusion present on imaging

| BISAP Score | In-Hospital Mortality Risk | Clinical Triage Tier |
| :---: | :---: | :---: |
| 0 | 0.1% | Low Risk |
| 1 | 0.4% | Low Risk |
| 2 | 1.6% | Intermediate Risk |
| 3 | 3.6% | High Risk / Stepdown |
| 4 | 7.4% | Critical Risk / ICU |
| 5 | 18.0% | Extremely High Risk / ICU |

---

### 3. Modified Marshall Scoring System for Organ Failure

Organ failure defined as a score $\ge 2$ in any domain:

| Domain | Score 0 | Score 1 | Score 2 (Organ Failure) | Score 3 | Score 4 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Respiratory ($\text{PaO}_2 / \text{FiO}_2$)** | $> 400$ | $301\text{--}400$ | $201\text{--}300$ | $101\text{--}200$ | $\le 101$ |
| **Renal ($\text{Cr in mg/dL}$)** | $\le 1.4$ | $1.5\text{--}1.8$ | $1.9\text{--}3.6$ | $3.7\text{--}4.9$ | $> 4.9$ |
| **Cardiovascular ($\text{SBP in mmHg}$)** | $> 90$ | $\le 90$ (fluid-responsive) | $\le 90$ (fluid-refractory) | $\le 90 + \text{pH} < 7.30$ | $\le 90 + \text{pH} < 7.20$ |

---

### 4. Goal-Directed Fluid & Bundle Guidelines
- **Fluid Selection**: **Lactated Ringer's (LR)** preferred over Normal Saline (reduces systemic inflammation, metabolic acidosis, and incidence of SIRS).
- **Rate**: $200\text{--}250\text{ mL/h}$ or initial $20\text{ mL/kg}$ bolus if hemoconcentration ($\text{Hct} > 44\%$) or hypotension present. Target $\text{UO} > 0.5\text{--}1.0\text{ mL/kg/h}$ and BUN reduction.
- **Nutrition**: Early oral feeding for mild pancreatitis; early enteral tube feeding (NG or NJ) within 24-72 hours for severe disease.
- **Antibiotic Stewardship**: Prophylactic antibiotics are **NOT indicated** for sterile acute necrotizing pancreatitis.

---

## Command Line Interface (CLI)

### 1. Single Patient Assessment
```bash
python cli.py --evaluate --patient-id "AP-001" --bun 32.0 --cr 2.2 --pao2-fio2 240.0 --sbp 85.0 --of-hours 52.0
```

### 2. Output as JSON
```bash
python cli.py --evaluate --patient-id "AP-002" --bun 12.0 --cr 0.9 --format json
```

### 3. Batch Patient Cohort Processing
```bash
python cli.py --batch cohort.json --format json --output evaluated_bundle.json
```

### 4. Interactive Console Wizard
```bash
python cli.py --interactive
```

---

## Unit Testing

Execute all unit tests with 100% standard Python:

```bash
python -m unittest discover -s tests -v
# or
python test_pancreas_guard.py
```
