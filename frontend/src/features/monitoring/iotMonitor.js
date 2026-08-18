import { API_BASE_URL } from "../../config/api";

export function getMockSensorSnapshot() {
  return {
    soilMoisture: 62,
    ec: 1.4,
    temperature: 27,
    humidity: 78
  };
}

const LATEST_READING_URL = `${API_BASE_URL}/api/monitoring/readings/latest`;
const DEVICE_STATUS_URL = `${API_BASE_URL}/api/monitoring/devices/status`;

const firstFiniteNumber = (...values) => {
  for (const value of values) {
    if (value === null || value === undefined || value === "") {
      continue;
    }

    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }

    const n = Number(value);
    if (Number.isFinite(n)) {
      return n;
    }
  }

  return null;
};

export async function getRealtimeSensorSnapshot() {
  const response = await fetch(LATEST_READING_URL);

  if (!response.ok) {
    throw new Error(`Failed to fetch IoT data from ${LATEST_READING_URL}: HTTP ${response.status}`);
  }

  const sensors = await response.json();

  const soilMoisture = firstFiniteNumber(
    sensors?.soil_moisture,
    sensors?.soilMoisture,
    sensors?.soil_moisture_percent,
    sensors?.soilMoisturePercent
  );

  const soilTemp = firstFiniteNumber(
    sensors?.soil_temperature_c,
    sensors?.soil_temp_c,
    sensors?.ds18b20_temperature_c
  );

  return {
    ...sensors,
    ...(soilMoisture != null ? { soil_moisture: soilMoisture } : {}),
    ...(soilTemp != null ? { soil_temperature_c: soilTemp } : {})
  };
}

export async function getMonitoringDeviceStatuses() {
  const response = await fetch(DEVICE_STATUS_URL);
  if (!response.ok) {
    throw new Error(`Device status request failed from ${DEVICE_STATUS_URL}: HTTP ${response.status}`);
  }
  const data = await response.json();
  return Array.isArray(data) ? data : [];
}
