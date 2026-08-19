"""Train and evaluate the Phase 3 Nai Miris whole-plant stage classifier.

The CSV manifest must contain image_path, plant_id, and stage_label. Splits are
made by plant_id so images from one plant never leak across datasets.
"""

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


CLASSES = ["seedling", "vegetative", "reproductive", "maturity"]
IMAGE_SIZE = (224, 224)
SEED = 20260819


def read_manifest(path: Path):
    rows = []
    with path.open(newline="", encoding="utf-8-sig") as source:
        for line, row in enumerate(csv.DictReader(source), start=2):
            missing = {"image_path", "plant_id", "stage_label"} - row.keys()
            if missing:
                raise ValueError(f"Manifest is missing columns: {sorted(missing)}")
            label = row["stage_label"].strip().lower()
            if label not in CLASSES:
                raise ValueError(f"Line {line}: unsupported stage_label {label!r}")
            image_path = (path.parent / row["image_path"]).resolve()
            if not image_path.is_file():
                raise FileNotFoundError(f"Line {line}: image not found: {image_path}")
            if not row["plant_id"].strip():
                raise ValueError(f"Line {line}: plant_id is required")
            rows.append({**row, "image_path": str(image_path), "plant_id": row["plant_id"].strip(), "stage_label": label})
    if not rows:
        raise ValueError("Manifest contains no image records")
    return rows


def split_by_plant(rows, seed=SEED):
    plants = sorted({row["plant_id"] for row in rows})
    if len(plants) < 7:
        raise ValueError("At least 7 distinct plants are required for a meaningful plant-separated split")
    random.Random(seed).shuffle(plants)
    train_end = max(1, round(len(plants) * 0.70))
    validation_end = train_end + max(1, round(len(plants) * 0.15))
    validation_end = min(validation_end, len(plants) - 1)
    groups = {
        "train": set(plants[:train_end]),
        "validation": set(plants[train_end:validation_end]),
        "test": set(plants[validation_end:]),
    }
    splits = {name: [row for row in rows if row["plant_id"] in ids] for name, ids in groups.items()}
    for name, records in splits.items():
        present = {row["stage_label"] for row in records}
        if present != set(CLASSES):
            print(f"WARNING: {name} split does not contain all classes; present={sorted(present)}")
    return splits


def make_dataset(tf, rows, batch_size, training):
    paths = [row["image_path"] for row in rows]
    labels = [CLASSES.index(row["stage_label"]) for row in rows]
    dataset = tf.data.Dataset.from_tensor_slices((paths, labels))
    if training:
        dataset = dataset.shuffle(len(rows), seed=SEED, reshuffle_each_iteration=True)

    def load_image(path, label):
        image = tf.io.decode_image(tf.io.read_file(path), channels=3, expand_animations=False)
        image.set_shape([None, None, 3])
        return tf.image.resize(image, IMAGE_SIZE), tf.one_hot(label, len(CLASSES))

    return dataset.map(load_image, num_parallel_calls=tf.data.AUTOTUNE).batch(batch_size).prefetch(tf.data.AUTOTUNE)


def build_model(tf):
    augmentation = tf.keras.Sequential([
        tf.keras.layers.RandomFlip("horizontal"),
        tf.keras.layers.RandomRotation(0.06),
        tf.keras.layers.RandomZoom(0.10),
        tf.keras.layers.RandomContrast(0.12),
    ], name="realistic_augmentation")
    base = tf.keras.applications.MobileNetV2(input_shape=(*IMAGE_SIZE, 3), include_top=False, weights="imagenet")
    base.trainable = False
    inputs = tf.keras.Input(shape=(*IMAGE_SIZE, 3), name="whole_plant_image")
    x = augmentation(inputs)
    x = tf.keras.applications.mobilenet_v2.preprocess_input(x)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.25)(x)
    outputs = tf.keras.layers.Dense(len(CLASSES), activation="softmax", name="stage_probabilities")(x)
    return tf.keras.Model(inputs, outputs), base


def compile_model(tf, model, learning_rate):
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate),
        loss="categorical_crossentropy",
        metrics=["accuracy"],
    )


def evaluate(tf, model, dataset):
    actual, predicted, confidences = [], [], []
    for images, labels in dataset:
        probabilities = model.predict(images, verbose=0)
        actual.extend(np.argmax(labels.numpy(), axis=1).tolist())
        predicted.extend(np.argmax(probabilities, axis=1).tolist())
        confidences.extend(np.max(probabilities, axis=1).tolist())
    matrix = tf.math.confusion_matrix(actual, predicted, num_classes=len(CLASSES)).numpy().tolist()
    per_class = {}
    for index, name in enumerate(CLASSES):
        tp = matrix[index][index]
        fp = sum(matrix[row][index] for row in range(len(CLASSES))) - tp
        fn = sum(matrix[index]) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[name] = {"precision": precision, "recall": recall, "f1": f1, "support": sum(matrix[index])}
    return {
        "test_size": len(actual),
        "accuracy": sum(a == p for a, p in zip(actual, predicted)) / len(actual),
        "macro_f1": sum(item["f1"] for item in per_class.values()) / len(CLASSES),
        "mean_confidence": float(np.mean(confidences)),
        "confusion_matrix": matrix,
        "per_class": per_class,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/growth_stage"))
    parser.add_argument("--version", default=datetime.now(timezone.utc).strftime("v1-%Y%m%d"))
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--head-epochs", type=int, default=15)
    parser.add_argument("--fine-tune-epochs", type=int, default=10)
    args = parser.parse_args()

    import tensorflow as tf
    tf.keras.utils.set_random_seed(SEED)
    rows = read_manifest(args.manifest.resolve())
    splits = split_by_plant(rows)
    datasets = {name: make_dataset(tf, records, args.batch_size, name == "train") for name, records in splits.items()}
    model, base = build_model(tf)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = args.output_dir / "best.keras"
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(checkpoint, monitor="val_loss", save_best_only=True),
        tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=5, restore_best_weights=True),
    ]
    compile_model(tf, model, 1e-3)
    model.fit(datasets["train"], validation_data=datasets["validation"], epochs=args.head_epochs, callbacks=callbacks)

    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False
    compile_model(tf, model, 1e-5)
    model.fit(datasets["train"], validation_data=datasets["validation"], epochs=args.fine_tune_epochs, callbacks=callbacks)

    best = tf.keras.models.load_model(checkpoint)
    metrics = evaluate(tf, best, datasets["test"])
    model_path = args.output_dir / "growth_stage.keras"
    best.save(model_path)
    metadata = {
        "model_name": "mobilenetv2_growth_stage",
        "version": args.version,
        "classes": CLASSES,
        "image_size": list(IMAGE_SIZE),
        "accept_threshold": 0.75,
        "provisional_threshold": 0.50,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": hashlib.sha256(args.manifest.read_bytes()).hexdigest(),
        "split_seed": SEED,
        "split_by": "plant_id",
        "split_counts": {name: len(records) for name, records in splits.items()},
        "class_counts": dict(Counter(row["stage_label"] for row in rows)),
        "metrics": metrics,
        "model_file": model_path.name,
    }
    (args.output_dir / "growth_stage.metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (args.output_dir / "evaluation.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
