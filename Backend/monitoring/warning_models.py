from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


WarningLevel = Literal["green", "yellow", "orange", "red"]
WarningStatus = Literal["open", "acknowledged", "resolved"]


class ThresholdProfile(BaseModel):
    stage_id: str
    stage_title: str
    duration: str
    parameter: str
    minimum: float
    maximum: float
    unit: str
    weight: float
    version: str
    validated: bool
    source_note: str


class WarningEvidence(BaseModel):
    parameter: str
    status: str
    latest: Optional[float] = None
    minimum: float
    maximum: float
    unit: str
    samples: int
    percent_outside_range: float
    consecutive_minutes: float
    hours_low: float
    hours_high: float
    trend_per_hour: Optional[float] = None
    risk_points: float
    threshold_validated: bool


class WarningEvaluation(BaseModel):
    device_id: str
    stage_id: str
    evaluated_at: float
    window_hours: int
    sample_count: int
    valid_sample_percent: float
    warning_score: int
    warning_level: WarningLevel
    summary: str
    recommendations: List[str] = Field(default_factory=list)
    evidence: List[WarningEvidence] = Field(default_factory=list)
    event_id: Optional[int] = None


class WarningEvent(BaseModel):
    id: int
    device_id: str
    plot_id: Optional[str] = None
    crop_cycle_id: Optional[str] = None
    stage_id: str
    warning_type: str
    warning_level: WarningLevel
    warning_score: int
    status: WarningStatus
    summary: str
    recommendations: List[str]
    evidence: List[Dict[str, object]]
    opened_at: float
    updated_at: float
    acknowledged_at: Optional[float] = None
    resolved_at: Optional[float] = None
    resolution_note: Optional[str] = None


class WarningActionRequest(BaseModel):
    note: Optional[str] = Field(default=None, max_length=500)
