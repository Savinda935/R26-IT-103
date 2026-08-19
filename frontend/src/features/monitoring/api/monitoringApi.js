import axios from "axios";
import { Platform } from "react-native";

import { API_BASE_URL, API_REQUEST_TIMEOUT_MS } from "../../../config/api";


const MONITORING_PREFIX = "/api/monitoring";

const appendImage = (formData, imageAsset, fallbackName) => {
  if (!imageAsset?.uri) {
    throw new Error("A valid image is required.");
  }

  const filename = imageAsset.fileName || fallbackName;
  const mimeType = imageAsset.mimeType || "image/jpeg";

  if (Platform.OS === "web" && imageAsset.file) {
    formData.append("image", imageAsset.file, filename);
    return;
  }

  formData.append("image", {
    uri: imageAsset.uri,
    name: filename,
    type: mimeType
  });
};

const uploadConfig = {
  // Axios supplies the correct multipart boundary on native and web.
  timeout: API_REQUEST_TIMEOUT_MS
};

export function getBackendErrorMessage(error, fallback = "Unable to contact the backend.") {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg).filter(Boolean).join("; ") || fallback;
  }
  if (error?.code === "ECONNABORTED") return "The backend took too long to respond. Please try again.";
  if (!error?.response && error?.message === "Network Error") {
    return `Cannot reach the backend at ${API_BASE_URL}. Check that FastAPI is running and the phone is on the same network.`;
  }
  return fallback;
}

export async function analyzeGerminationImage({ imageAsset, plantAgeDays }) {
  const formData = new FormData();

  formData.append("plant_age_days", String(plantAgeDays));
  appendImage(formData, imageAsset, `growth-${Date.now()}.jpg`);

  const response = await axios.post(
    `${API_BASE_URL}${MONITORING_PREFIX}/analytics/germination/analyze`,
    formData,
    uploadConfig
  );

  return response.data;
}

export async function analyzeGrowthStageImage({ imageAsset }) {
  const formData = new FormData();
  appendImage(formData, imageAsset, `growth-stage-${Date.now()}.jpg`);

  const response = await axios.post(
    `${API_BASE_URL}${MONITORING_PREFIX}/analytics/growth-stage/analyze`,
    formData,
    uploadConfig
  );
  const data = response.data;
  if (!data || typeof data.confidence !== "number" || typeof data.probabilities !== "object") {
    throw new Error("The backend returned an invalid growth-stage response.");
  }
  return data;
}

export async function checkMonitoringHealth() {
  const response = await axios.get(`${API_BASE_URL}${MONITORING_PREFIX}/health`, {
    timeout: 10000
  });
  return response.data;
}

export async function fetchAiAlertSummary(payload) {
  const response = await axios.post(`${API_BASE_URL}${MONITORING_PREFIX}/ai/alerts`, payload);
  return response.data;
}

export async function fetchSensorWindowAnalysis({ stageId = "stage1", hours = 24 } = {}) {
  const response = await axios.get(`${API_BASE_URL}${MONITORING_PREFIX}/analytics/window`, {
    params: {
      stage_id: stageId,
      hours
    }
  });
  return response.data;
}

export async function validateSensorReading(reading) {
  const response = await axios.post(`${API_BASE_URL}${MONITORING_PREFIX}/readings/validate`, reading);
  return response.data;
}

export async function fetchAggregatedSensorHistory({ interval = "hour", hours = 168, deviceId } = {}) {
  const response = await axios.get(`${API_BASE_URL}${MONITORING_PREFIX}/analytics/aggregate`, {
    params: {
      interval,
      hours,
      ...(deviceId ? { device_id: deviceId } : {})
    }
  });
  return response.data;
}

export async function fetchMonitoringDeviceStatuses() {
  const response = await axios.get(`${API_BASE_URL}${MONITORING_PREFIX}/devices/status`);
  return response.data;
}

export async function evaluateSensorWarnings({ deviceId = "device-001", stageId = "stage1", windowHours = 24 } = {}) {
  const response = await axios.post(`${API_BASE_URL}${MONITORING_PREFIX}/warnings/evaluate`, null, {
    params: {
      device_id: deviceId,
      stage_id: stageId,
      window_hours: windowHours
    }
  });
  return response.data;
}

export async function fetchWarningEvents({ status, deviceId } = {}) {
  const response = await axios.get(`${API_BASE_URL}${MONITORING_PREFIX}/warnings`, {
    params: {
      ...(status ? { status } : {}),
      ...(deviceId ? { device_id: deviceId } : {})
    }
  });
  return response.data;
}

export async function acknowledgeWarningEvent(eventId, note = null) {
  const response = await axios.post(
    `${API_BASE_URL}${MONITORING_PREFIX}/warnings/${eventId}/acknowledge`,
    { note }
  );
  return response.data;
}

export async function resolveWarningEvent(eventId, note = null) {
  const response = await axios.post(
    `${API_BASE_URL}${MONITORING_PREFIX}/warnings/${eventId}/resolve`,
    { note }
  );
  return response.data;
}

const toCamelFlag = (value) => value.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());

export async function fetchMonitoringStages() {
  const response = await axios.get(`${API_BASE_URL}${MONITORING_PREFIX}/stages`);
  return (Array.isArray(response.data) ? response.data : []).map((stage) => ({
    id: stage.id,
    title: stage.title,
    duration: stage.duration,
    dryThreshold: stage.dry_threshold,
    flags: (stage.flags || []).map(toCamelFlag),
    thresholds: {
      soilMoisture: stage.thresholds?.soil_moisture,
      soilTemp: stage.thresholds?.soil_temp,
      airHumidity: stage.thresholds?.air_humidity,
      airTemp: stage.thresholds?.air_temp,
      ec: stage.thresholds?.ec
    }
  }));
}
