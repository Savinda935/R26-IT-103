const AIR_TEMP_NOTE = "DHT22: 25-30C optimal, <20C slow growth, >35C heat stress.";

const STAGES = [
  {
    id: "stage1",
    title: "Germination",
    duration: "7-21 days",
    dryThreshold: 1000,
    thresholds: {
      soilMoisture: { min: 1000, max: 2000, unit: "analog", note: "Keep consistently moist." },
      soilTemp: { min: 25, max: 30, unit: "C", note: "Critical germination window." },
      airHumidity: { min: 70, max: 85, unit: "%", note: "Prevents casing from drying." },
      airTemp: { min: 25, max: 30, unit: "C", note: AIR_TEMP_NOTE },
      ec: { min: 0.5, max: 1.2, unit: "mS/cm", note: "Very low nutrients." }
    },
    flags: ["slowGrowth"]
  },
  {
    id: "stage2",
    title: "Seedling",
    duration: "2-4 weeks",
    dryThreshold: 1000,
    thresholds: {
      soilMoisture: { min: 1200, max: 2200, unit: "analog", note: "Slightly drier than germination." },
      soilTemp: { min: 22, max: 28, unit: "C", note: "Below 20C halts uptake." },
      airHumidity: { min: 60, max: 75, unit: "%", note: "Avoid >80% disease risk." },
      airTemp: { min: 25, max: 30, unit: "C", note: AIR_TEMP_NOTE },
      ec: { min: 0.8, max: 1.5, unit: "mS/cm", note: "Gentle feeding." }
    },
    flags: ["slowGrowth"]
  },
  {
    id: "stage3",
    title: "Vegetative",
    duration: "4-8 weeks",
    dryThreshold: 1000,
    thresholds: {
      soilMoisture: { min: 1500, max: 2500, unit: "analog", note: "Higher demand from leaf area." },
      soilTemp: { min: 20, max: 28, unit: "C", note: "Wide tolerance." },
      airHumidity: { min: 50, max: 70, unit: "%", note: "Dense foliage needs airflow." },
      airTemp: { min: 25, max: 30, unit: "C", note: AIR_TEMP_NOTE },
      ec: { min: 1.5, max: 2.5, unit: "mS/cm", note: "Full vegetative feed." }
    },
    flags: ["slowGrowth"]
  },
  {
    id: "stage4",
    title: "Flowering",
    duration: "2-3 weeks",
    dryThreshold: 1000,
    thresholds: {
      soilMoisture: { min: 1200, max: 2000, unit: "analog", note: "Slightly drier to trigger flowering." },
      soilTemp: { min: 20, max: 26, unit: "C", note: "Cool roots retain flowers." },
      airHumidity: { min: 50, max: 65, unit: "%", note: "Keep pollen dry." },
      airTemp: { min: 25, max: 30, unit: "C", note: AIR_TEMP_NOTE },
      ec: { min: 1.5, max: 2.2, unit: "mS/cm", note: "Bloom formula." }
    },
    flags: ["noFlowerDevelopment", "noFruitSet"]
  },
  {
    id: "stage5",
    title: "Fruiting & Ripening",
    duration: "3-6 weeks",
    dryThreshold: 1000,
    thresholds: {
      soilMoisture: { min: 1500, max: 2500, unit: "analog", note: "Consistency prevents cracking." },
      soilTemp: { min: 20, max: 26, unit: "C", note: "Cool roots + warm air." },
      airHumidity: { min: 45, max: 65, unit: "%", note: "Low humidity aids color." },
      airTemp: { min: 25, max: 30, unit: "C", note: AIR_TEMP_NOTE },
      ec: { min: 1.2, max: 2.0, unit: "mS/cm", note: "Lower than vegetative." }
    },
    flags: ["slowRipening"]
  }
];

const isNumber = (value) => typeof value === "number" && Number.isFinite(value);

const firstSoilMoisturePercent = (snapshot) => {
  if (!snapshot) {
    return null;
  }

  const candidates = [
    snapshot.soil_moisture,
    snapshot.soilMoisture,
    snapshot.soil_moisture_percent,
    snapshot.soilMoisturePercent
  ];

  for (const value of candidates) {
    if (isNumber(value)) {
      return value;
    }

    const n = Number(value);
    if (isNumber(n)) {
      return n;
    }
  }

  return null;
};

const rangeStatus = (value, range) => {
  if (!isNumber(value)) {
    return "unknown";
  }

  if (value < range.min) {
    return "low";
  }

  if (value > range.max) {
    return "high";
  }

  return "ok";
};

const normalizeReadings = (snapshot) => {
  if (!snapshot) {
    return {
      soilAnalog: null,
      soilMoisturePercent: null,
      soilTemp: null,
      airTemp: null,
      airHumidity: null,
      ec: null
    };
  }

  const soilAnalog = isNumber(snapshot.soil_analog) ? snapshot.soil_analog : null;
  const soilMoisturePercent = firstSoilMoisturePercent(snapshot);
  const soilTemp = isNumber(snapshot.soil_temperature_c)
    ? snapshot.soil_temperature_c
    : isNumber(snapshot.soil_temp_c)
      ? snapshot.soil_temp_c
      : isNumber(snapshot.ds18b20_temperature_c)
        ? snapshot.ds18b20_temperature_c
      : null;
  const airTemp = isNumber(snapshot.temperature_c) ? snapshot.temperature_c : null;
  const airHumidity = isNumber(snapshot.humidity) ? snapshot.humidity : null;
  const ec = isNumber(snapshot.ec) ? snapshot.ec : null;

  return {
    soilAnalog,
    soilMoisturePercent,
    soilTemp,
    airTemp,
    airHumidity,
    ec
  };
};

export const getStages = () => STAGES;

export const getStageById = (stageId, stages = STAGES) => stages.find((stage) => stage.id === stageId) || stages[0];

export const evaluateStage = (snapshot, stageId, flags = {}, stages = STAGES) => {
  const stage = getStageById(stageId, stages);
  const readings = normalizeReadings(snapshot);
  const moistureValue = stage.thresholds.soilMoisture?.unit === "%"
    ? readings.soilMoisturePercent
    : readings.soilAnalog;
  const statuses = {
    soilMoisture: rangeStatus(moistureValue, stage.thresholds.soilMoisture),
    soilTemp: rangeStatus(readings.soilTemp, stage.thresholds.soilTemp),
    airHumidity: rangeStatus(readings.airHumidity, stage.thresholds.airHumidity),
    airTemp: rangeStatus(readings.airTemp, stage.thresholds.airTemp),
    ec: rangeStatus(readings.ec, stage.thresholds.ec)
  };

  const alerts = [];
  const pushAlert = (level, title, detail) => alerts.push({ level, title, detail });

  if (isNumber(readings.airTemp)) {
    if (readings.airTemp > 35) {
      pushAlert("warning", "Heat Stress Warning", "Air temperature is above 35C. Crop heat stress risk is high.");
    } else if (readings.airTemp >= 25 && readings.airTemp <= 30) {
      pushAlert("info", "Optimal Air Temperature", "Air temperature is in the 25-30C optimal growth range.");
    } else if (readings.airTemp < 20) {
      pushAlert("warning", "Slow Growth Risk", "Air temperature is below 20C. Growth may slow down.");
    }
  }

  if (!isNumber(moistureValue)) {
    pushAlert("info", "Soil analog missing", "A calibrated soil-moisture value is not available.");
  }

  if (!isNumber(readings.soilTemp)) {
    pushAlert("info", "Soil temperature missing", "Soil temp rules are not evaluated.");
  }

  if (!isNumber(readings.ec)) {
    pushAlert("info", "EC sensor missing", "Nutrient alerts are not evaluated.");
  }

  if (isNumber(moistureValue) && readings.soilMoisturePercent != null && snapshot?.calibration_version && moistureValue < stage.dryThreshold) {
    pushAlert("alert", "Irrigation Required", "Soil moisture is below the dry-out threshold.");
  }

  if (stage.id === "stage1") {
    if (flags.slowGrowth && isNumber(readings.soilTemp) && readings.soilTemp > 32) {
      pushAlert("warning", "Root Stress Warning", "Slow germination with high soil temperature.");
    }

    if (isNumber(readings.airHumidity) && isNumber(readings.airTemp) && readings.airHumidity > 90 && readings.airTemp > 30) {
      pushAlert("alert", "Disease Risk Alert", "High humidity and temperature increase damping-off risk.")
    }
  }

  if (stage.id === "stage2") {
    if (flags.slowGrowth && isNumber(readings.ec) && readings.ec < 0.8) {
      pushAlert("warning", "Fertiliser Needed", "Slow growth with low EC.");
    }

    if (isNumber(readings.airHumidity) && isNumber(readings.airTemp) && readings.airHumidity > 80 && readings.airTemp > 28) {
      pushAlert("alert", "Disease Risk Alert", "Humidity and temperature favor damping-off disease.");
    }
  }

  if (stage.id === "stage3") {
    if (flags.slowGrowth && isNumber(readings.soilTemp) && readings.soilTemp > 30) {
      pushAlert("warning", "Root Stress Warning", "Slow growth with high soil temperature.");
    }

    if (flags.slowGrowth && isNumber(readings.ec) && readings.ec < 1.5) {
      pushAlert("warning", "Fertiliser Needed", "Slow growth with low EC.");
    }

    if (isNumber(readings.airHumidity) && isNumber(readings.airTemp) && readings.airHumidity > 80 && readings.airTemp > 30) {
      pushAlert("alert", "Disease Risk Alert", "High humidity and heat promote fungal disease.");
    }
  }

  if (stage.id === "stage4") {
    if (flags.noFruitSet && isNumber(readings.soilTemp) && readings.soilTemp > 28) {
      pushAlert("warning", "Root Stress Warning", "No fruit set with warm roots.");
    }

    if (flags.noFlowerDevelopment && isNumber(readings.ec) && readings.ec < 1.2) {
      pushAlert("warning", "Fertiliser Needed", "Low EC may delay flowering.");
    }

    if (isNumber(readings.airHumidity) && isNumber(readings.airTemp) && readings.airHumidity > 70 && readings.airTemp > 30) {
      pushAlert("alert", "Disease Risk Alert", "High humidity and temperature reduce pollination.");
    }
  }

  if (stage.id === "stage5") {
    if (flags.slowRipening && isNumber(readings.soilTemp) && readings.soilTemp > 28) {
      pushAlert("warning", "Root Stress Warning", "Slow ripening with warm roots.");
    }

    if (flags.slowRipening && isNumber(readings.ec) && readings.ec < 1.0) {
      pushAlert("warning", "Fertiliser Needed", "Low EC may slow ripening.");
    }

    if (isNumber(readings.airHumidity) && isNumber(readings.airTemp) && readings.airHumidity > 75 && readings.airTemp > 30) {
      pushAlert("alert", "Disease Risk Alert", "High humidity risks botrytis.");
    }
  }

  const allNormal = Object.values(statuses).every((status) => status === "ok");
  if (allNormal && !alerts.some((alert) => alert.level === "alert" || alert.level === "warning")) {
    pushAlert("ok", "Crop Growing Properly", "All parameters are within the optimal ranges.");
  }

  return {
    stage,
    readings,
    statuses,
    alerts
  };
};
