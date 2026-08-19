from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Reading(BaseModel):
    timestamp: Optional[float] = Field(default=None, description="Unix timestamp in seconds")
    humidity: Optional[float] = None
    temperature_c: Optional[float] = None
    heat_index_c: Optional[float] = None
    soil_moisture: Optional[float] = None
    soil_analog: Optional[float] = None
    soil_temperature_c: Optional[float] = None
    ec: Optional[float] = None
    quality_status: Optional[str] = None
    calibration_version: Optional[str] = None
    source: Optional[str] = None


class SummaryStats(BaseModel):
    avg: Dict[str, Optional[float]]
    min: Dict[str, Optional[float]]
    max: Dict[str, Optional[float]]
    trend: Dict[str, Optional[float]]
    count: int


class SensorQualityResult(BaseModel):
    status: str
    issues: List[str] = Field(default_factory=list)
    valid_field_count: int
    total_field_count: int


class ParameterWindowStats(BaseModel):
    latest: Optional[float] = None
    avg: Optional[float] = None
    min: Optional[float] = None
    max: Optional[float] = None
    trend_per_hour: Optional[float] = None
    samples: int = 0
    hours_low: float = 0
    hours_high: float = 0
    percent_in_range: Optional[float] = None
    status: str = "unknown"
    unit: str = ""


class SensorWindowAnalysis(BaseModel):
    stage_id: str
    window_start: Optional[float] = None
    window_end: Optional[float] = None
    sample_count: int
    valid_sample_percent: float
    warning_score: int
    warning_level: str
    parameters: Dict[str, ParameterWindowStats]
    contributing_factors: List[Dict[str, object]] = Field(default_factory=list)


class StageEvaluationRequest(BaseModel):
    stage_id: str
    flags: Dict[str, bool] = Field(default_factory=dict)
    reading: Optional[Reading] = None


class StageEvaluationResponse(BaseModel):
    stage: Dict[str, object]
    readings: Dict[str, Optional[float]]
    statuses: Dict[str, str]
    alerts: List[Dict[str, str]]


class StageDecisionRequest(BaseModel):
    expected_stage: Optional[str] = None
    ai_stage: Optional[str] = None
    reading: Optional[Reading] = None


class GerminationAnalysisRequest(BaseModel):
    plant_age_days: int = Field(..., ge=1, le=21, description="Plant age during the germination window")
    leaf_prediction: int = Field(..., ge=0, le=1, description="Binary leaf output from the trained model: 0 or 1")


class GerminationAnalysisResponse(BaseModel):
    day_number: int
    stage_id: str
    stage_label: str
    stage_window: str
    leaf_prediction: int
    leaf_status: str
    expected_leaf_by_day7: bool
    status: str
    message: str
    recommendation: str


class GrowthStagePredictionResponse(BaseModel):
    predicted_stage: Optional[str] = None
    confidence: float = Field(..., ge=0, le=1)
    decision: str
    accepted: bool
    requires_confirmation: bool
    message: str
    model_name: str
    model_version: str
    classes: List[str]
    probabilities: Dict[str, float]
    leaf_prediction: int = Field(..., ge=0, le=1)


class StageDecisionResponse(BaseModel):
    stage: Optional[str]
    status: str
    recommendation: Optional[str] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    moisture: Optional[float] = None
    ec: Optional[float] = None


class AiAlertRequest(BaseModel):
    stage_id: str
    readings: Dict[str, Optional[float]]
    statuses: Dict[str, str] = Field(default_factory=dict)
    history: List[Dict[str, Optional[float]]] = Field(default_factory=list)


class AiAlertResponse(BaseModel):
    risk_score: int
    anomaly_detected: bool
    summary: str
    recommendation: str
    anomalies: List[str] = Field(default_factory=list)


class AiAskRequest(BaseModel):
    question: str


class AiAskResponse(BaseModel):
    answer: str
