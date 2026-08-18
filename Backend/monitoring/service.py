import asyncio
import io
import json
import math
import os
import sqlite3
import time
from datetime import datetime
from contextlib import closing
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import httpx
import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image

from .ai_model import predict_leaf_presence
from .data_models import CanonicalSensorPayload, SensorValues
from .data_service import (
    build_default_setup,
    canonical_to_reading,
    init_phase1_db,
    register_monitoring_setup,
    store_five_minute_payload,
)
from .models import (
    AiAlertRequest,
    AiAlertResponse,
    AiAskRequest,
    AiAskResponse,
    GerminationAnalysisRequest,
    GerminationAnalysisResponse,
    Reading,
    SensorQualityResult,
    SensorWindowAnalysis,
    StageDecisionResponse,
    StageEvaluationResponse,
    SummaryStats
)
from .warning_service import init_warning_db, list_stages_from_db

DB_PATH = os.environ.get("IOT_DB_PATH", "iot_readings.db")
FIREBASE_URL = os.environ.get(
    "FIREBASE_URL",
    "https://sensorsdata-dd238-default-rtdb.asia-southeast1.firebasedatabase.app"
)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
FIREBASE_POLL_SECONDS = float(os.environ.get("FIREBASE_POLL_SECONDS", "30"))
DEFAULT_DEVICE_ID = os.environ.get("MONITORING_DEVICE_ID", "device-001")
DEFAULT_PLOT_ID = os.environ.get("MONITORING_PLOT_ID", "plot-001")
DEFAULT_CROP_CYCLE_ID = os.environ.get("MONITORING_CROP_CYCLE_ID", "cycle-001")
DEFAULT_PLANT_ID = os.environ.get("MONITORING_PLANT_ID")
DEFAULT_PLANTING_DATE = os.environ.get("MONITORING_PLANTING_DATE", "2026-08-17")

_poller_task: Optional[asyncio.Task] = None

SENSOR_FIELDS = [
    "humidity",
    "temperature_c",
    "heat_index_c",
    "soil_moisture",
    "soil_analog",
    "soil_temperature_c",
    "ec"
]

# Physical plausibility limits. Agronomic target ranges are stage-specific and
# intentionally kept separate from these validation limits.
SENSOR_VALID_RANGES = {
    "humidity": (0.0, 100.0),
    "temperature_c": (-10.0, 60.0),
    "heat_index_c": (-10.0, 80.0),
    "soil_moisture": (0.0, 100.0),
    "soil_analog": (0.0, 4095.0),
    "soil_temperature_c": (-10.0, 60.0),
    "ec": (0.0, 20.0)
}

# DHT22 air-temperature rules (all stages):
# - 25-30C optimal
# - below 20C slow growth
# - above 35C heat stress
AIR_TEMP_THRESHOLD = {"min": 25, "max": 30, "unit": "C"}

STAGES = [
    {
        "id": "stage1",
        "title": "Germination",
        "duration": "7-21 days",
        "dry_threshold": 1000,
        "thresholds": {
            "soil_moisture": {"min": 1000, "max": 2000, "unit": "analog"},
            "soil_temp": {"min": 25, "max": 30, "unit": "C"},
            "air_humidity": {"min": 70, "max": 85, "unit": "%"},
            "air_temp": dict(AIR_TEMP_THRESHOLD),
            "ec": {"min": 0.5, "max": 1.2, "unit": "mS/cm"}
        },
        "flags": ["slow_growth"]
    },
    {
        "id": "stage2",
        "title": "Seedling",
        "duration": "2-4 weeks",
        "dry_threshold": 1000,
        "thresholds": {
            "soil_moisture": {"min": 1200, "max": 2200, "unit": "analog"},
            "soil_temp": {"min": 22, "max": 28, "unit": "C"},
            "air_humidity": {"min": 60, "max": 75, "unit": "%"},
            "air_temp": dict(AIR_TEMP_THRESHOLD),
            "ec": {"min": 0.8, "max": 1.5, "unit": "mS/cm"}
        },
        "flags": ["slow_growth"]
    },
    {
        "id": "stage3",
        "title": "Vegetative",
        "duration": "4-8 weeks",
        "dry_threshold": 1000,
        "thresholds": {
            "soil_moisture": {"min": 1500, "max": 2500, "unit": "analog"},
            "soil_temp": {"min": 20, "max": 28, "unit": "C"},
            "air_humidity": {"min": 50, "max": 70, "unit": "%"},
            "air_temp": dict(AIR_TEMP_THRESHOLD),
            "ec": {"min": 1.5, "max": 2.5, "unit": "mS/cm"}
        },
        "flags": ["slow_growth"]
    },
    {
        "id": "stage4",
        "title": "Flowering",
        "duration": "2-3 weeks",
        "dry_threshold": 1000,
        "thresholds": {
            "soil_moisture": {"min": 1200, "max": 2000, "unit": "analog"},
            "soil_temp": {"min": 20, "max": 26, "unit": "C"},
            "air_humidity": {"min": 50, "max": 65, "unit": "%"},
            "air_temp": dict(AIR_TEMP_THRESHOLD),
            "ec": {"min": 1.5, "max": 2.2, "unit": "mS/cm"}
        },
        "flags": ["no_flower_development", "no_fruit_set"]
    },
    {
        "id": "stage5",
        "title": "Fruiting & Ripening",
        "duration": "3-6 weeks",
        "dry_threshold": 1000,
        "thresholds": {
            "soil_moisture": {"min": 1500, "max": 2500, "unit": "analog"},
            "soil_temp": {"min": 20, "max": 26, "unit": "C"},
            "air_humidity": {"min": 45, "max": 65, "unit": "%"},
            "air_temp": dict(AIR_TEMP_THRESHOLD),
            "ec": {"min": 1.2, "max": 2.0, "unit": "mS/cm"}
        },
        "flags": ["slow_ripening"]
    }
]

STAGE_LABELS = {
    "stage1": "Germination",
    "stage1a": "Early Germination",
    "stage1b": "Leaf Emergence",
    "stage1c": "Established Germination",
    "stage2": "Seedling",
    "stage3": "Vegetative Growth",
    "stage4": "Flowering",
    "stage5": "Fruiting & Ripening"
}

STAGE_LABEL_ALIASES = {
    "stage1": "stage1",
    "germination": "stage1",
    "germination stage": "stage1",
    "early germination": "stage1",
    "leaf emergence": "stage1",
    "established germination": "stage1",
    "stage2": "stage2",
    "seedling": "stage2",
    "seedling stage": "stage2",
    "stage3": "stage3",
    "vegetative": "stage3",
    "vegetative growth": "stage3",
    "vegetative growth stage": "stage3",
    "stage4": "stage4",
    "flowering": "stage4",
    "flowering stage": "stage4",
    "stage5": "stage5",
    "fruiting": "stage5",
    "ripening": "stage5",
    "fruiting & ripening": "stage5",
    "fruiting and ripening": "stage5",
    "fruiting stage": "stage5"
}


def get_stage(stage_id: str) -> Dict[str, object]:
    try:
        stages = list_stages_from_db(DB_PATH)
    except sqlite3.Error:
        stages = []
    source = stages or STAGES
    return next((stage for stage in source if stage["id"] == stage_id), source[0])


def normalize_stage_key(stage: Optional[str]) -> Optional[str]:
    if not stage:
        return None

    key = stage.strip().lower()
    return STAGE_LABEL_ALIASES.get(key)


def classify_germination_window(plant_age_days: int, leaf_prediction: int) -> GerminationAnalysisResponse:
    leaf_detected = bool(leaf_prediction)

    if plant_age_days <= 3:
        stage_id = "stage1a"
        stage_label = STAGE_LABELS[stage_id]
        if leaf_detected:
            status = "Early Leaf Detected"
            message = "A leaf appeared very early in the germination window."
            recommendation = "Keep the medium evenly moist and continue monitoring for stable emergence."
        else:
            status = "On Track"
            message = "A leaf is usually not expected yet during the first 1-3 days."
            recommendation = "Maintain consistent moisture and warm conditions until the emergence window opens."

    elif plant_age_days <= 7:
        stage_id = "stage1b"
        stage_label = STAGE_LABELS[stage_id]
        if leaf_detected:
            status = "Leaf Emerged"
            message = "Leaf detection is consistent with a healthy 4-7 day germination window."
            recommendation = "Continue gentle watering and avoid stressing the young shoot."
        else:
            status = "Leaf Missing"
            message = "By day 7, a leaf should normally be visible."
            recommendation = "Check watering, seed viability, light exposure, and planting depth."

    else:
        stage_id = "stage1c"
        stage_label = STAGE_LABELS[stage_id]
        if leaf_detected:
            status = "Established"
            message = "Leaf presence is stable and the plant is moving beyond germination."
            recommendation = "Prepare for seedling care and keep the canopy evenly supported."
        else:
            status = "Delayed Germination"
            message = "Leaf is still missing in the 8-21 day window."
            recommendation = "Review seed quality, watering consistency, and field conditions immediately."

    return GerminationAnalysisResponse(
        day_number=plant_age_days,
        stage_id=stage_id,
        stage_label=stage_label,
        stage_window="1-3 days" if stage_id == "stage1a" else "4-7 days" if stage_id == "stage1b" else "8-21 days",
        leaf_prediction=int(leaf_detected),
        leaf_status="Leaf detected" if leaf_detected else "No leaf detected",
        expected_leaf_by_day7=plant_age_days >= 4,
        status=status,
        message=message,
        recommendation=recommendation
    )


def is_number(value: Optional[float]) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def validate_reading_quality(reading: Reading) -> SensorQualityResult:
    issues: List[str] = []
    valid_count = 0

    for field in SENSOR_FIELDS:
        value = getattr(reading, field)
        if value is None:
            continue
        if not is_number(value):
            issues.append(f"{field}:not_numeric")
            continue

        minimum, maximum = SENSOR_VALID_RANGES[field]
        if value < minimum or value > maximum:
            issues.append(f"{field}:out_of_physical_range")
            continue
        if field == "soil_analog" and value in {0, 4095}:
            issues.append("soil_analog:adc_rail_value")
            continue
        valid_count += 1

    if issues:
        status = "suspect"
    elif valid_count == 0:
        status = "missing"
    else:
        status = "valid"

    return SensorQualityResult(
        status=status,
        issues=issues,
        valid_field_count=valid_count,
        total_field_count=len(SENSOR_FIELDS)
    )


def range_status(value: Optional[float], range_def: Dict[str, float]) -> str:
    if not is_number(value):
        return "unknown"

    if value < range_def["min"]:
        return "low"

    if value > range_def["max"]:
        return "high"

    return "ok"


def normalize_reading(reading: Optional[Reading]) -> Dict[str, Optional[float]]:
    if not reading:
        return {
            "soil_analog": None,
            "soil_moisture": None,
            "soil_temp": None,
            "air_temp": None,
            "air_humidity": None,
            "ec": None
        }

    return {
        "soil_analog": reading.soil_analog,
        "soil_moisture": reading.soil_moisture,
        "soil_temp": reading.soil_temperature_c,
        "air_temp": reading.temperature_c,
        "air_humidity": reading.humidity,
        "ec": reading.ec
    }


def select_moisture(readings: Dict[str, Optional[float]]) -> Optional[float]:
    if is_number(readings.get("soil_moisture")):
        return readings["soil_moisture"]

    if is_number(readings.get("soil_analog")):
        return readings["soil_analog"]

    return None


def evaluate_stage_decision(
    expected_stage: Optional[str],
    ai_stage: Optional[str],
    reading: Optional[Reading]
) -> StageDecisionResponse:
    readings = normalize_reading(reading)
    moisture = select_moisture(readings)
    temp = readings.get("air_temp")
    humidity = readings.get("air_humidity")
    ec = readings.get("ec")

    expected_key = normalize_stage_key(expected_stage)
    ai_key = normalize_stage_key(ai_stage)
    stage_key = expected_key or ai_key
    stage_label = STAGE_LABELS.get(stage_key) if stage_key else None

    if stage_key is None:
        return StageDecisionResponse(
            stage=None,
            status="Stage Unknown",
            recommendation="Provide expected stage or AI stage to evaluate.",
            temperature=temp,
            humidity=humidity,
            moisture=moisture,
            ec=ec
        )

    status = "Growth Delay"
    recommendation = None

    def has_values(*values: Optional[float]) -> bool:
        return all(is_number(value) for value in values)

    if stage_key == "stage1":
        if not has_values(moisture, temp, humidity):
            status = "Insufficient Data"
            recommendation = "Check soil moisture, temperature, and humidity sensors."
        elif moisture >= 70 and moisture <= 85 and temp >= 25 and temp <= 30 and humidity >= 70:
            status = "Healthy Germination"
        elif is_number(temp) and temp > 35:
            status = "Heat Stress"
            recommendation = "Reduce heat stress. Use shade and improve ventilation."
        elif is_number(temp) and temp < 20:
            status = "Slow Growth"
            recommendation = "Maintain warmer environment. Air temperature is below 20C."
        elif moisture < 70:
            status = "Dry Soil"
            recommendation = "Increase irrigation."
        elif temp < 25:
            status = "Low Temperature"
            recommendation = "Maintain warmer environment toward 25-30C."
        else:
            status = "Growth Delay"

    elif stage_key == "stage2":
        if not has_values(moisture, temp, humidity):
            status = "Insufficient Data"
            recommendation = "Check soil moisture, temperature, and humidity sensors."
        elif moisture >= 65 and moisture <= 75 and temp >= 25 and temp <= 30:
            status = "Healthy Seedling"
        elif is_number(temp) and temp > 35:
            status = "Heat Stress"
            recommendation = "Reduce heat stress. Use shade and improve ventilation."
        elif is_number(temp) and temp < 20:
            status = "Slow Growth"
            recommendation = "Maintain warmer environment. Air temperature is below 20C."
        elif humidity < 65:
            status = "Low Humidity"
            recommendation = "Increase humidity level."
        elif moisture < 65:
            status = "Water Deficiency"
            recommendation = "Apply water carefully."
        else:
            status = "Weak Seedling Growth"

    elif stage_key == "stage3":
        if not has_values(moisture, temp, ec):
            status = "Insufficient Data"
            recommendation = "Check soil moisture, temperature, and EC sensors."
        elif moisture >= 60 and moisture <= 70 and ec >= 1.5 and temp >= 25 and temp <= 30:
            status = "Healthy Vegetative Growth"
        elif is_number(temp) and temp > 35:
            status = "Heat Stress"
            recommendation = "Reduce heat stress. Use shade and improve ventilation."
        elif is_number(temp) and temp < 20:
            status = "Slow Growth"
            recommendation = "Maintain warmer environment. Air temperature is below 20C."
        elif ec < 1.5:
            status = "Low Nutrient Level"
            recommendation = "Apply nitrogen fertilizer."
        elif moisture < 60:
            status = "Low Moisture"
            recommendation = "Increase irrigation."
        else:
            status = "Slow Vegetative Growth"

    elif stage_key == "stage4":
        if not has_values(temp, humidity):
            status = "Insufficient Data"
            recommendation = "Check temperature and humidity sensors."
        elif temp >= 25 and temp <= 30 and humidity >= 60 and humidity <= 70:
            status = "Healthy Flowering"
        elif is_number(temp) and temp > 35:
            status = "Heat Stress"
            recommendation = "Reduce heat stress. Use shade and improve ventilation."
        elif is_number(temp) and temp < 20:
            status = "Slow Growth"
            recommendation = "Maintain warmer environment. Air temperature is below 20C."
        elif temp > 30:
            status = "Flower Drop Risk"
            recommendation = "Reduce heat stress."
        elif humidity < 60:
            status = "Dry Environment"
            recommendation = "Increase humidity."
        else:
            status = "Poor Flower Development"

    elif stage_key == "stage5":
        if not has_values(moisture, temp, ec):
            status = "Insufficient Data"
            recommendation = "Check soil moisture, temperature, and EC sensors."
        elif moisture >= 50 and moisture <= 65 and ec >= 2.0 and temp >= 25 and temp <= 30:
            status = "Healthy Fruiting"
        elif is_number(temp) and temp > 35:
            status = "Heat Stress"
            recommendation = "Reduce heat stress. Use shade and improve ventilation."
        elif is_number(temp) and temp < 20:
            status = "Slow Growth"
            recommendation = "Maintain warmer environment. Air temperature is below 20C."
        elif ec < 2.0:
            status = "Low Nutrient Supply"
            recommendation = "Apply potassium fertilizer."
        elif moisture > 70:
            status = "Overwatering Risk"
            recommendation = "Reduce irrigation."
        else:
            status = "Poor Fruit Development"

    if expected_key and ai_key and expected_key != ai_key:
        status = "Growth Delay Detected"
        recommendation = "AI stage does not match expected stage. Review crop development."

    return StageDecisionResponse(
        stage=stage_label,
        status=status,
        recommendation=recommendation,
        temperature=temp,
        humidity=humidity,
        moisture=moisture,
        ec=ec
    )


def evaluate_stage_logic(stage_id: str, reading: Optional[Reading], flags: Dict[str, bool]) -> StageEvaluationResponse:
    stage = get_stage(stage_id)
    readings = normalize_reading(reading)
    thresholds = stage["thresholds"]

    moisture_value = (
        readings["soil_moisture"]
        if thresholds["soil_moisture"].get("unit") == "%"
        else readings["soil_analog"]
    )
    statuses = {
        "soil_moisture": range_status(moisture_value, thresholds["soil_moisture"]),
        "soil_temp": range_status(readings["soil_temp"], thresholds["soil_temp"]),
        "air_humidity": range_status(readings["air_humidity"], thresholds["air_humidity"]),
        "air_temp": range_status(readings["air_temp"], thresholds["air_temp"]),
        "ec": range_status(readings["ec"], thresholds["ec"])
    }

    alerts: List[Dict[str, str]] = []

    def push_alert(level: str, title: str, detail: str) -> None:
        alerts.append({"level": level, "title": title, "detail": detail})

    if is_number(readings["air_temp"]):
        if readings["air_temp"] > 35:
            push_alert("warning", "Heat Stress Warning", "Air temperature is above 35C. Crop heat stress risk is high.")
        elif 25 <= readings["air_temp"] <= 30:
            push_alert("info", "Optimal Air Temperature", "Air temperature is in the 25-30C optimal growth range.")
        elif readings["air_temp"] < 20:
            push_alert("warning", "Slow Growth Risk", "Air temperature is below 20C. Growth may slow down.")

    if is_number(moisture_value) and moisture_value < stage["dry_threshold"]:
        push_alert("alert", "Irrigation Required", "Soil moisture is below the dry-out threshold.")

    if stage["id"] == "stage1":
        if flags.get("slow_growth") and is_number(readings["soil_temp"]) and readings["soil_temp"] > 32:
            push_alert("warning", "Root Stress Warning", "Slow germination with high soil temperature.")
        if is_number(readings["air_humidity"]) and is_number(readings["air_temp"]) and readings["air_humidity"] > 90 and readings["air_temp"] > 30:
            push_alert("alert", "Disease Risk Alert", "High humidity and temperature increase damping-off risk.")

    if stage["id"] == "stage2":
        if flags.get("slow_growth") and is_number(readings["ec"]) and readings["ec"] < 0.8:
            push_alert("warning", "Fertiliser Needed", "Slow growth with low EC.")
        if is_number(readings["air_humidity"]) and is_number(readings["air_temp"]) and readings["air_humidity"] > 80 and readings["air_temp"] > 28:
            push_alert("alert", "Disease Risk Alert", "Humidity and temperature favor damping-off disease.")

    if stage["id"] == "stage1":
        if flags.get("slow_growth") and is_number(readings["soil_temp"]) and readings["soil_temp"] > 30:
            push_alert("warning", "Root Stress Warning", "Slow growth with high soil temperature.")

        if is_number(readings["air_humidity"]) and is_number(readings["air_temp"]) and readings["air_humidity"] > 90 and readings["air_temp"] > 30:
            push_alert("alert", "Disease Risk Alert", "High humidity and temperature increase damping-off risk.")

    if stage["id"] == "stage4":
        if flags.get("no_fruit_set") and is_number(readings["soil_temp"]) and readings["soil_temp"] > 28:
            push_alert("warning", "Root Stress Warning", "No fruit set with warm roots.")
        if flags.get("no_flower_development") and is_number(readings["ec"]) and readings["ec"] < 1.2:
            push_alert("warning", "Fertiliser Needed", "Low EC may delay flowering.")
        if is_number(readings["air_humidity"]) and is_number(readings["air_temp"]) and readings["air_humidity"] > 70 and readings["air_temp"] > 30:
            push_alert("alert", "Disease Risk Alert", "High humidity and temperature reduce pollination.")

    if stage["id"] == "stage5":
        if flags.get("slow_ripening") and is_number(readings["soil_temp"]) and readings["soil_temp"] > 28:
            push_alert("warning", "Root Stress Warning", "Slow ripening with warm roots.")
        if flags.get("slow_ripening") and is_number(readings["ec"]) and readings["ec"] < 1.0:
            push_alert("warning", "Fertiliser Needed", "Low EC may slow ripening.")
        if is_number(readings["air_humidity"]) and is_number(readings["air_temp"]) and readings["air_humidity"] > 75 and readings["air_temp"] > 30:
            push_alert("alert", "Disease Risk Alert", "High humidity risks botrytis.")

    all_normal = all(status == "ok" for status in statuses.values())
    if all_normal and not alerts:
        push_alert("ok", "Crop Growing Properly", "All parameters are within the optimal ranges.")

    return StageEvaluationResponse(
        stage=stage,
        readings=readings,
        statuses=statuses,
        alerts=alerts
    )


def heuristic_ai_alerts(request: AiAlertRequest) -> AiAlertResponse:
    status_values = [status for status in request.statuses.values() if status != "unknown"]
    high_count = sum(1 for status in status_values if status == "high")
    low_count = sum(1 for status in status_values if status == "low")

    risk_score = max(0, min(100, 20 + high_count * 18 + low_count * 12))
    anomalies: List[str] = []
    summary = "No anomalies detected in current readings."
    recommendation = "Maintain current schedule and keep monitoring."

    humidity = request.readings.get("air_humidity")
    soil = request.readings.get("soil_analog")
    if isinstance(humidity, (int, float)) and humidity > 80:
        recommendation = "Improve airflow and avoid excess moisture around young plants."

    stage = get_stage(request.stage_id)
    if isinstance(soil, (int, float)) and stage.get("dry_threshold") and soil < stage["dry_threshold"]:
        recommendation = "Soil is below dry threshold. Irrigation check recommended."

    return AiAlertResponse(
        risk_score=int(risk_score),
        anomaly_detected=False,
        summary=summary,
        recommendation=recommendation,
        anomalies=anomalies
    )


def evaluate_germination_analysis(request: GerminationAnalysisRequest) -> GerminationAnalysisResponse:
    return classify_germination_window(request.plant_age_days, request.leaf_prediction)


def analyze_germination_image(plant_age_days: int, image_path: str) -> GerminationAnalysisResponse:
    leaf_prediction = predict_leaf_presence(image_path)
    return classify_germination_window(plant_age_days, leaf_prediction)


def call_gemini_alerts(request: AiAlertRequest) -> AiAlertResponse:
    if not GEMINI_API_KEY:
        return heuristic_ai_alerts(request)

    stage = get_stage(request.stage_id)
    prompt = (
        "You are an agronomy AI assistant for Scotch Bonnet peppers. "
        "Do not provide disease diagnosis; focus on growth conditions, moisture, and stage progression. "
        "Return ONLY valid JSON with keys: risk_score (0-100 integer), "
        "anomaly_detected (boolean), anomalies (array of short strings), "
        "summary (string), recommendation (string). "
        "Use the stage thresholds, current readings, status labels, and history trend.\n\n"
        f"Stage: {stage}\n"
        f"Readings: {request.readings}\n"
        f"Statuses: {request.statuses}\n"
        f"History (latest first): {request.history[::-1]}\n"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2,
            "response_mime_type": "application/json"
        }
    }

    try:
        response = httpx.post(f"{GEMINI_URL}?key={GEMINI_API_KEY}", json=payload, timeout=20)
        response.raise_for_status()
    except httpx.HTTPError:
        return heuristic_ai_alerts(request)

    data = response.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError):
        return heuristic_ai_alerts(request)

    risk_score = int(max(0, min(100, parsed.get("risk_score", 0))))
    anomaly_detected = bool(parsed.get("anomaly_detected", False))
    summary = str(parsed.get("summary", ""))
    recommendation = str(parsed.get("recommendation", ""))
    anomalies = parsed.get("anomalies", [])
    if not isinstance(anomalies, list):
        anomalies = []

    return AiAlertResponse(
        risk_score=risk_score,
        anomaly_detected=anomaly_detected,
        summary=summary,
        recommendation=recommendation,
        anomalies=anomalies
    )


def call_gemini_ask(request: AiAskRequest) -> AiAskResponse:
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    if not GEMINI_API_KEY:
        return AiAskResponse(answer="AI key is not configured. Please try again later.")

    prompt = (
        "You are an agronomy assistant for Scotch Bonnet peppers in Sri Lanka. "
        "Answer the farmer's question concisely in 2-4 sentences."
        f"\n\nQuestion: {question}\n"
    )

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3
        }
    }

    try:
        response = httpx.post(f"{GEMINI_URL}?key={GEMINI_API_KEY}", json=payload, timeout=20)
        response.raise_for_status()
    except httpx.HTTPError:
        return AiAskResponse(answer="AI service is temporarily unavailable. Please try again.")

    data = response.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        return AiAskResponse(answer="AI response could not be parsed. Please try again.")

    return AiAskResponse(answer=str(text).strip())


def init_db() -> None:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                humidity REAL,
                temperature_c REAL,
                heat_index_c REAL,
                soil_moisture REAL,
                soil_analog REAL,
                soil_temperature_c REAL,
                ec REAL,
                quality_status TEXT,
                calibration_version TEXT,
                source TEXT
            )
            """
        )
        existing_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(readings)").fetchall()
        }
        for column_name, column_type in (
            ("quality_status", "TEXT"),
            ("calibration_version", "TEXT"),
            ("source", "TEXT")
        ):
            if column_name not in existing_columns:
                connection.execute(f"ALTER TABLE readings ADD COLUMN {column_name} {column_type}")
        connection.commit()
    init_phase1_db(DB_PATH)
    register_monitoring_setup(
        DB_PATH,
        build_default_setup(
            plot_id=DEFAULT_PLOT_ID,
            crop_cycle_id=DEFAULT_CROP_CYCLE_ID,
            device_id=DEFAULT_DEVICE_ID,
            planting_date=DEFAULT_PLANTING_DATE,
        ),
    )
    init_warning_db(DB_PATH, STAGES)


def row_to_dict(row: sqlite3.Row) -> Dict[str, object]:
    return {
        "timestamp": row["timestamp"],
        "humidity": row["humidity"],
        "temperature_c": row["temperature_c"],
        "heat_index_c": row["heat_index_c"],
        "soil_moisture": row["soil_moisture"],
        "soil_analog": row["soil_analog"],
        "soil_temperature_c": row["soil_temperature_c"],
        "ec": row["ec"],
        "quality_status": row["quality_status"],
        "calibration_version": row["calibration_version"],
        "source": row["source"],
        "device_id": row["device_id"],
        "plot_id": row["plot_id"],
        "crop_cycle_id": row["crop_cycle_id"],
        "plant_id": row["plant_id"],
        "bucket_start": row["bucket_start"],
        "received_at": row["received_at"],
        "quality_issues": json.loads(row["quality_issues"] or "[]"),
        "schema_version": row["schema_version"]
    }


def reading_to_dict(reading: Reading, timestamp: Optional[float] = None) -> Dict[str, Optional[float]]:
    return {
        "timestamp": timestamp if timestamp is not None else reading.timestamp,
        "humidity": reading.humidity,
        "temperature_c": reading.temperature_c,
        "heat_index_c": reading.heat_index_c,
        "soil_moisture": reading.soil_moisture,
        "soil_analog": reading.soil_analog,
        "soil_temperature_c": reading.soil_temperature_c,
        "ec": reading.ec,
        "quality_status": reading.quality_status,
        "calibration_version": reading.calibration_version,
        "source": reading.source
    }


def parse_firebase_history_items(payload: Dict[str, object]) -> List[Dict[str, object]]:
    candidates = [
        payload.get("history"),
        payload.get("readings"),
        payload.get("sensorData"),
        payload.get("data")
    ]

    items: List[Dict[str, object]] = []
    for candidate in candidates:
        if isinstance(candidate, list):
            items = [entry for entry in candidate if isinstance(entry, dict)]
            if items:
                return items

        if isinstance(candidate, dict):
            for key, value in candidate.items():
                if not isinstance(value, dict):
                    continue

                entry = dict(value)
                if "timestamp" not in entry:
                    try:
                        entry["timestamp"] = float(key)
                    except (TypeError, ValueError):
                        decoded_timestamp = decode_firebase_push_timestamp(str(key))
                        if decoded_timestamp is not None:
                            entry["timestamp"] = decoded_timestamp
                items.append(entry)

            if items:
                return items

    return []


FIREBASE_PUSH_ALPHABET = "-0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ_abcdefghijklmnopqrstuvwxyz"


def decode_firebase_push_timestamp(push_id: str) -> Optional[float]:
    if len(push_id) < 8:
        return None
    timestamp_ms = 0
    for character in push_id[:8]:
        index = FIREBASE_PUSH_ALPHABET.find(character)
        if index < 0:
            return None
        timestamp_ms = timestamp_ms * 64 + index
    return timestamp_ms / 1000.0


def insert_reading(reading: Reading) -> float:
    timestamp = reading.timestamp or time.time()
    quality = validate_reading_quality(reading)
    quality_status = reading.quality_status or quality.status

    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.execute(
            """
            INSERT INTO readings (
                timestamp,
                humidity,
                temperature_c,
                heat_index_c,
                soil_moisture,
                soil_analog,
                soil_temperature_c,
                ec,
                quality_status,
                calibration_version,
                source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                timestamp,
                reading.humidity,
                reading.temperature_c,
                reading.heat_index_c,
                reading.soil_moisture,
                reading.soil_analog,
                reading.soil_temperature_c,
                reading.ec,
                quality_status,
                reading.calibration_version,
                reading.source
            )
        )
        connection.commit()

    return timestamp


def ingest_firebase_reading() -> float:
    payload = fetch_firebase_payload()
    reading = canonical_to_reading(payload)
    quality = validate_reading_quality(reading)
    result = store_five_minute_payload(DB_PATH, payload, quality.status, quality.issues)
    return result.recorded_at


async def firebase_poll_loop() -> None:
    while True:
        try:
            ingest_firebase_reading()
        except Exception:
            pass

        await asyncio.sleep(max(5.0, FIREBASE_POLL_SECONDS))


def start_firebase_poller() -> None:
    global _poller_task
    if FIREBASE_POLL_SECONDS <= 0:
        return

    if _poller_task and not _poller_task.done():
        return

    _poller_task = asyncio.create_task(firebase_poll_loop())


def stop_firebase_poller() -> None:
    global _poller_task
    if _poller_task and not _poller_task.done():
        _poller_task.cancel()


def fetch_readings(limit: int, since: Optional[float] = None) -> List[Dict[str, object]]:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        if since is not None:
            rows = connection.execute(
                "SELECT * FROM readings WHERE timestamp >= ? ORDER BY timestamp DESC LIMIT ?",
                (since, limit)
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM readings ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()

    return [row_to_dict(row) for row in rows]


def fetch_readings_chrono(limit: int, since: Optional[float] = None) -> List[Dict[str, object]]:
    with closing(sqlite3.connect(DB_PATH)) as connection:
        connection.row_factory = sqlite3.Row
        if since is not None:
            rows = connection.execute(
                "SELECT * FROM readings WHERE timestamp >= ? ORDER BY timestamp ASC LIMIT ?",
                (since, limit)
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM readings ORDER BY timestamp ASC LIMIT ?",
                (limit,)
            ).fetchall()

    return [row_to_dict(row) for row in rows]


def build_trend_chart(rows: List[Dict[str, Optional[float]]], field: str, title: str, unit: str) -> bytes:
    values = [row[field] for row in rows if row[field] is not None]
    if not values:
        return b""

    plt.figure(figsize=(6, 2.4))
    plt.plot(values, color="#76D34E", linewidth=2)
    plt.title(title, fontsize=10)
    plt.ylabel(unit, fontsize=8)
    plt.grid(alpha=0.2)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=160)
    plt.close()
    buffer.seek(0)
    return buffer.read()


def summarize_stage_alerts(rows: List[Dict[str, Optional[float]]], stage_id: str) -> Dict[str, object]:
    alert_entries = []
    counts = {"alert": 0, "warning": 0, "info": 0, "ok": 0}

    for row in rows:
        reading = Reading(**row)
        evaluation = evaluate_stage_logic(stage_id, reading, flags={})
        for alert in evaluation.alerts:
            counts[alert["level"]] = counts.get(alert["level"], 0) + 1
            alert_entries.append(
                {
                    "timestamp": row.get("timestamp"),
                    "title": alert["title"],
                    "detail": alert["detail"],
                    "level": alert["level"]
                }
            )

    alert_entries = alert_entries[-50:]
    return {
        "counts": counts,
        "entries": alert_entries
    }


def compute_summary(rows: List[Dict[str, Optional[float]]]) -> SummaryStats:
    fields = [
        "humidity",
        "temperature_c",
        "heat_index_c",
        "soil_moisture",
        "soil_analog",
        "soil_temperature_c",
        "ec"
    ]

    def collect(field: str) -> List[float]:
        return [row[field] for row in rows if row[field] is not None]

    avg = {}
    min_values = {}
    max_values = {}
    trend = {}

    for field in fields:
        values = collect(field)
        avg[field] = sum(values) / len(values) if values else None
        min_values[field] = min(values) if values else None
        max_values[field] = max(values) if values else None

        if len(values) >= 2:
            trend[field] = values[0] - values[1]
        else:
            trend[field] = None

    return SummaryStats(avg=avg, min=min_values, max=max_values, trend=trend, count=len(rows))


def _warning_level(score: int) -> str:
    if score >= 75:
        return "red"
    if score >= 50:
        return "orange"
    if score >= 25:
        return "yellow"
    return "green"


def analyze_sensor_window(
    rows: List[Dict[str, object]],
    stage_id: str
) -> SensorWindowAnalysis:
    stage = get_stage(stage_id)
    ordered = sorted(
        [row for row in rows if is_number(row.get("timestamp"))],
        key=lambda row: row["timestamp"]
    )
    mapping = {
        "soil_moisture": ("soil_analog", stage["thresholds"]["soil_moisture"], 15),
        "soil_temperature": ("soil_temperature_c", stage["thresholds"]["soil_temp"], 8),
        "air_temperature": ("temperature_c", stage["thresholds"]["air_temp"], 10),
        "humidity": ("humidity", stage["thresholds"]["air_humidity"], 7),
        "ec": ("ec", stage["thresholds"]["ec"], 10)
    }

    parameters: Dict[str, object] = {}
    contributing_factors: List[Dict[str, object]] = []
    warning_score = 0.0

    for output_name, (field, target, weight) in mapping.items():
        samples = [row for row in ordered if is_number(row.get(field))]
        values = [float(row[field]) for row in samples]
        hours_low = 0.0
        hours_high = 0.0

        for index in range(len(samples) - 1):
            duration_hours = max(0.0, min(1.0, (samples[index + 1]["timestamp"] - samples[index]["timestamp"]) / 3600.0))
            value = float(samples[index][field])
            if value < target["min"]:
                hours_low += duration_hours
            elif value > target["max"]:
                hours_high += duration_hours

        in_range_count = sum(target["min"] <= value <= target["max"] for value in values)
        percent_in_range = (in_range_count / len(values) * 100.0) if values else None
        latest = values[-1] if values else None
        if latest is None:
            status = "unknown"
        elif latest < target["min"]:
            status = "low"
        elif latest > target["max"]:
            status = "high"
        else:
            status = "ok"

        trend_per_hour = None
        if len(samples) >= 2:
            elapsed_hours = (samples[-1]["timestamp"] - samples[0]["timestamp"]) / 3600.0
            if elapsed_hours > 0:
                trend_per_hour = (values[-1] - values[0]) / elapsed_hours

        abnormal_fraction = 0.0 if percent_in_range is None else 1.0 - percent_in_range / 100.0
        persistence_bonus = 10.0 if abnormal_fraction >= 0.5 and (hours_low >= 0.5 or hours_high >= 0.5) else 0.0
        parameter_score = weight * abnormal_fraction + persistence_bonus
        warning_score += parameter_score
        if status in {"low", "high"} or abnormal_fraction >= 0.25:
            contributing_factors.append({
                "factor": output_name,
                "status": status if status != "ok" else "intermittent",
                "hours_low": round(hours_low, 2),
                "hours_high": round(hours_high, 2),
                "percent_in_range": round(percent_in_range or 0.0, 1),
                "risk_points": round(parameter_score, 1)
            })

        parameters[output_name] = {
            "latest": latest,
            "avg": sum(values) / len(values) if values else None,
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "trend_per_hour": trend_per_hour,
            "samples": len(values),
            "hours_low": round(hours_low, 2),
            "hours_high": round(hours_high, 2),
            "percent_in_range": round(percent_in_range, 1) if percent_in_range is not None else None,
            "status": status,
            "unit": target["unit"]
        }

    valid_rows = sum(
        1 for row in ordered
        if row.get("quality_status") in (None, "valid")
    )
    valid_percent = valid_rows / len(ordered) * 100.0 if ordered else 0.0
    if ordered and valid_percent < 75:
        warning_score += 10
        contributing_factors.append({
            "factor": "data_quality",
            "status": "suspect",
            "valid_sample_percent": round(valid_percent, 1),
            "risk_points": 10
        })

    score = int(round(min(100.0, warning_score)))
    contributing_factors.sort(key=lambda item: float(item.get("risk_points", 0)), reverse=True)
    return SensorWindowAnalysis(
        stage_id=stage["id"],
        window_start=ordered[0]["timestamp"] if ordered else None,
        window_end=ordered[-1]["timestamp"] if ordered else None,
        sample_count=len(ordered),
        valid_sample_percent=round(valid_percent, 1),
        warning_score=score,
        warning_level=_warning_level(score),
        parameters=parameters,
        contributing_factors=contributing_factors
    )


def _pick_first_optional_float(payload: Dict[str, object], keys: List[str]) -> Optional[float]:
    for key in keys:
        if key not in payload:
            continue

        value = payload[key]
        if value is None:
            continue

        try:
            return float(value)
        except (TypeError, ValueError):
            continue

    return None


SOIL_MOISTURE_FIREBASE_KEYS = [
    "soil_moisture",
    "soilMoisture",
    "soil_moisture_percent",
    "soilMoisturePercent",
]


SOIL_TEMP_FIREBASE_KEYS = [
    "soil_temperature_c",
    "soil_temp_c",
    "ds18b20_temperature_c",
]


AIR_TEMP_FIREBASE_KEYS = [
    "air_temperature_c",
    "dht_temperature_c",
    "temperature_c",
]


def fetch_firebase_reading() -> Reading:
    return canonical_to_reading(fetch_firebase_payload())


def fetch_firebase_payload() -> CanonicalSensorPayload:
    try:
        response = httpx.get(f"{FIREBASE_URL}/.json", timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    payload = response.json() or {}
    if all(key in payload for key in ("device_id", "plot_id", "crop_cycle_id", "sensors")):
        canonical_payload = dict(payload)
        if "recorded_at" not in canonical_payload and "timestamp" in canonical_payload:
            canonical_payload["recorded_at"] = canonical_payload["timestamp"]
        return CanonicalSensorPayload(**canonical_payload)

    sensors = payload.get("sensors", payload)
    soil_temperature_c = _pick_first_optional_float(sensors, SOIL_TEMP_FIREBASE_KEYS)
    soil_moisture = _pick_first_optional_float(sensors, SOIL_MOISTURE_FIREBASE_KEYS)

    return CanonicalSensorPayload(
        device_id=DEFAULT_DEVICE_ID,
        plot_id=DEFAULT_PLOT_ID,
        crop_cycle_id=DEFAULT_CROP_CYCLE_ID,
        plant_id=DEFAULT_PLANT_ID,
        recorded_at=_pick_first_optional_float(payload, ["recorded_at", "timestamp"]),
        sensors=SensorValues(
            air_temperature_c=_pick_first_optional_float(sensors, AIR_TEMP_FIREBASE_KEYS),
            relative_humidity_percent=_pick_first_optional_float(sensors, ["relative_humidity_percent", "humidity"]),
            heat_index_c=_pick_first_optional_float(sensors, ["heat_index_c"]),
            soil_temperature_c=soil_temperature_c,
            soil_moisture_raw=_pick_first_optional_float(sensors, ["soil_moisture_raw", "soil_analog"]),
            soil_moisture_percent=soil_moisture,
            ec_ms_cm=_pick_first_optional_float(sensors, ["ec_ms_cm", "ec"]),
        ),
        calibration_version=payload.get("calibration_version"),
        source="firebase",
    )


def fetch_firebase_history(
    limit: int = 500,
    since: Optional[float] = None,
    chronological: bool = False
) -> List[Dict[str, Optional[float]]]:
    try:
        response = httpx.get(f"{FIREBASE_URL}/.json", timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    payload = response.json() or {}
    items = parse_firebase_history_items(payload)
    rows: List[Dict[str, Optional[float]]] = []

    for item in items:
        normalized_item = dict(item)

        air_temp = _pick_first_optional_float(normalized_item, AIR_TEMP_FIREBASE_KEYS)
        if air_temp is not None:
            normalized_item["temperature_c"] = air_temp

        soil_temp = _pick_first_optional_float(normalized_item, SOIL_TEMP_FIREBASE_KEYS)
        if soil_temp is not None:
            normalized_item["soil_temperature_c"] = soil_temp

        soil_m_pct = _pick_first_optional_float(normalized_item, SOIL_MOISTURE_FIREBASE_KEYS)
        if soil_m_pct is not None:
            normalized_item["soil_moisture"] = soil_m_pct

        reading = Reading(**normalized_item)
        reading.source = reading.source or "firebase"
        timestamp = item.get("timestamp") if isinstance(item, dict) else None
        row = reading_to_dict(reading, timestamp=timestamp)

        if since is not None and isinstance(row.get("timestamp"), (int, float)):
            if row["timestamp"] < since:
                continue

        rows.append(row)

    rows.sort(key=lambda entry: entry.get("timestamp") or 0, reverse=not chronological)

    if limit > 0:
        rows = rows[:limit]

    return rows


def generate_report_from_rows(rows: List[Dict[str, Optional[float]]], title: str) -> StreamingResponse:
    if not rows:
        raise HTTPException(status_code=404, detail="No readings stored yet")

    buffer = io.BytesIO()
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.pdfgen import canvas

    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setTitle(title)
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(2 * cm, height - 2 * cm, title)
    pdf.setFont("Helvetica", 10)
    pdf.drawString(2 * cm, height - 2.6 * cm, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    pdf.drawString(2 * cm, height - 3.2 * cm, f"Readings: {len(rows)}")
    pdf.drawString(2 * cm, height - 3.8 * cm, "Note: Context flags are not applied in this report.")

    y = height - 4.6 * cm

    charts = [
        ("temperature_c", "Air temperature", "C"),
        ("humidity", "Air humidity", "%"),
        ("soil_moisture", "Soil moisture %", "%"),
        ("soil_analog", "Soil analog", ""),
        ("ec", "EC", "mS/cm")
    ]

    for field, chart_title, unit in charts:
        chart_bytes = build_trend_chart(rows, field, chart_title, unit)
        if chart_bytes:
            if y < 7 * cm:
                pdf.showPage()
                y = height - 2 * cm
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(2 * cm, y, chart_title)
            y -= 0.3 * cm
            pdf.drawInlineImage(chart_bytes, 2 * cm, y - 5.4 * cm, width=17 * cm, height=5 * cm)
            y -= 6 * cm

    for stage in STAGES:
        if y < 9 * cm:
            pdf.showPage()
            y = height - 2 * cm

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(2 * cm, y, f"Stage: {stage['title']} ({stage['duration']})")
        y -= 0.4 * cm

        pdf.setFont("Helvetica", 9)
        for key, data in stage["thresholds"].items():
            label = key.replace("_", " ").title()
            pdf.drawString(2.2 * cm, y, f"{label}: {data['min']} - {data['max']} {data['unit']}")
            y -= 0.3 * cm

        summary = summarize_stage_alerts(rows, stage["id"])
        counts = summary["counts"]
        pdf.drawString(
            2.2 * cm,
            y,
            f"Alerts: {counts['alert']} | Warnings: {counts['warning']} | Info: {counts['info']} | OK: {counts['ok']}"
        )
        y -= 0.4 * cm

        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawString(2.2 * cm, y, "Recent alerts")
        y -= 0.3 * cm

        pdf.setFont("Helvetica", 8)
        for entry in summary["entries"][-10:]:
            timestamp = datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S") if entry.get("timestamp") else "--"
            text = f"[{timestamp}] {entry['level'].upper()}: {entry['title']}"
            pdf.drawString(2.4 * cm, y, text)
            y -= 0.25 * cm
            if y < 3 * cm:
                pdf.showPage()
                y = height - 2 * cm

        y -= 0.2 * cm

    pdf.showPage()
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(2 * cm, height - 2 * cm, "Raw readings (latest 50)")
    pdf.setFont("Helvetica", 8)
    y = height - 2.6 * cm
    for row in rows[-50:]:
        timestamp = datetime.fromtimestamp(row["timestamp"]).strftime("%Y-%m-%d %H:%M:%S") if row.get("timestamp") else "--"
        line = (
            f"{timestamp} | T={row.get('temperature_c')} C | H={row.get('humidity')}% | "
            f"Soil%={row.get('soil_moisture')} | SoilA={row.get('soil_analog')} | EC={row.get('ec')}"
        )
        pdf.drawString(2 * cm, y, line)
        y -= 0.25 * cm
        if y < 2 * cm:
            pdf.showPage()
            y = height - 2 * cm

    pdf.save()
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=iot_stage_report.pdf"}
    )


def generate_report(minutes: int = 60, limit: int = 500) -> StreamingResponse:
    since = time.time() - minutes * 60
    rows = fetch_readings_chrono(limit=limit, since=since)
    title = f"IoT Stage Report (Last {minutes} minutes)"
    return generate_report_from_rows(rows, title)


def generate_firebase_report(limit: int = 500) -> StreamingResponse:
    rows = fetch_firebase_history(limit=limit, chronological=True)
    return generate_report_from_rows(rows, "IoT Stage Report (Firebase History)")
