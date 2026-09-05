"""
Comprehensive Unit Test Suite for Acute Pancreatitis Clinical Decision Support & Bundle Engine.
"""

import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pancreatitis_severity import (
    PancreatitisLabs,
    BISAPCalculator,
    ModifiedMarshallCalculator,
    RansonCalculator,
    CTSICalculator,
    AcutePancreatitisBundleEngine,
)
import cli


class TestBISAPCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = BISAPCalculator()

    def test_bisap_score_zero(self):
        labs = PancreatitisLabs(bun_mg_dl=12.0, age=40, temp_c=37.0, heart_rate_bpm=72, resp_rate_bpm=16, wbc_k_ul=8.0)
        res = self.calc.calculate(labs, gcs_score=15, pleural_effusion_present=False)
        self.assertEqual(res.total_score, 0)
        self.assertEqual(res.mortality_risk_pct, 0.1)

    def test_bisap_score_five_maximum(self):
        labs = PancreatitisLabs(bun_mg_dl=35.0, age=72, temp_c=38.8, heart_rate_bpm=115, resp_rate_bpm=26, wbc_k_ul=18.0)
        res = self.calc.calculate(labs, gcs_score=13, pleural_effusion_present=True)
        self.assertEqual(res.total_score, 5)
        self.assertEqual(res.mortality_risk_pct, 18.0)
        self.assertTrue(res.bun_gt_25)
        self.assertTrue(res.impaired_mental_status)
        self.assertTrue(res.sirs_present)
        self.assertTrue(res.age_gt_60)
        self.assertTrue(res.pleural_effusion)

    def test_bisap_score_two_intermediate(self):
        labs = PancreatitisLabs(bun_mg_dl=29.0, age=65, temp_c=37.0, heart_rate_bpm=75, resp_rate_bpm=16, wbc_k_ul=8.0)
        res = self.calc.calculate(labs, gcs_score=15, pleural_effusion_present=False)
        self.assertEqual(res.total_score, 2)
        self.assertEqual(res.mortality_risk_pct, 1.6)


class TestModifiedMarshallCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = ModifiedMarshallCalculator()

    def test_normal_marshall_zero(self):
        labs = PancreatitisLabs(pao2_fio2_ratio=460.0, creatinine_mg_dl=1.0, systolic_bp_mmhg=125.0)
        res = self.calc.calculate(labs)
        self.assertEqual(res.max_organ_score, 0)
        self.assertFalse(res.has_organ_failure)

    def test_respiratory_failure_marshall_score_2_and_3(self):
        labs_score2 = PancreatitisLabs(pao2_fio2_ratio=250.0, creatinine_mg_dl=1.0, systolic_bp_mmhg=120.0)
        res2 = self.calc.calculate(labs_score2)
        self.assertEqual(res2.respiratory_score, 2)
        self.assertTrue(res2.has_organ_failure)

        labs_score3 = PancreatitisLabs(pao2_fio2_ratio=150.0, creatinine_mg_dl=1.0, systolic_bp_mmhg=120.0)
        res3 = self.calc.calculate(labs_score3)
        self.assertEqual(res3.respiratory_score, 3)

    def test_renal_failure_marshall_score_2_and_4(self):
        labs_cr_2 = PancreatitisLabs(pao2_fio2_ratio=450.0, creatinine_mg_dl=2.4, systolic_bp_mmhg=120.0)
        res2 = self.calc.calculate(labs_cr_2)
        self.assertEqual(res2.renal_score, 2)
        self.assertTrue(res2.has_organ_failure)

        labs_cr_4 = PancreatitisLabs(pao2_fio2_ratio=450.0, creatinine_mg_dl=5.5, systolic_bp_mmhg=120.0)
        res4 = self.calc.calculate(labs_cr_4)
        self.assertEqual(res4.renal_score, 4)

    def test_cardiovascular_shock_marshall(self):
        labs_unresponsive = PancreatitisLabs(
            pao2_fio2_ratio=450.0, creatinine_mg_dl=1.0,
            systolic_bp_mmhg=80.0, fluid_responsive_hypotension=False,
            arterial_ph=7.25
        )
        res = self.calc.calculate(labs_unresponsive)
        self.assertEqual(res.cardiovascular_score, 3)
        self.assertTrue(res.has_organ_failure)


class TestRevisedAtlantaClassification(unittest.TestCase):
    def setUp(self):
        self.engine = AcutePancreatitisBundleEngine()

    def test_mild_acute_pancreatitis(self):
        labs = PancreatitisLabs(pao2_fio2_ratio=450.0, creatinine_mg_dl=0.9, systolic_bp_mmhg=120.0, bun_mg_dl=14.0)
        ev = self.engine.evaluate_patient("P_MILD", labs)
        self.assertEqual(ev.atlanta_classification.category, "Mild Acute Pancreatitis")
        self.assertEqual(ev.atlanta_classification.recommended_level_of_care, "Floor / Regular Ward")

    def test_moderately_severe_transient_organ_failure(self):
        labs = PancreatitisLabs(pao2_fio2_ratio=220.0, creatinine_mg_dl=1.1, systolic_bp_mmhg=120.0)
        ev = self.engine.evaluate_patient("P_MOD_SEV", labs, organ_failure_duration_hours=24.0)
        self.assertEqual(ev.atlanta_classification.category, "Moderately Severe Acute Pancreatitis")
        self.assertEqual(ev.atlanta_classification.organ_failure_status, "Transient (< 48h)")
        self.assertEqual(ev.atlanta_classification.recommended_level_of_care, "Stepdown / Intermediate Care")

    def test_severe_persistent_organ_failure(self):
        labs = PancreatitisLabs(pao2_fio2_ratio=180.0, creatinine_mg_dl=3.2, systolic_bp_mmhg=85.0)
        ev = self.engine.evaluate_patient("P_SEV", labs, organ_failure_duration_hours=52.0)
        self.assertEqual(ev.atlanta_classification.category, "Severe Acute Pancreatitis")
        self.assertEqual(ev.atlanta_classification.organ_failure_status, "Persistent (>= 48h)")
        self.assertEqual(ev.atlanta_classification.recommended_level_of_care, "Intensive Care Unit (ICU)")
        self.assertTrue(any("ICU" in act for act in ev.action_items))


class TestRansonAndCTSICalculators(unittest.TestCase):
    def setUp(self):
        self.ranson = RansonCalculator()
        self.ctsi = CTSICalculator()

    def test_ranson_admission_scoring(self):
        labs = PancreatitisLabs(age=62, wbc_k_ul=19.0, glucose_mg_dl=250.0, ldh_u_l=400.0, ast_u_l=300.0)
        res = self.ranson.evaluate(labs)
        self.assertEqual(len(res.admission_criteria_met), 5)
        self.assertGreaterEqual(res.total_score, 5)

    def test_ctsi_mild_grade_a(self):
        res = self.ctsi.calculate(balthazar_grade="A", necrosis_pct=0.0)
        self.assertEqual(res.total_ctsi, 0)
        self.assertEqual(res.morbidity_risk, "Mild (Low complication rate)")

    def test_ctsi_severe_grade_e_with_necrosis(self):
        res = self.ctsi.calculate(balthazar_grade="E", necrosis_pct=55.0)
        self.assertEqual(res.total_ctsi, 10)
        self.assertEqual(res.mortality_risk_pct, 17.0)


class TestFluidAndBundleGuidelines(unittest.TestCase):
    def setUp(self):
        self.engine = AcutePancreatitisBundleEngine()

    def test_lactated_ringers_bolus_on_hemoconcentration(self):
        labs = PancreatitisLabs(hematocrit_pct=48.0, bun_mg_dl=30.0)
        ev = self.engine.evaluate_patient("P_HEMO", labs)
        self.assertTrue(ev.fluid_guidelines.bolus_indicated)
        self.assertEqual(ev.fluid_guidelines.initial_rate_ml_hr, 250.0)
        self.assertIn("Lactated Ringer's", ev.fluid_guidelines.recommended_fluid)

    def test_no_prophylactic_antibiotics_sterile(self):
        labs = PancreatitisLabs()
        ev = self.engine.evaluate_patient("P_STERILE", labs)
        self.assertIn("NOT recommended", ev.antibiotic_guideline)


class TestCLIAndBatchExecution(unittest.TestCase):
    def test_cli_single_evaluation_json(self):
        out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = out
        try:
            code = cli.main([
                "--evaluate",
                "--patient-id", "CLI_PT_01",
                "--bun", "32.0",
                "--pao2-fio2", "220.0",
                "--format", "json"
            ])
            self.assertEqual(code, 0)
        finally:
            sys.stdout = old_stdout

        data = json.loads(out.getvalue())
        self.assertEqual(data["patient_id"], "CLI_PT_01")
        self.assertTrue(data["bisap"]["bun_gt_25"])

    def test_cli_batch_json(self):
        records = [
            {"patient_id": "P1", "bun": 35.0, "pao2_fio2": 150.0, "of_hours": 50.0},
            {"patient_id": "P2", "bun": 12.0, "pao2_fio2": 480.0, "of_hours": 0.0},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(records, f)
            temp_path = f.name

        try:
            out = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = out
            try:
                code = cli.main(["--batch", temp_path, "--format", "json"])
                self.assertEqual(code, 0)
            finally:
                sys.stdout = old_stdout

            data = json.loads(out.getvalue())
            self.assertEqual(len(data), 2)
            self.assertEqual(data[0]["atlanta_classification"]["category"], "Severe Acute Pancreatitis")
            self.assertEqual(data[1]["atlanta_classification"]["category"], "Mild Acute Pancreatitis")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_cli_json_flag(self):
        out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = out
        try:
            code = cli.main(["--evaluate", "--patient-id", "TEST_JSON", "--bun", "32.0", "--cr", "2.5", "--json"])
            self.assertEqual(code, 0)
        finally:
            sys.stdout = old_stdout

        data = json.loads(out.getvalue())
        self.assertEqual(data["patient_id"], "TEST_JSON")
        self.assertIn("bisap", data)

    def test_sample_csv_batch(self):
        sample_path = PROJECT_ROOT / "sample.csv"
        out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = out
        try:
            code = cli.main(["-i", str(sample_path), "--json"])
            self.assertEqual(code, 0)
        finally:
            sys.stdout = old_stdout

        data = json.loads(out.getvalue())
        self.assertEqual(len(data), 3)


class TestInputValidation(unittest.TestCase):
    """Tests for physiological range validation in PancreatitisLabs."""

    def test_negative_bun_rejected(self):
        with self.assertRaises(ValueError):
            PancreatitisLabs(bun_mg_dl=-5.0)

    def test_extreme_age_rejected(self):
        with self.assertRaises(ValueError):
            PancreatitisLabs(age=200)

    def test_temperature_out_of_range(self):
        with self.assertRaises(ValueError):
            PancreatitisLabs(temp_c=50.0)

    def test_phys_valid_values_accepted(self):
        labs = PancreatitisLabs(bun_mg_dl=35.0, age=65, temp_c=38.5, heart_rate_bpm=110)
        self.assertEqual(labs.bun_mg_dl, 35.0)
        self.assertEqual(labs.age, 65)

    def test_default_values_valid(self):
        labs = PancreatitisLabs()
        self.assertEqual(labs.bun_mg_dl, 15.0)
        self.assertEqual(labs.age, 45)


class TestCLISecurityAndErrors(unittest.TestCase):
    """Tests for CLI path traversal prevention and error handling."""

    def test_path_traversal_batch_rejected(self):
        """Batch with non-existent path returns error code 1."""
        out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = out
        try:
            code = cli.main(["--batch", "../../../etc/passwd", "--format", "json"])
            self.assertEqual(code, 1)
        finally:
            sys.stdout = old_stdout

    def test_path_traversal_output_rejected(self):
        """Output path escaping working directory is rejected."""
        out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = out
        try:
            code = cli.main([
                "--evaluate", "--patient-id", "PT-01",
                "--output", "../../tmp/evil.txt"
            ])
            self.assertEqual(code, 1)
        finally:
            sys.stdout = old_stdout

    def test_malformed_json_batch(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json content")
            temp_path = f.name

        try:
            out = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = out
            try:
                code = cli.main(["--batch", temp_path, "--format", "json"])
                self.assertEqual(code, 1)
            finally:
                sys.stdout = old_stdout
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_nonexistent_batch_file(self):
        out = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = out
        try:
            code = cli.main(["--batch", "nonexistent_file.csv", "--format", "json"])
            self.assertEqual(code, 1)
        finally:
            sys.stdout = old_stdout


if __name__ == "__main__":
    unittest.main()
