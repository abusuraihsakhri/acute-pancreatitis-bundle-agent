#!/usr/bin/env python3
"""
Command Line Interface for Acute Pancreatitis Clinical Decision Support & Bundle Care.
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import List, Optional

from pancreatitis_severity import (
    PancreatitisLabs,
    AcutePancreatitisBundleEngine,
    BISAPCalculator,
    ModifiedMarshallCalculator,
    RansonCalculator,
    CTSICalculator,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pancreatitis-bundle",
        description="Acute Pancreatitis Severity Classification & Bundle Care Decision Support System",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--interactive", "-I", action="store_true", help="Launch interactive clinical bundle wizard.")
    mode.add_argument("--evaluate", action="store_true", help="Evaluate single patient with CLI flags.")
    mode.add_argument("--batch", "-i", metavar="FILE", help="Batch evaluate cohort from CSV or JSON file.")

    # Patient & Vital Signs
    parser.add_argument("--patient-id", default="PT-PANC-01", help="Patient identifier.")
    parser.add_argument("--age", type=int, default=52, help="Patient age in years.")
    parser.add_argument("--gcs", type=int, default=15, help="Glasgow Coma Scale score (3-15).")
    parser.add_argument("--temp", type=float, default=38.4, help="Body temperature in Celsius.")
    parser.add_argument("--hr", type=int, default=104, help="Heart rate in beats per minute.")
    parser.add_argument("--rr", type=int, default=24, help="Respiratory rate in breaths per minute.")
    parser.add_argument("--sbp", type=float, default=115.0, help="Systolic blood pressure (mmHg).")

    # Lab Parameters
    parser.add_argument("--bun", type=float, default=28.0, help="Blood Urea Nitrogen (BUN) in mg/dL.")
    parser.add_argument("--cr", type=float, default=1.6, help="Serum Creatinine in mg/dL.")
    parser.add_argument("--hct", type=float, default=46.0, help="Hematocrit percentage (%).")
    parser.add_argument("--wbc", type=float, default=16.5, help="White blood cell count (x10^3/uL).")
    parser.add_argument("--pao2-fio2", type=float, default=320.0, help="PaO2 / FiO2 ratio (mmHg).")
    parser.add_argument("--ph", type=float, default=7.36, help="Arterial pH.")
    parser.add_argument("--glucose", type=float, default=160.0, help="Blood glucose (mg/dL).")
    parser.add_argument("--pleural-effusion", action="store_true", help="Pleural effusion detected on chest radiograph/CT.")
    parser.add_argument("--of-hours", type=float, default=0.0, help="Duration of organ failure in hours (e.g. 0, 24, 48).")

    # Imaging
    parser.add_argument("--balthazar", choices=["A", "B", "C", "D", "E"], default=None, help="Balthazar CT grade.")
    parser.add_argument("--necrosis", type=float, default=0.0, help="Pancreatic necrosis percentage (0, 30, 50).")

    # Output formatting
    parser.add_argument("--format", choices=["text", "json"], default="text", help="Output format (default: text).")
    parser.add_argument("--json", action="store_true", help="Output result as formatted JSON (shorthand for --format json).")
    parser.add_argument("--output", "-o", metavar="FILE", help="Write results to file.")

    return parser


def run_interactive():
    print("=" * 75)
    print("  ACUTE PANCREATITIS BUNDLE & SEVERITY ASSESSMENT WIZARD")
    print("=" * 75)
    try:
        patient_id = input("Patient ID [PT-PANC-01]: ").strip() or "PT-PANC-01"
        age = int(input("Age in years [52]: ").strip() or "52")
        gcs = int(input("Glasgow Coma Scale [15]: ").strip() or "15")

        print("\nEnter Vital Signs:")
        temp = float(input("  Temperature (°C) [38.4]: ").strip() or "38.4")
        hr = int(input("  Heart Rate (bpm) [104]: ").strip() or "104")
        rr = int(input("  Respiratory Rate (bpm) [24]: ").strip() or "24")
        sbp = float(input("  Systolic BP (mmHg) [115]: ").strip() or "115")

        print("\nEnter Laboratory Values:")
        bun = float(input("  BUN (mg/dL) [28.0]: ").strip() or "28.0")
        cr = float(input("  Creatinine (mg/dL) [1.6]: ").strip() or "1.6")
        hct = float(input("  Hematocrit (%) [46.0]: ").strip() or "46.0")
        wbc = float(input("  WBC (x10^3/uL) [16.5]: ").strip() or "16.5")
        pf = float(input("  PaO2/FiO2 Ratio [320.0]: ").strip() or "320.0")

        eff_str = input("Pleural Effusion on Imaging? (y/n) [n]: ").strip().lower()
        effusion = (eff_str == "y" or eff_str == "yes")

        of_str = input("Duration of Organ Failure in Hours [0]: ").strip() or "0"
        of_hours = float(of_str)

    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        sys.exit(0)

    labs = PancreatitisLabs(
        bun_mg_dl=bun, creatinine_mg_dl=cr, hematocrit_pct=hct,
        wbc_k_ul=wbc, temp_c=temp, heart_rate_bpm=hr,
        resp_rate_bpm=rr, pao2_fio2_ratio=pf, systolic_bp_mmhg=sbp,
        age=age,
    )

    engine = AcutePancreatitisBundleEngine()
    ev = engine.evaluate_patient(
        patient_id=patient_id,
        labs=labs,
        gcs_score=gcs,
        pleural_effusion=effusion,
        organ_failure_duration_hours=of_hours,
    )

    print("\n" + "=" * 75)
    print(f"  CLINICAL SUMMARY: {patient_id} ({ev.atlanta_classification.category.upper()})")
    print("=" * 75)
    print(f"Atlanta 2012 Tier: {ev.atlanta_classification.category}")
    print(f"  Organ Failure:   {ev.atlanta_classification.organ_failure_status}")
    print(f"  Triage Level:    {ev.atlanta_classification.recommended_level_of_care}")
    print("-" * 75)
    print(f"BISAP Score:       {ev.bisap.total_score}/5 | Risk: {ev.bisap.severity_tier}")
    print(f"  Predicted Mort:  {ev.bisap.mortality_risk_pct}%")
    print(f"  Criteria Met:    BUN>25: {ev.bisap.bun_gt_25}, Impaired Mental: {ev.bisap.impaired_mental_status}, SIRS: {ev.bisap.sirs_present}, Age>60: {ev.bisap.age_gt_60}, Effusion: {ev.bisap.pleural_effusion}")
    print("-" * 75)
    print(f"Modified Marshall: Max Score {ev.modified_marshall.max_organ_score}/4 (Organ Failure: {ev.modified_marshall.has_organ_failure})")
    print(f"  Respiratory:     {ev.modified_marshall.respiratory_score}/4")
    print(f"  Renal:           {ev.modified_marshall.renal_score}/4")
    print(f"  Cardiovascular:  {ev.modified_marshall.cardiovascular_score}/4")
    print("-" * 75)
    print(f"Fluid Resuscitation: Rate {ev.fluid_guidelines.initial_rate_ml_hr} mL/h | Bolus: {ev.fluid_guidelines.bolus_indicated}")
    print(f"  Fluid Type:      {ev.fluid_guidelines.recommended_fluid}")
    print(f"Nutrition Plan:    {ev.nutrition_guideline}")
    print(f"Antibiotic Rec:    {ev.antibiotic_guideline}")
    print("-" * 75)
    print("ACTION ITEMS:")
    for act in ev.action_items:
        print(f"  [!] {act}")
    print("=" * 75)


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.json:
        args.format = "json"

    if args.interactive or (not args.evaluate and not args.batch and len(sys.argv) == 1):
        run_interactive()
        return 0

    engine = AcutePancreatitisBundleEngine()

    if args.batch:
        path = Path(args.batch)
        evaluations = []
        if path.suffix.lower() == ".json":
            records = json.loads(path.read_text(encoding="utf-8"))
            for r in records:
                labs = PancreatitisLabs(
                    bun_mg_dl=float(r.get("bun", 15.0)),
                    creatinine_mg_dl=float(r.get("cr", 1.0)),
                    hematocrit_pct=float(r.get("hct", 40.0)),
                    wbc_k_ul=float(r.get("wbc", 9.0)),
                    temp_c=float(r.get("temp", 37.0)),
                    heart_rate_bpm=int(r.get("hr", 75)),
                    resp_rate_bpm=int(r.get("rr", 16)),
                    pao2_fio2_ratio=float(r.get("pao2_fio2", 450.0)),
                    systolic_bp_mmhg=float(r.get("sbp", 120.0)),
                    age=int(r.get("age", 45)),
                )
                ev = engine.evaluate_patient(
                    patient_id=str(r.get("patient_id", "PT")),
                    labs=labs,
                    gcs_score=int(r.get("gcs", 15)),
                    pleural_effusion=bool(r.get("pleural_effusion", False)),
                    organ_failure_duration_hours=float(r.get("of_hours", 0.0)),
                )
                evaluations.append(ev)
        else:
            with open(path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    labs = PancreatitisLabs(
                        bun_mg_dl=float(r.get("bun", 15.0)),
                        creatinine_mg_dl=float(r.get("cr", 1.0)),
                        hematocrit_pct=float(r.get("hct", 40.0)),
                        wbc_k_ul=float(r.get("wbc", 9.0)),
                        temp_c=float(r.get("temp", 37.0)),
                        heart_rate_bpm=int(r.get("hr", 75)),
                        resp_rate_bpm=int(r.get("rr", 16)),
                        pao2_fio2_ratio=float(r.get("pao2_fio2", 450.0)),
                        systolic_bp_mmhg=float(r.get("sbp", 120.0)),
                        age=int(r.get("age", 45)),
                    )
                    ev = engine.evaluate_patient(
                        patient_id=str(r.get("patient_id", "PT")),
                        labs=labs,
                        gcs_score=int(r.get("gcs", 15)),
                        pleural_effusion=bool(r.get("pleural_effusion", False)),
                    )
                    evaluations.append(ev)

        if args.format == "json":
            out_str = json.dumps([e.__dict__ for e in evaluations], default=lambda o: o.__dict__, indent=2)
        else:
            out_lines = []
            for ev in evaluations:
                out_lines.append(
                    f"Patient {ev.patient_id}: {ev.atlanta_classification.category} | "
                    f"BISAP={ev.bisap.total_score} | Marshall Max={ev.modified_marshall.max_organ_score} | "
                    f"Triage={ev.atlanta_classification.recommended_level_of_care}"
                )
            out_str = "\n".join(out_lines)

        if args.output:
            Path(args.output).write_text(out_str, encoding="utf-8")
        else:
            print(out_str)
        return 0

    # Single patient CLI evaluation
    labs = PancreatitisLabs(
        bun_mg_dl=args.bun,
        creatinine_mg_dl=args.cr,
        hematocrit_pct=args.hct,
        wbc_k_ul=args.wbc,
        temp_c=args.temp,
        heart_rate_bpm=args.hr,
        resp_rate_bpm=args.rr,
        pao2_fio2_ratio=args.pao2_fio2,
        systolic_bp_mmhg=args.sbp,
        arterial_ph=args.ph,
        glucose_mg_dl=args.glucose,
        age=args.age,
    )

    ev = engine.evaluate_patient(
        patient_id=args.patient_id,
        labs=labs,
        gcs_score=args.gcs,
        pleural_effusion=args.pleural_effusion,
        organ_failure_duration_hours=args.of_hours,
        ct_balthazar_grade=args.balthazar,
        ct_necrosis_pct=args.necrosis,
    )

    if args.format == "json":
        out_str = json.dumps(ev.__dict__, default=lambda o: o.__dict__, indent=2)
    else:
        out_str = (
            f"Acute Pancreatitis Clinical Dossier for {ev.patient_id}:\n"
            f"  Atlanta 2012:      {ev.atlanta_classification.category} ({ev.atlanta_classification.organ_failure_status})\n"
            f"  Recommended Level: {ev.atlanta_classification.recommended_level_of_care}\n"
            f"  BISAP Score:       {ev.bisap.total_score}/5 (Mortality: {ev.bisap.mortality_risk_pct}% - {ev.bisap.severity_tier})\n"
            f"  Modified Marshall: Max Score {ev.modified_marshall.max_organ_score}/4 (Organ Failure: {ev.modified_marshall.has_organ_failure})\n"
            f"  SIRS Criteria:     {ev.sirs_criteria_count}/4 criteria met\n"
            f"  Fluid Protocol:    {ev.fluid_guidelines.initial_rate_ml_hr} mL/h ({ev.fluid_guidelines.recommended_fluid})\n"
            f"  Nutrition Plan:    {ev.nutrition_guideline}\n"
            f"  Antibiotics:       {ev.antibiotic_guideline}\n"
            f"  Action Items:      {len(ev.action_items)} triggered\n"
        )
        for act in ev.action_items:
            out_str += f"    * {act}\n"

    if args.output:
        Path(args.output).write_text(out_str, encoding="utf-8")
    else:
        print(out_str)

    return 0


if __name__ == "__main__":
    sys.exit(main())
