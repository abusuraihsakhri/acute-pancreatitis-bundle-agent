#!/usr/bin/env python3
"""Command-line interface for the acute pancreatitis assessment calculators."""

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from pancreatitis_severity import AcutePancreatitisBundleEngine, PancreatitisLabs


def _resolve_safe_path(file_path: str) -> Path:
    """Resolve an output path and require it to remain under the working directory."""
    path = Path(file_path).resolve()
    cwd = Path.cwd().resolve()
    try:
        path.relative_to(cwd)
    except ValueError as exc:
        raise ValueError(
            f"Path '{file_path}' escapes the working directory. "
            "Output files must remain within the current working directory."
        ) from exc
    return path


def _resolve_input_path(file_path: str) -> Path:
    """Resolve an input file path and require an existing regular file."""
    path = Path(file_path).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {file_path}")
    return path


def _safe_float(value: Any, field_name: str, min_val: float, max_val: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number: {value!r}") from exc
    if parsed < min_val or parsed > max_val:
        raise ValueError(
            f"{field_name}={parsed} is outside valid range [{min_val}, {max_val}]"
        )
    return parsed


def _safe_int(value: Any, field_name: str, min_val: int, max_val: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer: {value!r}") from exc
    if str(value).strip() not in {str(parsed), f"{parsed}.0"}:
        try:
            if float(value) != parsed:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field_name} must be an integer: {value!r}") from exc
    if parsed < min_val or parsed > max_val:
        raise ValueError(
            f"{field_name}={parsed} is outside valid range [{min_val}, {max_val}]"
        )
    return parsed


def _safe_bool(value: Any, field_name: str) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return False
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized in {"true", "t", "yes", "y", "1"}:
        return True
    if normalized in {"false", "f", "no", "n", "0"}:
        return False
    raise ValueError(
        f"{field_name} must be a boolean value (true/false, yes/no, 1/0): {value!r}"
    )


def _local_complications(value: Any) -> List[str]:
    if value is None or value == "":
        return []
    items = value if isinstance(value, list) else str(value).split(";")
    return [str(item).strip() for item in items if str(item).strip()]


def _record_to_assessment(
    record: Dict[str, Any], engine: AcutePancreatitisBundleEngine
):
    fluid_responsive = _safe_bool(
        record.get("fluid_responsive_hypotension", False),
        "fluid_responsive_hypotension",
    )
    labs = PancreatitisLabs(
        bun_mg_dl=_safe_float(record.get("bun", 15.0), "bun", 0.0, 300.0),
        creatinine_mg_dl=_safe_float(record.get("cr", 1.0), "cr", 0.0, 30.0),
        hematocrit_pct=_safe_float(record.get("hct", 40.0), "hct", 0.0, 75.0),
        wbc_k_ul=_safe_float(record.get("wbc", 9.0), "wbc", 0.0, 100.0),
        temp_c=_safe_float(record.get("temp", 37.0), "temp", 25.0, 45.0),
        heart_rate_bpm=_safe_int(record.get("hr", 75), "hr", 0, 300),
        resp_rate_bpm=_safe_int(record.get("rr", 16), "rr", 0, 80),
        pao2_fio2_ratio=_safe_float(
            record.get("pao2_fio2", 450.0), "pao2_fio2", 0.0, 800.0
        ),
        systolic_bp_mmhg=_safe_float(record.get("sbp", 120.0), "sbp", 0.0, 300.0),
        arterial_ph=_safe_float(record.get("ph", 7.40), "ph", 6.5, 8.0),
        glucose_mg_dl=_safe_float(
            record.get("glucose", 110.0), "glucose", 0.0, 1200.0
        ),
        age=_safe_int(record.get("age", 45), "age", 0, 150),
        fluid_responsive_hypotension=fluid_responsive,
    )
    balthazar_raw = record.get("balthazar")
    balthazar = (
        str(balthazar_raw).strip().upper()
        if balthazar_raw not in (None, "")
        else None
    )
    return engine.evaluate_patient(
        patient_id=str(record.get("patient_id", "PT")).strip() or "PT",
        labs=labs,
        gcs_score=_safe_int(record.get("gcs", 15), "gcs", 3, 15),
        pleural_effusion=_safe_bool(
            record.get("pleural_effusion", False), "pleural_effusion"
        ),
        organ_failure_duration_hours=_safe_float(
            record.get("of_hours", 0.0), "of_hours", 0.0, 10000.0
        ),
        local_complications=_local_complications(record.get("local_complications")),
        systemic_complications=_safe_bool(
            record.get(
                "systemic_complication",
                record.get("systemic_complications", False),
            ),
            "systemic_complication",
        ),
        ct_balthazar_grade=balthazar,
        ct_necrosis_pct=_safe_float(
            record.get("necrosis", 0.0), "necrosis", 0.0, 100.0
        ),
        weight_kg=_safe_float(
            record.get("weight", 70.0), "weight", 20.0, 350.0
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pancreatitis-bundle",
        description="Acute pancreatitis severity and supportive-care assessment calculator",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--interactive", "-I", action="store_true", help="Launch the interactive wizard."
    )
    mode.add_argument(
        "--evaluate", action="store_true", help="Evaluate one patient from CLI flags."
    )
    mode.add_argument(
        "--batch", "-i", metavar="FILE", help="Evaluate a CSV or JSON cohort file."
    )

    parser.add_argument("--patient-id", default="PT-PANC-01")
    parser.add_argument("--age", type=int, default=52)
    parser.add_argument("--weight", type=float, default=70.0, help="Body weight in kg.")
    parser.add_argument("--gcs", type=int, default=15)
    parser.add_argument("--temp", type=float, default=38.4)
    parser.add_argument("--hr", type=int, default=104)
    parser.add_argument("--rr", type=int, default=24)
    parser.add_argument("--sbp", type=float, default=115.0)
    parser.add_argument("--bun", type=float, default=28.0)
    parser.add_argument("--cr", type=float, default=1.6)
    parser.add_argument("--hct", type=float, default=46.0)
    parser.add_argument("--wbc", type=float, default=16.5)
    parser.add_argument("--pao2-fio2", type=float, default=320.0)
    parser.add_argument("--ph", type=float, default=7.36)
    parser.add_argument("--glucose", type=float, default=160.0)

    parser.add_argument("--pleural-effusion", action="store_true")
    parser.add_argument(
        "--fluid-responsive-hypotension",
        action="store_true",
        help="Hypotension improves with fluid resuscitation (Marshall cardiovascular scoring).",
    )
    parser.add_argument("--of-hours", type=float, default=0.0)
    parser.add_argument(
        "--local-complication",
        action="append",
        default=[],
        help="Local complication; repeat this option for multiple complications.",
    )
    parser.add_argument(
        "--systemic-complication",
        action="store_true",
        help="Exacerbation of a pre-existing comorbidity attributable to pancreatitis.",
    )
    parser.add_argument(
        "--balthazar", choices=["A", "B", "C", "D", "E"], default=None
    )
    parser.add_argument("--necrosis", type=float, default=0.0)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--json", action="store_true", help="Shorthand for --format json.")
    parser.add_argument("--output", "-o", metavar="FILE")
    return parser


def _prompt(prompt: str, default: str) -> str:
    value = input(f"{prompt} [{default}]: ").strip()
    return value or default


def run_interactive() -> int:
    print("Acute Pancreatitis Assessment")
    print("Enter available values. This tool is decision support, not a treatment order.")
    try:
        record: Dict[str, Any] = {
            "patient_id": _prompt("Patient ID", "PT-PANC-01"),
            "age": _prompt("Age (years)", "52"),
            "weight": _prompt("Weight (kg)", "70"),
            "gcs": _prompt("Glasgow Coma Scale", "15"),
            "temp": _prompt("Temperature (C)", "38.4"),
            "hr": _prompt("Heart rate (bpm)", "104"),
            "rr": _prompt("Respiratory rate (/min)", "24"),
            "sbp": _prompt("Systolic BP (mmHg)", "115"),
            "bun": _prompt("BUN (mg/dL)", "28"),
            "cr": _prompt("Creatinine (mg/dL)", "1.6"),
            "hct": _prompt("Hematocrit (%)", "46"),
            "wbc": _prompt("WBC (x10^3/uL)", "16.5"),
            "pao2_fio2": _prompt("PaO2/FiO2", "320"),
            "ph": _prompt("Arterial pH", "7.36"),
            "pleural_effusion": _prompt("Pleural effusion? (y/n)", "n"),
            "of_hours": _prompt("Organ failure duration (hours)", "0"),
        }
        evaluation = _record_to_assessment(record, AcutePancreatitisBundleEngine())
    except (KeyboardInterrupt, EOFError):
        print("\nAborted.")
        return 130
    except (ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    print(_format_text(evaluation))
    return 0


def _format_text(evaluation) -> str:
    lines = [
        f"Acute pancreatitis assessment: {evaluation.patient_id}",
        f"Atlanta category: {evaluation.atlanta_classification.category}",
        f"Organ failure: {evaluation.atlanta_classification.organ_failure_status}",
        f"Care setting: {evaluation.atlanta_classification.recommended_level_of_care}",
        f"BISAP: {evaluation.bisap.total_score}/5 ({evaluation.bisap.severity_tier})",
        f"Modified Marshall maximum: {evaluation.modified_marshall.max_organ_score}/4",
        f"SIRS: {evaluation.sirs_criteria_count}/4 criteria",
        f"Initial fluid reference rate: {evaluation.fluid_guidelines.initial_rate_ml_hr:.1f} mL/h",
        f"Fluid bolus flag: {evaluation.fluid_guidelines.bolus_indicated}",
    ]
    if evaluation.ctsi is not None:
        lines.append(
            f"CTSI: {evaluation.ctsi.total_ctsi}/10 (Balthazar {evaluation.ctsi.balthazar_grade})"
        )
    lines.extend(
        [
            f"Nutrition: {evaluation.nutrition_guideline}",
            f"Antibiotics: {evaluation.antibiotic_guideline}",
            "Action items:",
        ]
    )
    if evaluation.action_items:
        lines.extend(f"  - {item}" for item in evaluation.action_items)
    else:
        lines.append("  - No additional flags from the entered data.")
    return "\n".join(lines)


def _serialize(evaluation) -> Dict[str, Any]:
    return asdict(evaluation)


def _write_or_print(text: str, output: Optional[str]) -> int:
    if output:
        try:
            path = _resolve_safe_path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        except (OSError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    else:
        print(text)
    return 0


def _load_records(path: Path) -> Iterable[Dict[str, Any]]:
    if path.suffix.lower() == ".json":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise ValueError(f"Error reading JSON file: {exc}") from exc
        if not isinstance(data, list):
            raise ValueError("JSON file must contain a list of patient records")
        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                raise ValueError(f"JSON record {index} must be an object")
            yield item
        return

    if path.suffix.lower() not in {".csv", ".txt"}:
        raise ValueError("Batch input must be CSV or JSON")
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)
    except OSError as exc:
        raise ValueError(f"Error reading CSV file: {exc}") from exc


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.json:
        args.format = "json"

    if args.interactive or (argv is None and len(sys.argv) == 1):
        return run_interactive()

    engine = AcutePancreatitisBundleEngine()

    if args.batch:
        try:
            path = _resolve_input_path(args.batch)
            evaluations = []
            for index, record in enumerate(_load_records(path), start=1):
                try:
                    evaluations.append(_record_to_assessment(record, engine))
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"Error in record {index}: {exc}") from exc
        except (FileNotFoundError, ValueError) as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        if args.format == "json":
            output = json.dumps([_serialize(item) for item in evaluations], indent=2)
        else:
            output = "\n".join(
                f"{item.patient_id}: {item.atlanta_classification.category} | "
                f"BISAP={item.bisap.total_score} | Marshall={item.modified_marshall.max_organ_score}"
                for item in evaluations
            )
        return _write_or_print(output, args.output)

    try:
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
            fluid_responsive_hypotension=args.fluid_responsive_hypotension,
        )
        evaluation = engine.evaluate_patient(
            patient_id=args.patient_id,
            labs=labs,
            gcs_score=args.gcs,
            pleural_effusion=args.pleural_effusion,
            organ_failure_duration_hours=args.of_hours,
            local_complications=args.local_complication,
            systemic_complications=args.systemic_complication,
            ct_balthazar_grade=args.balthazar,
            ct_necrosis_pct=args.necrosis,
            weight_kg=args.weight,
        )
    except (ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output = (
        json.dumps(_serialize(evaluation), indent=2)
        if args.format == "json"
        else _format_text(evaluation)
    )
    return _write_or_print(output, args.output)


if __name__ == "__main__":
    raise SystemExit(main())
