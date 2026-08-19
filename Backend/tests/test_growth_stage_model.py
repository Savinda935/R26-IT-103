import unittest

from monitoring.ai_model import classify_stage_probabilities


METADATA = {
    "model_name": "mobilenetv2_growth_stage",
    "version": "test-v1",
    "classes": ["seedling", "vegetative", "reproductive", "maturity"],
    "accept_threshold": 0.75,
    "provisional_threshold": 0.50,
}


class GrowthStageConfidenceTests(unittest.TestCase):
    def test_high_confidence_prediction_is_accepted(self):
        result = classify_stage_probabilities([0.02, 0.82, 0.08, 0.08], METADATA)
        self.assertEqual(result["predicted_stage"], "vegetative")
        self.assertEqual(result["decision"], "accepted")
        self.assertTrue(result["accepted"])

    def test_medium_confidence_prediction_requires_confirmation(self):
        result = classify_stage_probabilities([0.62, 0.10, 0.18, 0.10], METADATA)
        self.assertEqual(result["predicted_stage"], "seedling")
        self.assertEqual(result["decision"], "provisional")
        self.assertTrue(result["requires_confirmation"])

    def test_low_confidence_prediction_is_rejected(self):
        result = classify_stage_probabilities([0.24, 0.26, 0.28, 0.22], METADATA)
        self.assertIsNone(result["predicted_stage"])
        self.assertEqual(result["decision"], "rejected")
        self.assertFalse(result["accepted"])

    def test_class_count_must_match_model_output(self):
        with self.assertRaises(ValueError):
            classify_stage_probabilities([0.5, 0.5], METADATA)


if __name__ == "__main__":
    unittest.main()
