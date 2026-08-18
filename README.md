# 🌶️ NAIMIRIS - Smart Farming Platform for Scotch Bonnet Peppers

![Status](https://img.shields.io/badge/Status-Research%20Project-success)
![AI](https://img.shields.io/badge/AI-Powered-blue)
![IoT](https://img.shields.io/badge/IoT-Enabled-orange)
![License](https://img.shields.io/badge/License-Academic-green)

---

# 📌 Project Overview

**NAIMIRIS** is an AI-powered smart farming platform designed specifically for **Scotch Bonnet Pepper (Nai Miris)** cultivation in Sri Lanka.

The system helps small-scale farmers maximize profits, reduce farming risks, and improve crop productivity using:

- Artificial Intelligence (AI)
- Machine Learning (ML)
- IoT Sensors
- Image Processing
- Data Analytics

NAIMIRIS supports farmers throughout the entire cultivation lifecycle:

✅ Pre-analysis & cultivation planning  
✅ Crop growth monitoring  
✅ Pest detection & treatment guidance  

---

# 🎯 Objectives

- Maximize farming profit and ROI
- Reduce crop losses and risks
- Provide accurate cultivation guidance
- Support data-driven farming decisions
- Improve productivity for small-scale farmers

---

# 🚀 Key Features

## 📍 AI-Based Smart Decision Support
- Image-based land analysis
- Budget-aware cultivation planning
- Resource-based crop recommendations
- Yield & profit prediction

---

## 🌱 AI + IoT Crop Growth Monitoring
- Weekly crop image analysis
- Real-time environmental monitoring
- Growth stage classification
- Irrigation & fertilizer recommendations

---

## 🐛 AI Pest Monitoring & Control
- Pest detection using leaf images
- Severity analysis (Low / Medium / High)
- Accurate pesticide dosage recommendations
- Early pest attack detection

---

# 🧠 Technologies Used

## Frontend
- React Native 

## Backend
- python
- Express.js

## Database
- Firebase
- MongoDB

## AI / ML
- Python
- TensorFlow / PyTorch
- OpenCV
- CNN Models

## IoT & Cloud
- ESP32 / NodeMCU
- Soil Moisture Sensors
- Temperature & Humidity Sensors
- Firebase / ThingSpeak / Blynk

---

# 🏗️ System Modules

## 1️⃣ Pre-Analysis & Smart Decision Support
This module generates optimized farming plans based on:
- Land conditions
- Farmer budget
- Available resources
- Environmental factors

### Features
- Land suitability analysis
- Budget-aware recommendations
- Profit prediction
- Resource planning

---

## 2️⃣ Technology-Assisted A-to-Z Farming Guidance
AI and IoT-based monitoring system for Nai Miris cultivation.

### Features
- Weekly crop growth monitoring
- Real-time sensor monitoring
- Growth-stage analysis
- Smart cultivation guidance

### Sensors Used
- Soil Moisture Sensor
- EC Sensor
- Temperature Sensor
- Humidity Sensor

---

## 3️⃣ AI-Driven Pest Monitoring & Control
Detects pest attacks and provides treatment recommendations.

### Features
- Pest classification
- Severity analysis
- Pesticide dosage recommendation
- Smartphone image upload

---

# 📊 Research Innovations

✅ Crop-specific AI models for Nai Miris  
✅ Integrated AI + IoT monitoring  
✅ Profit-focused farming guidance  
✅ Wet-zone optimized recommendations  
✅ Low-cost smart farming solution  

---

# 📱 Commercialization Potential

NAIMIRIS can be commercialized as:
- Smart farming mobile application
- Agricultural advisory platform
- Subscription-based farming assistant

---

# 👨‍💻 Team Members

| Name | Role |
|------|------|
| IT2271464 - Kumarage K.J.B.H | Pre-Analysis & Smart Decision Support |
| IT22124630 - Savinda R.M.D | Technology-Assisted Farming Guidance |
| IT22212740 - Gunawardana T.D.A | AI Pest Monitoring & Control |

---

# 📚 Research Areas

- Artificial Intelligence
- Machine Learning
- Smart Agriculture
- IoT-based Monitoring
- Image Processing
- Precision Farming

---

# 🔮 Future Enhancements

- Weather prediction integration
- Market price prediction
- Automated irrigation systems
- Mobile notification system
- Multi-crop support

---

# ⚙️ Installation

## Clone Repository
```bash
git clone https://github.com/Savinda935/R26-IT-103.git
```

---

## Monitoring Component — Progress

The Phase 1 monitoring software foundation is implemented. Completed and pending work is tracked below.

### Phase 1 software — completed

- [x] Define canonical sensor names and measurement units.
- [x] Add plot, crop-cycle, plant, and device identifiers to the data model.
- [x] Add database tables for plots, crop cycles, plants, and devices.
- [x] Add safe migration support for the existing readings database.
- [x] Standardize the canonical Firebase/API payload structure.
- [x] Retain backward compatibility with the current legacy Firebase fields.
- [x] Store one representative reading per device per five-minute UTC bucket.
- [x] Update a bucket when a newer reading arrives instead of creating duplicates.
- [x] Store data-quality status, issues, calibration version, source, and raw payload metadata.
- [x] Implement physical-range and ADC-rail validation.
- [x] Implement hourly and daily aggregation.
- [x] Implement device `online`, `offline`, and `never_seen` detection.
- [x] Align frontend monitoring requests with `/api/monitoring` backend endpoints.
- [x] Route mobile live monitoring through the backend rather than directly through Firebase.
- [x] Display device connectivity on the IoT dashboard.
- [x] Add automated Phase 1 backend tests.
- [x] Verify backend compilation, FastAPI routes, and the Expo production bundle.

### Phase 2 sensor warnings — completed

- [x] Move active stage thresholds into versioned SQLite profiles.
- [x] Make backend/database profiles authoritative for monitoring stage thresholds.
- [x] Create five stage-specific profiles for moisture, soil temperature, air temperature, humidity, and EC.
- [x] Mark all current agronomic thresholds provisional until calibration and supervisor validation.
- [x] Exclude raw soil ADC from irrigation decisions and use calibrated moisture percentage only.
- [x] Ignore uncalibrated or ADC-rail moisture values when calculating irrigation warnings.
- [x] Calculate duration below/above limits, consecutive abnormal minutes, percentage outside range, and trend per hour.
- [x] Calculate deterministic green, yellow, orange, and red warning levels.
- [x] Store explainable warning evidence and contributing risk points.
- [x] Implement warning lifecycle states: `open`, `acknowledged`, and `resolved`.
- [x] Automatically resolve open stage warnings after readings return to normal.
- [x] Add deterministic recommendations for moisture, temperature, humidity, soil temperature, EC, and data-quality conditions.
- [x] Prevent EC fertilizer actions when readings, calibration, or measurement method are unavailable.
- [x] Add simulated normal, dry, heat-trend, uncalibrated-moisture, and lifecycle tests.

Phase 2 endpoints:

- `GET /api/monitoring/thresholds`
- `POST /api/monitoring/warnings/evaluate`
- `GET /api/monitoring/warnings`
- `POST /api/monitoring/warnings/{event_id}/acknowledge`
- `POST /api/monitoring/warnings/{event_id}/resolve`

### Current Firebase/API status

- [x] Firebase Realtime Database is reachable at the configured project URL.
- [x] Live `sensors` and legacy `history` data can be fetched.
- [x] The Firebase root structure is confirmed as `sensors` plus `history`.
- [x] Backend compatibility supports the observed legacy sensor keys.
- [x] Firebase push IDs are converted to historical Unix timestamps when `recorded_at` is absent.
- [x] `dht_temperature_c` is mapped to canonical air temperature and prioritized over the inconsistent legacy `temperature_c` value.
- [x] DS18B20 `-127 C` readings are classified as suspect data.
- [x] Soil ADC rail readings such as `4095` are classified as suspect data.
- [ ] Replace the current uncommissioned/test readings after physical sensors are installed and calibrated.
- [ ] Fix the DS18B20 `-127 C` read/disconnection error.
- [ ] Connect and calibrate the soil sensor currently reporting ADC `4095` and `0%`.
- [ ] Add EC readings; EC is not present in the current Firebase payload.
- [ ] Replace duplicate `dht_temperature_c` and `temperature_c` fields with canonical `air_temperature_c` in the ESP32 firmware.
- [ ] Add an explicit `recorded_at` Unix timestamp to every new Firebase record.
- [ ] Verify the commissioned device through `GET /api/monitoring/readings/latest`.

### Hardware details — pending

- [ ] Provide the exact ESP32 board model.
- [x] Confirm soil-moisture sensor: Capacitive Soil Moisture Sensor V2.0.
- [ ] Confirm the ESP32 ADC resolution and soil-moisture ADC pin.
- [ ] Provide the EC sensor and interface-board models.
- [ ] Confirm whether EC measures irrigation water, nutrient solution, or soil solution.
- [x] Confirm soil-temperature sensor: waterproof DS18B20.
- [x] Confirm air-temperature and humidity sensor: DHT22, with the same device supplying both measurements.
- [ ] Document ESP32 pin assignments and installed firmware version.

### Sensor placement — pending

- [ ] Install the air-temperature/humidity sensor in ventilated protection, in shade, at crop-canopy height.
- [ ] Install the soil-temperature probe in the active root zone.
- [ ] Install the soil-moisture probe in representative root-zone soil.
- [ ] Install the EC probe according to its documented measurement method.
- [ ] Protect the ESP32 and electrical connections from rain and irrigation water.
- [ ] Photograph and document every sensor position.
- [ ] Decide whether different soil, shade, drainage, or irrigation zones require multiple devices.

### Soil-moisture calibration — pending

- [ ] Record at least 20 stable dry/reference readings.
- [ ] Record at least 20 stable saturated-and-drained soil readings.
- [ ] Repeat the dry and wet procedures at least three times.
- [ ] Record soil type, sensor code, date, raw readings, means, and photographs.
- [ ] Confirm ADC direction and calculate the 0–100% conversion.
- [ ] Assign a traceable calibration version such as `field-v1-2026-08-20`.

### EC calibration — pending

- [ ] Obtain fresh EC calibration solutions covering the expected range.
- [ ] Record every standard solution value and temperature.
- [ ] Record raw and corrected sensor readings at least three times per solution.
- [ ] Test an independent check solution not used to calculate calibration.
- [ ] Document the temperature-compensation method.
- [ ] Assign a traceable EC calibration version.
- [ ] Obtain agriculture-domain approval before using EC for fertilizer recommendations.

### Monitoring identifiers and crop information — pending

- [ ] Choose the final plot ID and name.
- [ ] Choose the final crop-cycle ID.
- [ ] Confirm the real planting date.
- [ ] Choose the final ESP32/device ID and code.
- [ ] Assign plant IDs if plants will be monitored individually.
- [ ] Record the plot soil type and general location.
- [ ] Submit the final setup through `POST /api/monitoring/setup` or backend environment values.

### ESP32 payload migration — pending

- [x] Confirm the Firebase database root and its `sensors`/`history` nodes.
- [ ] Update ESP32 firmware to send `Backend/monitoring/firebase_payload.example.json`.
- [ ] Send Unix timestamps in UTC seconds.
- [ ] Send unavailable values as `null`, not fabricated zero values.
- [ ] Include `device_id`, `plot_id`, `crop_cycle_id`, and `calibration_version` in every payload.

### Demonstration evidence

- [ ] Demonstrate live ESP32-to-Firebase transmission with installed sensors.
- [ ] Demonstrate live Firebase-to-backend ingestion with the commissioned device.
- [x] Verify five-minute deduplication with automated tests.
- [x] Verify hourly and daily aggregation with automated tests.
- [x] Verify offline-state calculation with automated tests.
- [ ] Show five-minute storage, aggregation, and offline detection using the physical device during the presentation.
- [ ] Retain calibration sheets, hardware photographs, field API responses, screenshots, and test results.

Detailed field instructions are available in [Monitoring Phase 1 Setup](docs/MONITORING_PHASE1_SETUP.md).
