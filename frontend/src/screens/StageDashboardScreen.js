import React, { useEffect, useMemo, useState } from "react";
import { Alert, Image, Platform, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import * as FileSystem from "expo-file-system";
import * as Print from "expo-print";
import * as Sharing from "expo-sharing";
import Svg, { Polyline, Rect } from "react-native-svg";
import ScreenHeader from "../components/ui/ScreenHeader";
import SectionCard from "../components/ui/SectionCard";
import StatTile from "../components/ui/StatTile";
import PrimaryButton from "../components/ui/PrimaryButton";
import { theme } from "../config/theme";
import { getRealtimeSensorSnapshot } from "../features/monitoring/iotMonitor";
import { evaluateStage, getStages } from "../features/monitoring/stageLogic";
import { getAiAlertSummary as getMockAiAlertSummary } from "../features/monitoring/aiAlerts";
import { fetchAiAlertSummary } from "../services/aiService";
import { fetchMonitoringStages } from "../features/monitoring/api/monitoringApi";
import { appendLocalArray } from "../services/storage";

const HISTORY_LIMIT = 60;

const TEXT = {
  en: {
    stageLogic: "Stage logic",
    smartAlerts: "Smart Alerts",
    stageDashboard: "Stage Dashboard",
    stageSubtitle: "Scotch Bonnet pepper thresholds and alerts.",
    stageSelection: "Stage selection",
    current: "Current",
    updated: "Updated",
    language: "Language",
    english: "English",
    sinhala: "Sinhala",
    contextFlags: "Context flags",
    toggleFlags: "Toggle observed issues to activate combination rules.",
    liveReadings: "Live readings",
    liveSubtitle: "Realtime sensor values used for stage logic.",
    smartAlertsTitle: "Smart alerts",
    smartAlertsSubtitle: "Stage-specific combination rules.",
    noAlerts: "No alerts yet. Waiting for sensor data.",
    thresholds: "Stage thresholds",
    thresholdsSubtitle: "Target ranges for the selected growth stage.",
    trendCharts: "Trend charts",
    trendChartsSubtitle: "Short-term trends with optimal range band.",
    chartTabTrends: "Trends",
    chartTabSnapshot: "Snapshot",
    matchSummary: "Match summary",
    matchSubtitle: "How close the readings are to the optimal range.",
    matchScore: "Match score",
    metricsInRange: "Metrics in range",
    statusLow: "Low",
    statusHigh: "High",
    statusNormal: "Normal",
    statusUnknown: "Unknown",
    soilAnalog: "Soil analog",
    soilMoisturePercent: "Soil moisture %",
    soilTemp: "Soil temp",
    airTemp: "Air temp",
    airHumidity: "Humidity",
    ec: "EC",
    stageLogicLabel: "Stage logic",
    stageThresholds: "Stage thresholds",
    soilMoistureLabel: "Soil moisture (analog)",
    soilTempLabel: "Soil temp",
    airHumidityLabel: "Air humidity",
    airTempLabel: "Air temp",
    ecLabel: "EC",
    chartEmpty: "Waiting for enough data to draw the chart.",
    aiRiskTitle: "AI Risk Summary",
    aiRiskScore: "Risk score",
    aiStable: "Stable",
    aiAnomaly: "Anomaly",
    downloadReport: "Download report",
    downloadSubtitle: "Export a full stage-by-stage PDF report.",
    downloadButton: "Download PDF",
    downloadFailed: "Download failed. Please try again.",
    downloadSuccess: "Report downloaded successfully."
  },
  si: {
    stageLogic: "අදියර තර්ක",
    smartAlerts: "බුද්ධිමත් අනතුරු",
    stageDashboard: "අදියර පුවරුව",
    stageSubtitle: "ස්කොච් බොනට් මිරිස් සඳහා සීමා සහ අනතුරු.",
    stageSelection: "අදියර තේරීම",
    current: "වත්මන්",
    updated: "යාවත්කාලීන",
    language: "භාෂාව",
    english: "English",
    sinhala: "සිංහල",
    contextFlags: "සන්දර්භ ලකුණු",
    toggleFlags: "නිරීක්ෂිත ගැටලු සක්‍රීය කර සන්යෝජන නීති ක්‍රියාත්මක කරන්න.",
    liveReadings: "සජීවී කියවීම්",
    liveSubtitle: "අදියර තර්කයට භාවිතා වන සජීවී සංවේදක අගයන්.",
    smartAlertsTitle: "බුද්ධිමත් අනතුරු",
    smartAlertsSubtitle: "අදියර අනුව සන්යෝජන නීති.",
    noAlerts: "තවම අනතුරු නැත. සංවේදක දත්ත බලාපොරොත්තු වෙමින්.",
    thresholds: "අදියර සීමා",
    thresholdsSubtitle: "තෝරාගත් වර්ධන අදියරේ ඉලක්ක පරාස.",
    trendCharts: "ප්‍රවණතා ප්‍රස්ථාර",
    trendChartsSubtitle: "අවම පරාස සහිත කෙටි කාලීන ප්‍රවණතා.",
    chartTabTrends: "ප්‍රවණතා",
    chartTabSnapshot: "සාරාංශය",
    matchSummary: "ගැළපීමේ සාරාංශය",
    matchSubtitle: "දත්ත ප්‍රමාණවත් පරාසයට 얼마나 ගැළපේද යන්න.",
    matchScore: "ගැළපීමේ ලකුණු",
    metricsInRange: "පරාසයේ ඇති මිනුම්",
    statusLow: "අඩු",
    statusHigh: "ඉහළ",
    statusNormal: "සාමාන්‍ය",
    statusUnknown: "නොදන්නා",
    soilAnalog: "බිම් තෙතමන (ආනලොග්)",
    soilMoisturePercent: "බිම් තෙතමන %",
    soilTemp: "බිම් උෂ්ණත්වය",
    airTemp: "වායු උෂ්ණත්වය",
    airHumidity: "ආර්ද්‍රතාව",
    ec: "EC",
    stageLogicLabel: "අදියර තර්ක",
    stageThresholds: "අදියර සීමා",
    soilMoistureLabel: "බිම් තෙතමන (ආනලොග්)",
    soilTempLabel: "බිම් උෂ්ණත්වය",
    airHumidityLabel: "වායු ආර්ද්‍රතාව",
    airTempLabel: "වායු උෂ්ණත්වය",
    ecLabel: "EC",
    chartEmpty: "ප්‍රස්ථාරයට ප්‍රමාණවත් දත්ත තවම නොමැත.",
    aiRiskTitle: "AI අවදානම් සාරාංශය",
    aiRiskScore: "අවදානම් ලකුණ",
    aiStable: "ස්ථාවර",
    aiAnomaly: "අසමාන්‍ය",
    downloadReport: "වාර්තාව බාගන්න",
    downloadSubtitle: "අදියර අනුව සම්පූර්ණ PDF වාර්තාවක් ලබාගන්න.",
    downloadButton: "PDF බාගන්න",
    downloadFailed: "බාගත කිරීම අසාර්ථකයි. නැවත උත්සාහ කරන්න.",
    downloadSuccess: "වාර්තාව සාර්ථකව බාගත විය."
  }
};

const STAGE_LABELS = {
  stage1: { en: "Germination", si: "අංකුරණය" },
  stage2: { en: "Seedling", si: "අංකුර පැල" },
  stage3: { en: "Vegetative", si: "ශාක වර්ධන" },
  stage4: { en: "Flowering", si: "මල් දැමීම" },
  stage5: { en: "Fruiting & Ripening", si: "පල හා පළා වීම" }
};

const STAGE_DURATIONS = {
  stage1: { en: "7-21 days", si: "දින 7-21" },
  stage2: { en: "2-4 weeks", si: "සති 2-4" },
  stage3: { en: "4-8 weeks", si: "සති 4-8" },
  stage4: { en: "2-3 weeks", si: "සති 2-3" },
  stage5: { en: "3-6 weeks", si: "සති 3-6" }
};

const FLAG_LABELS = {
  slowGrowth: { en: "Slow growth", si: "ධීර වර්ධනය" },
  noFlowerDevelopment: { en: "No flower development", si: "මල් නොවර්ධනය" },
  noFruitSet: { en: "No fruit set", si: "පල නොඑල්ලීම" },
  slowRipening: { en: "Slow ripening", si: "මන්දගාමි පළා වීම" }
};

const ALERT_TITLE_TRANSLATIONS = {
  "Irrigation Required": "ජලය අවශ්‍යයි",
  "Root Stress Warning": "මුල් ආතතියේ අනතුරු",
  "Disease Risk Alert": "රෝග අවදානම් අනතුරු",
  "Fertiliser Needed": "පොහොර අවශ්‍යයි",
  "Crop Growing Properly": "බෝගය හොඳින් වර්ධනය වේ",
  "Soil analog missing": "බිම් ආනලොග් අගය නොමැත",
  "Soil temperature missing": "බිම් උෂ්ණත්ව අගය නොමැත",
  "EC sensor missing": "EC සංවේදක අගය නොමැත",
  "Heat Stress Warning": "උෂ්ණත්ව ආතති අනතුරු",
  "Optimal Air Temperature": "ප්‍රශස්ත වායු උෂ්ණත්වය",
  "Slow Growth Risk": "මන්දගාමී වර්ධන අවදානම"
};

const ALERT_DETAIL_TRANSLATIONS = {
  "Soil moisture is below the dry-out threshold.": "බිම් තෙතමන වියළීමේ සීමාවට පහළයි.",
  "Slow germination with high soil temperature.": "බිම් උෂ්ණත්වය වැඩිවීම සමඟ අංකුරණය මන්දගාමිව ඇත.",
  "High humidity and temperature increase damping-off risk.": "ඉහළ ආර්ද්‍රතාව සහ උෂ්ණත්වය damping-off අවදානම වැඩි කරයි.",
  "Slow growth with low EC.": "EC අඩුවීම සමඟ වර්ධනය මන්දගාමිව ඇත.",
  "Humidity and temperature favor damping-off disease.": "ආර්ද්‍රතාව හා උෂ්ණත්වය damping-off රෝගයට හේතු වේ.",
  "Slow growth with high soil temperature.": "බිම් උෂ්ණත්වය වැඩිවීම සමඟ වර්ධනය මන්දගාමිව ඇත.",
  "High humidity and heat promote fungal disease.": "ඉහළ ආර්ද්‍රතාව හා උෂ්ණත්වය දිලීර රෝග වැඩි කරයි.",
  "No fruit set with warm roots.": "මුල් උෂ්ණත්වය ඉහළ වීම සමඟ පල නොඑල්ලීම.",
  "Low EC may delay flowering.": "EC අඩුවීම මල් හටගැනීම ප්‍රමාද කරයි.",
  "High humidity and temperature reduce pollination.": "ඉහළ ආර්ද්‍රතාව හා උෂ්ණත්වය රේණුකරණය අඩු කරයි.",
  "Slow ripening with warm roots.": "මුල් උෂ්ණත්වය ඉහළ වීම සමඟ පළා වීම මන්දගාමිව ඇත.",
  "Low EC may slow ripening.": "EC අඩුවීම පළා වීම මන්දගාමී කරයි.",
  "High humidity risks botrytis.": "ඉහළ ආර්ද්‍රතාව botrytis අවදානම වැඩි කරයි.",
  "All parameters are within the optimal ranges.": "සියලු පරාමිතීන් ප්‍රමාණවත් පරාසයේ ඇත.",
  "Thresholds use analog scale. Check soil sensor mapping.": "සීමා ආනලොග් පරිමාණය භාවිත කරයි. බිම් සංවේදක සිතියම පරීක්ෂා කරන්න.",
  "Soil temp rules are not evaluated.": "බිම් උෂ්ණත්ව නීති ඇගයීමට නොගන්නා ලදී.",
  "Nutrient alerts are not evaluated.": "පෝෂක අනතුරු ඇගයීමට නොගන්නා ලදී.",
  "Air temperature is above 35C. Crop heat stress risk is high.": "වායු උෂ්ණත්වය 35C ඉක්මවා ඇත. උෂ්ණත්ව ආතති අවදානම ඉහළයි.",
  "Air temperature is in the 25-30C optimal growth range.": "වායු උෂ්ණත්වය 25-30C ප්‍රශස්ත පරාසයේ ඇත.",
  "Air temperature is below 20C. Growth may slow down.": "වායු උෂ්ණත්වය 20Cට අඩුයි. වර්ධනය මන්දගාමී විය හැක."
};

const NOTE_TRANSLATIONS = {
  "Keep consistently moist.": "නිතරම තෙතමනය තබා ගන්න.",
  "Critical germination window.": "අංකුරණයට අත්‍යවශ්‍ය පරාසය.",
  "Prevents casing from drying.": "අංකුර තලය වියළීම වැළැක්වේ.",
  "Supports warm soil.": "බිම උණුසුම්ව තබා ගන්න.",
  "Very low nutrients.": "ඉතා අඩු පෝෂක මට්ටමක්.",
  "Slightly drier than germination.": "අංකුරණයට වඩා ටිකක් වියළි.",
  "Below 20C halts uptake.": "20Cට පහළින් අවශෝෂණය නවතයි.",
  "Avoid >80% disease risk.": "80% ඉක්මවා රෝග අවදානම වැඩිය.",
  "Delicate stems.": "නොබලවත් කඳන්.",
  "Gentle feeding.": "මද පෝෂණය.",
  "Higher demand from leaf area.": "පත්‍ර ප්‍රමාණය වැඩි නිසා වැඩි ජල අවශ්‍යතාව.",
  "Wide tolerance.": "පුළුල් ඉවසීමක්.",
  "Dense foliage needs airflow.": "ඝන පත්‍රභාවයට වායුසංසරණය අවශ්‍යයි.",
  "Optimal photosynthesis.": "ප්‍රශස්ත ප්‍රභාසංශ්ලේෂණය.",
  "Full vegetative feed.": "සම්පූර්ණ වර්ධන පෝෂණය.",
  "Slightly drier to trigger flowering.": "මල් හටගැනීමට ටිකක් වියළි තබා ගන්න.",
  "Cool roots retain flowers.": "සිසිල් මූල මල් රඳවා තබයි.",
  "Keep pollen dry.": "රාණු වියළිව තබා ගන්න.",
  "Avoid >32C heat stress.": "32C ඉක්මවීමේ උෂ්ණත්ව ආතතිය වැළැක්වෙන්න.",
  "Bloom formula.": "මල් වර්ධන පොහොර මිශ්‍රණය.",
  "Consistency prevents cracking.": "නිරන්තර තෙතමනය ඉරීම වැළැක්වෙයි.",
  "Cool roots + warm air.": "සිසිල් මූල + උණුසුම් වායු.",
  "Low humidity aids color.": "අඩු ආර්ද්‍රතාව වර්ණ ගැන්වීමට උපකාරී.",
  "Warm days help ripening.": "උණුසුම් දින පළා වීමට උපකාරී.",
  "Lower than vegetative.": "වර්ධන අදියරට වඩා අඩුයි.",
  "DHT22: 25-30C optimal, <20C slow growth, >35C heat stress.": "DHT22: 25-30C ප්‍රශස්ත, <20C මන්දගාමී වර්ධන, >35C උෂ්ණත්ව ආතතිය."
};

const formatValue = (value, unit) => {
  if (typeof value !== "number") {
    return "--";
  }

  return unit ? `${value.toFixed(2)} ${unit}` : value.toFixed(2);
};

const getTone = (status) => (status === "ok" ? "default" : status === "unknown" ? "default" : "accent");

const getLocalized = (value, language) => value?.[language] || value?.en || value;

const SENSOR_COLORS = [
  theme.colors.accent,
  theme.colors.primary,
  theme.colors.primaryDark,
  theme.colors.text,
  theme.colors.danger
];

const getStatusStyle = (status) => {
  switch (status) {
    case "ok":
      return {
        pillStyle: styles.statusNormal,
        textStyle: styles.statusNormalText
      };
    case "low":
      return {
        pillStyle: styles.statusLow,
        textStyle: styles.statusLowText
      };
    case "high":
      return {
        pillStyle: styles.statusHigh,
        textStyle: styles.statusHighText
      };
    default:
      return {
        pillStyle: styles.statusUnknown,
        textStyle: styles.statusUnknownText
      };
  }
};

const SensorCard = ({ title, value, unit, range, status, statusLabel, color }) => {
  const numeric = typeof value === "number" ? value : null;
  const percent = numeric && range
    ? Math.min(Math.max(((numeric - range.min) / (range.max - range.min)) * 100, 0), 100)
    : 0;
  const statusInfo = getStatusStyle(status);

  return (
    <View style={styles.sensorCard}>
      <View style={styles.sensorHeader}>
        <View style={styles.sensorTitleRow}>
          <View style={[styles.sensorIcon, { backgroundColor: color }]} />
          <Text style={styles.sensorTitle}>{title}</Text>
        </View>
        <View style={[styles.statusPill, statusInfo.pillStyle]}>
          <Text style={[styles.statusPillText, statusInfo.textStyle]}>{statusLabel}</Text>
        </View>
      </View>
      <Text style={styles.sensorValue}>{numeric !== null ? `${numeric.toFixed(1)}${unit}` : "--"}</Text>
      <View style={styles.sensorMetaRow}>
        <Text style={styles.sensorMetaText}>
          Optimal: {range.min} - {range.max}{unit}
        </Text>
        <Text style={styles.sensorMetaText}>{numeric !== null ? `${Math.round(percent)}%` : "--"}</Text>
      </View>
      <View style={styles.sensorBarTrack}>
        <View style={[styles.sensorBarFill, { width: `${percent}%`, backgroundColor: color }]} />
      </View>
    </View>
  );
};

const GrowthStageSelectorCard = ({ stages, stageId, onStageChange, language }) => {
  const currentIndex = stages.findIndex((stage) => stage.id === stageId);
  const progress = stages.length > 1 ? (currentIndex / (stages.length - 1)) * 100 : 0;
  const stageEmojis = {
    stage1: "🌱",
    stage2: "🌿",
    stage3: "🍃",
    stage4: "🌸",
    stage5: "🍑"
  };

  return (
    <View style={styles.stageSelector}>
      <Text style={styles.stageSelectorTitle}>Growth stage</Text>
      <View style={styles.stageSelectorTrack}>
        <View style={styles.stageSelectorLine} />
        <View style={[styles.stageSelectorLineActive, { width: `${progress}%` }]} />
        <View style={styles.stageSelectorRow}>
          {stages.map((stage, index) => {
            const isActive = stage.id === stageId;
            const isPast = index < currentIndex;
            const emoji = stageEmojis[stage.id] || "🌶️";
            return (
              <Pressable
                key={stage.id}
                onPress={() => onStageChange(stage.id)}
                style={styles.stageSelectorItem}
              >
                <View
                  style={[
                    styles.stageSelectorDot,
                    isActive && styles.stageSelectorDotActive,
                    isPast && !isActive && styles.stageSelectorDotPast
                  ]}
                >
                  <Text style={[styles.stageSelectorDotEmoji, isActive && styles.stageSelectorDotEmojiActive]}>
                    {emoji}
                  </Text>
                </View>
                <Text style={styles.stageSelectorLabel}>{getLocalized(STAGE_LABELS[stage.id], language)}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>
      <View style={styles.stageSelectorDetail}>
        <Text style={styles.stageSelectorCurrent}>{getLocalized(STAGE_LABELS[stageId], language)}</Text>
        <Text style={styles.stageSelectorDuration}>{getLocalized(STAGE_DURATIONS[stageId], language)}</Text>
      </View>
    </View>
  );
};

const SensorTrendChart = ({ series, emptyLabel }) => {
  const [width, setWidth] = useState(0);
  const height = 180;
  const numericValues = series.flatMap((item) => item.values.filter((value) => typeof value === "number"));

  const buildLine = (values, min, max) => {
    const spread = max - min || 1;
    const step = width / Math.max(values.length - 1, 1);
    return values
      .map((value, index) => {
        if (typeof value !== "number") {
          return null;
        }
        const x = step * index;
        const y = height - ((value - min) / spread) * height;
        return `${x},${y}`;
      })
      .filter(Boolean)
      .join(" ");
  };

  if (!numericValues.length) {
    return (
      <View style={styles.trendCard}>
        <Text style={styles.trendEmpty}>{emptyLabel}</Text>
      </View>
    );
  }

  const min = Math.min(...numericValues);
  const max = Math.max(...numericValues);

  return (
    <View style={styles.trendCard} onLayout={(event) => setWidth(event.nativeEvent.layout.width)}>
      <Text style={styles.trendTitle}>Sensor trends</Text>
      {width > 0 ? (
        <Svg width={width} height={height}>
          <Rect x={0} y={0} width={width} height={height} fill={theme.colors.surfaceAlt} rx={12} />
          {series.map((item) => (
            <Polyline
              key={item.key}
              points={buildLine(item.values, min, max)}
              fill="none"
              stroke={item.color}
              strokeWidth={2.5}
            />
          ))}
        </Svg>
      ) : null}
      <View style={styles.trendLegend}>
        {series.map((item) => (
          <View key={item.key} style={styles.trendLegendItem}>
            <View style={[styles.trendLegendDot, { backgroundColor: item.color }]} />
            <Text style={styles.trendLegendText}>{item.label}</Text>
          </View>
        ))}
      </View>
    </View>
  );
};

const SensorSnapshotBars = ({ metrics, emptyLabel }) => {
  const [width, setWidth] = useState(0);

  const toNumber = (value) => (typeof value === "number" && Number.isFinite(value) ? value : null);
  const clamp01 = (value) => Math.min(1, Math.max(0, value));

  const rows = metrics.map((metric) => {
    const value = toNumber(metric.value);
    const rangeMin = toNumber(metric.range?.min);
    const rangeMax = toNumber(metric.range?.max);
    const domainMin = Math.min(
      ...(typeof value === "number" ? [value] : []),
      ...(typeof rangeMin === "number" ? [rangeMin] : []),
      ...(typeof rangeMax === "number" ? [rangeMax] : [])
    );
    const domainMax = Math.max(
      ...(typeof value === "number" ? [value] : []),
      ...(typeof rangeMin === "number" ? [rangeMin] : []),
      ...(typeof rangeMax === "number" ? [rangeMax] : [])
    );

    const spread = Number.isFinite(domainMax - domainMin) && domainMax !== domainMin ? domainMax - domainMin : 1;
    const pad = spread * 0.15;
    const min = Number.isFinite(domainMin) ? domainMin - pad : 0;
    const max = Number.isFinite(domainMax) ? domainMax + pad : 1;
    const scale = (v) => (v - min) / (max - min || 1);

    return {
      ...metric,
      value,
      min,
      max,
      valuePct: value == null ? null : clamp01(scale(value)),
      rangeStartPct: rangeMin == null ? null : clamp01(scale(rangeMin)),
      rangeEndPct: rangeMax == null ? null : clamp01(scale(rangeMax))
    };
  });

  const hasAnyValue = rows.some((row) => row.value != null);
  if (!hasAnyValue) {
    return (
      <View style={styles.snapshotCard}>
        <Text style={styles.trendEmpty}>{emptyLabel}</Text>
      </View>
    );
  }

  return (
    <View style={styles.snapshotCard} onLayout={(event) => setWidth(event.nativeEvent.layout.width)}>
      {rows.map((row) => (
        <View key={row.key} style={styles.snapshotRow}>
          <View style={styles.snapshotRowHeader}>
            <Text style={styles.snapshotLabel}>{row.title}</Text>
            <Text style={styles.snapshotValue}>
              {row.value == null ? "--" : row.value}
              {row.unit ? ` ${row.unit}` : ""}
            </Text>
          </View>
          <View style={styles.snapshotBarTrack}>
            {width > 0 && row.rangeStartPct != null && row.rangeEndPct != null ? (
              <View
                style={[
                  styles.snapshotBarRange,
                  {
                    left: Math.min(row.rangeStartPct, row.rangeEndPct) * width,
                    width: Math.max(4, Math.abs(row.rangeEndPct - row.rangeStartPct) * width)
                  }
                ]}
              />
            ) : null}
            {width > 0 && row.valuePct != null ? (
              <View style={[styles.snapshotMarker, { left: row.valuePct * width - 5, borderColor: row.color }]} />
            ) : null}
          </View>
          <View style={styles.snapshotScaleRow}>
            <Text style={styles.snapshotScaleText}>{Number.isFinite(row.min) ? row.min.toFixed(1) : "--"}</Text>
            <Text style={styles.snapshotScaleText}>{Number.isFinite(row.max) ? row.max.toFixed(1) : "--"}</Text>
          </View>
        </View>
      ))}
    </View>
  );
};

const AlertPanel = ({ alerts, emptyLabel }) => {
  if (!alerts.length) {
    return <Text style={styles.emptyText}>{emptyLabel}</Text>;
  }

  return (
    <View style={styles.alertStack}>
      {alerts.map((alert, index) => (
        <View key={`${alert.title}-${index}`} style={[styles.alertCard, styles[`alert${alert.level}`]]}>
          <View style={styles.alertHeader}>
            <View style={[styles.alertBadge, styles[`alertBadge${alert.level}`]]} />
            <Text style={styles.alertTitle}>{alert.title}</Text>
          </View>
          <Text style={styles.alertDetail}>{alert.detail}</Text>
        </View>
      ))}
    </View>
  );
};

const buildPolyline = (values, width, height) => {
  const numericValues = values.filter((value) => typeof value === "number");
  if (numericValues.length < 2) {
    return "";
  }

  const min = Math.min(...numericValues);
  const max = Math.max(...numericValues);
  const spread = max - min || 1;
  const step = width / Math.max(values.length - 1, 1);

  return values
    .map((value, index) => {
      if (typeof value !== "number") {
        return null;
      }
      const x = step * index;
      const y = height - ((value - min) / spread) * height;
      return `${x},${y}`;
    })
    .filter(Boolean)
    .join(" ");
};

const buildChartSvg = (title, unit, values, color) => {
  const width = 520;
  const height = 160;
  const points = buildPolyline(values, width, height);

  if (!points) {
    return `<div style="font-size:12px;color:#6C7A6B">No data yet.</div>`;
  }

  return `
    <div style="margin-bottom:16px;">
      <div style="font-size:12px;color:#0E1713;font-weight:600;margin-bottom:6px;">${title}</div>
      <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}" xmlns="http://www.w3.org/2000/svg">
        <polyline points="${points}" fill="none" stroke="${color}" stroke-width="2" />
      </svg>
      <div style="font-size:11px;color:#6C7A6B;">${unit}</div>
    </div>
  `;
};

export default function StageDashboardScreen() {
  const [stages, setStages] = useState(getStages());
  const [stageId, setStageId] = useState(getStages()[1]?.id || getStages()[0].id);
  const [language, setLanguage] = useState("en");
  const [chartTab, setChartTab] = useState("trends");
  const [flags, setFlags] = useState({
    slowGrowth: false,
    noFlowerDevelopment: false,
    noFruitSet: false,
    slowRipening: false
  });
  const [snapshot, setSnapshot] = useState(null);
  const [history, setHistory] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [isDownloading, setIsDownloading] = useState(false);

  useEffect(() => {
    let isMounted = true;
    fetchMonitoringStages()
      .then((backendStages) => {
        if (isMounted && backendStages.length) {
          setStages(backendStages);
        }
      })
      .catch((error) => console.warn("Using fallback stage profiles", error));
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    appendLocalArray("stageHistory", { stageId, timestamp: Date.now() }, 90).catch((error) => {
      console.warn("Failed to save stage history", error);
    });
  }, [stageId]);

  const t = (key) => TEXT[language][key] || TEXT.en[key] || key;
  const statusLabelFor = (status) => {
    switch (status) {
      case "low":
        return t("statusLow");
      case "high":
        return t("statusHigh");
      case "ok":
        return t("statusNormal");
      default:
        return t("statusUnknown");
    }
  };

  const toNumber = (value) => {
    const numeric = typeof value === "number" ? value : Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  };

  const handleDownloadReport = async () => {
    try {
      setIsDownloading(true);
      const now = new Date();
      const stageSummaries = stages.map((item) => evaluateStage(snapshot, item.id, {}, stages));

      const chartHtml = [
        buildChartSvg(t("airTemp"), "C", history.map((entry) => entry.airTemp), "#2F7D32"),
        buildChartSvg(t("airHumidity"), "%", history.map((entry) => entry.airHumidity), "#76D34E"),
        buildChartSvg(t("soilAnalog"), "", history.map((entry) => entry.soilAnalog), "#F2B949"),
        buildChartSvg(t("ec"), "mS/cm", history.map((entry) => entry.ec), "#22372B")
      ].join("");

      const alertsHtml = stageSummaries
        .map((entry) => {
          const stageName = getLocalized(STAGE_LABELS[entry.stage.id], language);
          const stageAlerts = entry.alerts
            .map((alert) => `<li><strong>${alert.title}</strong> - ${alert.detail}</li>`)
            .join("");
          return `
            <h3>${stageName}</h3>
            <ul>${stageAlerts || `<li>${t("noAlerts")}</li>`}</ul>
          `;
        })
        .join("");

      const thresholdsHtml = stageSummaries
        .map((entry) => {
          const stageName = getLocalized(STAGE_LABELS[entry.stage.id], language);
          const rows = Object.entries(entry.stage.thresholds)
            .map(([key, range]) => `<tr><td>${key}</td><td>${range.min} - ${range.max} ${range.unit}</td></tr>`)
            .join("");
          return `
            <h3>${stageName}</h3>
            <table>
              <thead><tr><th>Metric</th><th>Range</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          `;
        })
        .join("");

      const reportHtml = `
        <html>
          <head>
            <meta charset="utf-8" />
            <style>
              body { font-family: Arial, sans-serif; color: #0E1713; padding: 24px; }
              h1 { font-size: 20px; margin-bottom: 4px; }
              h2 { font-size: 16px; margin-top: 20px; }
              h3 { font-size: 14px; margin-top: 12px; }
              table { width: 100%; border-collapse: collapse; margin-top: 8px; }
              th, td { border: 1px solid #DDE3DD; padding: 6px; font-size: 12px; text-align: left; }
              ul { padding-left: 18px; }
              li { font-size: 12px; margin-bottom: 4px; }
              .meta { font-size: 12px; color: #6C7A6B; }
              .section { margin-top: 16px; }
            </style>
          </head>
          <body>
            <h1>IoT Stage Report</h1>
            <div class="meta">Generated: ${now.toLocaleString()}</div>
            <div class="section">
              <h2>${t("trendCharts")}</h2>
              ${chartHtml}
            </div>
            <div class="section">
              <h2>${t("smartAlertsTitle")}</h2>
              ${alertsHtml}
            </div>
            <div class="section">
              <h2>${t("thresholds")}</h2>
              ${thresholdsHtml}
            </div>
          </body>
        </html>
      `;

      if (Platform.OS === "web") {
        const reportWindow = window.open("", "_blank");
        if (!reportWindow) {
          throw new Error("Popup blocked");
        }
        reportWindow.document.write(reportHtml);
        reportWindow.document.close();
        reportWindow.focus();
        reportWindow.print();
        Alert.alert(t("downloadReport"), t("downloadSuccess"));
        return;
      }

      const { uri } = await Print.printToFileAsync({ html: reportHtml });
      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(uri, {
          mimeType: "application/pdf",
          dialogTitle: t("downloadReport")
        });
        Alert.alert(t("downloadReport"), t("downloadSuccess"));
      } else {
        const fileName = `iot_stage_report_${Date.now()}.pdf`;
        const targetUri = `${FileSystem.documentDirectory}${fileName}`;
        await FileSystem.copyAsync({ from: uri, to: targetUri });
        Alert.alert(t("downloadReport"), `Saved to ${targetUri}`);
      }
    } catch (error) {
      console.error("Failed to download report", error);
      Alert.alert(t("downloadReport"), t("downloadFailed"));
    } finally {
      setIsDownloading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;

    const loadSnapshot = async () => {
      try {
        const data = await getRealtimeSensorSnapshot();
        if (isMounted) {
          setSnapshot(data);
          setHistory((prevHistory) => {
            const nextEntry = {
              soilAnalog: toNumber(data?.soil_analog),
              soilMoisture: toNumber(
                data?.soil_moisture ??
                  data?.soilMoisture ??
                  data?.soil_moisture_percent ??
                  data?.soilMoisturePercent
              ),
              soilTemp: toNumber(data?.soil_temperature_c ?? data?.soil_temp_c ?? data?.ds18b20_temperature_c),
              airTemp: toNumber(data?.temperature_c),
              airHumidity: toNumber(data?.humidity),
              ec: toNumber(data?.ec),
              timestamp: Date.now()
            };

            const nextHistory = [...prevHistory, nextEntry];
            return nextHistory.length > HISTORY_LIMIT ? nextHistory.slice(-HISTORY_LIMIT) : nextHistory;
          });
          setLastUpdated(new Date());
        }
      } catch (error) {
        console.error("Failed to load IoT snapshot", error);
      }
    };

    loadSnapshot();
    const intervalId = setInterval(loadSnapshot, 5000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  const evaluation = useMemo(() => evaluateStage(snapshot, stageId, flags, stages), [snapshot, stageId, flags, stages]);
  const { stage, readings, statuses, alerts } = evaluation;
  const stageTitle = getLocalized(STAGE_LABELS[stage.id], language);
  const stageDuration = getLocalized(STAGE_DURATIONS[stage.id], language);

  const sensorCards = [
    {
      key: "soilAnalog",
      title: stage.thresholds.soilMoisture?.unit === "%" ? t("soilMoisturePercent") : t("soilAnalog"),
      value: stage.thresholds.soilMoisture?.unit === "%" ? readings.soilMoisturePercent : readings.soilAnalog,
      unit: stage.thresholds.soilMoisture?.unit || "",
      range: stage.thresholds.soilMoisture,
      status: statuses.soilMoisture,
      statusLabel: statusLabelFor(statuses.soilMoisture)
    },
    {
      key: "soilMoisturePercent",
      title: t("soilMoisturePercent"),
      value: readings.soilMoisturePercent,
      unit: "%",
      range: { min: 0, max: 100 },
      status: "unknown",
      statusLabel: t("statusUnknown")
    },
    {
      key: "soilTemp",
      title: t("soilTemp"),
      value: readings.soilTemp,
      unit: "C",
      range: stage.thresholds.soilTemp,
      status: statuses.soilTemp,
      statusLabel: statusLabelFor(statuses.soilTemp)
    },
    {
      key: "airTemp",
      title: t("airTemp"),
      value: readings.airTemp,
      unit: "C",
      range: stage.thresholds.airTemp,
      status: statuses.airTemp,
      statusLabel: statusLabelFor(statuses.airTemp)
    },
    {
      key: "airHumidity",
      title: t("airHumidity"),
      value: readings.airHumidity,
      unit: "%",
      range: stage.thresholds.airHumidity,
      status: statuses.airHumidity,
      statusLabel: statusLabelFor(statuses.airHumidity)
    },
    {
      key: "ec",
      title: t("ec"),
      value: readings.ec,
      unit: "mS/cm",
      range: stage.thresholds.ec,
      status: statuses.ec,
      statusLabel: statusLabelFor(statuses.ec)
    }
  ];

  const activeFlags = stage.flags;
  const thresholdRows = Object.entries(stage.thresholds).map(([key, range]) => ({
    key,
    label:
      key === "soilMoisture"
        ? t("soilMoistureLabel")
        : key === "soilTemp"
          ? t("soilTempLabel")
          : key === "airHumidity"
            ? t("airHumidityLabel")
            : key === "airTemp"
              ? t("airTempLabel")
              : t("ecLabel"),
    range: `${range.min} - ${range.max} ${range.unit}`,
    note: language === "si" ? NOTE_TRANSLATIONS[range.note] || range.note : range.note
  }));

  const localAlerts = alerts.map((alert) => ({
    ...alert,
    title: language === "si" ? ALERT_TITLE_TRANSLATIONS[alert.title] || alert.title : alert.title,
    detail: language === "si" ? ALERT_DETAIL_TRANSLATIONS[alert.detail] || alert.detail : alert.detail
  }));

  const statusValues = Object.values(statuses).filter((status) => status !== "unknown");
  const okCount = statusValues.filter((status) => status === "ok").length;
  const matchScore = statusValues.length ? Math.round((okCount / statusValues.length) * 100) : 0;
  const mockAiSummary = useMemo(
    () => getMockAiAlertSummary({ readings, statuses, history, stage }),
    [readings, statuses, history, stage]
  );
  const [aiSummary, setAiSummary] = useState(mockAiSummary);

  useEffect(() => {
    setAiSummary(mockAiSummary);
  }, [mockAiSummary]);

  useEffect(() => {
    if (!snapshot) {
      return;
    }

    let isMounted = true;
    const timer = setTimeout(async () => {
      try {
        const payload = {
          stage_id: stageId,
          readings: {
            soil_analog: readings.soilAnalog,
            soil_moisture: readings.soilMoisturePercent,
            soil_temp: readings.soilTemp,
            air_temp: readings.airTemp,
            air_humidity: readings.airHumidity,
            ec: readings.ec
          },
          statuses,
          history: history.slice(-24)
        };

        const result = await fetchAiAlertSummary({ payload });
        if (isMounted && result) {
          setAiSummary(result);
        }
      } catch (error) {
        console.warn("AI alerts fallback to mock", error);
      }
    }, 500);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [snapshot, stageId, readings, statuses, history]);

  const trendSeries = [
    {
      key: "soilTemp",
      label: t("soilTemp"),
      values: history.map((entry) => entry.soilTemp),
      color: SENSOR_COLORS[0]
    },
    {
      key: "airTemp",
      label: t("airTemp"),
      values: history.map((entry) => entry.airTemp),
      color: SENSOR_COLORS[1]
    },
    {
      key: "humidity",
      label: t("airHumidity"),
      values: history.map((entry) => entry.airHumidity),
      color: SENSOR_COLORS[2]
    }
  ];

  const latestHistory = history[history.length - 1] || {};
  const snapshotMetrics = [
    {
      key: "soilAnalog",
      title: t("soilAnalog"),
      value: latestHistory.soilAnalog,
      unit: "",
      range: stage.thresholds.soilMoisture,
      color: SENSOR_COLORS[0]
    },
    {
      key: "soilMoisturePercent",
      title: t("soilMoisturePercent"),
      value: latestHistory.soilMoisture,
      unit: "%",
      range: { min: 0, max: 100 },
      color: SENSOR_COLORS[1]
    },
    {
      key: "soilTemp",
      title: t("soilTemp"),
      value: latestHistory.soilTemp,
      unit: "C",
      range: stage.thresholds.soilTemp,
      color: SENSOR_COLORS[2]
    },
    {
      key: "airTemp",
      title: t("airTemp"),
      value: latestHistory.airTemp,
      unit: "C",
      range: stage.thresholds.airTemp,
      color: SENSOR_COLORS[3]
    },
    {
      key: "airHumidity",
      title: t("airHumidity"),
      value: latestHistory.airHumidity,
      unit: "%",
      range: stage.thresholds.airHumidity,
      color: SENSOR_COLORS[4] || SENSOR_COLORS[0]
    },
    {
      key: "ec",
      title: t("ec"),
      value: latestHistory.ec,
      unit: "mS/cm",
      range: stage.thresholds.ec,
      color: SENSOR_COLORS[0]
    }
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <ScreenHeader
        eyebrow={t("stageLogic")}
        badge={t("smartAlerts")}
        title={t("stageDashboard")}
        subtitle={t("stageSubtitle")}
      />

      <View style={styles.bannerCard}>
        <Image
          source={require("../images/A to Z guide.jpeg")}
          style={styles.bannerImage}
          resizeMode="cover"
        />
        <View style={styles.bannerOverlay}>
          <Text style={styles.bannerTitle}>A to Z Guide</Text>
          <Text style={styles.bannerSubtitle}>Field checklist for each growth stage.</Text>
        </View>
      </View>

      <SectionCard title={t("language")} subtitle="">
        <View style={styles.languageRow}>
          <View style={styles.languageButton}>
            <PrimaryButton
              label={t("english")}
              onPress={() => setLanguage("en")}
              variant={language === "en" ? "primary" : "outline"}
            />
          </View>
          <View style={styles.languageButton}>
            <PrimaryButton
              label={t("sinhala")}
              onPress={() => setLanguage("si")}
              variant={language === "si" ? "primary" : "outline"}
            />
          </View>
        </View>
      </SectionCard>

      <SectionCard
        title={t("stageSelection")}
        subtitle={`${t("current")}: ${stageTitle} (${stageDuration})${lastUpdated ? ` • ${t("updated")}: ${lastUpdated.toLocaleTimeString()}` : ""}`}
      >
        <GrowthStageSelectorCard
          stages={stages}
          stageId={stageId}
          onStageChange={setStageId}
          language={language}
        />
      </SectionCard>

      {activeFlags.length ? (
        <SectionCard title={t("contextFlags")} subtitle={t("toggleFlags")}>
          <View style={styles.flagRow}>
            {activeFlags.map((flag) => (
              <View key={flag} style={styles.flagButton}>
                <PrimaryButton
                  label={getLocalized(FLAG_LABELS[flag], language)}
                  onPress={() => setFlags((prev) => ({ ...prev, [flag]: !prev[flag] }))}
                  variant={flags[flag] ? "primary" : "outline"}
                />
              </View>
            ))}
          </View>
        </SectionCard>
      ) : null}

      <SectionCard title={t("liveReadings")} subtitle={t("liveSubtitle")}>
        <View style={styles.sensorGrid}>
          {sensorCards.map((card, index) => (
            <View key={card.key} style={styles.sensorCell}>
              <SensorCard
                title={card.title}
                value={card.value}
                unit={card.unit}
                range={card.range}
                status={card.status}
                statusLabel={card.statusLabel}
                color={SENSOR_COLORS[index % SENSOR_COLORS.length]}
              />
            </View>
          ))}
        </View>
      </SectionCard>

      <SectionCard title={t("matchSummary")} subtitle={t("matchSubtitle")}>
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label={t("matchScore")} value={`${matchScore}%`} tone={matchScore >= 70 ? "accent" : "default"} />
          </View>
          <View style={styles.gridItem}>
            <StatTile label={t("metricsInRange")} value={`${okCount}/${statusValues.length || 0}`} />
          </View>
        </View>
      </SectionCard>

      <SectionCard title={t("downloadReport")} subtitle={t("downloadSubtitle")}>
        <PrimaryButton
          label={isDownloading ? `${t("downloadButton")}...` : t("downloadButton")}
          onPress={handleDownloadReport}
          disabled={isDownloading}
        />
      </SectionCard>

      <SectionCard title={t("trendCharts")} subtitle={t("trendChartsSubtitle")}>
        <View style={styles.chartTabRow}>
          <View style={styles.chartTabButton}>
            <PrimaryButton
              label={t("chartTabTrends")}
              onPress={() => setChartTab("trends")}
              variant={chartTab === "trends" ? "primary" : "outline"}
            />
          </View>
          <View style={styles.chartTabButton}>
            <PrimaryButton
              label={t("chartTabSnapshot")}
              onPress={() => setChartTab("snapshot")}
              variant={chartTab === "snapshot" ? "primary" : "outline"}
            />
          </View>
        </View>
        {chartTab === "snapshot" ? (
          <SensorSnapshotBars metrics={snapshotMetrics} emptyLabel={t("chartEmpty")} />
        ) : (
          <SensorTrendChart series={trendSeries} emptyLabel={t("chartEmpty")} />
        )}
      </SectionCard>

      <SectionCard title={t("smartAlertsTitle")} subtitle={t("smartAlertsSubtitle")}>
        <View style={styles.aiPanel}>
          <View style={styles.aiHeader}>
            <Text style={styles.aiTitle}>{t("aiRiskTitle")}</Text>
            <View style={[styles.aiBadge, aiSummary.anomalyDetected ? styles.aiBadgeAlert : styles.aiBadgeOk]}>
              <Text style={styles.aiBadgeText}>
                {aiSummary.anomalyDetected ? t("aiAnomaly") : t("aiStable")}
              </Text>
            </View>
          </View>
          <View style={styles.aiRow}>
            <Text style={styles.aiScoreLabel}>{t("aiRiskScore")}</Text>
            <Text style={styles.aiScoreValue}>{aiSummary.riskScore}</Text>
          </View>
          <Text style={styles.aiSummaryText}>{aiSummary.summary}</Text>
          <Text style={styles.aiRecommendation}>{aiSummary.recommendation}</Text>
        </View>
        <AlertPanel alerts={localAlerts} emptyLabel={t("noAlerts")} />
      </SectionCard>

      <SectionCard title={t("thresholds")} subtitle={t("thresholdsSubtitle")}>
        {thresholdRows.map((row) => (
          <View key={row.key} style={styles.thresholdRow}>
            <View style={styles.thresholdText}>
              <Text style={styles.thresholdLabel}>{row.label}</Text>
              <Text style={styles.thresholdNote}>{row.note}</Text>
            </View>
            <Text style={styles.thresholdRange}>{row.range}</Text>
          </View>
        ))}
      </SectionCard>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.lg },
  bannerCard: {
    borderRadius: theme.radius.lg,
    overflow: "hidden",
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    marginBottom: theme.spacing.lg
  },
  bannerImage: {
    width: "100%",
    height: 160
  },
  bannerOverlay: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    padding: theme.spacing.md,
    backgroundColor: "rgba(14, 23, 19, 0.75)"
  },
  bannerTitle: {
    color: theme.colors.text,
    fontFamily: theme.typography.title,
    fontSize: 16
  },
  bannerSubtitle: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 12,
    marginTop: theme.spacing.xs
  },
  grid: {
    flexDirection: "row",
    marginBottom: theme.spacing.sm
  },
  gridItem: {
    flex: 1,
    marginRight: theme.spacing.sm
  },
  languageRow: {
    flexDirection: "row",
    marginHorizontal: -theme.spacing.xs
  },
  languageButton: {
    width: "50%",
    padding: theme.spacing.xs
  },
  flagRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginHorizontal: -theme.spacing.xs
  },
  flagButton: {
    width: "50%",
    padding: theme.spacing.xs
  },
  sensorGrid: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginHorizontal: -theme.spacing.xs
  },
  sensorCell: {
    width: "50%",
    padding: theme.spacing.xs
  },
  sensorCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    padding: theme.spacing.md
  },
  sensorHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: theme.spacing.sm
  },
  sensorTitleRow: {
    flexDirection: "row",
    alignItems: "center"
  },
  sensorIcon: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: theme.spacing.sm
  },
  sensorTitle: {
    color: theme.colors.muted,
    fontFamily: theme.typography.medium,
    fontSize: 12
  },
  sensorValue: {
    color: theme.colors.text,
    fontFamily: theme.typography.title,
    fontSize: 20,
    marginBottom: theme.spacing.xs
  },
  sensorMetaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: theme.spacing.sm
  },
  sensorMetaText: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 11
  },
  sensorBarTrack: {
    height: 8,
    backgroundColor: theme.colors.surfaceAlt,
    borderRadius: 8,
    overflow: "hidden"
  },
  sensorBarFill: {
    height: "100%",
    borderRadius: 8
  },
  statusPill: {
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: 2,
    borderRadius: theme.radius.sm,
    borderWidth: 1
  },
  statusPillText: {
    fontFamily: theme.typography.medium,
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: 0.6
  },
  statusNormal: {
    backgroundColor: theme.colors.glow,
    borderColor: theme.colors.primary
  },
  statusNormalText: {
    color: theme.colors.primary
  },
  statusLow: {
    backgroundColor: "#2B2418",
    borderColor: theme.colors.accent
  },
  statusLowText: {
    color: theme.colors.accent
  },
  statusHigh: {
    backgroundColor: "#2B1A1A",
    borderColor: theme.colors.danger
  },
  statusHighText: {
    color: theme.colors.danger
  },
  statusUnknown: {
    backgroundColor: theme.colors.surfaceAlt,
    borderColor: theme.colors.borderStrong
  },
  statusUnknownText: {
    color: theme.colors.muted
  },
  stageSelector: {
    backgroundColor: theme.colors.surfaceAlt,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    padding: theme.spacing.md
  },
  stageSelectorTitle: {
    color: theme.colors.muted,
    fontFamily: theme.typography.medium,
    fontSize: 12,
    marginBottom: theme.spacing.md
  },
  stageSelectorTrack: {
    position: "relative",
    marginBottom: theme.spacing.md
  },
  stageSelectorLine: {
    position: "absolute",
    top: 14,
    left: 16,
    right: 16,
    height: 2,
    backgroundColor: theme.colors.borderStrong
  },
  stageSelectorLineActive: {
    position: "absolute",
    top: 14,
    left: 16,
    height: 2,
    backgroundColor: theme.colors.primary
  },
  stageSelectorRow: {
    flexDirection: "row",
    justifyContent: "space-between"
  },
  stageSelectorItem: {
    alignItems: "center",
    width: "18%"
  },
  stageSelectorDot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    alignItems: "center",
    justifyContent: "center"
  },
  stageSelectorDotActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary
  },
  stageSelectorDotPast: {
    backgroundColor: theme.colors.surfaceAlt,
    borderColor: theme.colors.borderStrong
  },
  stageSelectorDotText: {
    fontFamily: theme.typography.medium,
    fontSize: 12,
    color: theme.colors.muted
  },
  stageSelectorDotTextActive: {
    color: "#0E1713"
  },
  stageSelectorDotEmoji: {
    fontSize: 14
  },
  stageSelectorDotEmojiActive: {
    fontSize: 15
  },
  stageSelectorLabel: {
    marginTop: theme.spacing.xs,
    fontSize: 10,
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    textAlign: "center"
  },
  stageSelectorDetail: {
    alignItems: "center"
  },
  stageSelectorCurrent: {
    color: theme.colors.text,
    fontFamily: theme.typography.title,
    fontSize: 16
  },
  stageSelectorDuration: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 12,
    marginTop: theme.spacing.xs
  },
  trendCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    padding: theme.spacing.md
  },
  trendTitle: {
    color: theme.colors.muted,
    fontFamily: theme.typography.medium,
    fontSize: 12,
    marginBottom: theme.spacing.sm
  },
  trendLegend: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: theme.spacing.sm
  },
  trendLegendItem: {
    flexDirection: "row",
    alignItems: "center",
    marginRight: theme.spacing.md,
    marginBottom: theme.spacing.xs
  },
  trendLegendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: theme.spacing.xs
  },
  trendLegendText: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 11
  },
  trendEmpty: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 12
  },
  chartTabRow: {
    flexDirection: "row",
    marginBottom: theme.spacing.sm
  },
  chartTabButton: {
    flex: 1,
    marginRight: theme.spacing.sm
  },
  snapshotCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    padding: theme.spacing.md
  },
  snapshotRow: {
    marginBottom: theme.spacing.md
  },
  snapshotRowHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: theme.spacing.xs
  },
  snapshotLabel: {
    color: theme.colors.muted,
    fontFamily: theme.typography.medium,
    fontSize: 12
  },
  snapshotValue: {
    color: theme.colors.text,
    fontFamily: theme.typography.title,
    fontSize: 12
  },
  snapshotBarTrack: {
    height: 14,
    backgroundColor: theme.colors.surfaceAlt,
    borderRadius: 10,
    overflow: "hidden",
    position: "relative"
  },
  snapshotBarRange: {
    position: "absolute",
    top: 0,
    bottom: 0,
    backgroundColor: theme.colors.glow
  },
  snapshotMarker: {
    position: "absolute",
    top: 2,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: theme.colors.surface,
    borderWidth: 2
  },
  snapshotScaleRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: theme.spacing.xs
  },
  snapshotScaleText: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 10
  },
  aiPanel: {
    backgroundColor: theme.colors.surfaceAlt,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    padding: theme.spacing.md,
    marginBottom: theme.spacing.md
  },
  aiHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: theme.spacing.sm
  },
  aiTitle: {
    color: theme.colors.text,
    fontFamily: theme.typography.medium,
    fontSize: 13
  },
  aiBadge: {
    paddingHorizontal: theme.spacing.sm,
    paddingVertical: 2,
    borderRadius: theme.radius.sm,
    borderWidth: 1
  },
  aiBadgeOk: {
    borderColor: theme.colors.primary,
    backgroundColor: theme.colors.glow
  },
  aiBadgeAlert: {
    borderColor: theme.colors.danger,
    backgroundColor: "#2B1A1A"
  },
  aiBadgeText: {
    color: theme.colors.text,
    fontFamily: theme.typography.medium,
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: 1.1
  },
  aiRow: {
    flexDirection: "row",
    alignItems: "baseline",
    justifyContent: "space-between",
    marginBottom: theme.spacing.xs
  },
  aiScoreLabel: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 12
  },
  aiScoreValue: {
    color: theme.colors.text,
    fontFamily: theme.typography.title,
    fontSize: 20
  },
  aiSummaryText: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 12,
    marginBottom: theme.spacing.xs
  },
  aiRecommendation: {
    color: theme.colors.text,
    fontFamily: theme.typography.body,
    fontSize: 12
  },
  alertStack: {
    gap: theme.spacing.sm
  },
  alertCard: {
    padding: theme.spacing.md,
    borderRadius: theme.radius.lg,
    borderWidth: 1
  },
  alertHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: theme.spacing.xs
  },
  alertBadge: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: theme.spacing.sm
  },
  alertBadgealert: {
    backgroundColor: theme.colors.danger
  },
  alertBadgewarning: {
    backgroundColor: theme.colors.accent
  },
  alertBadgeinfo: {
    backgroundColor: theme.colors.borderStrong
  },
  alertBadgeok: {
    backgroundColor: theme.colors.primary
  },
  alertTitle: {
    color: theme.colors.text,
    fontFamily: theme.typography.medium,
    fontSize: 14,
    marginBottom: theme.spacing.xs
  },
  alertDetail: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 12
  },
  alertalert: {
    borderColor: theme.colors.danger,
    backgroundColor: "#2B1A1A"
  },
  alertwarning: {
    borderColor: theme.colors.accent,
    backgroundColor: "#2C2418"
  },
  alertinfo: {
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceAlt
  },
  alertok: {
    borderColor: theme.colors.primary,
    backgroundColor: theme.colors.glow
  },
  emptyText: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 12
  },
  thresholdRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingVertical: theme.spacing.sm,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border
  },
  thresholdText: {
    flex: 1,
    paddingRight: theme.spacing.md
  },
  thresholdLabel: {
    color: theme.colors.text,
    fontFamily: theme.typography.medium,
    fontSize: 13
  },
  thresholdNote: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 11,
    marginTop: theme.spacing.xs
  },
  thresholdRange: {
    color: theme.colors.text,
    fontFamily: theme.typography.medium,
    fontSize: 12
  }
});
