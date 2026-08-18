# NAIMIRIS Repository Agent Notes

## 1. Project Overview

This repository currently contains Savinda's **Technology-Assisted A-to-Z Farming Guidance / IoT Monitoring** component for the NAIMIRIS mobile application.

It also contains a shared **React Native / Expo mobile app shell** that already has screens and folders for the other planned components, including Krishan's Pre-Analysis component and Tashini's Technology-Assisted A-to-Z Farming Guidance component.

Savinda's monitoring backend, Krishan's pre-analysis backend, and Tashini's initial guidance backend are implemented as separate FastAPI modules. New component logic should stay in separate modules and must not be placed inside `Backend/monitoring/`.

## 2. Savinda's Component Status

Savinda's component already includes:

- FastAPI backend
- React Native / Expo frontend
- Firebase IoT sensor data fetching
- SQLite sensor reading storage
- Crop growth stage evaluation
- Environmental condition validation
- Gemini AI alert generation
- Farmer Q&A endpoint
- Analytics summary endpoints
- Firebase history reading
- PDF report generation
- Monitoring dashboards in the frontend

The monitoring component focuses on IoT sensor readings, Scotch Bonnet/Nai Miris growth stages, environmental thresholds, alerts, analytics, and reports.

## 3. Current Backend Structure

### `Backend/main.py`

Main FastAPI server entry file.

Responsibilities:

- Loads environment variables using `python-dotenv`
- Creates the FastAPI app
- Adds CORS middleware
- Initializes the SQLite database on startup
- Starts the Firebase polling loop on startup
- Stops the Firebase polling loop on shutdown
- Registers the monitoring router
- Provides `GET /health`

### `Backend/monitoring/models.py`

Contains Pydantic request and response schemas for Savinda's monitoring module.

Important models include:

- `Reading`
- `SummaryStats`
- `StageEvaluationRequest`
- `StageEvaluationResponse`
- `StageDecisionRequest`
- `StageDecisionResponse`
- `AiAlertRequest`
- `AiAlertResponse`
- `AiAskRequest`
- `AiAskResponse`

### `Backend/monitoring/routes.py`

Contains FastAPI route definitions for monitoring.

Responsibilities:

- Accepting/storing sensor readings
- Fetching latest and historical readings
- Returning analytics summaries
- Returning Firebase history summaries
- Listing growth stages
- Evaluating stage conditions
- Calling AI alert and Q&A logic
- Generating PDF reports

Routes are currently registered without a module prefix, so endpoints are exposed directly at paths such as `/readings`, `/analytics/summary`, and `/ai/alerts`.

### `Backend/monitoring/service.py`

Main service/business logic file for Savinda's component.

Responsibilities:

- Stage threshold definitions
- Growth stage decision logic
- Environmental validation rules
- Local alert generation
- Gemini AI alert generation
- Gemini farmer Q&A
- SQLite database initialization
- SQLite reading insert/fetch logic
- Firebase latest reading fetch
- Firebase history parsing
- Background Firebase polling
- Analytics summary calculation
- PDF report and chart generation

This file is currently large and mixes several responsibilities, but it should not be refactored until the existing behavior is protected.

### `Backend/requirements.txt`

Python dependencies for the backend.

Current main dependencies:

- `fastapi`
- `uvicorn[standard]`
- `httpx`
- `matplotlib`
- `reportlab`
- `python-dotenv`
- `python-multipart`
- `ultralytics`
- `numpy`
- `pillow`
- `tensorflow`

### `Backend/iot_readings.db`

SQLite database used by the monitoring backend to store IoT readings.

This is a runtime/generated file and should not normally be committed to Git.

### `Backend/.env`

Local backend environment file.

Used for values such as:

- `FIREBASE_URL`
- `IOT_DB_PATH`
- `GEMINI_API_KEY`
- `GEMINI_MODEL`
- `FIREBASE_POLL_SECONDS`

This file may contain secrets and should not normally be committed to Git.

### Large ML Model Artifacts

Large trained model files are local runtime artifacts and must not be committed to normal Git history.

Ignored model patterns include:

- `*.keras`
- `*.h5`
- `*.pt`

Current local model locations expected by the backend:

- Krishan pre-analysis model: `Backend/preanalysis/loveda_unet_25epoch_best.keras`
- Tashini pest-control model: `Backend/pest_control/best.pt`

These files should be shared through Git LFS, cloud storage, release assets, or manual setup instructions. If they are needed locally, place them at the paths above or set:

- `PREANALYSIS_MODEL_PATH`
- `PEST_CONTROL_MODEL_PATH`

Do not add large model files back into Git with `git add -f` unless the repository has been explicitly migrated to Git LFS.

## 4. Current Frontend Structure

### `frontend/App.js`

Main Expo app entry file.

Responsibilities:

- Loads custom fonts
- Wraps the app in `AppProvider`
- Creates the React Navigation container
- Loads the root navigator

### `frontend/src/navigation/`

Contains app navigation setup.

Important files:

- `RootNavigator.js`: stack navigation for welcome, onboarding, service screens, and feature screens
- `TabNavigator.js`: bottom tab navigation for Home, Pre-Analysis, Monitoring, Stage, and Pest areas

### `frontend/src/screens/`

Contains screen-level UI files.

Monitoring-related screens include:

- `MonitoringServicesScreen.js`
- `IoTDashboardScreen.js`
- `GrowthMonitoringScreen.js`
- `StageDashboardScreen.js`
- `DataAnalysisScreen.js`

Pre-analysis screens already exist, but currently mostly use placeholder/mock logic:

- `PreAnalysisServicesScreen.js`
- `LandAnalysisScreen.js`
- `BudgetPlanningScreen.js`
- `ProfitPredictionScreen.js`

Pest control screens also exist with placeholder/mock logic:

- `PestServicesScreen.js`
- `PestDetectionScreen.js`: re-exports the connected Tashini pest-detection screen from `frontend/src/features/pestControl/screens/PestDetectionScreen.js`
- `SeverityAnalysisScreen.js`
- `TreatmentPlanScreen.js`

### `frontend/src/features/monitoring/`

Contains monitoring-specific frontend logic.

Important files:

- `iotMonitor.js`: fetches live IoT sensor data from Firebase
- `stageLogic.js`: local frontend growth stage evaluation logic
- `aiAlerts.js`: mock/local AI alert summary logic
- `growthAnalyzer.js`: mock/local growth stage guidance logic

### `frontend/src/services/`

Contains shared service/helper files for API, AI, IoT, and local storage.

Important files:

- `apiClient.js`: generic API client, but currently uses a placeholder base URL
- `aiService.js`: calls backend AI alert endpoint
- `iotService.js`: ThingSpeak-related helper
- `storage.js`: local JSON storage using Expo FileSystem

### `frontend/src/config/api.js`

Contains the configurable backend base URL used by Tashini's frontend pest-control API client.

Resolution order:

- `EXPO_PUBLIC_BACKEND_BASE_URL`
- Expo dev host IP with port `8000`
- PC IPv4 fallback currently set to `http://10.68.28.18:8000`

Do not use `localhost` for mobile-device API calls.

### `frontend/src/state/`

Contains global app state.

Current file:

- `AppContext.js`

Uses React Context and `useReducer` to store shared app values such as budget, land, sensor state, growth stage, pest severity, and active plan ID.

### `frontend/src/components/ui/`

Contains reusable UI components used across screens.

Current components:

- `PrimaryButton.js`
- `ScreenHeader.js`
- `SectionCard.js`
- `StatTile.js`

Krishan should reuse these components for consistent UI style.

## 5. Current API Endpoints

Existing monitoring endpoints:

- `GET /health`
- `POST /readings`
- `POST /readings/firebase`
- `GET /readings/latest`
- `GET /readings`
- `GET /analytics/summary`
- `GET /analytics/summary/firebase`
- `GET /analytics/history/firebase`
- `GET /stages`
- `POST /analytics/stage/evaluate`
- `POST /analytics/stage/decision`
- `POST /ai/alerts`
- `POST /ai/ask`
- `GET /report/pdf`
- `GET /report/firebase/pdf`

These endpoints belong to Savinda's monitoring component and should continue working when Krishan's component is added.

## 6. Important Notes for Krishan

- Krishan's Pre-Analysis component should be added separately inside `Backend/preanalysis/`.
- Do not place Krishan's logic inside `Backend/monitoring/`.
- Follow the same backend module pattern used by Savinda:
  - `models.py`
  - `routes.py`
  - `service.py`
- Krishan's PP1 land-image model integration is isolated in `Backend/preanalysis/ai_model.py`.
- Krishan's default trained model file is `Backend/preanalysis/loveda_unet_25epoch_best.keras`.
- The model path can be overridden with `PREANALYSIS_MODEL_PATH`.
- PP1 backend logic should stay focused on land suitability and estimated plant count only.
- Add pre-analysis frontend API calls separately.
- Existing frontend files under `frontend/src/features/preAnalysis/` are mostly placeholder/mock logic.
- Existing pre-analysis screens can be reused, but they should be connected to real backend APIs later.
- Keep Savinda's monitoring routes working.
- Avoid changing monitoring files unless the change is required for integration, such as registering a new router in `Backend/main.py`.

## 7. Suggested Krishan Backend Module

Suggested folder structure:

```text
Backend/preanalysis/
  __init__.py
  ai_model.py
  loveda_unet_25epoch_best.keras  # local/ignored model artifact
  models.py
  routes.py
  service.py
```

Current / suggested endpoints:

- `POST /api/preanalysis/land-image/analyze`
- `POST /api/preanalysis/land/suitability`
- `POST /api/preanalysis/budget/plan`
- `POST /api/preanalysis/profit/predict`
- `POST /api/preanalysis/decision-support`
- `GET /api/preanalysis/report/pdf`

Recommended backend responsibilities:

- `models.py`: Pydantic request/response schemas
- `routes.py`: FastAPI endpoint definitions
- `service.py`: land suitability, budget planning, profit prediction, and decision-support logic

### `POST /api/preanalysis/land-image/analyze`

Accepts a multipart satellite/top-view land image and `land_size_perch`.

The U-Net model analyzes land-cover percentages and groups them according to PP1 backend logic:

- usable farming area: agriculture + barren/open land
- unusable area: buildings + roads + water + forest
- unknown area: unclear/unclassified pixels

PP1 decision logic:

- usable farming area >= 50%: `Good for farming`
- usable farming area < 50%: `Not good for farming`
- unknown area > 50%: `Need clearer image`

Plant count logic:

- `1 perch = 272.25 sq ft`
- Nai Miris spacing: `3 ft x 3 ft = 9 sq ft per plant`
- practical field factor: `75%` for paths and drainage

Final PP1 outputs:

- land suitability
- usable farming percentage and usable land size
- estimated Nai Miris plant count

If TensorFlow is not installed in the active backend Python environment, `Backend/preanalysis/ai_model.py` falls back to lightweight color-based satellite image segmentation so the PP1 flow can still run. The fallback is only a development/PP1 continuity path; install TensorFlow and provide the `.keras` model for trained U-Net inference.

Current frontend addition:

```text
frontend/src/features/preAnalysis/
  api/
    preAnalysisApi.js
  screens/
    LandAnalysisScreen.js
```

The original navigation screen remains at:

```text
frontend/src/screens/LandAnalysisScreen.js
```

It re-exports the feature screen so existing `RootNavigator.js` and `TabNavigator.js` imports keep working.

Current frontend API functions:

- `analyzeLandImage({ imageAsset, landSizePerch })`
- `runPreAnalysisDecisionSupport(payload)`

Connected backend endpoint:

- `POST /api/preanalysis/land-image/analyze`

Request format:

- multipart form-data
- field name: `image`
- field name: `land_size_perch`

Expected backend response fields currently used by the UI:

- `suitability`
- `usable_farming_percentage`
- `usable_land_perch`
- `usable_land_sqft`
- `estimated_plant_count`
- `land_cover_percentages`
- `message`

## 8. Current Problems / Warnings

- `Backend/monitoring/service.py` is large and mixes many responsibilities.
- `Backend/.env` should not be committed.
- `Backend/iot_readings.db` should not be committed.
- `__pycache__` files should not be committed.
- `frontend/src/services/apiClient.js` currently has a placeholder base URL.
- Monitoring logic is duplicated in frontend and backend.
- Krishan and Tashini backend modules are implemented as separate backend modules.
- Backend route paths currently have no monitoring-specific prefix, so new modules should use separate prefixes to avoid conflicts.
- Some frontend pre-analysis and pest-control logic is mock/demo logic, not production backend integration.

## 9. Safe Next Steps

1. Keep Savinda's monitoring module unchanged unless router registration requires a small import/include addition.
2. Keep Krishan's PP1 pre-analysis flow focused on land suitability and estimated plant count.
3. Keep Tashini's pest-control ML inference isolated in `Backend/pest_control/ai_model.py`.
4. Add frontend API services inside each feature folder instead of mixing module APIs together.
5. Do not commit runtime files: `.env`, SQLite databases, `__pycache__`, `.expo`, `node_modules`, or large model artifacts.
6. If model files must be versioned, migrate them to Git LFS before committing.
7. Add tests around API request/response contracts before refactoring shared backend structure.

## 10. Important Notes for Tashini

- Tashini's Technology-Assisted A-to-Z Farming Guidance component is placed under `Backend/pest_control/`.
- Do not place Tashini's backend logic inside `Backend/guidance/`.
- Do not place Tashini's backend logic inside `Backend/monitoring/`.
- Tashini's router is registered in `Backend/main.py` with the prefix `/api/pest-control`.
- Tashini's module contains both rule-based growth guidance and a YOLO-based disease prediction endpoint.
- The YOLO integration is isolated in `Backend/pest_control/ai_model.py`.
- The default model file is `Backend/pest_control/best.pt`.
- The model path can be overridden with the `PEST_CONTROL_MODEL_PATH` environment variable.
- Image uploads use FastAPI `UploadFile`, so `python-multipart` is required.
- YOLO inference uses the `ultralytics` package.
- Keep Savinda's monitoring endpoints working exactly as they currently do.
- Avoid changing Krishan's `Backend/preanalysis/` module unless import compatibility requires it.

Current Tashini backend files:

```text
Backend/pest_control/
  __init__.py
  ai_model.py
  best.pt  # local/ignored model artifact
  models.py
  service.py
  routes.py
```

Current Tashini endpoints:

- `GET /api/pest-control/health`
- `GET /api/pest-control/stages`
- `POST /api/pest-control/analyze`
- `POST /api/pest-control/predict-disease`

### `Backend/pest_control/ai_model.py`

Loads the trained YOLO model using Ultralytics and exposes:

- `predict_disease(image_path)`

This function accepts a local image path, runs YOLO prediction, and returns:

- best detected disease name
- confidence score
- bounding boxes
- affected-area ratio estimate
- full prediction list

### `POST /api/pest-control/predict-disease`

Accepts a multipart image upload, saves it temporarily, runs `predict_disease(image_path)`, returns JSON predictions, and removes the temporary image file after inference.

The response is aligned with Tashini's proposal for AI-driven pest monitoring and control:

- detects pest/disease from Nai Miris leaf images
- estimates severity as `none`, `low`, `medium`, or `high`
- estimates affected leaf area from YOLO bounding boxes
- returns pesticide/treatment recommendation
- returns dosage and safety guidance

Do not mix this model-loading code into `models.py`, `service.py`, or `Backend/monitoring/`. Keep ML inference isolated so the team can test and replace the trained model safely.

## 11. Tashini Frontend Connection Status

Tashini's React Native pest-detection frontend is connected to the existing FastAPI pest-control backend.

Current frontend files:

```text
frontend/src/features/pestControl/
  api/
    pestApi.js
  screens/
    PestDetectionScreen.js
  pestDetector.js
  severityScoring.js
  treatmentAdvisor.js
```

The original navigation screen remains at:

```text
frontend/src/screens/PestDetectionScreen.js
```

It re-exports the feature screen so existing `RootNavigator.js` and `TabNavigator.js` imports keep working.

Current frontend API functions:

- `predictDiseaseFromImage(imageAsset)`
- `checkPestControlHealth()`

Connected backend endpoint:

- `POST /api/pest-control/predict-disease`

Request format:

- multipart form-data
- field name: `image`

Expected backend response fields currently used by the UI:

- `filename`
- `model`
- `pest_name`
- `disease_name`
- `confidence`
- `severity`
- `affected_area_ratio`
- `treatment_recommendation`
- `treatment`
- `predictions`

The frontend displays severity and treatment recommendation when these values are returned by the backend.

Frontend dependencies added for this integration:

- `axios`
- `expo-image-picker`

Keep Savinda's monitoring frontend and Krishan's pre-analysis frontend unchanged when working on Tashini's pest-control UI.

## 12. Monitoring Phase Update and Progress

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
