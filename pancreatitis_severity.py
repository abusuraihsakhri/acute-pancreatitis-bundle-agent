#!/usr/bin/env python3
"""Acute pancreatitis severity and supportive-care calculation utilities.

The module implements established scoring/classification frameworks for educational
and decision-support use. It does not diagnose acute pancreatitis and does not
replace clinical assessment, local protocols, or specialist judgment.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PancreatitisLabs:
    """Laboratory values and vital signs used by the calculators."""

    bun_mg_dl: float = 15.0
    creatinine_mg_dl: float = 1.0
    hematocrit_pct: float = 40.0
    wbc_k_ul: float = 9.0
    temp_c: float = 37.0
    heart_rate_bpm: int = 75
    resp_rate_bpm: int = 16
    spo2_pct: float = 98.0
    pao2_fio2_ratio: float = 450.0
    systolic_bp_mmhg: float = 120.0
    fluid_responsive_hypotension: bool = False
    arterial_ph: float = 7.40
    glucose_mg_dl: float = 110.0
    calcium_mg_dl: float = 9.2
    albumin_g_dl: float = 4.0
    ldh_u_l: float = 180.0
    ast_u_l: float = 35.0
    lipase_u_l: float = 150.0
    age: int = 45

    _VALIDATION_RANGES = {
        "bun_mg_dl": (0.0, 300.0),
        "creatinine_mg_dl": (0.0, 30.0),
        "hematocrit_pct": (0.0, 75.0),
        "wbc_k_ul": (0.0, 100.0),
        "temp_c": (25.0, 45.0),
        "heart_rate_bpm": (0, 300),
        "resp_rate_bpm": (0, 80),
        "spo2_pct": (0.0, 100.0),
        "pao2_fio2_ratio": (0.0, 800.0),
        "systolic_bp_mmhg": (0.0, 300.0),
        "arterial_ph": (6.5, 8.0),
        "glucose_mg_dl": (0.0, 1200.0),
        "calcium_mg_dl": (0.0, 20.0),
        "albumin_g_dl": (0.0, 8.0),
        "ldh_u_l": (0.0, 5000.0),
        "ast_u_l": (0.0, 5000.0),
        "lipase_u_l": (0.0, 10000.0),
        "age": (0, 150),
    }

    def __post_init__(self) -> None:
        for field_name, (lo, hi) in self._VALIDATION_RANGES.items():
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(
                    f"{field_name} must be numeric, got {type(value).__name__}"
                )
            if value < lo or value > hi:
                raise ValueError(
                    f"{field_name}={value} is outside valid range [{lo}, {hi}]"
                )
        if not isinstance(self.fluid_responsive_hypotension, bool):
            raise TypeError("fluid_responsive_hypotension must be boolean")


@dataclass
class BISAPResult:
    bun_gt_25: bool
    impaired_mental_status: bool
    sirs_present: bool
    age_gt_60: bool
    pleural_effusion: bool
    total_score: int
    mortality_risk_pct: float
    severity_tier: str


@dataclass
class MarshallScoreResult:
    respiratory_score: int
    renal_score: int
    cardiovascular_score: int
    max_organ_score: int
    has_organ_failure: bool
    organ_failure_systems: List[str]


@dataclass
class AtlantaClassificationResult:
    category: str
    organ_failure_status: str
    local_complications: List[str]
    systemic_complications: bool
    recommended_level_of_care: str


@dataclass
class RansonResult:
    admission_criteria_met: List[str]
    at_48h_criteria_met: List[str]
    total_score: int
    estimated_mortality_pct: float


@dataclass
class CTSIResult:
    balthazar_grade: str
    balthazar_points: int
    necrosis_pct: float
    necrosis_points: int
    total_ctsi: int
    morbidity_risk: str
    mortality_risk_pct: float


@dataclass
class FluidResuscitationGuideline:
    recommended_fluid: str
    initial_rate_ml_hr: float
    bolus_indicated: bool
    resuscitation_targets: List[str]
    precautions: List[str]


@dataclass
class ComprehensivePancreatitisAssessment:
    patient_id: str
    atlanta_classification: AtlantaClassificationResult
    bisap: BISAPResult
    modified_marshall: MarshallScoreResult
    sirs_criteria_count: int
    sirs_present: bool
    fluid_guidelines: FluidResuscitationGuideline
    nutrition_guideline: str
    antibiotic_guideline: str
    action_items: List[str]
    ctsi: Optional[CTSIResult] = None


class BISAPCalculator:
    """Bedside Index for Severity in Acute Pancreatitis (BISAP)."""

    def calculate(
        self,
        labs: PancreatitisLabs,
        gcs_score: int = 15,
        pleural_effusion_present: bool = False,
    ) -> BISAPResult:
        if not isinstance(gcs_score, int) or isinstance(gcs_score, bool):
            raise TypeError("gcs_score must be an integer")
        if not 3 <= gcs_score <= 15:
            raise ValueError("gcs_score must be between 3 and 15")
        if not isinstance(pleural_effusion_present, bool):
            raise TypeError("pleural_effusion_present must be boolean")

        sirs_met = self._is_sirs(labs)
        criteria = {
            "bun_gt_25": labs.bun_mg_dl > 25.0,
            "impaired_mental": gcs_score < 15,
            "sirs": sirs_met,
            "age_gt_60": labs.age > 60,
            "pleural_effusion": pleural_effusion_present,
        }
        score = sum(1 for value in criteria.values() if value)

        mortality_map = {0: 0.1, 1: 0.4, 2: 1.6, 3: 3.6, 4: 7.4, 5: 18.0}
        mortality = mortality_map[score]

        if score <= 1:
            tier = "BISAP 0-1 (lower observed risk)"
        elif score == 2:
            tier = "BISAP 2 (intermediate observed risk)"
        elif score == 3:
            tier = "BISAP 3 (higher observed risk)"
        else:
            tier = "BISAP 4-5 (highest observed risk group)"

        return BISAPResult(
            bun_gt_25=criteria["bun_gt_25"],
            impaired_mental_status=criteria["impaired_mental"],
            sirs_present=criteria["sirs"],
            age_gt_60=criteria["age_gt_60"],
            pleural_effusion=criteria["pleural_effusion"],
            total_score=score,
            mortality_risk_pct=mortality,
            severity_tier=tier,
        )

    def _is_sirs(self, labs: PancreatitisLabs) -> bool:
        return self.count_sirs(labs) >= 2

    @staticmethod
    def count_sirs(labs: PancreatitisLabs) -> int:
        criteria = [
            labs.temp_c > 38.0 or labs.temp_c < 36.0,
            labs.heart_rate_bpm > 90,
            labs.resp_rate_bpm > 20,
            labs.wbc_k_ul > 12.0 or labs.wbc_k_ul < 4.0,
        ]
        return sum(1 for criterion in criteria if criterion)


class ModifiedMarshallCalculator:
    """Modified Marshall organ dysfunction scoring used by Revised Atlanta."""

    def calculate(self, labs: PancreatitisLabs) -> MarshallScoreResult:
        respiratory = self._score_respiratory(labs.pao2_fio2_ratio)
        renal = self._score_renal(labs.creatinine_mg_dl)
        cardiovascular = self._score_cardiovascular(
            labs.systolic_bp_mmhg,
            labs.fluid_responsive_hypotension,
            labs.arterial_ph,
        )

        max_score = max(respiratory, renal, cardiovascular)
        failed_systems: List[str] = []
        if respiratory >= 2:
            failed_systems.append(
                f"Respiratory failure (score {respiratory}, PaO2/FiO2={labs.pao2_fio2_ratio:.0f})"
            )
        if renal >= 2:
            failed_systems.append(
                f"Renal failure (score {renal}, creatinine={labs.creatinine_mg_dl:.1f} mg/dL)"
            )
        if cardiovascular >= 2:
            failed_systems.append(
                f"Cardiovascular failure (score {cardiovascular}, SBP={labs.systolic_bp_mmhg:.0f} mmHg)"
            )

        return MarshallScoreResult(
            respiratory_score=respiratory,
            renal_score=renal,
            cardiovascular_score=cardiovascular,
            max_organ_score=max_score,
            has_organ_failure=max_score >= 2,
            organ_failure_systems=failed_systems,
        )

    @staticmethod
    def _score_respiratory(pf_ratio: float) -> int:
        if pf_ratio > 400.0:
            return 0
        if pf_ratio >= 301.0:
            return 1
        if pf_ratio >= 201.0:
            return 2
        if pf_ratio >= 101.0:
            return 3
        return 4

    @staticmethod
    def _score_renal(creatinine: float) -> int:
        if creatinine <= 1.4:
            return 0
        if creatinine <= 1.8:
            return 1
        if creatinine <= 3.6:
            return 2
        if creatinine <= 4.9:
            return 3
        return 4

    @staticmethod
    def _score_cardiovascular(
        systolic_bp: float,
        fluid_responsive: bool,
        arterial_ph: float,
    ) -> int:
        if systolic_bp > 90.0:
            return 0
        if fluid_responsive:
            return 1
        if arterial_ph < 7.20:
            return 4
        if arterial_ph < 7.30:
            return 3
        return 2


class RansonCalculator:
    """Ranson criteria for non-gallstone acute pancreatitis."""

    def calculate_admission(self, labs: PancreatitisLabs) -> List[str]:
        criteria: List[str] = []
        if labs.age > 55:
            criteria.append("Age > 55 years")
        if labs.wbc_k_ul > 16.0:
            criteria.append("WBC > 16,000/uL")
        if labs.glucose_mg_dl > 200.0:
            criteria.append("Blood glucose > 200 mg/dL")
        if labs.ldh_u_l > 350.0:
            criteria.append("Serum LDH > 350 IU/L")
        if labs.ast_u_l > 250.0:
            criteria.append("Serum AST > 250 IU/L")
        return criteria

    def calculate_48h(
        self,
        hct_drop_pct: float = 0.0,
        bun_increase_mg_dl: float = 0.0,
        serum_calcium_mg_dl: float = 9.0,
        pao2_mmhg: float = 95.0,
        base_deficit_meq_l: float = 0.0,
        fluid_sequestration_l: float = 0.0,
    ) -> List[str]:
        criteria: List[str] = []
        if hct_drop_pct > 10.0:
            criteria.append("Hematocrit drop > 10%")
        if bun_increase_mg_dl > 5.0:
            criteria.append("BUN rise > 5 mg/dL")
        if serum_calcium_mg_dl < 8.0:
            criteria.append("Serum calcium < 8.0 mg/dL")
        if pao2_mmhg < 60.0:
            criteria.append("Arterial PaO2 < 60 mmHg")
        if base_deficit_meq_l > 4.0:
            criteria.append("Base deficit > 4 mEq/L")
        if fluid_sequestration_l > 6.0:
            criteria.append("Fluid sequestration > 6 L")
        return criteria

    def evaluate(self, labs: PancreatitisLabs, **kwargs) -> RansonResult:
        admission = self.calculate_admission(labs)
        at_48h = self.calculate_48h(**kwargs)
        total = len(admission) + len(at_48h)
        if total <= 2:
            mortality = 1.0
        elif total <= 4:
            mortality = 15.0
        elif total <= 6:
            mortality = 40.0
        else:
            mortality = 100.0
        return RansonResult(admission, at_48h, total, mortality)


class CTSICalculator:
    """Original Balthazar CT Severity Index (CTSI)."""

    BALTHAZAR_MAP = {
        "A": (0, "Normal pancreas"),
        "B": (1, "Focal or diffuse enlargement"),
        "C": (2, "Pancreatic abnormalities with peripancreatic inflammation"),
        "D": (3, "Single peripancreatic fluid collection"),
        "E": (4, "Two or more collections or retroperitoneal gas"),
    }

    def calculate(
        self,
        balthazar_grade: str = "A",
        necrosis_pct: float = 0.0,
    ) -> CTSIResult:
        if not isinstance(balthazar_grade, str):
            raise TypeError("balthazar_grade must be a string from A to E")
        grade = balthazar_grade.strip().upper()
        if grade not in self.BALTHAZAR_MAP:
            raise ValueError("balthazar_grade must be one of A, B, C, D, or E")
        if isinstance(necrosis_pct, bool) or not isinstance(necrosis_pct, (int, float)):
            raise TypeError("necrosis_pct must be numeric")
        necrosis = float(necrosis_pct)
        if not 0.0 <= necrosis <= 100.0:
            raise ValueError("necrosis_pct must be between 0 and 100")

        balthazar_points = self.BALTHAZAR_MAP[grade][0]
        if necrosis == 0.0:
            necrosis_points = 0
        elif necrosis <= 30.0:
            necrosis_points = 2
        elif necrosis <= 50.0:
            necrosis_points = 4
        else:
            necrosis_points = 6

        total = balthazar_points + necrosis_points
        if total <= 3:
            morbidity = "Lower CTSI group (0-3)"
            mortality = 3.0
        elif total <= 6:
            morbidity = "Intermediate CTSI group (4-6)"
            mortality = 6.0
        else:
            morbidity = "Higher CTSI group (7-10)"
            mortality = 17.0

        return CTSIResult(
            balthazar_grade=grade,
            balthazar_points=balthazar_points,
            necrosis_pct=necrosis,
            necrosis_points=necrosis_points,
            total_ctsi=total,
            morbidity_risk=morbidity,
            mortality_risk_pct=mortality,
        )


class AcutePancreatitisBundleEngine:
    """Combine severity frameworks into one structured assessment."""

    def __init__(self) -> None:
        self.bisap_calc = BISAPCalculator()
        self.marshall_calc = ModifiedMarshallCalculator()
        self.ranson_calc = RansonCalculator()
        self.ctsi_calc = CTSICalculator()

    def evaluate_patient(
        self,
        patient_id: str,
        labs: PancreatitisLabs,
        gcs_score: int = 15,
        pleural_effusion: bool = False,
        organ_failure_duration_hours: float = 0.0,
        local_complications: Optional[List[str]] = None,
        ct_balthazar_grade: Optional[str] = None,
        ct_necrosis_pct: float = 0.0,
        systemic_complications: bool = False,
        weight_kg: float = 70.0,
    ) -> ComprehensivePancreatitisAssessment:
        if not isinstance(patient_id, str):
            raise TypeError("patient_id must be a string")
        if not patient_id.strip():
            raise ValueError("patient_id cannot be empty")
        if isinstance(organ_failure_duration_hours, bool) or not isinstance(
            organ_failure_duration_hours, (int, float)
        ):
            raise TypeError("organ_failure_duration_hours must be numeric")
        if organ_failure_duration_hours < 0:
            raise ValueError("organ_failure_duration_hours cannot be negative")
        if not isinstance(systemic_complications, bool):
            raise TypeError("systemic_complications must be boolean")
        if isinstance(weight_kg, bool) or not isinstance(weight_kg, (int, float)):
            raise TypeError("weight_kg must be numeric")
        if not 20.0 <= float(weight_kg) <= 350.0:
            raise ValueError("weight_kg must be between 20 and 350")

        local_comps = list(local_complications or [])
        if any(not isinstance(item, str) for item in local_comps):
            raise TypeError("local_complications must contain strings")

        bisap = self.bisap_calc.calculate(labs, gcs_score, pleural_effusion)
        marshall = self.marshall_calc.calculate(labs)
        sirs_count = BISAPCalculator.count_sirs(labs)
        sirs_present = sirs_count >= 2

        # Revised Atlanta severity depends on organ failure and local/systemic
        # complications. BISAP and SIRS are risk markers, not Atlanta severity criteria.
        if marshall.has_organ_failure and organ_failure_duration_hours >= 48.0:
            atlanta_category = "Severe Acute Pancreatitis"
            organ_failure_status = "Persistent (>= 48h)"
            care_level = "Critical-care assessment / ICU-level support as indicated"
        elif marshall.has_organ_failure:
            atlanta_category = "Moderately Severe Acute Pancreatitis"
            organ_failure_status = "Transient (< 48h)"
            care_level = "Monitored setting; escalate according to organ support needs"
        elif local_comps or systemic_complications:
            atlanta_category = "Moderately Severe Acute Pancreatitis"
            organ_failure_status = "None"
            care_level = "Monitored inpatient care according to complications"
        else:
            atlanta_category = "Mild Acute Pancreatitis"
            organ_failure_status = "None"
            care_level = "Standard inpatient care as clinically indicated"

        atlanta = AtlantaClassificationResult(
            category=atlanta_category,
            organ_failure_status=organ_failure_status,
            local_complications=local_comps,
            systemic_complications=systemic_complications,
            recommended_level_of_care=care_level,
        )

        # Moderate goal-directed starting reference; repeated reassessment takes precedence.
        weight = float(weight_kg)
        initial_rate = round(1.5 * weight, 1)
        bolus_indicated = (
            labs.systolic_bp_mmhg <= 90.0 or labs.fluid_responsive_hypotension
        )
        fluid_guidelines = FluidResuscitationGuideline(
            recommended_fluid="Lactated Ringer's solution (unless contraindicated)",
            initial_rate_ml_hr=initial_rate,
            bolus_indicated=bolus_indicated,
            resuscitation_targets=[
                "Reassess volume status, urine output, BUN, hematocrit, and vital signs frequently",
                "Aim for adequate perfusion while avoiding fluid overload",
                "Adjust fluids to clinical response and comorbidity",
            ],
            precautions=[
                "A fixed-rate plan is not appropriate for shock, heart failure, or advanced kidney disease",
                "Elevated BUN or hematocrit should prompt reassessment rather than automatic aggressive bolusing",
                "Reduce or stop fluids if overload develops",
            ],
        )

        if atlanta_category == "Mild Acute Pancreatitis":
            nutrition = (
                "Start oral feeding early (generally within 24-48 hours) as tolerated; "
                "a low-fat solid diet is acceptable without requiring a clear-liquid step-up."
            )
        else:
            nutrition = (
                "Use enteral nutrition when oral intake is not feasible; nasogastric feeding is "
                "generally acceptable, with parenteral nutrition reserved for cases where enteral feeding is not possible."
            )

        antibiotics = (
            "Do not use prophylactic antibiotics for sterile acute pancreatitis or sterile necrosis. "
            "When infection is suspected or confirmed, obtain appropriate cultures when feasible and select therapy "
            "according to the infection source, local susceptibility data, and agents with appropriate tissue penetration."
        )

        ctsi: Optional[CTSIResult] = None
        if ct_balthazar_grade is not None:
            ctsi = self.ctsi_calc.calculate(ct_balthazar_grade, ct_necrosis_pct)
        elif ct_necrosis_pct != 0.0:
            raise ValueError(
                "ct_balthazar_grade is required when ct_necrosis_pct is provided"
            )

        actions: List[str] = []
        if atlanta_category == "Severe Acute Pancreatitis":
            actions.append(
                "Persistent organ failure: obtain critical-care assessment and provide organ support as indicated."
            )
        if marshall.has_organ_failure:
            actions.extend(
                f"Organ failure identified: {system_failure}"
                for system_failure in marshall.organ_failure_systems
            )
        if bisap.total_score >= 3:
            actions.append(
                f"BISAP {bisap.total_score}/5: higher-risk group; increase monitoring and reassess clinical trajectory."
            )
        if bolus_indicated:
            actions.append(
                f"Possible hypovolemia/hypotension: consider a cautious LR bolus (about 10 mL/kg; {10 * weight:.0f} mL at this weight) "
                "with prompt reassessment rather than routine aggressive hydration."
            )
        if labs.bun_mg_dl > 25.0 or labs.hematocrit_pct > 44.0:
            actions.append(
                "BUN and/or hematocrit is elevated: reassess intravascular volume and trend values; do not use either value alone to mandate a bolus."
            )
        if sirs_present:
            actions.append(
                f"SIRS present ({sirs_count}/4 criteria): monitor persistence and organ function."
            )

        return ComprehensivePancreatitisAssessment(
            patient_id=patient_id.strip(),
            atlanta_classification=atlanta,
            bisap=bisap,
            modified_marshall=marshall,
            sirs_criteria_count=sirs_count,
            sirs_present=sirs_present,
            fluid_guidelines=fluid_guidelines,
            nutrition_guideline=nutrition,
            antibiotic_guideline=antibiotics,
            action_items=actions,
            ctsi=ctsi,
        )
