import time
from typing import Dict, List, Optional
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from . import service as monitoring_service
from .ai_model import predict_growth_stage
from .data_models import (
    AggregationResponse,
    CanonicalSensorPayload,
    DeviceStatus,
    IngestionResult,
    MonitoringSetupRequest,
)
from .data_service import (
    aggregate_readings,
    canonical_to_reading,
    get_monitoring_setup,
    legacy_to_canonical,
    list_device_statuses,
    register_monitoring_setup,
    store_five_minute_payload,
)
from .warning_models import ThresholdProfile, WarningActionRequest, WarningEvaluation, WarningEvent
from .warning_service import (
    change_warning_status,
    evaluate_warnings,
    list_stages_from_db,
    list_threshold_profiles,
    list_warning_events,
)

from .models import (
    AiAlertRequest,
    AiAlertResponse,
    AiAskRequest,
    AiAskResponse,
    GerminationAnalysisRequest,
    GerminationAnalysisResponse,
    GrowthStagePredictionResponse,
    Reading,
    SensorQualityResult,
    SensorWindowAnalysis,
    StageDecisionRequest,
    StageDecisionResponse,
    StageEvaluationRequest,
    StageEvaluationResponse,
    SummaryStats
)
from .service import (
    STAGES,
    analyze_sensor_window,
    analyze_germination_image,
    call_gemini_alerts,
    call_gemini_ask,
    compute_summary,
    evaluate_germination_analysis,
    evaluate_stage_decision,
    evaluate_stage_logic,
    fetch_firebase_reading,
    fetch_readings,
    fetch_readings_chrono,
    fetch_firebase_history,
    generate_report,
    generate_firebase_report,
    ingest_firebase_reading,
    validate_reading_quality
)

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


@router.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok", "module": "monitoring"}


@router.post("/readings", response_model=IngestionResult)
def store_reading(reading: Reading) -> IngestionResult:
    reading.source = reading.source or "api"
    payload = legacy_to_canonical(
        reading,
        device_id=monitoring_service.DEFAULT_DEVICE_ID,
        plot_id=monitoring_service.DEFAULT_PLOT_ID,
        crop_cycle_id=monitoring_service.DEFAULT_CROP_CYCLE_ID,
        plant_id=monitoring_service.DEFAULT_PLANT_ID,
    )
    quality = validate_reading_quality(reading)
    return store_five_minute_payload(
        monitoring_service.DB_PATH,
        payload,
        quality.status,
        quality.issues,
    )


@router.post("/setup")
def configure_monitoring(setup: MonitoringSetupRequest) -> Dict[str, object]:
    try:
        return register_monitoring_setup(monitoring_service.DB_PATH, setup)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/setup")
def monitoring_setup() -> Dict[str, List[Dict[str, object]]]:
    return get_monitoring_setup(monitoring_service.DB_PATH)


@router.post("/ingest", response_model=IngestionResult)
def ingest_canonical_payload(payload: CanonicalSensorPayload) -> IngestionResult:
    reading = canonical_to_reading(payload)
    quality = validate_reading_quality(reading)
    try:
        return store_five_minute_payload(
            monitoring_service.DB_PATH,
            payload,
            quality.status,
            quality.issues,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/readings/validate", response_model=SensorQualityResult)
def validate_reading(reading: Reading) -> SensorQualityResult:
    return validate_reading_quality(reading)


@router.post("/readings/firebase")
def store_firebase_reading() -> Dict[str, float]:
    timestamp = ingest_firebase_reading()
    return {"stored_at": timestamp}


@router.get("/readings/latest")
def latest_reading() -> Dict[str, object]:
    rows = fetch_readings(limit=1)
    if not rows:
        raise HTTPException(status_code=404, detail="No readings stored yet")

    return rows[0]


@router.get("/readings")
def list_readings(limit: int = 100, chronological: bool = False) -> List[Dict[str, object]]:
    if limit < 1 or limit > 10000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 10000")
    if chronological:
        rows = fetch_readings(limit=limit)
        rows.reverse()
        return rows
    return fetch_readings(limit=limit)


@router.get("/analytics/summary", response_model=SummaryStats)
def summary(minutes: int = 30) -> SummaryStats:
    since = time.time() - minutes * 60
    rows = fetch_readings(limit=1000, since=since)
    return compute_summary(rows)


@router.get("/analytics/window", response_model=SensorWindowAnalysis)
def sensor_window(stage_id: str = "stage1", hours: int = 24) -> SensorWindowAnalysis:
    if hours < 1 or hours > 24 * 31:
        raise HTTPException(status_code=400, detail="hours must be between 1 and 744")
    if not any(stage["id"] == stage_id for stage in STAGES):
        raise HTTPException(status_code=400, detail="Unknown stage_id")
    rows = fetch_readings_chrono(limit=10000, since=time.time() - hours * 3600)
    return analyze_sensor_window(rows, stage_id)


@router.get("/analytics/aggregate", response_model=AggregationResponse)
def aggregated_history(
    interval: str = "hour",
    hours: int = 24 * 7,
    device_id: Optional[str] = None,
) -> AggregationResponse:
    if interval not in {"hour", "day"}:
        raise HTTPException(status_code=400, detail="interval must be 'hour' or 'day'")
    if hours < 1 or hours > 24 * 366:
        raise HTTPException(status_code=400, detail="hours must be between 1 and 8784")
    return aggregate_readings(
        monitoring_service.DB_PATH,
        interval=interval,
        since=time.time() - hours * 3600,
        device_id=device_id,
    )


@router.get("/devices/status", response_model=List[DeviceStatus])
def device_statuses() -> List[DeviceStatus]:
    return list_device_statuses(monitoring_service.DB_PATH)


@router.get("/analytics/summary/firebase", response_model=SummaryStats)
def summary_firebase(limit: int = 500) -> SummaryStats:
    rows = fetch_firebase_history(limit=limit, chronological=False)
    if not rows:
        raise HTTPException(status_code=404, detail="No Firebase history data available")
    return compute_summary(rows)


@router.get("/analytics/history/firebase")
def history_firebase(limit: int = 200, chronological: bool = True) -> List[Dict[str, Optional[float]]]:
    rows = fetch_firebase_history(limit=limit, chronological=chronological)
    if not rows:
        raise HTTPException(status_code=404, detail="No Firebase history data available")
    return rows


@router.get("/stages")
def list_stages() -> List[Dict[str, object]]:
    return list_stages_from_db(monitoring_service.DB_PATH)


@router.get("/thresholds", response_model=List[ThresholdProfile])
def threshold_profiles(stage_id: Optional[str] = None) -> List[ThresholdProfile]:
    profiles = list_threshold_profiles(monitoring_service.DB_PATH, stage_id)
    if stage_id and not profiles:
        raise HTTPException(status_code=404, detail="Threshold profile not found")
    return profiles


@router.post("/warnings/evaluate", response_model=WarningEvaluation)
def evaluate_sensor_warnings(
    device_id: str = monitoring_service.DEFAULT_DEVICE_ID,
    stage_id: str = "stage1",
    window_hours: int = 24,
) -> WarningEvaluation:
    if window_hours < 1 or window_hours > 24 * 31:
        raise HTTPException(status_code=400, detail="window_hours must be between 1 and 744")
    try:
        return evaluate_warnings(
            monitoring_service.DB_PATH,
            device_id=device_id,
            stage_id=stage_id,
            window_hours=window_hours,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.get("/warnings", response_model=List[WarningEvent])
def warning_history(status: Optional[str] = None, device_id: Optional[str] = None) -> List[WarningEvent]:
    if status and status not in {"open", "acknowledged", "resolved"}:
        raise HTTPException(status_code=400, detail="Invalid warning status")
    return list_warning_events(monitoring_service.DB_PATH, status=status, device_id=device_id)


@router.post("/warnings/{event_id}/acknowledge", response_model=WarningEvent)
def acknowledge_warning(event_id: int, request: WarningActionRequest) -> WarningEvent:
    try:
        return change_warning_status(monitoring_service.DB_PATH, event_id, "acknowledge", request.note)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/warnings/{event_id}/resolve", response_model=WarningEvent)
def resolve_warning(event_id: int, request: WarningActionRequest) -> WarningEvent:
    try:
        return change_warning_status(monitoring_service.DB_PATH, event_id, "resolve", request.note)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@router.post("/analytics/stage/evaluate", response_model=StageEvaluationResponse)
def evaluate_stage(request: StageEvaluationRequest) -> StageEvaluationResponse:
    if request.reading is None:
        rows = fetch_readings(limit=1)
        if not rows:
            raise HTTPException(status_code=404, detail="No readings stored yet")
        reading = Reading(**rows[0])
    else:
        reading = request.reading

    return evaluate_stage_logic(request.stage_id, reading, request.flags)


@router.post("/analytics/stage/decision", response_model=StageDecisionResponse)
def stage_decision(request: StageDecisionRequest) -> StageDecisionResponse:
    if request.reading is None:
        rows = fetch_readings(limit=1)
        if not rows:
            raise HTTPException(status_code=404, detail="No readings stored yet")
        reading = Reading(**rows[0])
    else:
        reading = request.reading

    return evaluate_stage_decision(request.expected_stage, request.ai_stage, reading)


@router.post("/analytics/germination/evaluate", response_model=GerminationAnalysisResponse)
def germination_evaluation(request: GerminationAnalysisRequest) -> GerminationAnalysisResponse:
    return evaluate_germination_analysis(request)


@router.post("/analytics/germination/analyze", response_model=GerminationAnalysisResponse)
def germination_image_analysis(
    plant_age_days: int = Form(..., ge=1, le=21),
    image: UploadFile = File(...)
) -> GerminationAnalysisResponse:
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")

    suffix = Path(image.filename or "").suffix or ".jpg"
    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            temp_file.write(image.file.read())

        return analyze_germination_image(plant_age_days, temp_path)
    except (FileNotFoundError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    finally:
        image.file.close()
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


@router.post("/analytics/growth-stage/analyze", response_model=GrowthStagePredictionResponse)
def growth_stage_image_analysis(
    image: UploadFile = File(...)
) -> GrowthStagePredictionResponse:
    """Classify a standardized whole-plant image using the trained Phase 3 model."""
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file must be an image")

    suffix = Path(image.filename or "").suffix or ".jpg"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            temp_file.write(image.file.read())
        return GrowthStagePredictionResponse(**predict_growth_stage(temp_path))
    except (FileNotFoundError, RuntimeError) as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    except (OSError, ValueError) as error:
        raise HTTPException(status_code=400, detail=f"Invalid image or model output: {error}") from error
    finally:
        image.file.close()
        if temp_path:
            Path(temp_path).unlink(missing_ok=True)


@router.post("/ai/alerts", response_model=AiAlertResponse)
def ai_alerts(request: AiAlertRequest) -> AiAlertResponse:
    return call_gemini_alerts(request)


@router.post("/ai/ask", response_model=AiAskResponse)
def ai_ask(request: AiAskRequest) -> AiAskResponse:
    return call_gemini_ask(request)


@router.get("/report/pdf")
def report(minutes: int = 60, limit: int = 500) -> StreamingResponse:
    return generate_report(minutes=minutes, limit=limit)


@router.get("/report/firebase/pdf")
def report_firebase(limit: int = 500) -> StreamingResponse:
    return generate_firebase_report(limit=limit)
