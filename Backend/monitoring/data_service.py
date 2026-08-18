import json
import math
import sqlite3
import time
from contextlib import closing
from datetime import date
from typing import Dict, List, Optional

from .data_models import (
    AggregatedPeriod,
    AggregationResponse,
    CanonicalSensorPayload,
    DeviceStatus,
    IngestionResult,
    MonitoringSetupRequest,
    PlotCreate,
    CropCycleCreate,
    DeviceCreate,
    SensorValues,
)
from .models import Reading


FIVE_MINUTES_SECONDS = 300
AGGREGATE_FIELDS = (
    "humidity",
    "temperature_c",
    "heat_index_c",
    "soil_moisture",
    "soil_analog",
    "soil_temperature_c",
    "ec",
)


def init_phase1_db(db_path: str) -> None:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS plots (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT,
                soil_type TEXT,
                created_at REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS crop_cycles (
                id TEXT PRIMARY KEY,
                plot_id TEXT NOT NULL,
                crop_name TEXT NOT NULL,
                variety TEXT NOT NULL,
                planting_date TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at REAL NOT NULL,
                FOREIGN KEY (plot_id) REFERENCES plots(id)
            );

            CREATE TABLE IF NOT EXISTS plants (
                id TEXT PRIMARY KEY,
                crop_cycle_id TEXT NOT NULL,
                plant_code TEXT NOT NULL,
                row_number TEXT,
                position TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY (crop_cycle_id) REFERENCES crop_cycles(id)
            );

            CREATE TABLE IF NOT EXISTS devices (
                id TEXT PRIMARY KEY,
                plot_id TEXT NOT NULL,
                device_code TEXT NOT NULL,
                firmware_version TEXT,
                expected_interval_seconds INTEGER NOT NULL DEFAULT 300,
                last_seen_at REAL,
                status TEXT NOT NULL DEFAULT 'never_seen',
                created_at REAL NOT NULL,
                FOREIGN KEY (plot_id) REFERENCES plots(id)
            );
            """
        )

        reading_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(readings)").fetchall()
        }
        additions = (
            ("device_id", "TEXT"),
            ("plot_id", "TEXT"),
            ("crop_cycle_id", "TEXT"),
            ("plant_id", "TEXT"),
            ("bucket_start", "REAL"),
            ("received_at", "REAL"),
            ("quality_issues", "TEXT"),
            ("raw_payload", "TEXT"),
            ("schema_version", "TEXT"),
        )
        for column_name, column_type in additions:
            if column_name not in reading_columns:
                connection.execute(f"ALTER TABLE readings ADD COLUMN {column_name} {column_type}")

        connection.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_readings_device_bucket "
            "ON readings(device_id, bucket_start) WHERE device_id IS NOT NULL AND bucket_start IS NOT NULL"
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_readings_device_timestamp ON readings(device_id, timestamp)"
        )
        connection.commit()


def register_monitoring_setup(db_path: str, setup: MonitoringSetupRequest) -> Dict[str, object]:
    if setup.crop_cycle.plot_id != setup.plot.id:
        raise ValueError("crop_cycle.plot_id must match plot.id")
    if setup.device.plot_id != setup.plot.id:
        raise ValueError("device.plot_id must match plot.id")
    if any(plant.crop_cycle_id != setup.crop_cycle.id for plant in setup.plants):
        raise ValueError("Every plant.crop_cycle_id must match crop_cycle.id")
    date.fromisoformat(setup.crop_cycle.planting_date)

    now = time.time()
    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            "INSERT INTO plots(id, name, location, soil_type, created_at) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, location=excluded.location, soil_type=excluded.soil_type",
            (setup.plot.id, setup.plot.name, setup.plot.location, setup.plot.soil_type, now),
        )
        connection.execute(
            "INSERT INTO crop_cycles(id, plot_id, crop_name, variety, planting_date, status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "plot_id=excluded.plot_id, crop_name=excluded.crop_name, variety=excluded.variety, "
            "planting_date=excluded.planting_date, status=excluded.status",
            (
                setup.crop_cycle.id,
                setup.crop_cycle.plot_id,
                setup.crop_cycle.crop_name,
                setup.crop_cycle.variety,
                setup.crop_cycle.planting_date,
                setup.crop_cycle.status,
                now,
            ),
        )
        connection.execute(
            "INSERT INTO devices(id, plot_id, device_code, firmware_version, expected_interval_seconds, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
            "plot_id=excluded.plot_id, device_code=excluded.device_code, "
            "firmware_version=excluded.firmware_version, expected_interval_seconds=excluded.expected_interval_seconds",
            (
                setup.device.id,
                setup.device.plot_id,
                setup.device.device_code,
                setup.device.firmware_version,
                setup.device.expected_interval_seconds,
                now,
            ),
        )
        for plant in setup.plants:
            connection.execute(
                "INSERT INTO plants(id, crop_cycle_id, plant_code, row_number, position, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET "
                "crop_cycle_id=excluded.crop_cycle_id, plant_code=excluded.plant_code, "
                "row_number=excluded.row_number, position=excluded.position",
                (plant.id, plant.crop_cycle_id, plant.plant_code, plant.row_number, plant.position, now),
            )
        connection.commit()

    return {
        "plot_id": setup.plot.id,
        "crop_cycle_id": setup.crop_cycle.id,
        "device_id": setup.device.id,
        "plant_ids": [plant.id for plant in setup.plants],
    }


def build_default_setup(
    plot_id: str,
    crop_cycle_id: str,
    device_id: str,
    planting_date: str,
) -> MonitoringSetupRequest:
    return MonitoringSetupRequest(
        plot=PlotCreate(id=plot_id, name="Primary Nai Miris plot"),
        crop_cycle=CropCycleCreate(
            id=crop_cycle_id,
            plot_id=plot_id,
            planting_date=planting_date,
        ),
        device=DeviceCreate(
            id=device_id,
            plot_id=plot_id,
            device_code=device_id,
            expected_interval_seconds=FIVE_MINUTES_SECONDS,
        ),
    )


def get_monitoring_setup(db_path: str) -> Dict[str, List[Dict[str, object]]]:
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        return {
            "plots": [dict(row) for row in connection.execute("SELECT * FROM plots ORDER BY id")],
            "crop_cycles": [dict(row) for row in connection.execute("SELECT * FROM crop_cycles ORDER BY id")],
            "plants": [dict(row) for row in connection.execute("SELECT * FROM plants ORDER BY id")],
            "devices": [dict(row) for row in connection.execute("SELECT * FROM devices ORDER BY id")],
        }


def canonical_to_reading(payload: CanonicalSensorPayload) -> Reading:
    sensors = payload.sensors
    return Reading(
        timestamp=payload.recorded_at,
        humidity=sensors.relative_humidity_percent,
        temperature_c=sensors.air_temperature_c,
        heat_index_c=sensors.heat_index_c,
        soil_moisture=sensors.soil_moisture_percent,
        soil_analog=sensors.soil_moisture_raw,
        soil_temperature_c=sensors.soil_temperature_c,
        ec=sensors.ec_ms_cm,
        calibration_version=payload.calibration_version,
        source=payload.source,
    )


def legacy_to_canonical(
    reading: Reading,
    device_id: str,
    plot_id: str,
    crop_cycle_id: str,
    plant_id: Optional[str] = None,
) -> CanonicalSensorPayload:
    return CanonicalSensorPayload(
        device_id=device_id,
        plot_id=plot_id,
        crop_cycle_id=crop_cycle_id,
        plant_id=plant_id,
        recorded_at=reading.timestamp,
        sensors=SensorValues(
            air_temperature_c=reading.temperature_c,
            relative_humidity_percent=reading.humidity,
            heat_index_c=reading.heat_index_c,
            soil_temperature_c=reading.soil_temperature_c,
            soil_moisture_raw=reading.soil_analog,
            soil_moisture_percent=reading.soil_moisture,
            ec_ms_cm=reading.ec,
        ),
        calibration_version=reading.calibration_version,
        source=reading.source or "legacy",
    )


def _ensure_identifiers_exist(connection: sqlite3.Connection, payload: CanonicalSensorPayload) -> None:
    checks = (
        ("devices", payload.device_id),
        ("plots", payload.plot_id),
        ("crop_cycles", payload.crop_cycle_id),
    )
    if payload.plant_id:
        checks += (("plants", payload.plant_id),)
    for table, identifier in checks:
        if connection.execute(f"SELECT 1 FROM {table} WHERE id = ?", (identifier,)).fetchone() is None:
            raise ValueError(f"Unknown {table[:-1]} id: {identifier}")


def store_five_minute_payload(
    db_path: str,
    payload: CanonicalSensorPayload,
    quality_status: str,
    quality_issues: List[str],
) -> IngestionResult:
    reading = canonical_to_reading(payload)
    recorded_at = float(payload.recorded_at if payload.recorded_at is not None else time.time())
    bucket_start = math.floor(recorded_at / FIVE_MINUTES_SECONDS) * FIVE_MINUTES_SECONDS
    received_at = time.time()

    values = (
        recorded_at,
        reading.humidity,
        reading.temperature_c,
        reading.heat_index_c,
        reading.soil_moisture,
        reading.soil_analog,
        reading.soil_temperature_c,
        reading.ec,
        quality_status,
        reading.calibration_version,
        reading.source,
        payload.device_id,
        payload.plot_id,
        payload.crop_cycle_id,
        payload.plant_id,
        bucket_start,
        received_at,
        json.dumps(quality_issues),
        payload.model_dump_json(),
        payload.schema_version,
    )

    with closing(sqlite3.connect(db_path)) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _ensure_identifiers_exist(connection, payload)
        existing = connection.execute(
            "SELECT id FROM readings WHERE device_id = ? AND bucket_start = ?",
            (payload.device_id, bucket_start),
        ).fetchone()
        connection.execute(
            """
            INSERT INTO readings(
                timestamp, humidity, temperature_c, heat_index_c, soil_moisture,
                soil_analog, soil_temperature_c, ec, quality_status,
                calibration_version, source, device_id, plot_id, crop_cycle_id,
                plant_id, bucket_start, received_at, quality_issues, raw_payload,
                schema_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(device_id, bucket_start) WHERE device_id IS NOT NULL AND bucket_start IS NOT NULL
            DO UPDATE SET
                timestamp=excluded.timestamp, humidity=excluded.humidity,
                temperature_c=excluded.temperature_c, heat_index_c=excluded.heat_index_c,
                soil_moisture=excluded.soil_moisture, soil_analog=excluded.soil_analog,
                soil_temperature_c=excluded.soil_temperature_c, ec=excluded.ec,
                quality_status=excluded.quality_status,
                calibration_version=excluded.calibration_version, source=excluded.source,
                plot_id=excluded.plot_id, crop_cycle_id=excluded.crop_cycle_id,
                plant_id=excluded.plant_id, received_at=excluded.received_at,
                quality_issues=excluded.quality_issues, raw_payload=excluded.raw_payload,
                schema_version=excluded.schema_version
            """,
            values,
        )
        row = connection.execute(
            "SELECT id FROM readings WHERE device_id = ? AND bucket_start = ?",
            (payload.device_id, bucket_start),
        ).fetchone()
        connection.execute(
            "UPDATE devices SET last_seen_at = ?, status = 'online' WHERE id = ?",
            (recorded_at, payload.device_id),
        )
        connection.commit()

    return IngestionResult(
        status="updated" if existing else "inserted",
        reading_id=int(row[0]),
        recorded_at=recorded_at,
        bucket_start=bucket_start,
        quality_status=quality_status,
        quality_issues=quality_issues,
    )


def list_device_statuses(db_path: str, now: Optional[float] = None) -> List[DeviceStatus]:
    current_time = float(now if now is not None else time.time())
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            "SELECT id, device_code, plot_id, last_seen_at, expected_interval_seconds FROM devices ORDER BY id"
        ).fetchall()
        results: List[DeviceStatus] = []
        for row in rows:
            last_seen = row["last_seen_at"]
            if last_seen is None:
                seconds_since_seen = None
                status = "never_seen"
            else:
                seconds_since_seen = max(0.0, current_time - float(last_seen))
                status = "offline" if seconds_since_seen > row["expected_interval_seconds"] * 2 else "online"
            connection.execute("UPDATE devices SET status = ? WHERE id = ?", (status, row["id"]))
            results.append(
                DeviceStatus(
                    device_id=row["id"],
                    device_code=row["device_code"],
                    plot_id=row["plot_id"],
                    last_seen_at=last_seen,
                    expected_interval_seconds=row["expected_interval_seconds"],
                    seconds_since_seen=round(seconds_since_seen, 1) if seconds_since_seen is not None else None,
                    status=status,
                )
            )
        connection.commit()
    return results


def aggregate_readings(
    db_path: str,
    interval: str,
    since: float,
    device_id: Optional[str] = None,
) -> AggregationResponse:
    period_seconds = 3600 if interval == "hour" else 86400
    query = "SELECT * FROM readings WHERE timestamp >= ?"
    params: List[object] = [since]
    if device_id:
        query += " AND device_id = ?"
        params.append(device_id)
    query += " ORDER BY timestamp ASC"

    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        rows = [dict(row) for row in connection.execute(query, params).fetchall()]

    groups: Dict[float, List[Dict[str, object]]] = {}
    for row in rows:
        period_start = math.floor(float(row["timestamp"]) / period_seconds) * period_seconds
        groups.setdefault(period_start, []).append(row)

    periods: List[AggregatedPeriod] = []
    for period_start, period_rows in sorted(groups.items()):
        averages: Dict[str, Optional[float]] = {}
        minimums: Dict[str, Optional[float]] = {}
        maximums: Dict[str, Optional[float]] = {}
        for field in AGGREGATE_FIELDS:
            values = [float(row[field]) for row in period_rows if row.get(field) is not None]
            averages[field] = sum(values) / len(values) if values else None
            minimums[field] = min(values) if values else None
            maximums[field] = max(values) if values else None
        valid_count = sum(row.get("quality_status") == "valid" for row in period_rows)
        periods.append(
            AggregatedPeriod(
                period_start=period_start,
                period_end=period_start + period_seconds,
                sample_count=len(period_rows),
                valid_sample_count=valid_count,
                valid_sample_percent=round(valid_count / len(period_rows) * 100.0, 1),
                averages=averages,
                minimums=minimums,
                maximums=maximums,
            )
        )
    return AggregationResponse(interval=interval, device_id=device_id, periods=periods)
