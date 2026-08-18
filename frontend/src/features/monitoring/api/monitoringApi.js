import axios from "axios";

import { API_BASE_URL } from "../../../config/api";


const MONITORING_PREFIX = "/api/monitoring";

export async function analyzeGerminationImage({ imageAsset, plantAgeDays }) {
  const formData = new FormData();
  const filename = imageAsset.fileName || `growth-${Date.now()}.jpg`;
  const mimeType = imageAsset.mimeType || "image/jpeg";

  formData.append("plant_age_days", String(plantAgeDays));
  formData.append("image", {
    uri: imageAsset.uri,
    name: filename,
    type: mimeType
  });

  const response = await axios.post(
    `${API_BASE_URL}${MONITORING_PREFIX}/analytics/germination/analyze`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data"
      }
    }
  );

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
