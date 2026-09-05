#!/usr/bin/env python3
"""
Acute Pancreatitis Clinical Decision Support & Bundle Care Protocol Engine.

Clinical Frameworks:
1. Revised Atlanta Classification 2012 (Mild, Moderately Severe, Severe).
2. Bedside Index for Severity in Acute Pancreatitis (BISAP) Score & Mortality Stratification.
3. Modified Marshall Scoring System for Multiorgan Failure (Respiratory, Renal, Cardiovascular).
4. Systemic Inflammatory Response Syndrome (SIRS) Trajectory & Persistent SIRS Detection.
5. Ranson's Criteria (Admission and 48-Hour Progression).
6. Balthazar Computed Tomography Severity Index (CTSI) & Necrosis Assessment.
7. Goal-Directed Fluid Resuscitation & Enteral Nutrition Bundle Guidelines.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PancreatitisLabs:
    """Laboratory values and vitals for acute pancreatitis assessment.

    All numeric fields are validated to be within physiologically plausible ranges
    on instantiation. Raises ValueError for out-of-range values.
    """

    bun_mg_dl: float = 15.0
    creatinine_mg_dl: float = 1.0
    hematocrit_pct: float = 40.0
    wbc_k_ul: float = 9.0
    temp_c: float = 37.0
    heart_rate_bpm: int = 75
    resp_rate_bpm: int = 16
    spo2_pct: float = 98.0
    pao2_fio2_ratio: float = 450.0  # PaO2/FiO2 ratio (e.g. 95/0.21 = 452)
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

    # Physiological validation ranges (min, max) — None means unbounded
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

    def __post_init__(self):
        """Validate all numeric fields are within physiological ranges."""
        for field_name, (lo, hi) in self._VALIDATION_RANGES.items():
            value = getattr(self, field_name)
            if value is None:
                continue
            if not isinstance(value, (int, float)):
                raise TypeError(f"{field_name} must be numeric, got {type(value).__name__}")
            if value < lo or value > hi:
                raise ValueError(
                    f"{field_name}={value} is outside valid range [{lo}, {hi}]"
                )


@dataclass
class BISAPResult:
    bun_gt_25: bool
    impaired_mental_status: bool
    sirs_present: bool
    age_gt_60: bool
    pleural_effusion: bool
    total_score: int
    mortality_risk_pct: float
    severity_tier: str  # "Low Risk (< 1%)", "Intermediate (1-4%)", "High Risk (> 15%)"


@dataclass
class MarshallScoreResult:
    respiratory_score: int  # 0-4
    renal_score: int        # 0-4
    cardiovascular_score: int # 0-4
    max_organ_score: int
    has_organ_failure: bool  # score >= 2 in any domain
    organ_failure_systems: List[str]


@dataclass
class AtlantaClassificationResult:
    category: str  # "Mild Acute Pancreatitis", "Moderately Severe Acute Pancreatitis", "Severe Acute Pancreatitis"
    organ_failure_status: str  # "None", "Transient (< 48h)", "Persistent (>= 48h)"
    local_complications: List[str]
    systemic_complications: bool
    recommended_level_of_care: str  # "Floor / Regular Ward", "Stepdown / Intermediate Care", "Intensive Care Unit (ICU)"


@dataclass
class RansonResult:
    admission_criteria_met: List[str]
    at_48h_criteria_met: List[str]
    total_score: int
    estimated_mortality_pct: float


@dataclass
class CTSIResult:
    balthazar_grade: str  # A to E
    balthazar_points: int # 0 to 4
    necrosis_pct: float   # 0, <30%, 30-50%, >50%
    necrosis_points: int  # 0, 2, 4, 6
    total_ctsi: int       # 0 to 10
    morbidity_risk: str
    mortality_risk_pct: float


@dataclass
class FluidResuscitationGuideline:
    recommended_fluid: str  # "Lactated Ringer's Solution (Preferred)"
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


class BISAPCalculator:
    """
    Bedside Index for Severity in Acute Pancreatitis (BISAP).
    Wu BU et al. Gut. 2008;57(12):1698-1703.
    """

    def calculate(
        self,
        labs: PancreatitisLabs,
        gcs_score: int = 15,
        pleural_effusion_present: bool = False,
    ) -> BISAPResult:
        sirs_met = self._is_sirs(labs)
        impaired_mental = gcs_score < 15

        criteria = {
            "bun_gt_25": labs.bun_mg_dl > 25.0,
            "impaired_mental": impaired_mental,
            "sirs": sirs_met,
            "age_gt_60": labs.age > 60,
            "pleural_effusion": pleural_effusion_present,
        }

        score = sum(1 for v in criteria.values() if v)

        # Standard BISAP mortality correlation
        mortality_map = {0: 0.1, 1: 0.4, 2: 1.6, 3: 3.6, 4: 7.4, 5: 18.0}
        mortality = mortality_map.get(score, 18.0)

        if score <= 1:
            tier = "Low Risk of In-Hospital Mortality (< 1%)"
        elif score == 2:
            tier = "Intermediate Risk (1.6%)"
        elif score == 3:
            tier = "High Risk of Severe Disease & Mortality (3.6%)"
        else:
            tier = "Critical Risk (> 7-18% Mortality)"

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
        crit_count = self.count_sirs(labs)
        return crit_count >= 2

    @staticmethod
    def count_sirs(labs: PancreatitisLabs) -> int:
        crit = [
            (labs.temp_c > 38.0 or labs.temp_c < 36.0),
            (labs.heart_rate_bpm > 90),
            (labs.resp_rate_bpm > 20),
            (labs.wbc_k_ul > 12.0 or labs.wbc_k_ul < 4.0),
        ]
        return sum(1 for c in crit if c)


class ModifiedMarshallCalculator:
    """
    Modified Marshall Scoring System for Organ Dysfunction in Acute Pancreatitis.
    Marshall JC et al. Crit Care Med. 1995;23(10):1638-1652.
    Banks PA et al. Gut. 2013;62(1):102-111 (Atlanta 2012 definition).
    """

    def calculate(self, labs: PancreatitisLabs) -> MarshallScoreResult:
        # Respiratory: PaO2 / FiO2
        resp = self._score_respiratory(labs.pao2_fio2_ratio)

        # Renal: Serum Creatinine
        renal = self._score_renal(labs.creatinine_mg_dl)

        # Cardiovascular: Systolic BP & Fluid responsiveness
        cardio = self._score_cardiovascular(labs.systolic_bp_mmhg, labs.fluid_responsive_hypotension, labs.arterial_ph)

        max_score = max(resp, renal, cardio)
        failed_systems = []
        if resp >= 2:
            failed_systems.append(f"Respiratory Failure (Score {resp}, PaO2/FiO2={labs.pao2_fio2_ratio:.0f})")
        if renal >= 2:
            failed_systems.append(f"Renal Failure (Score {renal}, Cr={labs.creatinine_mg_dl:.1f} mg/dL)")
        if cardio >= 2:
            failed_systems.append(f"Cardiovascular Failure (Score {cardio}, SBP={labs.systolic_bp_mmhg:.0f} mmHg)")

        return MarshallScoreResult(
            respiratory_score=resp,
            renal_score=renal,
            cardiovascular_score=cardio,
            max_organ_score=max_score,
            has_organ_failure=(max_score >= 2),
            organ_failure_systems=failed_systems,
        )

    def _score_respiratory(self, pf_ratio: float) -> int:
        if pf_ratio > 400.0:
            return 0
        elif pf_ratio >= 301.0:
            return 1
        elif pf_ratio >= 201.0:
            return 2
        elif pf_ratio >= 101.0:
            return 3
        else:
            return 4

    def _score_renal(self, cr: float) -> int:
        if cr <= 1.4:
            return 0
        elif cr <= 1.8:
            return 1
        elif cr <= 3.6:
            return 2
        elif cr <= 4.9:
            return 3
        else:
            return 4

    def _score_cardiovascular(self, sbp: float, fluid_responsive: bool, ph: float) -> int:
        if sbp > 90.0:
            return 0
        if sbp <= 90.0 and fluid_responsive:
            return 1
        if sbp <= 90.0 and not fluid_responsive:
            if ph < 7.20:
                return 4
            elif ph < 7.30:
                return 3
            else:
                return 2
        return 0


class RansonCalculator:
    """Ranson Criteria for Pancreatitis Severity (Admission & 48 Hours)."""

    def calculate_admission(self, labs: PancreatitisLabs) -> List[str]:
        hits = []
        if labs.age > 55:
            hits.append("Age > 55 years")
        if labs.wbc_k_ul > 16.0:
            hits.append("WBC > 16,000 /uL")
        if labs.glucose_mg_dl > 200.0:
            hits.append("Blood Glucose > 200 mg/dL")
        if labs.ldh_u_l > 350.0:
            hits.append("Serum LDH > 350 IU/L")
        if labs.ast_u_l > 250.0:
            hits.append("Serum AST > 250 IU/L")
        return hits

    def calculate_48h(
        self,
        hct_drop_pct: float = 0.0,
        bun_increase_mg_dl: float = 0.0,
        serum_calcium_mg_dl: float = 9.0,
        pao2_mmhg: float = 95.0,
        base_deficit_meq_l: float = 0.0,
        fluid_sequestration_l: float = 0.0,
    ) -> List[str]:
        hits = []
        if hct_drop_pct > 10.0:
            hits.append("Hematocrit drop > 10%")
        if bun_increase_mg_dl > 5.0:
            hits.append("BUN rise > 5 mg/dL")
        if serum_calcium_mg_dl < 8.0:
            hits.append("Serum Calcium < 8.0 mg/dL")
        if pao2_mmhg < 60.0:
            hits.append("Arterial PaO2 < 60 mmHg")
        if base_deficit_meq_l > 4.0:
            hits.append("Base deficit > 4 mEq/L")
        if fluid_sequestration_l > 6.0:
            hits.append("Fluid sequestration > 6 Liters")
        return hits

    def evaluate(self, labs: PancreatitisLabs, **kwargs) -> RansonResult:
        adm = self.calculate_admission(labs)
        post48 = self.calculate_48h(**kwargs)
        total = len(adm) + len(post48)

        if total <= 2:
            mort = 1.0
        elif total <= 4:
            mort = 15.0
        elif total <= 6:
            mort = 40.0
        else:
            mort = 100.0

        return RansonResult(
            admission_criteria_met=adm,
            at_48h_criteria_met=post48,
            total_score=total,
            estimated_mortality_pct=mort,
        )


class CTSICalculator:
    """Balthazar Computed Tomography Severity Index (CTSI)."""

    BALTHAZAR_MAP = {
        "A": (0, "Normal pancreas"),
        "B": (1, "Focal or diffuse enlargement"),
        "C": (2, "Intrinsic pancreatic abnormalities with peripancreatic inflammation"),
        "D": (3, "Single ill-defined peripancreatic fluid collection"),
        "E": (4, "Two or more multiple collections or retroperitoneal air"),
    }

    def calculate(self, balthazar_grade: str = "A", necrosis_pct: float = 0.0) -> CTSIResult:
        grade_upper = balthazar_grade.upper()
        b_pts, desc = self.BALTHAZAR_MAP.get(grade_upper, (0, "Normal pancreas"))

        if necrosis_pct == 0.0:
            n_pts = 0
        elif necrosis_pct <= 30.0:
            n_pts = 2
        elif necrosis_pct <= 50.0:
            n_pts = 4
        else:
            n_pts = 6

        total = b_pts + n_pts
        if total <= 3:
            morbidity = "Mild (Low complication rate)"
            mortality = 3.0
        elif total <= 6:
            morbidity = "Moderate (Intermediate risk of necrosis infection)"
            mortality = 6.0
        else:
            morbidity = "Severe (High complication rate, frequent infected necrosis)"
            mortality = 17.0

        return CTSIResult(
            balthazar_grade=grade_upper,
            balthazar_points=b_pts,
            necrosis_pct=necrosis_pct,
            necrosis_points=n_pts,
            total_ctsi=total,
            morbidity_risk=morbidity,
            mortality_risk_pct=mortality,
        )


class AcutePancreatitisBundleEngine:
    """Master Decision Support Engine for Acute Pancreatitis Care Bundle."""

    def __init__(self):
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
    ) -> ComprehensivePancreatitisAssessment:
        local_comps = local_complications or []

        # 1. BISAP & Marshall Scores
        bisap_res = self.bisap_calc.calculate(labs, gcs_score, pleural_effusion)
        marshall_res = self.marshall_calc.calculate(labs)
        sirs_count = BISAPCalculator.count_sirs(labs)
        sirs_present = sirs_count >= 2

        # 2. Atlanta Classification 2012
        if marshall_res.has_organ_failure:
            if organ_failure_duration_hours >= 48.0:
                atlanta_cat = "Severe Acute Pancreatitis"
                of_status = "Persistent (>= 48h)"
                loc = "Intensive Care Unit (ICU)"
            else:
                atlanta_cat = "Moderately Severe Acute Pancreatitis"
                of_status = "Transient (< 48h)"
                loc = "Stepdown / Intermediate Care"
        elif local_comps or bisap_res.total_score >= 2 or sirs_present:
            atlanta_cat = "Moderately Severe Acute Pancreatitis"
            of_status = "None"
            loc = "Stepdown / Intermediate Care"
        else:
            atlanta_cat = "Mild Acute Pancreatitis"
            of_status = "None"
            loc = "Floor / Regular Ward"

        atlanta_res = AtlantaClassificationResult(
            category=atlanta_cat,
            organ_failure_status=of_status,
            local_complications=local_comps,
            systemic_complications=sirs_present or marshall_res.has_organ_failure,
            recommended_level_of_care=loc,
        )

        # 3. Fluid Resuscitation Protocol
        # Goal-Directed: 200-250 mL/h of LR or 5-10 mL/kg/h bolus if SBP < 90 or BUN high
        bolus = (labs.systolic_bp_mmhg <= 90.0 or labs.bun_mg_dl > 25.0 or labs.hematocrit_pct > 44.0)
        rate = 250.0 if bolus else 150.0

        fluid_guidelines = FluidResuscitationGuideline(
            recommended_fluid="Lactated Ringer's Solution (Preferred over Normal Saline to prevent hyperchloremic acidosis)",
            initial_rate_ml_hr=rate,
            bolus_indicated=bolus,
            resuscitation_targets=[
                "Urine output > 0.5 - 1.0 mL/kg/h",
                "Reduction in BUN within 24 hours",
                "Normalization of Hematocrit (< 44%)",
                "Mean Arterial Pressure (MAP) >= 65 mmHg",
            ],
            precautions=[
                "Avoid aggressive fluid overload in patients with pre-existing heart failure, ESRD, or Hct < 35%",
                "Re-evaluate hemodynamic response every 4-6 hours",
            ],
        )

        # 4. Nutrition Guideline
        if atlanta_cat == "Mild Acute Pancreatitis":
            nutrition = "Early oral feeding (low-fat solid or liquid diet) as soon as abdominal pain improves and ileus resolves."
        else:
            nutrition = "Early enteral nutrition via nasogastric (NG) or nasojejunal (NJ) tube within 24-72 hours. Total Parenteral Nutrition (TPN) should be avoided unless enteral route not tolerated."

        # 5. Antibiotic Guidelines
        antibiotics = "Prophylactic antibiotics NOT recommended for sterile acute pancreatitis or acute necrotizing pancreatitis without proven infection. Initiate carbapenems/fluoroquinolones only if infected necrosis suspected (gas on CT or positive aspirate)."

        # 6. Action Items
        actions = []
        if atlanta_cat == "Severe Acute Pancreatitis":
            actions.append("URGENT ICU ADMISSION: Persistent organ failure detected. Intensivist consultation.")
        if marshall_res.has_organ_failure:
            for sys_fail in marshall_res.organ_failure_systems:
                actions.append(f"ORGAN FAILURE ESCALATION: {sys_fail}")
        if bisap_res.total_score >= 3:
            actions.append(f"HIGH MORTALITY RISK: BISAP Score {bisap_res.total_score} (predicted mortality {bisap_res.mortality_risk_pct}%). Frequent vital signs q1h.")
        if bolus:
            actions.append("FLUID RESUSCITATION: Administer 20 mL/kg IV Lactated Ringer's bolus over 30-60 min, then 250 mL/h.")
        if sirs_present:
            actions.append(f"SIRS PROTOCOL: {sirs_count}/4 SIRS criteria met. Monitor for persistent SIRS at 24h & 48h.")

        return ComprehensivePancreatitisAssessment(
            patient_id=patient_id,
            atlanta_classification=atlanta_res,
            bisap=bisap_res,
            modified_marshall=marshall_res,
            sirs_criteria_count=sirs_count,
            sirs_present=sirs_present,
            fluid_guidelines=fluid_guidelines,
            nutrition_guideline=nutrition,
            antibiotic_guideline=antibiotics,
            action_items=actions,
        )
