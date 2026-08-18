import json
import math
import sqlite3
import time
from contextlib import closing
from typing import Dict, List, Optional

from .warning_models import ThresholdProfile, WarningEvaluation, WarningEvidence, WarningEvent


PARAMETER_COLUMNS = {
    "soil_moisture_percent": "soil_moisture",
    "soil_temperature_c": "soil_temperature_c",
    "air_temperature_c": "temperature_c",
    "relative_humidity_percent": "humidity",
    "ec_ms_cm": "ec",
}

RECOMMENDATIONS = {
    ("soil_moisture_percent", "low"): [
        "Inspect the soil-moisture probe position and irrigation line before acting.",
        "If the reading is confirmed, irrigate toward the calibrated stage target without waterlogging.",
        "Recheck soil moisture after the configured irrigation interval.",
    ],
    ("soil_moisture_percent", "high"): [
        "Pause additional irrigation and inspect the root zone for standing water.",
        "Check drainage and verify that the moisture probe is not directly beside an emitter.",
    ],
    ("air_temperature_c", "low"): [
        "Protect young plants from cold exposure and verify the DHT22 placement.",
        "Recheck the temperature trend before changing crop management.",
    ],
    ("air_temperature_c", "high"): [
        "Provide temporary shade where practical and improve airflow around the crop.",
        "Inspect plants during peak heat and avoid unnecessary midday stress.",
    ],
    ("soil_temperature_c", "low"): [
        "Verify DS18B20 contact with root-zone soil and protect the root zone from excessive cooling.",
    ],
    ("soil_temperature_c", "high"): [
        "Verify probe depth and consider mulch or shading to reduce root-zone heating.",
    ],
    ("relative_humidity_percent", "low"): [
        "Verify DHT22 placement and inspect plants for excessive drying.",
        "Avoid increasing irrigation solely from humidity; confirm root-zone moisture first.",
    ],
    ("relative_humidity_percent", "high"): [
        "Improve airflow and avoid prolonged wet foliage.",
        "Inspect plants for fungal symptoms; this warning is a risk indicator, not a disease diagnosis.",
    ],
    ("ec_ms_cm", "low"): [
        "Verify EC calibration and measurement medium before interpreting nutrient status.",
        "Review the approved fertilizer schedule; do not calculate dosage from this warning alone.",
    ],
    ("ec_ms_cm", "high"): [
        "Stop additional fertilizer until the EC reading and calibration are verified.",
        "Inspect irrigation-water quality and possible salt accumulation with an agriculture-domain advisor.",
    ],
}


def init_warning_db(db_path: str, stages: List[Dict[str, object]]) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS growth_stages (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                duration TEXT NOT NULL,
                flags_json TEXT NOT NULL DEFAULT '[]',
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS threshold_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stage_id TEXT NOT NULL,
                parameter TEXT NOT NULL,
                minimum REAL NOT NULL,
                maximum REAL NOT NULL,
                unit TEXT NOT NULL,
                weight REAL NOT NULL,
                version TEXT NOT NULL,
                validated INTEGER NOT NULL DEFAULT 0,
                source_note TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(stage_id, parameter, version),
                FOREIGN KEY(stage_id) REFERENCES growth_stages(id)
            );

            CREATE TABLE IF NOT EXISTS warning_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                plot_id TEXT,
                crop_cycle_id TEXT,
                stage_id TEXT NOT NULL,
                warning_type TEXT NOT NULL,
                warning_level TEXT NOT NULL,
                warning_score INTEGER NOT NULL,
                status TEXT NOT NULL,
                summary TEXT NOT NULL,
                recommendations_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                opened_at REAL NOT NULL,
                updated_at REAL NOT NULL,
                acknowledged_at REAL,
                resolved_at REAL,
                resolution_note TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_warning_events_status
            ON warning_events(device_id, status, updated_at);
            """
        )

        moisture_percent_ranges = {
            "stage1": (70.0, 85.0),
            "stage2": (65.0, 75.0),
            "stage3": (60.0, 70.0),
            "stage4": (55.0, 70.0),
            "stage5": (50.0, 65.0),
        }
        parameter_map = {
            "soil_moisture": ("soil_moisture_percent", 15.0, False, "Provisional calibrated-percentage profile; calibration and field validation required."),
            "soil_temp": ("soil_temperature_c", 8.0, False, "Provisional crop-stage profile; field validation required."),
            "air_temp": ("air_temperature_c", 10.0, False, "Provisional DHT22 crop-stage profile; supervisor validation required."),
            "air_humidity": ("relative_humidity_percent", 7.0, False, "Provisional DHT22 crop-stage profile; supervisor validation required."),
            "ec": ("ec_ms_cm", 10.0, False, "Inactive in field decisions until EC hardware and method are validated."),
        }
        for stage in stages:
            connection.execute(
                "INSERT INTO growth_stages(id, title, duration, flags_json) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET title=excluded.title, duration=excluded.duration, flags_json=excluded.flags_json",
                (stage["id"], stage["title"], stage["duration"], json.dumps(stage.get("flags", []))),
            )
            for legacy_name, threshold in stage["thresholds"].items():
                parameter, weight, validated, note = parameter_map[legacy_name]
                minimum = threshold["min"]
                maximum = threshold["max"]
                unit = threshold["unit"]
                if legacy_name == "soil_moisture":
                    minimum, maximum = moisture_percent_ranges[stage["id"]]
                    unit = "%"
                connection.execute(
                    "INSERT OR IGNORE INTO threshold_profiles("
                    "stage_id, parameter, minimum, maximum, unit, weight, version, validated, source_note"
                    ") VALUES (?, ?, ?, ?, ?, ?, 'phase2-v1', ?, ?)",
                    (
                        stage["id"], parameter, minimum, maximum,
                        unit, weight, int(validated), note,
                    ),
                )
        connection.commit()


def list_threshold_profiles(db_path: str, stage_id: Optional[str] = None) -> List[ThresholdProfile]:
    query = (
        "SELECT tp.stage_id, gs.title stage_title, gs.duration, tp.parameter, tp.minimum, "
        "tp.maximum, tp.unit, tp.weight, tp.version, tp.validated, tp.source_note "
        "FROM threshold_profiles tp JOIN growth_stages gs ON gs.id=tp.stage_id "
        "WHERE tp.active=1 AND gs.active=1"
    )
    params: List[object] = []
    if stage_id:
        query += " AND tp.stage_id=?"
        params.append(stage_id)
    query += " ORDER BY tp.stage_id, tp.parameter"
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()
    return [
        ThresholdProfile(
            **{**dict(row), "validated": bool(row["validated"])}
        ) for row in rows
    ]


def list_stages_from_db(db_path: str) -> List[Dict[str, object]]:
    profiles = list_threshold_profiles(db_path)
    stages: Dict[str, Dict[str, object]] = {}
    reverse_names = {
        "soil_moisture_percent": "soil_moisture",
        "soil_temperature_c": "soil_temp",
        "air_temperature_c": "air_temp",
        "relative_humidity_percent": "air_humidity",
        "ec_ms_cm": "ec",
    }
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        stage_rows = connection.execute(
            "SELECT id, title, duration, flags_json FROM growth_stages WHERE active=1 ORDER BY id"
        ).fetchall()
    for row in stage_rows:
        stages[row["id"]] = {
            "id": row["id"], "title": row["title"], "duration": row["duration"],
            "thresholds": {}, "flags": json.loads(row["flags_json"]),
        }
    for profile in profiles:
        stages[profile.stage_id]["thresholds"][reverse_names[profile.parameter]] = {
            "min": profile.minimum,
            "max": profile.maximum,
            "unit": profile.unit,
            "validated": profile.validated,
            "version": profile.version,
        }
        if profile.parameter == "soil_moisture_percent":
            stages[profile.stage_id]["dry_threshold"] = profile.minimum
    return list(stages.values())


def _level(score: int) -> str:
    if score >= 75:
        return "red"
    if score >= 50:
        return "orange"
    if score >= 25:
        return "yellow"
    return "green"


def _parameter_evidence(
    rows: List[Dict[str, object]],
    profile: ThresholdProfile,
    expected_interval_seconds: int,
) -> Optional[WarningEvidence]:
    column = PARAMETER_COLUMNS[profile.parameter]
    issue_prefixes = {
        "soil_moisture_percent": ("soil_analog:", "soil_moisture:"),
        "soil_temperature_c": ("soil_temperature_c:",),
        "air_temperature_c": ("temperature_c:",),
        "relative_humidity_percent": ("humidity:",),
        "ec_ms_cm": ("ec:",),
    }

    def field_is_usable(row: Dict[str, object]) -> bool:
        value = row.get(column)
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            return False
        if profile.parameter == "soil_moisture_percent" and not row.get("calibration_version"):
            return False
        raw_issues = row.get("quality_issues") or "[]"
        try:
            issues = json.loads(raw_issues) if isinstance(raw_issues, str) else raw_issues
        except json.JSONDecodeError:
            issues = []
        return not any(
            str(issue).startswith(prefix)
            for issue in issues
            for prefix in issue_prefixes[profile.parameter]
        )

    samples = [row for row in rows if field_is_usable(row)]
    if not samples:
        return None
    samples.sort(key=lambda row: float(row["timestamp"]))
    values = [float(row[column]) for row in samples]
    outside = [value < profile.minimum or value > profile.maximum for value in values]
    low_hours = 0.0
    high_hours = 0.0
    consecutive_seconds = 0.0
    max_consecutive_seconds = 0.0
    interval_cap = max(60, expected_interval_seconds * 2)
    for index in range(len(samples) - 1):
        seconds = max(0.0, min(interval_cap, float(samples[index + 1]["timestamp"]) - float(samples[index]["timestamp"])))
        value = values[index]
        if value < profile.minimum:
            low_hours += seconds / 3600.0
            consecutive_seconds += seconds
        elif value > profile.maximum:
            high_hours += seconds / 3600.0
            consecutive_seconds += seconds
        else:
            consecutive_seconds = 0.0
        max_consecutive_seconds = max(max_consecutive_seconds, consecutive_seconds)

    latest = values[-1]
    status = "low" if latest < profile.minimum else "high" if latest > profile.maximum else "ok"
    percent_outside = sum(outside) / len(outside) * 100.0
    trend = None
    elapsed_hours = (float(samples[-1]["timestamp"]) - float(samples[0]["timestamp"])) / 3600.0
    if elapsed_hours > 0:
        trend = (values[-1] - values[0]) / elapsed_hours

    range_width = max(profile.maximum - profile.minimum, 0.0001)
    if latest < profile.minimum:
        deviation = min(2.0, (profile.minimum - latest) / range_width)
    elif latest > profile.maximum:
        deviation = min(2.0, (latest - profile.maximum) / range_width)
    else:
        deviation = 0.0
    persistence_ratio = percent_outside / 100.0
    persistence_bonus = 10.0 if max_consecutive_seconds >= expected_interval_seconds * 2 else 0.0
    trend_bonus = 5.0 if trend is not None and status != "ok" and abs(trend) >= range_width * 0.1 else 0.0
    risk_points = min(30.0, profile.weight * persistence_ratio + profile.weight * deviation + persistence_bonus + trend_bonus)
    return WarningEvidence(
        parameter=profile.parameter,
        status=status if status != "ok" else ("intermittent" if percent_outside >= 25 else "ok"),
        latest=latest,
        minimum=profile.minimum,
        maximum=profile.maximum,
        unit=profile.unit,
        samples=len(samples),
        percent_outside_range=round(percent_outside, 1),
        consecutive_minutes=round(max_consecutive_seconds / 60.0, 1),
        hours_low=round(low_hours, 2),
        hours_high=round(high_hours, 2),
        trend_per_hour=round(trend, 3) if trend is not None else None,
        risk_points=round(risk_points, 1),
        threshold_validated=profile.validated,
    )


def evaluate_warnings(
    db_path: str,
    device_id: str,
    stage_id: str,
    window_hours: int,
    now: Optional[float] = None,
    persist_event: bool = True,
) -> WarningEvaluation:
    evaluated_at = float(now if now is not None else time.time())
    profiles = list_threshold_profiles(db_path, stage_id)
    if not profiles:
        raise ValueError(f"Unknown stage_id: {stage_id}")
    since = evaluated_at - window_hours * 3600
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        device = connection.execute(
            "SELECT plot_id, expected_interval_seconds FROM devices WHERE id=?", (device_id,)
        ).fetchone()
        if device is None:
            raise ValueError(f"Unknown device id: {device_id}")
        rows = [dict(row) for row in connection.execute(
            "SELECT * FROM readings WHERE device_id=? AND timestamp>=? AND timestamp<=? ORDER BY timestamp",
            (device_id, since, evaluated_at),
        ).fetchall()]
    valid_count = sum(row.get("quality_status") == "valid" for row in rows)
    valid_percent = valid_count / len(rows) * 100.0 if rows else 0.0
    evidence = [
        item for profile in profiles
        if (item := _parameter_evidence(rows, profile, int(device["expected_interval_seconds"]))) is not None
    ]
    relevant = [item for item in evidence if item.status != "ok"]
    score = int(round(min(100.0, sum(item.risk_points for item in relevant))))
    if rows and valid_percent < 75:
        score = min(100, score + 10)
    level = _level(score)
    relevant.sort(key=lambda item: item.risk_points, reverse=True)
    recommendations: List[str] = []
    for item in relevant:
        status = item.status if item.status in {"low", "high"} else ""
        for recommendation in RECOMMENDATIONS.get((item.parameter, status), []):
            if recommendation not in recommendations:
                recommendations.append(recommendation)
    if not rows:
        summary = "No stored sensor readings are available for this device and time window."
        recommendations = ["Check device power, Wi-Fi, Firebase delivery, and backend ingestion."]
    elif level == "green":
        summary = "No persistent stage-threshold warning was detected in the selected window."
        recommendations = ["Continue the current schedule and keep monitoring."]
    elif relevant:
        factors = ", ".join(f"{item.parameter} ({item.status})" for item in relevant[:3])
        summary = f"{level.capitalize()} warning from persistent or trending conditions: {factors}."
    else:
        summary = f"{level.capitalize()} data-quality warning: fewer than 75% of stored readings passed all validation checks."
        recommendations = [
            "Inspect sensor connections, calibration metadata, and data-quality issues before making a crop-management decision."
        ]
    evaluation = WarningEvaluation(
        device_id=device_id,
        stage_id=stage_id,
        evaluated_at=evaluated_at,
        window_hours=window_hours,
        sample_count=len(rows),
        valid_sample_percent=round(valid_percent, 1),
        warning_score=score,
        warning_level=level,
        summary=summary,
        recommendations=recommendations,
        evidence=relevant,
    )
    if persist_event:
        evaluation.event_id = persist_warning_evaluation(db_path, evaluation)
    return evaluation


def persist_warning_evaluation(db_path: str, evaluation: WarningEvaluation) -> Optional[int]:
    warning_type = evaluation.evidence[0].parameter if evaluation.evidence else "sensor_window"
    now = evaluation.evaluated_at
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        context = connection.execute(
            "SELECT plot_id FROM devices WHERE id=?", (evaluation.device_id,)
        ).fetchone()
        cycle = connection.execute(
            "SELECT crop_cycle_id FROM readings WHERE device_id=? ORDER BY timestamp DESC LIMIT 1",
            (evaluation.device_id,),
        ).fetchone()
        open_event = connection.execute(
            "SELECT id FROM warning_events WHERE device_id=? AND stage_id=? AND warning_type=? "
            "AND status IN ('open','acknowledged') ORDER BY id DESC LIMIT 1",
            (evaluation.device_id, evaluation.stage_id, warning_type),
        ).fetchone()
        if evaluation.warning_level == "green":
            connection.execute(
                "UPDATE warning_events SET status='resolved', resolved_at=?, updated_at=?, "
                "resolution_note=COALESCE(resolution_note, 'Automatically resolved after readings returned to normal.') "
                "WHERE device_id=? AND stage_id=? AND status IN ('open','acknowledged')",
                (now, now, evaluation.device_id, evaluation.stage_id),
            )
            connection.commit()
            return None
        payload = (
            evaluation.warning_level, evaluation.warning_score, evaluation.summary,
            json.dumps(evaluation.recommendations),
            json.dumps([item.model_dump() for item in evaluation.evidence]), now,
        )
        if open_event:
            connection.execute(
                "UPDATE warning_events SET warning_level=?, warning_score=?, summary=?, "
                "recommendations_json=?, evidence_json=?, updated_at=? WHERE id=?",
                (*payload, open_event["id"]),
            )
            event_id = int(open_event["id"])
        else:
            cursor = connection.execute(
                "INSERT INTO warning_events(device_id, plot_id, crop_cycle_id, stage_id, warning_type, "
                "warning_level, warning_score, status, summary, recommendations_json, evidence_json, opened_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)",
                (
                    evaluation.device_id, context["plot_id"] if context else None,
                    cycle["crop_cycle_id"] if cycle else None, evaluation.stage_id, warning_type,
                    evaluation.warning_level, evaluation.warning_score, evaluation.summary,
                    json.dumps(evaluation.recommendations),
                    json.dumps([item.model_dump() for item in evaluation.evidence]), now, now,
                ),
            )
            event_id = int(cursor.lastrowid)
        connection.commit()
    return event_id


def _row_to_event(row: sqlite3.Row) -> WarningEvent:
    data = dict(row)
    data["recommendations"] = json.loads(data.pop("recommendations_json"))
    data["evidence"] = json.loads(data.pop("evidence_json"))
    return WarningEvent(**data)


def list_warning_events(db_path: str, status: Optional[str] = None, device_id: Optional[str] = None) -> List[WarningEvent]:
    query = "SELECT * FROM warning_events WHERE 1=1"
    params: List[object] = []
    if status:
        query += " AND status=?"
        params.append(status)
    if device_id:
        query += " AND device_id=?"
        params.append(device_id)
    query += " ORDER BY updated_at DESC"
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        return [_row_to_event(row) for row in connection.execute(query, params).fetchall()]


def change_warning_status(db_path: str, event_id: int, action: str, note: Optional[str] = None) -> WarningEvent:
    now = time.time()
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute("SELECT * FROM warning_events WHERE id=?", (event_id,)).fetchone()
        if row is None:
            raise ValueError("Warning event not found")
        if action == "acknowledge":
            if row["status"] == "resolved":
                raise ValueError("Resolved warning cannot be acknowledged")
            connection.execute(
                "UPDATE warning_events SET status='acknowledged', acknowledged_at=?, updated_at=? WHERE id=?",
                (now, now, event_id),
            )
        elif action == "resolve":
            connection.execute(
                "UPDATE warning_events SET status='resolved', resolved_at=?, updated_at=?, resolution_note=? WHERE id=?",
                (now, now, note, event_id),
            )
        else:
            raise ValueError("Unknown warning action")
        connection.commit()
        updated = connection.execute("SELECT * FROM warning_events WHERE id=?", (event_id,)).fetchone()
    return _row_to_event(updated)
