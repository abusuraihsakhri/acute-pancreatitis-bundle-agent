# Acute Pancreatitis Bundle Agent

> **Domain:** Gastroenterology, Hepatology & Clinical Nutrition  
> **Reference Guidelines & Standards:** `AASLD & ACG Clinical Practice Guidelines`

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB.svg?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688.svg?logo=fastapi&logoColor=white)
![Audit Trail](https://img.shields.io/badge/Audit-HMAC--SHA256_Tamper--Evident-brightgreen.svg)
![Zero-PHI Guard](https://img.shields.io/badge/Guard-Zero--PHI_Outbound-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)

</div>

---

## 📖 What It Does

**Acute Pancreatitis Bundle Agent** is an advanced analytical and computational platform implementing Revised Atlanta Classification & 24h SIRS Resuscitation Agent.

Acute Pancreatitis Clinical Decision Support & Bundle Care Protocol Engine.

Clinical Frameworks:
1. Revised Atlanta Classification 2012 (Mild, Moderately Severe, Severe).
2. Bedside Index for Severity in Acute Pancreatitis (BISAP) Score & Mortality Stratification.
3. Modified Marshall Scoring System for Multiorgan Failure (Respiratory, Renal, Cardiovascular).
4. Systemic Inflammatory Response Syndrome (SIRS) Trajectory & Persistent SIRS Detection.
5. Ranson's Criteria (Admission and 48-Hour Progression).
6. Balthazar Computed Tomography Severity Index (CTSI) & Necrosis Assessment.
7. Goal-Directed Fluid Resuscitation & Enteral Nutrition Bundle Guidelines.

---

## ⚙️ Key Capabilities & Algorithmic Modules

### 🔬 Core Algorithmic & Evaluation Engines

- **`PancreatitisLabs`** — dedicated module for pancreatitis labs evaluation and state verification.
- **`BISAPResult`** — dedicated module for b i s a p result evaluation and state verification.
- **`MarshallScoreResult`** — dedicated module for marshall score result evaluation and state verification.
- **`AtlantaClassificationResult`** — dedicated module for atlanta classification result evaluation and state verification.
- **`RansonResult`** — dedicated module for ranson result evaluation and state verification.
- **`CTSIResult`** — dedicated module for c t s i result evaluation and state verification.

---

## 📐 Mathematical Formulation & Logic

```text
  score = sum(1 for v in criteria.values() if v)
  elif score == 2:
  elif score == 3:
  max_score = max(resp, renal, cardio)
  adm = self.calculate_admission(labs)
```

---

## 💻 CLI Quickstart & Usage

### 1. Guided Interactive Mode
```bash
python cli.py
```

### 2. Direct Parameterized Evaluation
```bash
python cli.py --interactive <value> --evaluate <value> --batch <value> --patient-id <value>
```

### Parameter Reference
- `--interactive`: Specifies input measurement or parameter value.
- `--evaluate`: Specifies input measurement or parameter value.
- `--batch`: Specifies input measurement or parameter value.
- `--patient-id`: Specifies input measurement or parameter value.
- `--age`: Specifies input measurement or parameter value.
- `--gcs`: Specifies input measurement or parameter value.
- `--temp`: Specifies input measurement or parameter value.
- `--hr`: Specifies input measurement or parameter value.
- `--rr`: Specifies input measurement or parameter value.
- `--sbp`: Specifies input measurement or parameter value.

### Input Data Schema

| Field | Description | Requirement |
|:------|:------------|:------------|
| `case_id` | Parameter / observation metric | Required |
| `patient_synthetic_id` | Parameter / observation metric | Required |
| `metric_primary` | Parameter / observation metric | Required |
| `metric_secondary` | Parameter / observation metric | Required |
| `is_stat` | Parameter / observation metric | Required |
| `status_flag` | Parameter / observation metric | Required |

---

## 🛡️ Security & Enterprise Architecture

* **Zero-PHI Outbound Interceptor:** Active AST and regex inspection blocking SSNs, MRNs, phone numbers, and patient identifiers.
* **Tamper-Evident HMAC-SHA256 Audit Trail:** Chained, cryptographically signed logs for every evaluation and state transition.
* **Air-Gapped LLM Reasoning Adapter:** Agnostic integration for local Ollama instances (`llama3`, `mistral`), Claude 3.5 Sonnet, GPT-4o, and deterministic test mocks.
* **Active Learning Bayesian Calibration:** Dynamic tracker updating worker reliability weights and monitoring Brier calibration drift.
* **FastAPI & Prometheus Telemetry:** Exposes OpenAPI 3.1 REST endpoints and operational Prometheus metrics (`/metrics`).

---

## 🧪 Testing & Verification

Run the automated test suite:

```bash
pytest -v
```

Execute high-throughput batch simulation benchmarks:

```bash
python simulator.py --tasks 1000 --concurrency 8
```

---

## 🐳 Container Deployment

```bash
docker build -t acute-pancreatitis-bundle-agent .
docker run -p 8000:8000 acute-pancreatitis-bundle-agent
```
