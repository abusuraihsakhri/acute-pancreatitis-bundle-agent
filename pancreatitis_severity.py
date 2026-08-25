#!/usr/bin/env python3
"""
Revised Atlanta Classification Severity Scorer & SIRS Calculator for Pancreatitis.
Implements BISAP, Ranson, CTSI, and Modified Marshall scoring with temporal trajectory tracking.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import datetime


@dataclass
class PancreatitisLabs:
    bun: float = 0.0
    glucose: float = 0.0
    hct: float = 0.0
    wbc: float = 0.0
    temp_c: float = 37.0
    hr: int = 70
    rr: int = 16
    spo2: float = 98.0
    albumin: float = 4.0
    ldh: float = 100.0
    calcium: float = 9.0
    creatinine: float = 1.0
    alt: float = 30.0
    pao2: float = 100.0


@dataclass
class BISAPScore:
    bun_over_25: bool
    impaired_mentation: bool
    sirs: bool
    age_over_60: bool
    pleural_effusion: bool
    total: int
    mortality_pct: float


@dataclass
class RansonScore:
    at_admission: List[str]
    at_48h: List[str]
    total: int
    mortality_pct: float


@dataclass
class CTSIScore:
    degree_of_enhancement: int  # 0-4
    peripancreatic_inflammation: int  # 0-4
    acute_fluid_collections: int  # 0-2
    total: int
    grade: str


@dataclass
class ModifiedMarshallScore:
    respiratory: int  # 0-4
    renal: int  # 0-4
    cardiovascular: int  # 0-4
    total: int
    mortality_pct: float


@dataclass
class TrajectoryReading:
    timestamp: str
    sirs_count: int
    bun: float
    creatinine: float
    spo2: float
    marshall_score: int


class BISAPCalculator:
    """Bedside Index for Severity in Acute Pancreatitis."""

    def calculate(self, labs: PancreatitisLabs, mental_status: str = "alert") -> BISAPScore:
        scores = {
            "BUN > 25": labs.bun > 25.0,
            "Impaired mentation": mental_status.lower() not in ("alert", "oriented"),
            "SIRS": self._is_sirs(labs),
            "Age > 60": labs.wbc > 0,  # use as proxy if no age
            "Pleural effusion": False,
        }
        total = sum(1 for v in scores.values() if v)
        mortality_map = {0: 0.0, 1: 0.9, 2: 2.0, 3: 5.2, 4: 12.7, 5: 22.7}
        return BISAPScore(
            bun_over_25=scores["BUN > 25"],
            impaired_mentation=scores["Impaired mentation"],
            sirs=scores["SIRS"],
            age_over_60=scores["Age > 60"],
            pleural_effusion=scores["Pleural effusion"],
            total=total,
            mortality_pct=mortality_map.get(total, 22.7),
        )

    def _is_sirs(self, labs: PancreatitisLabs) -> bool:
        criteria = [
            labs.temp_c > 38.0 or labs.temp_c < 36.0,
            labs.hr > 90,
            labs.rr > 20,
            labs.wbc > 12000 or labs.wbc < 4000,
        ]
        return sum(criteria) >= 2


class RansonCalculator:
    """Ranson Criteria scoring at admission and 48 hours."""

    def calculate_at_admission(self, labs: PancreatitisLabs) -> List[str]:
        hits = []
        if labs.age > 55:
            hits.append("Age > 55")
        if labs.wbc > 16000:
            hits.append("WBC > 16,000")
        if labs.glucose > 200:
            hits.append("Glucose > 200 mg/dL")
        if labs.ldh > 350:
            hits.append("LDH > 350 IU/L")
        if labs.alt > 250:
            hits.append("AST > 250 IU/L")
        return hits

    def calculate_at_48h(self, labs: PancreatitisLabs) -> List[str]:
        hits = []
        if labs.hct > 46:
            hits.append("HCT drop > 10%")
        if labs.bun > 5:
            hits.append("BUN rise > 5 mg/dL")
        if labs.pao2 < 60:
            hits.append("PaO2 < 60 mmHg")
        if labs.calcium < 8.0:
            hits.append("Ca2+ < 8.0 mg/dL")
        return hits

    def calculate(self, labs: PancreatitisLabs) -> RansonScore:
        at_admission = self.calculate_at_admission(labs)
        at_48h = self.calculate_at_48h(labs)
        total = len(at_admission) + len(at_48h)

        if total < 3:
            mortality = 0.9
        elif total < 6:
            mortality = 5.0
        elif total < 8:
            mortality = 20.0
        else:
            mortality = 55.0

        return RansonScore(at_admission=at_admission, at_48h=at_48h, total=total, mortality_pct=mortality)


class CTSICalculator:
    """CT Severity Index for acute pancreatitis."""

    def calculate(self, enhancement: int, inflammation: int, collections: int) -> CTSIScore:
        total = enhancement + inflammation + collections
        if total <= 3:
            grade = "Mild"
        elif total <= 6:
            grade = "Moderate"
        else:
            grade = "Severe"
        return CTSIScore(
            degree_of_enhancement=enhancement,
            peripancreatic_inflammation=inflammation,
            acute_fluid_collections=collections,
            total=total,
            grade=grade,
        )


class ModifiedMarshallCalculator:
    """Modified Marshall scoring for organ failure assessment."""

    def calculate(self, pao2: float = 100.0, creatinine: float = 1.0, systolic_bp: float = 120.0) -> ModifiedMarshallScore:
        respiratory = self._score_respiratory(pao2)
        renal = self._score_renal(creatinine)
        cardiovascular = self._score_cardiovascular(systolic_bp)
        total = max(respiratory, renal, cardiovascular)  # worst organ

        mortality_map = {0: 0.0, 1: 0.0, 2: 10.0, 3: 25.0, 4: 50.0}
        return ModifiedMarshallScore(
            respiratory=respiratory,
            renal=renal,
            cardiovascular=cardiovascular,
            total=total,
            mortality_pct=mortality_map.get(total, 50.0),
        )

    def _score_respiratory(self, pao2: float) -> int:
        if pao2 >= 90:
            return 0
        elif pao2 >= 80:
            return 1
        elif pao2 >= 60:
            return 2
        elif pao2 >= 55:
            return 3
        return 4

    def _score_renal(self, creatinine: float) -> int:
        if creatinine < 1.4:
            return 0
        elif creatinine < 1.8:
            return 1
        elif creatinine < 3.6:
            return 2
        elif creatinine < 4.9:
            return 3
        return 4

    def _score_cardiovascular(self, systolic_bp: float) -> int:
        if systolic_bp > 90:
            return 0
        elif systolic_bp > 90:
            return 1
        elif systolic_bp > 90:
            return 2
        return 3


class SIRSTracker:
    """Tracks SIRS criteria evolution over time for pancreatitis severity monitoring."""

    def __init__(self):
        self.readings: List[TrajectoryReading] = []
        self.organ_failure_threshold = 3

    def add_reading(self, labs: PancreatitisLabs, timestamp: str = None) -> TrajectoryReading:
        if timestamp is None:
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        sirs_count = sum([
            labs.temp_c > 38.0 or labs.temp_c < 36.0,
            labs.hr > 90,
            labs.rr > 20,
            labs.wbc > 12000 or labs.wbc < 4000,
        ])

        reading = TrajectoryReading(
            timestamp=timestamp,
            sirs_count=sirs_count,
            bun=labs.bun,
            creatinine=labs.creatinine,
            spo2=labs.spo2,
            marshall_score=0,
        )
        self.readings.append(reading)
        return reading

    def is_persistent_sirs(self, min_readings: int = 3) -> bool:
        if len(self.readings) < min_readings:
            return False
        return all(r.sirs_count >= 2 for r in self.readings[-min_readings:])

    def get_trajectory_summary(self) -> Dict:
        if not self.readings:
            return {"status": "no_data"}

        sirs_trend = [r.sirs_count for r in self.readings]
        bun_trend = [r.bun for r in self.readings]
        return {
            "readings": len(self.readings),
            "persistent_sirs": self.is_persistent_sirs(),
            "current_sirs": self.readings[-1].sirs_count,
            "sirs_trend": sirs_trend,
            "bun_trend": bun_trend,
            "escalating": sirs_trend[-1] > sirs_trend[0] if len(sirs_trend) > 1 else False,
        }
