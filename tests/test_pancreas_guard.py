import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import cli
from pancreatitis_severity import (
    AcutePancreatitisBundleEngine,
    BISAPCalculator,
    CTSICalculator,
    ModifiedMarshallCalculator,
    PancreatitisLabs,
    RansonCalculator,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestBISAPCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = BISAPCalculator()

    def test_score_zero(self):
        labs = PancreatitisLabs(bun_mg_dl=12, age=40, temp_c=37, heart_rate_bpm=72, resp_rate_bpm=16, wbc_k_ul=8)
        result = self.calc.calculate(labs)
        self.assertEqual(result.total_score, 0)
        self.assertEqual(result.mortality_risk_pct, 0.1)

    def test_score_five(self):
        labs = PancreatitisLabs(bun_mg_dl=35, age=72, temp_c=38.8, heart_rate_bpm=115, resp_rate_bpm=26, wbc_k_ul=18)
        result = self.calc.calculate(labs, gcs_score=13, pleural_effusion_present=True)
        self.assertEqual(result.total_score, 5)
        self.assertTrue(result.sirs_present)

    def test_gcs_validation(self):
        with self.assertRaises(ValueError):
            self.calc.calculate(PancreatitisLabs(), gcs_score=16)


class TestModifiedMarshallCalculator(unittest.TestCase):
    def setUp(self):
        self.calc = ModifiedMarshallCalculator()

    def test_normal(self):
        result = self.calc.calculate(PancreatitisLabs())
        self.assertEqual(result.max_organ_score, 0)
        self.assertFalse(result.has_organ_failure)

    def test_respiratory_failure(self):
        result = self.calc.calculate(PancreatitisLabs(pao2_fio2_ratio=250))
        self.assertEqual(result.respiratory_score, 2)
        self.assertTrue(result.has_organ_failure)

    def test_renal_failure(self):
        result = self.calc.calculate(PancreatitisLabs(creatinine_mg_dl=2.4))
        self.assertEqual(result.renal_score, 2)

    def test_cardiovascular_failure(self):
        result = self.calc.calculate(PancreatitisLabs(systolic_bp_mmhg=80, arterial_ph=7.25))
        self.assertEqual(result.cardiovascular_score, 3)

    def test_fluid_responsive_hypotension_score_one(self):
        result = self.calc.calculate(PancreatitisLabs(systolic_bp_mmhg=80, fluid_responsive_hypotension=True))
        self.assertEqual(result.cardiovascular_score, 1)
        self.assertFalse(result.has_organ_failure)


class TestRevisedAtlantaClassification(unittest.TestCase):
    def setUp(self):
        self.engine = AcutePancreatitisBundleEngine()

    def test_mild(self):
        evaluation = self.engine.evaluate_patient("P", PancreatitisLabs())
        self.assertEqual(evaluation.atlanta_classification.category, "Mild Acute Pancreatitis")

    def test_sirs_does_not_define_moderately_severe(self):
        labs = PancreatitisLabs(temp_c=38.8, heart_rate_bpm=110, resp_rate_bpm=25, wbc_k_ul=18)
        evaluation = self.engine.evaluate_patient("P", labs)
        self.assertTrue(evaluation.sirs_present)
        self.assertEqual(evaluation.atlanta_classification.category, "Mild Acute Pancreatitis")

    def test_bisap_does_not_define_moderately_severe(self):
        labs = PancreatitisLabs(bun_mg_dl=30, age=70)
        evaluation = self.engine.evaluate_patient("P", labs)
        self.assertGreaterEqual(evaluation.bisap.total_score, 2)
        self.assertEqual(evaluation.atlanta_classification.category, "Mild Acute Pancreatitis")

    def test_transient_organ_failure_is_moderately_severe(self):
        labs = PancreatitisLabs(pao2_fio2_ratio=220)
        evaluation = self.engine.evaluate_patient("P", labs, organ_failure_duration_hours=24)
        self.assertEqual(evaluation.atlanta_classification.category, "Moderately Severe Acute Pancreatitis")
        self.assertEqual(evaluation.atlanta_classification.organ_failure_status, "Transient (< 48h)")

    def test_local_complication_is_moderately_severe(self):
        evaluation = self.engine.evaluate_patient("P", PancreatitisLabs(), local_complications=["acute peripancreatic fluid collection"])
        self.assertEqual(evaluation.atlanta_classification.category, "Moderately Severe Acute Pancreatitis")

    def test_systemic_complication_is_moderately_severe(self):
        evaluation = self.engine.evaluate_patient("P", PancreatitisLabs(), systemic_complications=True)
        self.assertEqual(evaluation.atlanta_classification.category, "Moderately Severe Acute Pancreatitis")
        self.assertTrue(evaluation.atlanta_classification.systemic_complications)

    def test_persistent_organ_failure_is_severe(self):
        labs = PancreatitisLabs(creatinine_mg_dl=2.4)
        evaluation = self.engine.evaluate_patient("P", labs, organ_failure_duration_hours=48)
        self.assertEqual(evaluation.atlanta_classification.category, "Severe Acute Pancreatitis")


class TestCTSI(unittest.TestCase):
    def setUp(self):
        self.calc = CTSICalculator()
        self.engine = AcutePancreatitisBundleEngine()

    def test_grade_a(self):
        self.assertEqual(self.calc.calculate("A", 0).total_ctsi, 0)

    def test_grade_e_55_percent(self):
        self.assertEqual(self.calc.calculate("E", 55).total_ctsi, 10)

    def test_invalid_grade_rejected(self):
        with self.assertRaises(ValueError):
            self.calc.calculate("Z", 0)

    def test_invalid_necrosis_rejected(self):
        with self.assertRaises(ValueError):
            self.calc.calculate("A", -1)

    def test_engine_returns_ctsi_when_requested(self):
        evaluation = self.engine.evaluate_patient("P", PancreatitisLabs(), ct_balthazar_grade="D", ct_necrosis_pct=30)
        self.assertIsNotNone(evaluation.ctsi)
        self.assertEqual(evaluation.ctsi.total_ctsi, 5)

    def test_necrosis_without_grade_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.evaluate_patient("P", PancreatitisLabs(), ct_necrosis_pct=30)


class TestFluidNutritionAntibiotics(unittest.TestCase):
    def setUp(self):
        self.engine = AcutePancreatitisBundleEngine()

    def test_weight_based_reference_rate(self):
        evaluation = self.engine.evaluate_patient("P", PancreatitisLabs(), weight_kg=80)
        self.assertEqual(evaluation.fluid_guidelines.initial_rate_ml_hr, 120.0)

    def test_high_bun_hct_alone_do_not_trigger_bolus(self):
        labs = PancreatitisLabs(bun_mg_dl=35, hematocrit_pct=48, systolic_bp_mmhg=120)
        evaluation = self.engine.evaluate_patient("P", labs)
        self.assertFalse(evaluation.fluid_guidelines.bolus_indicated)
        self.assertTrue(any("reassess" in item.lower() for item in evaluation.action_items))

    def test_hypotension_triggers_bolus_flag(self):
        evaluation = self.engine.evaluate_patient("P", PancreatitisLabs(systolic_bp_mmhg=88))
        self.assertTrue(evaluation.fluid_guidelines.bolus_indicated)
        self.assertTrue(any("10" in item and "bolus" in item.lower() for item in evaluation.action_items))

    def test_early_oral_feeding_language(self):
        evaluation = self.engine.evaluate_patient("P", PancreatitisLabs())
        self.assertIn("24-48", evaluation.nutrition_guideline)

    def test_no_prophylactic_antibiotics(self):
        evaluation = self.engine.evaluate_patient("P", PancreatitisLabs())
        self.assertIn("Do not use prophylactic antibiotics", evaluation.antibiotic_guideline)


class TestRanson(unittest.TestCase):
    def test_admission_criteria(self):
        labs = PancreatitisLabs(age=62, wbc_k_ul=19, glucose_mg_dl=250, ldh_u_l=400, ast_u_l=300)
        result = RansonCalculator().evaluate(labs)
        self.assertEqual(len(result.admission_criteria_met), 5)


class TestValidation(unittest.TestCase):
    def test_negative_bun_rejected(self):
        with self.assertRaises(ValueError):
            PancreatitisLabs(bun_mg_dl=-1)

    def test_boolean_numeric_field_rejected(self):
        with self.assertRaises(TypeError):
            PancreatitisLabs(age=True)

    def test_negative_organ_failure_duration_rejected(self):
        with self.assertRaises(ValueError):
            AcutePancreatitisBundleEngine().evaluate_patient("P", PancreatitisLabs(), organ_failure_duration_hours=-1)

    def test_weight_range_rejected(self):
        with self.assertRaises(ValueError):
            AcutePancreatitisBundleEngine().evaluate_patient("P", PancreatitisLabs(), weight_kg=5)


class TestCLI(unittest.TestCase):
    def _run(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_single_json(self):
        code, output, _ = self._run(["--evaluate", "--patient-id", "CLI", "--bun", "32", "--json"])
        self.assertEqual(code, 0)
        data = json.loads(output)
        self.assertEqual(data["patient_id"], "CLI")

    def test_single_invalid_input_returns_one(self):
        code, _, error = self._run(["--evaluate", "--gcs", "20"])
        self.assertEqual(code, 1)
        self.assertIn("gcs_score", error)

    def test_ctsi_appears_in_json(self):
        code, output, _ = self._run(["--evaluate", "--balthazar", "D", "--necrosis", "30", "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["ctsi"]["total_ctsi"], 5)

    def test_batch_json(self):
        records = [
            {"patient_id": "A", "cr": 2.4, "of_hours": 50},
            {"patient_id": "B", "bun": 12, "pao2_fio2": 480},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(records, handle)
            path = handle.name
        try:
            code, output, _ = self._run(["--batch", path, "--json"])
            self.assertEqual(code, 0)
            data = json.loads(output)
            self.assertEqual(data[0]["atlanta_classification"]["category"], "Severe Acute Pancreatitis")
            self.assertEqual(data[1]["atlanta_classification"]["category"], "Mild Acute Pancreatitis")
        finally:
            os.remove(path)

    def test_csv_false_boolean_is_false(self):
        content = "patient_id,pleural_effusion,bun,age\nP,False,30,70\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            handle.write(content)
            path = handle.name
        try:
            code, output, _ = self._run(["--batch", path, "--json"])
            self.assertEqual(code, 0)
            data = json.loads(output)[0]
            self.assertFalse(data["bisap"]["pleural_effusion"])
            self.assertEqual(data["bisap"]["total_score"], 2)
        finally:
            os.remove(path)

    def test_csv_of_hours_is_honored(self):
        content = "patient_id,cr,of_hours\nP,2.4,50\n"
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as handle:
            handle.write(content)
            path = handle.name
        try:
            code, output, _ = self._run(["--batch", path, "--json"])
            self.assertEqual(code, 0)
            data = json.loads(output)[0]
            self.assertEqual(data["atlanta_classification"]["category"], "Severe Acute Pancreatitis")
        finally:
            os.remove(path)

    def test_sample_csv(self):
        code, output, _ = self._run(["--batch", str(PROJECT_ROOT / "sample.csv"), "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(output)), 3)

    def test_malformed_json_returns_one(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            handle.write("{invalid")
            path = handle.name
        try:
            code, _, error = self._run(["--batch", path])
            self.assertEqual(code, 1)
            self.assertIn("JSON", error)
        finally:
            os.remove(path)

    def test_nonexistent_batch_returns_one(self):
        code, _, error = self._run(["--batch", "does-not-exist.csv"])
        self.assertEqual(code, 1)
        self.assertIn("File not found", error)

    def test_output_path_traversal_rejected(self):
        code, _, error = self._run(["--evaluate", "--output", "../../outside.txt"])
        self.assertEqual(code, 1)
        self.assertIn("escapes the working directory", error)

    def test_safe_bool_invalid_rejected(self):
        with self.assertRaises(ValueError):
            cli._safe_bool("maybe", "flag")


if __name__ == "__main__":
    unittest.main()
