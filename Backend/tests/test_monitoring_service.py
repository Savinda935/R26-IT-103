import tempfile
import unittest
from pathlib import Path

from monitoring.data_models import (
    CanonicalSensorPayload,
    CropCycleCreate,
    DeviceCreate,
    MonitoringSetupRequest,
    PlotCreate,
    SensorValues,
)
from monitoring.data_service import (
    aggregate_readings,
    list_device_statuses,
    register_monitoring_setup,
    store_five_minute_payload,
)
from monitoring.models import Reading
from monitoring import service


class ReadingQualityTests(unittest.TestCase):
    def test_valid_reading(self):
        result = service.validate_reading_quality(
            Reading(
                humidity=72,
                temperature_c=28,
                soil_moisture=55,
                soil_analog=1500,
                soil_temperature_c=26,
                ec=1.1
            )
        )

        self.assertEqual(result.status, "valid")
        self.assertEqual(result.issues, [])
        self.assertEqual(result.valid_field_count, 6)

    def test_out_of_range_reading_is_suspect(self):
        result = service.validate_reading_quality(
            Reading(humidity=140, temperature_c=28)
        )

        self.assertEqual(result.status, "suspect")
        self.assertIn("humidity:out_of_physical_range", result.issues)

    def test_adc_rail_value_is_suspect(self):
        result = service.validate_reading_quality(Reading(soil_analog=4095))
        self.assertEqual(result.status, "suspect")
        self.assertIn("soil_analog:adc_rail_value", result.issues)

    def test_empty_reading_is_missing(self):
        result = service.validate_reading_quality(Reading())
        self.assertEqual(result.status, "missing")


class SensorWindowTests(unittest.TestCase):
    def test_persistent_low_soil_moisture_is_measured(self):
        rows = [
            {
                "timestamp": 0.0,
                "soil_analog": 800.0,
                "soil_temperature_c": 27.0,
                "temperature_c": 28.0,
                "humidity": 76.0,
                "ec": 0.9,
                "quality_status": "valid"
            },
            {
                "timestamp": 1800.0,
                "soil_analog": 850.0,
                "soil_temperature_c": 27.0,
                "temperature_c": 28.0,
                "humidity": 76.0,
                "ec": 0.9,
                "quality_status": "valid"
            },
            {
                "timestamp": 3600.0,
                "soil_analog": 900.0,
                "soil_temperature_c": 27.0,
                "temperature_c": 28.0,
                "humidity": 76.0,
                "ec": 0.9,
                "quality_status": "valid"
            }
        ]

        result = service.analyze_sensor_window(rows, "stage1")

        self.assertEqual(result.parameters["soil_moisture"].status, "low")
        self.assertEqual(result.parameters["soil_moisture"].hours_low, 1.0)
        self.assertEqual(result.parameters["soil_moisture"].percent_in_range, 0.0)
        self.assertEqual(result.warning_level, "yellow")
        self.assertTrue(any(item["factor"] == "soil_moisture" for item in result.contributing_factors))

    def test_invalid_stage_falls_back_to_stage_one(self):
        result = service.analyze_sensor_window([], "not-a-stage")
        self.assertEqual(result.stage_id, "stage1")


class ReadingStorageTests(unittest.TestCase):
    def test_quality_metadata_is_stored(self):
        original_path = service.DB_PATH
        with tempfile.TemporaryDirectory() as directory:
            service.DB_PATH = str(Path(directory) / "readings.db")
            try:
                service.init_db()
                service.insert_reading(
                    Reading(
                        timestamp=100.0,
                        humidity=70,
                        temperature_c=28,
                        calibration_version="field-v1",
                        source="test"
                    )
                )
                stored = service.fetch_readings(limit=1)[0]
            finally:
                service.DB_PATH = original_path

        self.assertEqual(stored["quality_status"], "valid")
        self.assertEqual(stored["calibration_version"], "field-v1")
        self.assertEqual(stored["source"], "test")


class PhaseOneDataTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_directory.name) / "phase1.db")
        original_path = service.DB_PATH
        service.DB_PATH = self.db_path
        try:
            service.init_db()
        finally:
            service.DB_PATH = original_path

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_setup_and_five_minute_upsert(self):
        payload = CanonicalSensorPayload(
            device_id="device-001",
            plot_id="plot-001",
            crop_cycle_id="cycle-001",
            recorded_at=600.0,
            sensors=SensorValues(
                air_temperature_c=28,
                relative_humidity_percent=70,
                soil_moisture_percent=52,
                soil_moisture_raw=1600,
                soil_temperature_c=26,
                ec_ms_cm=1.1,
            ),
        )
        first = store_five_minute_payload(self.db_path, payload, "valid", [])
        payload.recorded_at = 780.0
        payload.sensors.air_temperature_c = 29
        second = store_five_minute_payload(self.db_path, payload, "valid", [])

        self.assertEqual(first.status, "inserted")
        self.assertEqual(second.status, "updated")
        self.assertEqual(first.reading_id, second.reading_id)

    def test_hourly_and_daily_aggregation(self):
        for recorded_at, temperature in ((3600.0, 26.0), (3900.0, 30.0), (90000.0, 28.0)):
            payload = CanonicalSensorPayload(
                device_id="device-001",
                plot_id="plot-001",
                crop_cycle_id="cycle-001",
                recorded_at=recorded_at,
                sensors=SensorValues(air_temperature_c=temperature),
            )
            store_five_minute_payload(self.db_path, payload, "valid", [])

        hourly = aggregate_readings(self.db_path, "hour", since=0)
        daily = aggregate_readings(self.db_path, "day", since=0)

        self.assertEqual(len(hourly.periods), 2)
        self.assertEqual(hourly.periods[0].averages["temperature_c"], 28.0)
        self.assertEqual(len(daily.periods), 2)

    def test_device_offline_detection(self):
        payload = CanonicalSensorPayload(
            device_id="device-001",
            plot_id="plot-001",
            crop_cycle_id="cycle-001",
            recorded_at=1000.0,
            sensors=SensorValues(air_temperature_c=28),
        )
        store_five_minute_payload(self.db_path, payload, "valid", [])

        online = list_device_statuses(self.db_path, now=1500.0)[0]
        offline = list_device_statuses(self.db_path, now=1701.0)[0]

        self.assertEqual(online.status, "online")
        self.assertEqual(offline.status, "offline")

    def test_setup_rejects_mismatched_identifiers(self):
        setup = MonitoringSetupRequest(
            plot=PlotCreate(id="plot-x", name="Plot X"),
            crop_cycle=CropCycleCreate(
                id="cycle-x",
                plot_id="different-plot",
                planting_date="2026-08-17",
            ),
            device=DeviceCreate(id="device-x", plot_id="plot-x", device_code="ESP32-X"),
        )
        with self.assertRaises(ValueError):
            register_monitoring_setup(self.db_path, setup)

    def test_firebase_push_id_timestamp_is_decoded(self):
        items = service.parse_firebase_history_items({
            "history": {
                "-OsLCW56ufKupFxuKLID": {
                    "dht_temperature_c": 25.3,
                    "humidity": 60.5,
                }
            }
        })
        self.assertEqual(len(items), 1)
        self.assertIsInstance(items[0].get("timestamp"), float)
        self.assertGreater(items[0]["timestamp"], 1_700_000_000)


if __name__ == "__main__":
    unittest.main()
