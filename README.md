# Acute Pancreatitis Bundle Agent

### [Open the Live Application →](https://abusuraihsakhri.github.io/acute-pancreatitis-bundle-agent/)

A Python calculator and browser interface for structured acute pancreatitis severity assessment. It combines the Revised Atlanta Classification, BISAP, Modified Marshall organ dysfunction score, SIRS criteria, Ranson criteria, and the original Balthazar CT Severity Index (CTSI).

The project is intended for education, research, and clinical decision support. It assumes acute pancreatitis has already been diagnosed and does not replace clinical judgment, local protocols, or specialist assessment.

## Features

- Revised Atlanta severity classification based on organ failure and local/systemic complications.
- BISAP and Modified Marshall scoring from clinical and laboratory inputs.
- SIRS count, Ranson criteria utilities, and optional Balthazar CTSI calculation.
- Goal-directed fluid prompts using a moderate starting strategy with reassessment rather than routine aggressive hydration.
- Nutrition and antibiotic stewardship guidance.
- Single-patient CLI, interactive mode, and CSV/JSON batch processing.
- Static browser interface that runs the same Python calculation module locally with Pyodide.
- No external Python runtime dependencies.

## Browser interface

The static application lives in `site/` and is deployed by `.github/workflows/pages.yml` using GitHub Pages with **GitHub Actions** as the source.

The browser downloads the Pyodide runtime and then executes `pancreatitis_severity.py` locally. Entered clinical values are not uploaded to this repository or stored by the page. The initial runtime download is comparatively large; subsequent calculations are local.

## Python requirements

Python 3.10 or newer is supported.

```bash
git clone https://github.com/abusuraihsakhri/acute-pancreatitis-bundle-agent.git
cd acute-pancreatitis-bundle-agent
python -m pip install .
```

## CLI

Single-patient JSON output:

```bash
pancreatitis-bundle --evaluate \
  --patient-id PT-001 \
  --age 58 --weight 70 --gcs 14 \
  --bun 32 --cr 2.2 --hct 47 \
  --temp 38.8 --hr 112 --rr 26 \
  --pao2-fio2 280 --sbp 95 \
  --pleural-effusion --of-hours 48 --json
```

Batch processing:

```bash
pancreatitis-bundle --batch sample.csv --json
```

Optional CT inputs:

```bash
pancreatitis-bundle --evaluate --balthazar D --necrosis 30 --json
```

Interactive mode:

```bash
pancreatitis-bundle --interactive
```

## Python API

```python
from pancreatitis_severity import AcutePancreatitisBundleEngine, PancreatitisLabs

labs = PancreatitisLabs(
    bun_mg_dl=32,
    creatinine_mg_dl=2.2,
    hematocrit_pct=47,
    temp_c=38.8,
    heart_rate_bpm=112,
    resp_rate_bpm=26,
    pao2_fio2_ratio=280,
    systolic_bp_mmhg=95,
    age=58,
)

result = AcutePancreatitisBundleEngine().evaluate_patient(
    patient_id="PT-001",
    labs=labs,
    gcs_score=14,
    pleural_effusion=True,
    organ_failure_duration_hours=48,
    weight_kg=70,
)

print(result.atlanta_classification.category)
print(result.bisap.total_score)
```

## Testing

```bash
python -m pip install ".[test]"
python -m pytest -q
```

CI runs the test suite on Python 3.10 through 3.14, verifies the installed CLI, performs a batch smoke test, builds the package, and checks dependency consistency.

## Clinical scope

Revised Atlanta severity is determined by organ failure duration and local/systemic complications; BISAP and SIRS are reported as separate risk markers and do not by themselves change the Atlanta severity category. Fluid guidance is deliberately framed as a starting reference with repeated reassessment because aggressive fixed-volume resuscitation can cause harm.

Key references:

- Banks PA, et al. *Gut*. 2013;62:102-111. Revised Atlanta Classification. PMID: 23100216.
- Tenner S, et al. *Am J Gastroenterol*. 2024;119:419-437. ACG guideline on acute pancreatitis. PMID: 38857482.
- de-Madaria E, et al. *N Engl J Med*. 2022;387:989-1000. WATERFALL fluid-resuscitation trial. PMID: 36103415.

Population-derived risk estimates and scoring systems should not be interpreted as individualized outcome predictions.

## License

MIT License. See `LICENSE`.
