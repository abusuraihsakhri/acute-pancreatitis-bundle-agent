# Acute Pancreatitis Severity Classification & Bundle Care Decision Support System

A Python clinical decision support system and CLI tool for acute pancreatitis severity stratification, organ failure surveillance, and bundle care management. Implements the Revised Atlanta Classification (2012), Bedside Index for Severity in Acute Pancreatitis (BISAP), Modified Marshall Scoring System for multiorgan failure, Systemic Inflammatory Response Syndrome (SIRS) criteria, Ranson's Criteria, Balthazar CT Severity Index (CTSI), and goal-directed fluid/nutrition resuscitation protocols.

Requires Python standard library only (zero external runtime dependencies).

---

## Features

- **Revised Atlanta Classification (2012):** Classifies presentation into Mild (no organ failure/complications), Moderately Severe (transient organ failure < 48 hours or local/systemic complications), or Severe (persistent organ failure >= 48 hours in one or more systems).
- **Modified Marshall Organ Failure Score:** Evaluates respiratory ($PaO_2/FiO_2$), renal (serum creatinine), and cardiovascular (systolic blood pressure/inotropic support) dysfunction with standard physiological thresholds.
- **BISAP Score & Mortality Stratification:** Points tallied for BUN > 25 mg/dL, Impaired mental status (GCS < 15), SIRS present, Age > 60 years, and Pleural effusion.
- **Goal-Directed Fluid Resuscitation:** Evaluates hematocrit, BUN, and urine output targets; recommends Lactated Ringer's solution protocols and warns against volume overload in renal/heart failure.
- **Nutritional & Antibiotic Stewardship:** Outlines evidence-based guidance for early enteral feeding vs. TPN, and stewardship protocols against routine prophylactic antibiotics in sterile acute pancreatitis.
- **Interactive Wizard & Batch CLI:** Full command-line wizard, single-patient parameterized evaluation, and batch evaluation of patient cohorts via CSV.

---

## Installation & Requirements

- Python 3.10+ (tested on 3.10, 3.11, 3.12)
- Zero external runtime dependencies. `pytest` is optional for running unit tests.

```bash
git clone https://github.com/abusuraihsakhri/acute-pancreatitis-bundle-agent.git
cd acute-pancreatitis-bundle-agent
```

---

## CLI Usage

### 1. Single Patient Evaluation
Evaluate acute pancreatitis presentation:
```bash
python cli.py --evaluate --patient-id PT-001 --bun 32.0 --cr 2.2 --temp 38.8 --hr 112 --rr 26 --pao2-fio2 280 --sbp 95 --pleural-effusion --of-hours 48
```
Output as JSON:
```bash
python cli.py --evaluate --patient-id PT-001 --bun 32.0 --cr 2.2 --temp 38.8 --hr 112 --rr 26 --pao2-fio2 280 --sbp 95 --pleural-effusion --of-hours 48 --json
```

### 2. Batch Patient CSV Evaluation
Process cohort CSV file:
```bash
python cli.py -i sample.csv --json
```

### 3. CT Severity Index Evaluation
Incorporate contrast CT findings:
```bash
python cli.py --evaluate --patient-id PT-CT-01 --bun 26.0 --balthazar D --necrosis 30 --json
```

### 4. Interactive Clinical Wizard
Launch terminal clinical decision wizard:
```bash
python cli.py --interactive
```

---

## Python API Quickstart

```python
from pancreatitis_severity import (
    PancreatitisLabs,
    AcutePancreatitisBundleEngine,
)

engine = AcutePancreatitisBundleEngine()

labs = PancreatitisLabs(
    bun_mg_dl=32.0,
    creatinine_mg_dl=2.2,
    hematocrit_pct=47.0,
    wbc_k_ul=18.5,
    temp_c=38.8,
    heart_rate_bpm=112,
    resp_rate_bpm=26,
    pao2_fio2_ratio=280.0,
    systolic_bp_mmhg=95.0,
    has_pleural_effusion=True,
    organ_failure_duration_hours=48.0,
)

result = engine.evaluate_patient(
    patient_id="PT-001",
    labs=labs,
    age=58,
    gcs_score=14,
)

print(f"Atlanta Category: {result.atlanta_classification.category}")
print(f"BISAP Score: {result.bisap.total_score} (Mortality: {result.bisap.mortality_risk_pct}%)")
print(f"Organ Failure Present: {result.modified_marshall.has_organ_failure}")
print(f"Recommended Fluid: {result.fluid_guidelines.recommended_fluid}")
for item in result.action_items:
    print(f" * {item}")
```

---

## Input Validation & Safety

All laboratory values and vital signs are validated against physiological ranges on instantiation. Out-of-range values raise `ValueError` with a descriptive message:

```python
from pancreatitis_severity import PancreatitisLabs

# This will raise ValueError: bun_mg_dl=-5.0 is outside valid range [0.0, 300.0]
labs = PancreatitisLabs(bun_mg_dl=-5.0)
```

The CLI also includes:
- **Path traversal protection**: Output files (`--output`) must reside within the working directory.
- **Graceful error handling**: Malformed CSV/JSON batch files produce clear error messages and exit code 1.
- **Per-field validation**: Each lab value in batch files is validated before processing.

## Running Tests

Run the test suite using standard `unittest` or `pytest`:

```bash
python test_pancreas_guard.py
# or
pytest -v
```

The test suite includes 28 tests covering clinical calculations, CLI execution, input validation, and security controls.

