import importlib
import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

import numpy as np
from PIL import Image


MODEL_PATH = Path(
    os.environ.get(
        "GROWTH_MODEL_PATH",
        Path(__file__).with_name("growth.pt")
    )
)

STAGE_MODEL_PATH = Path(
    os.environ.get("GROWTH_STAGE_MODEL_PATH", Path(__file__).with_name("growth_stage.keras"))
)
STAGE_METADATA_PATH = Path(
    os.environ.get("GROWTH_STAGE_METADATA_PATH", Path(__file__).with_name("growth_stage.metadata.json"))
)
DEFAULT_STAGE_CLASSES = ["seedling", "vegetative", "reproductive", "maturity"]


@lru_cache(maxsize=1)
def load_growth_model():
    """Load the trained growth model once and reuse it for future predictions."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Growth model file not found: {MODEL_PATH}")

    try:
        torch = importlib.import_module("torch")
    except ImportError as error:
        raise RuntimeError("PyTorch is not installed. Install backend requirements or provide a fallback model.") from error

    try:
        return torch.jit.load(str(MODEL_PATH), map_location="cpu")
    except Exception:
        return torch.load(str(MODEL_PATH), map_location="cpu")


def _coerce_leaf_prediction(value: object) -> int:
    """Convert various prediction formats to binary leaf presence (0 or 1)."""
    if isinstance(value, bool):
        return int(value)

    if isinstance(value, (int, float)):
        return 1 if float(value) >= 0.5 else 0

    if isinstance(value, dict):
        for key in ("leaf_prediction", "prediction", "result", "label"):
            if key in value:
                return _coerce_leaf_prediction(value[key])

    if isinstance(value, (list, tuple)) and value:
        return _coerce_leaf_prediction(value[0])

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "leaf", "present", "detected"}:
            return 1
        if normalized in {"0", "false", "absent", "missing", "none"}:
            return 0

    return 0


def _fallback_leaf_prediction(image_path: str) -> int:
    """Fallback leaf detection using vegetation ratio analysis."""
    image = Image.open(image_path).convert("RGB").resize((256, 256))
    pixels = np.asarray(image, dtype=np.float32) / 255.0
    green = pixels[:, :, 1]
    red = pixels[:, :, 0]
    blue = pixels[:, :, 2]

    vegetation_mask = (green > red * 1.04) & (green > blue * 1.02) & ((green - red) > 0.03)
    leaf_ratio = float(np.count_nonzero(vegetation_mask)) / max(float(vegetation_mask.size), 1.0)
    return 1 if leaf_ratio >= 0.04 else 0


def _predict_from_growth_model(model, image_path: str) -> int:
    """Run prediction using the trained growth model."""
    try:
        torch = importlib.import_module("torch")
    except ImportError:
        return _fallback_leaf_prediction(image_path)

    image = Image.open(image_path).convert("RGB").resize((224, 224))
    array = np.asarray(image, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(array).permute(2, 0, 1).unsqueeze(0)

    with torch.no_grad():
        prediction = model(tensor)

    if isinstance(prediction, (list, tuple)) and prediction:
        prediction = prediction[0]

    if hasattr(prediction, "detach"):
        prediction = prediction.detach().cpu().numpy()

    return _coerce_leaf_prediction(prediction)


def predict_leaf_presence(image_path: str) -> int:
    """Predict leaf presence from an image using the growth model with fallback."""
    try:
        model = load_growth_model()
        return _predict_from_growth_model(model, image_path)
    except (FileNotFoundError, RuntimeError):
        return _fallback_leaf_prediction(image_path)
    except Exception:
        return _fallback_leaf_prediction(image_path)


@lru_cache(maxsize=1)
def load_growth_stage_model():
    """Load the exported Keras stage classifier and its training metadata."""
    if not STAGE_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Growth-stage model not found: {STAGE_MODEL_PATH}. Run the Phase 3 training pipeline first."
        )
    if not STAGE_METADATA_PATH.exists():
        raise FileNotFoundError(f"Growth-stage metadata not found: {STAGE_METADATA_PATH}")

    try:
        tensorflow = importlib.import_module("tensorflow")
    except ImportError as error:
        raise RuntimeError("TensorFlow is required for growth-stage inference.") from error

    metadata = json.loads(STAGE_METADATA_PATH.read_text(encoding="utf-8"))
    model = tensorflow.keras.models.load_model(STAGE_MODEL_PATH)
    return model, metadata


def classify_stage_probabilities(probabilities, metadata: Dict) -> Dict[str, object]:
    """Apply metadata-driven confidence rejection to model probabilities."""
    classes = metadata.get("classes") or DEFAULT_STAGE_CLASSES
    values = [float(value) for value in np.asarray(probabilities).reshape(-1)]
    if len(values) != len(classes):
        raise ValueError("Model output count does not match metadata classes")

    best_index = int(np.argmax(values))
    confidence = values[best_index]
    accept_threshold = float(metadata.get("accept_threshold", 0.75))
    provisional_threshold = float(metadata.get("provisional_threshold", 0.50))

    if confidence >= accept_threshold:
        decision, accepted, confirmation = "accepted", True, False
        message = "Growth stage classified with sufficient confidence."
    elif confidence >= provisional_threshold:
        decision, accepted, confirmation = "provisional", False, True
        message = "Provisional result; farmer or reviewer confirmation is required."
    else:
        decision, accepted, confirmation = "rejected", False, False
        message = "Unable to classify reliably; capture a clearer whole-plant image."

    return {
        "predicted_stage": classes[best_index] if decision != "rejected" else None,
        "confidence": round(confidence, 6),
        "decision": decision,
        "accepted": accepted,
        "requires_confirmation": confirmation,
        "message": message,
        "model_name": metadata.get("model_name", "mobilenetv2_growth_stage"),
        "model_version": metadata.get("version", "unknown"),
        "classes": classes,
        "probabilities": {name: round(value, 6) for name, value in zip(classes, values)},
    }


def predict_growth_stage(image_path: str) -> Dict[str, object]:
    """Predict an observable whole-plant stage while retaining leaf sub-analysis."""
    model, metadata = load_growth_stage_model()
    image_size = metadata.get("image_size", [224, 224])
    image = Image.open(image_path).convert("RGB").resize(tuple(image_size))
    array = np.asarray(image, dtype=np.float32)
    prediction = model.predict(np.expand_dims(array, axis=0), verbose=0)[0]
    result = classify_stage_probabilities(prediction, metadata)
    result["leaf_prediction"] = predict_leaf_presence(image_path)
    return result
