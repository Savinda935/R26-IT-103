# Phase 3 Growth-Stage Model

## Observable classes

Use one verified whole-plant label per image. Visible characteristics are the primary label evidence; days after transplanting are supporting guidance because field conditions can shift development timing.

| Class | BBCH principal stages | Nai Miris/Chilli guidance | Required observable characteristics |
| --- | --- | --- | --- |
| `seedling` | 0–1: germination, emergence, first leaves | Approximately 0–14 days after transplanting | Cotyledons emerged, 1–4 true leaves, small canopy (typically below 10 cm), slow early visible growth, and no flowers or fruit. |
| `vegetative` | 2–4: side-shoot/tillering, stem elongation, leaf development | Approximately 14–45 days after transplanting | Rapid leaf production, branching, increasing plant height and canopy closure, with no flowers visible. |
| `reproductive` | 5–7: inflorescence emergence, flowering, fruit development | Approximately 35–70 days after transplanting | First flowers, open flowers, fruit set, or developing green fruit; vegetative growth is no longer the only dominant feature. |
| `maturity` | 8–9: ripening, senescence, harvest readiness | Approximately 90–150 days after transplanting | Fruit color change toward the cultivar's ripe color, harvest-ready fruit, reduced vegetative growth, or lower-leaf senescence. |

The reproductive and maturity labels must be based on visible structures rather than age alone. Flowering and fruit development remain one `reproductive` class because they overlap. Record `flower_present` and `fruit_present` separately for later indicator analysis. The existing binary leaf-presence model remains an early seedling/germination sub-analysis and is not a fifth stage class.

### Sensor context

The reference table associates the stages with these trends:

- `seedling`: relatively stable moisture, limited canopy evapotranspiration, stable EC, and no clear canopy-temperature difference.
- `vegetative`: higher moisture depletion, increasing canopy-temperature difference, gradual EC decline, and high humidity/transpiration demand.
- `reproductive`: peak moisture depletion and nutrient demand, maximum canopy-temperature difference, and high transpiration load.
- `maturity`: reduced moisture demand and transpiration, declining canopy-temperature difference, and stable or slightly increasing EC as uptake slows.

These trends are contextual inputs for later image–IoT fusion, not image labels. Numeric limits remain provisional until the actual Nai Miris sensors, measurement method, field capacity, and calibration have been validated.

## Standardized photography protocol

- Photograph the complete plant, with only one plant in frame.
- Use approximately the same distance, camera height, and level angle each week.
- Use daylight without harsh shadow, blur, or strong backlighting.
- Use a plain background where practical and include a fixed scale marker.
- Keep the plant centered and ensure leaves, flowers, and fruit are not cropped.
- Retake dark, blurred, obstructed, or multi-plant images.
- Preserve the original image; do not apply beauty filters or color correction.
- Name files with plant and capture date, for example `P001_2026-08-19.jpg`.

Each manifest record must include `image_path`, `plant_id`, `capture_date`, `plant_age_days`, `stage_label`, flower/fruit indicators, labeler, verifier, and notes. An agriculture-domain reviewer should verify labels.

## Dataset target

- Minimum prototype: 150–200 images per class.
- Preferred: 300–500 images per class.
- Collect from at least 30–50 plants over multiple weeks.
- Include realistic differences in lighting, angle, background, and normal/delayed development.
- Never put images from one plant into multiple splits.

Copy `dataset_manifest.example.csv` to a dataset folder, replace the example rows, and store image paths relative to that CSV. Dataset images and trained artifacts are intentionally excluded from Git.

## Training

From `Backend`:

```powershell
python training/growth_stage/train.py `
  --manifest path/to/dataset/manifest.csv `
  --output-dir artifacts/growth_stage `
  --version v1-20260819
```

The pipeline freezes an ImageNet-pretrained MobileNetV2 backbone, trains the classification head, fine-tunes the upper 30 layers, selects the lowest-validation-loss checkpoint, and evaluates the untouched plant-separated test set.

Outputs include:

- `growth_stage.keras`
- `growth_stage.metadata.json`
- `evaluation.json`, including confusion matrix and per-class precision, recall, and F1

Copy the selected model and metadata beside `Backend/monitoring/ai_model.py`, or configure `GROWTH_STAGE_MODEL_PATH` and `GROWTH_STAGE_METADATA_PATH`.

Inference endpoint:

```text
POST /api/monitoring/analytics/growth-stage/analyze
multipart field: image
```

Confidence behavior is metadata-driven: at least `0.75` is accepted, `0.50–0.74` is provisional and needs confirmation, and below `0.50` is rejected with a clearer-image request.
