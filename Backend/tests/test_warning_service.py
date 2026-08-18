import tempfile
import unittest
from pathlib import Path

from monitoring import service
from monitoring.data_models import CanonicalSensorPayload, SensorValues
from monitoring.data_service import store_five_minute_payload
from monitoring.warning_service import (
    change_warning_status,
    evaluate_warnings,
    list_stages_from_db,
    list_threshold_profiles,
    list_warning_events,
)


class WarningEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_directory.name) / "warnings.db")
        original_path = service.DB_PATH
        service.DB_PATH = self.db_path
        try:
            service.init_db()
        finally:
            service.DB_PATH = original_path

    def tearDown(self):
        self.temp_directory.cleanup()

    def store_sequence(self, start, count, moisture, temperatures=None):
        temperatures = temperatures or [28.0] * count
        for index in range(count):
            payload = CanonicalSensorPayload(
                device_id="device-001",
                plot_id="plot-001",
                crop_cycle_id="cycle-001",
                recorded_at=start + index * 300,
                sensors=SensorValues(
                    air_temperature_c=temperatures[index],
                    relative_humidity_percent=76,
                    soil_temperature_c=27,
                    soil_moisture_raw=1600,
                    soil_moisture_percent=moisture,
                    ec_ms_cm=0.9,
                ),
                calibration_version="simulated-v1",
                source="simulation",
            )
            store_five_minute_payload(self.db_path, payload, "valid", [])

    def test_threshold_profiles_are_database_backed(self):
        profiles = list_threshold_profiles(self.db_path, "stage1")
        stages = list_stages_from_db(self.db_path)

        self.assertEqual(len(profiles), 5)
        moisture = next(item for item in profiles if item.parameter == "soil_moisture_percent")
        self.assertEqual(moisture.unit, "%")
        self.assertFalse(moisture.validated)
        self.assertEqual(stages[0]["thresholds"]["soil_moisture"]["unit"], "%")

    def test_persistent_dry_sequence_creates_explainable_warning(self):
        self.store_sequence(start=10_000, count=12, moisture=20)
        evaluation = evaluate_warnings(
            self.db_path,
            device_id="device-001",
            stage_id="stage1",
            window_hours=1,
            now=10_000 + 11 * 300,
        )

        self.assertIn(evaluation.warning_level, {"yellow", "orange", "red"})
        self.assertIsNotNone(evaluation.event_id)
        moisture = next(item for item in evaluation.evidence if item.parameter == "soil_moisture_percent")
        self.assertEqual(moisture.status, "low")
        self.assertGreaterEqual(moisture.consecutive_minutes, 50)
        self.assertTrue(any("irrigation" in item.lower() for item in evaluation.recommendations))

    def test_rising_heat_adds_trend_evidence(self):
        temperatures = [28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]
        self.store_sequence(start=20_000, count=12, moisture=75, temperatures=temperatures)
        evaluation = evaluate_warnings(
            self.db_path,
            device_id="device-001",
            stage_id="stage1",
            window_hours=1,
            now=20_000 + 11 * 300,
            persist_event=False,
        )

        temperature = next(item for item in evaluation.evidence if item.parameter == "air_temperature_c")
        self.assertEqual(temperature.status, "high")
        self.assertGreater(temperature.trend_per_hour, 0)
        self.assertGreater(temperature.risk_points, 0)

    def test_warning_lifecycle_open_acknowledge_resolve(self):
        self.store_sequence(start=30_000, count=12, moisture=20)
        evaluation = evaluate_warnings(
            self.db_path, "device-001", "stage1", 1, now=30_000 + 11 * 300
        )
        opened = list_warning_events(self.db_path, status="open")
        self.assertEqual(len(opened), 1)

        acknowledged = change_warning_status(self.db_path, evaluation.event_id, "acknowledge")
        self.assertEqual(acknowledged.status, "acknowledged")

        resolved = change_warning_status(self.db_path, evaluation.event_id, "resolve", "Irrigation checked")
        self.assertEqual(resolved.status, "resolved")
        self.assertEqual(resolved.resolution_note, "Irrigation checked")

    def test_normal_sequence_remains_green_without_event(self):
        self.store_sequence(start=40_000, count=12, moisture=75)
        evaluation = evaluate_warnings(
            self.db_path, "device-001", "stage1", 1, now=40_000 + 11 * 300
        )
        self.assertEqual(evaluation.warning_level, "green")
        self.assertIsNone(evaluation.event_id)
        self.assertEqual(list_warning_events(self.db_path), [])

    def test_uncalibrated_moisture_is_not_used_for_irrigation_warning(self):
        for index in range(12):
            payload = CanonicalSensorPayload(
                device_id="device-001",
                plot_id="plot-001",
                crop_cycle_id="cycle-001",
                recorded_at=50_000 + index * 300,
                sensors=SensorValues(
                    air_temperature_c=28,
                    relative_humidity_percent=76,
                    soil_temperature_c=27,
                    soil_moisture_raw=4095,
                    soil_moisture_percent=0,
                ),
                calibration_version=None,
                source="simulation",
            )
            store_five_minute_payload(
                self.db_path,
                payload,
                "suspect",
                ["soil_analog:adc_rail_value"],
            )

        evaluation = evaluate_warnings(
            self.db_path, "device-001", "stage1", 1, now=50_000 + 11 * 300,
            persist_event=False,
        )
        self.assertFalse(any(item.parameter == "soil_moisture_percent" for item in evaluation.evidence))
        self.assertFalse(any("irrigat" in item.lower() for item in evaluation.recommendations))


if __name__ == "__main__":
    unittest.main()
