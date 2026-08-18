# Monitoring Phase 1: field and data setup

This document defines the sensor contract used by the backend and the physical work that must be completed before agronomic thresholds are treated as field-valid.

## Canonical sensors

| Field | Meaning | Unit | Recommended device/placement |
|---|---|---|---|
| `air_temperature_c` | Air temperature | degrees Celsius | Confirmed DHT22 inside a ventilated radiation shield, shaded and at canopy height |
| `relative_humidity_percent` | Relative humidity | percent | Confirmed same DHT22 as air temperature; do not allow direct rain or irrigation contact |
| `heat_index_c` | Calculated heat index | degrees Celsius | Calculate from air temperature and humidity in firmware or leave null |
| `soil_temperature_c` | Root-zone soil temperature | degrees Celsius | Confirmed waterproof DS18B20 approximately 10 cm deep near, but not touching, the plant stem |
| `soil_moisture_raw` | Unconverted moisture ADC reading | ADC counts | Confirmed Capacitive Soil Moisture Sensor V2.0 in representative root-zone soil, inserted consistently and away from metal |
| `soil_moisture_percent` | Calibrated moisture estimate | percent | Calculated from the recorded dry/wet calibration values; never substitute raw ADC counts |
| `ec_ms_cm` | Electrical conductivity from the documented EC measurement method | mS/cm | Use the EC probe according to its manufacturer method; document whether it measures irrigation water, nutrient solution, or soil solution |

Use at least one sensing device per management zone. Do not claim that one probe represents an entire field if soil, shade, drainage, or irrigation differs substantially across the plot.

## Confirmed hardware inventory

- Soil moisture: Capacitive Soil Moisture Sensor V2.0
- Soil temperature: waterproof DS18B20
- Air temperature: DHT22
- Relative humidity: the same DHT22
- EC: pending; no sensor selected or installed
- ESP32 board model, ADC resolution, pins, and firmware version: pending

The attached calibration protocol mentions a V1.2 sensor as a recommendation, but this project uses the student-confirmed V2.0 sensor. Calibration constants must therefore come from the actual V2.0 unit and field soil rather than typical values in the protocol.

## Identifiers

Initial defaults are:

- Plot: `plot-001`
- Crop cycle: `cycle-001`
- Device: `device-001`
- Plant: optional during plot-level sensing

Override these with `MONITORING_PLOT_ID`, `MONITORING_CROP_CYCLE_ID`, `MONITORING_DEVICE_ID`, `MONITORING_PLANT_ID`, and `MONITORING_PLANTING_DATE` in the backend environment. Register or update the complete setup with `POST /api/monitoring/setup`.

## Firebase contract

Write the object shown in `Backend/monitoring/firebase_payload.example.json` to the configured Firebase root. All timestamps are Unix seconds in UTC. Fields that are not installed may be `null`; do not send fabricated zero values.

The backend temporarily accepts the legacy keys `temperature_c`, `humidity`, `soil_analog`, `soil_moisture`, `soil_temp_c`, `soil_temperature_c`, `ds18b20_temperature_c`, and `ec`. New firmware should use only the canonical names.

## Soil-moisture calibration work

1. Install the probe in the same soil type used for Nai Miris.
2. Record at least 20 stable raw readings in air/dry soil and calculate the mean.
3. Saturate a representative soil sample, allow free drainage, place the probe consistently, and record at least 20 stable wet readings.
4. Repeat the dry and wet procedure three times.
5. Enter the final dry and wet reference values into ESP32 conversion code. For probes where wet soil produces the lower ADC value, use `moisture_percent = (raw_dry - raw) / (raw_dry - raw_wet) * 100`, then clamp the result to 0–100%. This maps the wet reference to 100% and the dry reference to 0%.
6. Confirm that output increases/decreases in the expected direction and is clamped to 0–100%.
7. Set `calibration_version` to a traceable value such as `field-v1-2026-08-20`.
8. Retain the raw readings, calculated means, soil type, date, probe serial number, and photographs as project evidence.

The percentage is a calibrated project estimate, not laboratory volumetric water content unless it is validated against gravimetric samples.

Do not use `map(raw, wet, dry, 0, 100)` for moisture percentage: that expression maps the wet reference to 0% and the dry reference to 100%. If Arduino `map()` is used, the moisture-oriented mapping is `map(raw, dry, wet, 0, 100)`, followed by `constrain(value, 0, 100)`. The floating-point formula above is preferred.

## EC calibration work

1. Identify the exact EC sensor and whether it measures water, nutrient solution, or soil solution.
2. Clean the probe according to its manual.
3. Use fresh standard calibration solutions that cover the expected range.
4. Record solution value, solution temperature, raw sensor output, corrected reading, date, and probe serial number.
5. Repeat each standard at least three times.
6. Verify with a check solution not used to fit the calibration.
7. Document temperature compensation.
8. Create a new `calibration_version` whenever the probe or calibration coefficients change.

Do not use the current stage EC thresholds for fertilizer dosage decisions until the measurement method and field limits are reviewed by an agriculture-domain supervisor.

Do not mix ppm and µS/cm during calibration. A 342 ppm solution and a 1413 µS/cm solution are not interchangeable numeric targets. Use the units and conversion factor specified by the exact EC-probe manufacturer. The simple expression `known_ppm / measured_voltage` is insufficient unless the probe documentation explicitly defines that model.

## Current Firebase status (reviewed 2026-08-17)

The configured Firebase database is reachable and has `sensors` and `history` nodes. The current legacy payload is accepted by the backend, including `dht_temperature_c` and Firebase push-key timestamps.

The observed values are test/uncommissioned data, not field-calibrated evidence:

- DS18B20 reports `-127 C`, which is the disconnected/read-error value and is marked suspect.
- Soil ADC is pinned at `4095` and reported moisture is `0%`; this is marked as an ADC rail condition until the probe is connected and calibrated.
- EC is not currently present.
- History records use `uptime_sec` and Firebase push IDs rather than explicit Unix timestamps. The backend decodes the timestamp embedded in each push ID, but new firmware should send `recorded_at` explicitly.
- Both `dht_temperature_c` and an older `temperature_c` field are present and disagree. The backend now prioritizes `dht_temperature_c`; new firmware should publish only `air_temperature_c`.

## Storage and device status

- The backend may poll Firebase more frequently, but it stores one row per device per five-minute UTC bucket.
- A newer reading in the same bucket updates that bucket instead of creating a duplicate.
- A device is `offline` after it misses two expected reporting intervals. The default interval is five minutes, so the default offline threshold is ten minutes.
- Hourly and daily summaries are available from `GET /api/monitoring/analytics/aggregate`.
- Raw five-minute records remain the evidence source; aggregates are calculated from those records.

## Demonstration checklist

- Show the physical placement of every sensor.
- Show calibration sheets and photographs.
- Show one canonical Firebase payload.
- Show the same reading in `GET /api/monitoring/readings/latest`.
- Send multiple readings in one five-minute period and show that only one bucket is stored.
- Show hourly and daily aggregation responses.
- Disconnect the ESP32 for more than two reporting intervals and show the mobile device status changing to `OFFLINE`.
