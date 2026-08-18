# Monitoring Phase 2: explainable sensor warnings

## Processing flow

1. Read the selected device's stored five-minute samples for the requested time window.
2. Load the selected growth stage's active threshold profiles from SQLite.
3. Exclude missing, non-finite, field-invalid, and uncalibrated moisture values.
4. Calculate latest state, percentage outside range, hours low/high, longest consecutive abnormal period, and trend per hour.
5. Convert deviation, persistence, and trend into risk points.
6. Map the total score to a warning level.
7. Attach deterministic recommendations and store/update the warning event.

## Warning levels

| Score | Level | Meaning |
|---:|---|---|
| 0–24 | Green | No persistent stage-threshold warning detected |
| 25–49 | Yellow | Advisory; inspect and verify the condition |
| 50–74 | Orange | Corrective action is recommended |
| 75–100 | Red | Urgent inspection is required |

The score is capped at 100. A parameter contributes points from the percentage of samples outside its range, current deviation, persistence across at least two reporting intervals, and a worsening trend.

## Safety rules

- Raw capacitive-sensor ADC values are stored for calibration and diagnostics but are not used for irrigation decisions.
- Soil-moisture percentage is excluded until a `calibration_version` is present.
- DS18B20 `-127 C`, ADC rail values, and other field-specific quality failures are excluded from agronomic evidence.
- EC recommendations require an actual reading. Current EC thresholds are provisional and must not generate fertilizer dosage.
- Recommendations say what to inspect or verify. They do not diagnose disease or prescribe pesticide/fertilizer dosage.

## Lifecycle

- `open`: a yellow/orange/red condition created a warning.
- `acknowledged`: the farmer has seen the warning.
- `resolved`: the farmer resolved it manually or a later green evaluation automatically closed it.

Repeated evaluations update the matching open event instead of creating duplicate warnings for the same device, stage, and primary factor.

## Demonstration

Evaluate the default device and stage:

```http
POST /api/monitoring/warnings/evaluate?device_id=device-001&stage_id=stage1&window_hours=24
```

List open warnings:

```http
GET /api/monitoring/warnings?status=open&device_id=device-001
```

Acknowledge and resolve:

```http
POST /api/monitoring/warnings/1/acknowledge
Content-Type: application/json

{"note":"Farmer inspected the plot"}
```

```http
POST /api/monitoring/warnings/1/resolve
Content-Type: application/json

{"note":"Irrigation line repaired and moisture recovered"}
```

Automated tests use simulated five-minute sequences for normal readings, prolonged low calibrated moisture, increasing heat, uncalibrated moisture, and the full warning lifecycle.
