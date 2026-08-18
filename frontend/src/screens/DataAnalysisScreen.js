import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Alert, Linking, ScrollView, StyleSheet, Text, View } from "react-native";
import Svg, { Circle, Path, Polyline, Rect } from "react-native-svg";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";
import ScreenHeader from "../components/ui/ScreenHeader";
import SectionCard from "../components/ui/SectionCard";
import StatTile from "../components/ui/StatTile";
import PrimaryButton from "../components/ui/PrimaryButton";
import { theme } from "../config/theme";
import { WET_ZONE_LIMITS } from "../config/constants";
import { API_BASE_URL } from "../config/api";

const SUMMARY_ENDPOINT = "/api/monitoring/analytics/summary?minutes=10080";
const HISTORY_ENDPOINT = "/api/monitoring/readings";
const REPORT_ENDPOINT = "/api/monitoring/report/pdf?minutes=10080&limit=2000";

const TEXT = {
  en: {
    eyebrow: "Monitoring",
    badge: "Firebase",
    title: "Data analysis",
    subtitle: "Summary stats and trends from Firebase history.",
    language: "Language",
    english: "English",
    sinhala: "Sinhala",
    summarySnapshot: "Summary snapshot",
    latestSummary: "Latest Firebase summary",
    updated: "Updated",
    refresh: "Refresh",
    refreshing: "Refreshing...",
    minMax: "Min / Max",
    minMaxSubtitle: "Range observed in Firebase history",
    rangeChart: "Range chart",
    rangeChartSubtitle: "Min–Max range with Avg marker.",
    lineChart: "Line chart",
    lineChartSubtitle: "Short-term trends from Firebase readings.",
    chartTabLine: "Line",
    chartTabRange: "Range",
    pieChart: "Issue breakdown",
    pieChartSubtitle: "What was out of range most often (recent history).",
    pieOk: "OK",
    pieTemp: "Temperature",
    pieHumidity: "Humidity",
    pieSoil: "Soil moisture",
    exportReport: "Export report",
    exportReportSubtitle: "Download the Firebase PDF report",
    reportHelper: "Use the report for weekly review and PP1 evidence.",
    openPdf: "Open PDF report",
    avgTemp: "Avg temp",
    avgHumidity: "Avg humidity",
    avgSoil: "Avg soil",
    avgEc: "Avg EC",
    temp: "Temp",
    humidity: "Humidity",
    soil: "Soil",
    ec: "EC",
    minLabel: "Min",
    maxLabel: "Max",
    trendLabel: "Trend",
    chartEmpty: "Waiting for enough data to draw the chart.",
    loadFailedTitle: "Data analysis",
    loadFailedBody: "Failed to load Firebase summary data.",
    reportFailedTitle: "Report",
    reportFailedBody: "Unable to download the PDF report."
  },
  si: {
    eyebrow: "නිරීක්ෂණ",
    badge: "Firebase",
    title: "දත්ත විශ්ලේෂණය",
    subtitle: "Firebase ඉතිහාසයෙන් සාරාංශ අගයන් සහ ප්‍රවණතා.",
    language: "භාෂාව",
    english: "English",
    sinhala: "සිංහල",
    summarySnapshot: "සාරාංශය",
    latestSummary: "අවසන් Firebase සාරාංශය",
    updated: "යාවත්කාලීන",
    refresh: "යාවත්කාලීන කරන්න",
    refreshing: "යාවත්කාලීන වෙමින්...",
    minMax: "අවම / උපරිම",
    minMaxSubtitle: "Firebase ඉතිහාසයේ දක්නට ලැබුණු පරාසය",
    rangeChart: "පරාස ප්‍රස්ථාරය",
    rangeChartSubtitle: "අවම–උපරිම පරාසය සහ සාමාන්‍ය සලකුණ.",
    lineChart: "රේඛා ප්‍රස්ථාරය",
    lineChartSubtitle: "Firebase කියවීම් වල කෙටි කාලීන ප්‍රවණතා.",
    chartTabLine: "රේඛා",
    chartTabRange: "පරාසය",
    pieChart: "ගැටලු ව්‍යාප්තිය",
    pieChartSubtitle: "අවසාන දත්ත වලදී වැඩිපුරම සීමාවෙන් පිට වූ දේ.",
    pieOk: "සාමාන්‍ය",
    pieTemp: "උෂ්ණත්වය",
    pieHumidity: "ආර්ද්‍රතාව",
    pieSoil: "බිම් තෙතමන",
    exportReport: "වාර්තාව",
    exportReportSubtitle: "Firebase PDF වාර්තාව බාගන්න",
    reportHelper: "සතිපතා සමාලෝචනය සහ PP1 සාක්ෂි සඳහා භාවිතා කරන්න.",
    openPdf: "PDF වාර්තාව විවෘත කරන්න",
    avgTemp: "සාමාන්‍ය උෂ්ණත්වය",
    avgHumidity: "සාමාන්‍ය ආර්ද්‍රතාව",
    avgSoil: "සාමාන්‍ය බිම් තෙතමන",
    avgEc: "සාමාන්‍ය EC",
    temp: "උෂ්ණත්වය",
    humidity: "ආර්ද්‍රතාව",
    soil: "බිම් තෙතමන",
    ec: "EC",
    minLabel: "අවම",
    maxLabel: "උපරිම",
    trendLabel: "ප්‍රවණතාව",
    chartEmpty: "ප්‍රස්ථාරයට ප්‍රමාණවත් දත්ත තවම නොමැත.",
    loadFailedTitle: "දත්ත විශ්ලේෂණය",
    loadFailedBody: "Firebase සාරාංශ දත්ත ලබාගත නොහැක.",
    reportFailedTitle: "වාර්තාව",
    reportFailedBody: "PDF වාර්තාව බාගත කළ නොහැක."
  }
};

const formatValue = (value, unit) => {
  if (typeof value !== "number") {
    return "--";
  }

  const fixed = Number.isFinite(value) ? value.toFixed(2) : "--";
  return unit ? `${fixed} ${unit}` : fixed;
};

const formatTrend = (value, unit) => {
  if (typeof value !== "number") {
    return "--";
  }

  const direction = value > 0 ? "up" : value < 0 ? "down" : "flat";
  return `${direction} ${formatValue(Math.abs(value), unit)}`;
};

const RangeBar = ({ label, unit, min, max, avg, trend, accentColor }) => {
  const [width, setWidth] = useState(0);
  const safe = (value) => (typeof value === "number" && Number.isFinite(value) ? value : null);
  const _min = safe(min);
  const _max = safe(max);
  const _avg = safe(avg);

  const domainMin = Math.min(...[_min, _max, _avg].filter((v) => typeof v === "number"));
  const domainMax = Math.max(...[_min, _max, _avg].filter((v) => typeof v === "number"));
  const spread = domainMax - domainMin || 1;
  const pad = spread * 0.2;
  const leftVal = Number.isFinite(domainMin) ? domainMin - pad : 0;
  const rightVal = Number.isFinite(domainMax) ? domainMax + pad : 1;
  const scale = (v) => (v - leftVal) / (rightVal - leftVal || 1);
  const clamp01 = (v) => Math.min(1, Math.max(0, v));

  const minPct = _min == null ? null : clamp01(scale(_min));
  const maxPct = _max == null ? null : clamp01(scale(_max));
  const avgPct = _avg == null ? null : clamp01(scale(_avg));

  return (
    <View style={styles.rangeRow} onLayout={(event) => setWidth(event.nativeEvent.layout.width)}>
      <View style={styles.rangeHeader}>
        <Text style={styles.rangeLabel}>{label}</Text>
        <Text style={styles.rangeMeta}>
          {safe(avg) == null ? "--" : avg.toFixed(2)}
          {unit ? ` ${unit}` : ""}
          {typeof trend === "number" ? `  •  ${trend > 0 ? "↑" : trend < 0 ? "↓" : "→"} ${Math.abs(trend).toFixed(2)}${unit ? ` ${unit}` : ""}` : ""}
        </Text>
      </View>
      <View style={styles.rangeTrack}>
        {width > 0 && minPct != null && maxPct != null ? (
          <View
            style={[
              styles.rangeBand,
              {
                left: Math.min(minPct, maxPct) * width,
                width: Math.max(4, Math.abs(maxPct - minPct) * width),
                backgroundColor: `${accentColor}22`
              }
            ]}
          />
        ) : null}
        {width > 0 && avgPct != null ? (
          <View style={[styles.rangeMarker, { left: avgPct * width - 5, borderColor: accentColor }]} />
        ) : null}
      </View>
      <View style={styles.rangeScale}>
        <Text style={styles.rangeScaleText}>{_min == null ? "--" : `${_min.toFixed(2)}${unit ? ` ${unit}` : ""}`}</Text>
        <Text style={styles.rangeScaleText}>{_max == null ? "--" : `${_max.toFixed(2)}${unit ? ` ${unit}` : ""}`}</Text>
      </View>
    </View>
  );
};

const MultiLineChart = ({ title, series, emptyLabel }) => {
  const [width, setWidth] = useState(0);
  const height = 190;
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
      <View style={styles.chartCard}>
        <Text style={styles.chartTitle}>{title}</Text>
        <Text style={styles.chartEmpty}>{emptyLabel}</Text>
      </View>
    );
  }

  const min = Math.min(...numericValues);
  const max = Math.max(...numericValues);

  return (
    <View style={styles.chartCard} onLayout={(event) => setWidth(event.nativeEvent.layout.width)}>
      <Text style={styles.chartTitle}>{title}</Text>
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
      <View style={styles.chartLegend}>
        {series.map((item) => (
          <View key={item.key} style={styles.chartLegendItem}>
            <View style={[styles.chartLegendDot, { backgroundColor: item.color }]} />
            <Text style={styles.chartLegendText}>{item.label}</Text>
          </View>
        ))}
      </View>
    </View>
  );
};

const PieChart = ({ data, size = 180 }) => {
  const radius = size / 2;
  const cx = radius;
  const cy = radius;
  const strokeColor = theme.colors.borderStrong;

  const total = data.reduce((sum, item) => sum + (item.value || 0), 0);
  if (!total) {
    return null;
  }

  const polarToCartesian = (centerX, centerY, r, angleInDegrees) => {
    const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180.0;
    return {
      x: centerX + r * Math.cos(angleInRadians),
      y: centerY + r * Math.sin(angleInRadians)
    };
  };

  const describeArc = (x, y, r, startAngle, endAngle) => {
    const start = polarToCartesian(x, y, r, endAngle);
    const end = polarToCartesian(x, y, r, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
    return ["M", x, y, "L", start.x, start.y, "A", r, r, 0, largeArcFlag, 0, end.x, end.y, "Z"].join(" ");
  };

  let currentAngle = 0;
  const arcs = data.map((slice) => {
    const sliceAngle = (slice.value / total) * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + sliceAngle;
    currentAngle = endAngle;
    return {
      key: slice.key,
      d: describeArc(cx, cy, radius - 2, startAngle, endAngle),
      color: slice.color,
      sliceAngle
    };
  });

  if (arcs.length === 1) {
    return (
      <Svg width={size} height={size}>
        <Circle cx={cx} cy={cy} r={radius - 2} fill={arcs[0].color} />
        <Circle cx={cx} cy={cy} r={radius - 2} fill="none" stroke={strokeColor} strokeWidth={1} />
      </Svg>
    );
  }

  return (
    <Svg width={size} height={size}>
      {arcs.map((arc) => (
        <Path key={arc.key} d={arc.d} fill={arc.color} stroke={strokeColor} strokeWidth={1} />
      ))}
    </Svg>
  );
};

export default function DataAnalysisScreen() {
  const [summary, setSummary] = useState(null);
  const [historyRows, setHistoryRows] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState("en");
  const [chartTab, setChartTab] = useState("line");
  const [downloadingReport, setDownloadingReport] = useState(false);

  const t = useCallback((key) => TEXT[language][key] || TEXT.en[key] || key, [language]);

  const loadSummary = useCallback(async () => {
    const url = `${API_BASE_URL}${SUMMARY_ENDPOINT}`;
    const historyUrl = `${API_BASE_URL}${HISTORY_ENDPOINT}?limit=120&chronological=true`;
    try {
      setLoading(true);
      const [response, historyResponse] = await Promise.all([fetch(url), fetch(historyUrl)]);
      if (!response.ok) {
        throw new Error(`Failed to load summary: ${response.status}`);
      }
      if (!historyResponse.ok) {
        throw new Error(`Failed to load history: ${historyResponse.status}`);
      }
      const [data, historyData] = await Promise.all([response.json(), historyResponse.json()]);
      setSummary(data);
      setHistoryRows(Array.isArray(historyData) ? historyData : []);
      setLastUpdated(new Date());
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error("Failed to load data analysis", { url, historyUrl, message, error });
      Alert.alert(
        t("loadFailedTitle"),
        `${t("loadFailedBody")}\n\nURL: ${url}\nError: ${message}\n\nTip: Your phone must be on the same Wi‑Fi as the PC backend, or set EXPO_PUBLIC_BACKEND_BASE_URL to a public HTTPS URL (ngrok).`
      );
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const handleOpenReport = async () => {
    try {
      setDownloadingReport(true);
      const url = `${API_BASE_URL}${REPORT_ENDPOINT}`;
      const filename = `naimiris-firebase-report-${new Date().toISOString().slice(0, 10)}.pdf`;
      const localUri = `${FileSystem.documentDirectory}${filename}`;
      const result = await FileSystem.downloadAsync(url, localUri);

      if (!result?.uri) {
        throw new Error("Download failed");
      }

      const canShare = await Sharing.isAvailableAsync();
      if (canShare) {
        await Sharing.shareAsync(result.uri, {
          mimeType: "application/pdf",
          dialogTitle: filename,
          UTI: "com.adobe.pdf"
        });
      } else {
        await Linking.openURL(result.uri);
      }
    } catch (error) {
      console.error("Failed to download report", error);
      Alert.alert(t("reportFailedTitle"), t("reportFailedBody"));
    } finally {
      setDownloadingReport(false);
    }
  };

  const avg = summary?.avg || {};
  const min = summary?.min || {};
  const max = summary?.max || {};
  const trend = summary?.trend || {};

  const rangeMetrics = useMemo(
    () => [
      { key: "temperature_c", label: t("temp"), unit: "C", color: theme.colors.primary },
      { key: "humidity", label: t("humidity"), unit: "%", color: theme.colors.accent },
      { key: "soil_moisture", label: t("soil"), unit: "%", color: "#76D34E" },
      { key: "ec", label: t("ec"), unit: "mS/cm", color: "#F2B949" }
    ],
    [t]
  );

  const lineSeries = useMemo(() => {
    const rows = Array.isArray(historyRows) ? historyRows : [];
    return [
      {
        key: "temperature_c",
        label: t("temp"),
        values: rows.map((row) => row?.temperature_c),
        color: theme.colors.primary
      },
      {
        key: "humidity",
        label: t("humidity"),
        values: rows.map((row) => row?.humidity),
        color: theme.colors.accent
      },
      {
        key: "soil_moisture",
        label: t("soil"),
        values: rows.map((row) => row?.soil_moisture),
        color: "#76D34E"
      },
      {
        key: "ec",
        label: t("ec"),
        values: rows.map((row) => row?.ec),
        color: "#F2B949"
      }
    ];
  }, [historyRows, t]);

  const issueBreakdown = useMemo(() => {
    const limits = WET_ZONE_LIMITS || {};
    const soilMin = typeof limits.soilMoistureMin === "number" ? limits.soilMoistureMin : null;
    const soilMax = typeof limits.soilMoistureMax === "number" ? limits.soilMoistureMax : null;
    const tempMin = typeof limits.temperatureMinC === "number" ? limits.temperatureMinC : null;
    const tempMax = typeof limits.temperatureMaxC === "number" ? limits.temperatureMaxC : null;
    const humMin = typeof limits.humidityMin === "number" ? limits.humidityMin : null;
    const humMax = typeof limits.humidityMax === "number" ? limits.humidityMax : null;

    const counts = { ok: 0, temp: 0, humidity: 0, soil: 0 };
    const rows = Array.isArray(historyRows) ? historyRows : [];

    const isOut = (value, minVal, maxVal) => {
      if (typeof value !== "number") return false;
      if (typeof minVal === "number" && value < minVal) return true;
      if (typeof maxVal === "number" && value > maxVal) return true;
      return false;
    };

    rows.forEach((row) => {
      const soilIssue = isOut(row?.soil_moisture, soilMin, soilMax);
      const tempIssue = isOut(row?.temperature_c, tempMin, tempMax);
      const humIssue = isOut(row?.humidity, humMin, humMax);

      // Partition each reading into ONE dominant issue so the pie sums to 100%.
      if (soilIssue) counts.soil += 1;
      else if (tempIssue) counts.temp += 1;
      else if (humIssue) counts.humidity += 1;
      else counts.ok += 1;
    });

    return [
      { key: "ok", label: t("pieOk"), value: counts.ok, color: theme.colors.glow },
      { key: "soil", label: t("pieSoil"), value: counts.soil, color: "#76D34E" },
      { key: "temp", label: t("pieTemp"), value: counts.temp, color: theme.colors.primary },
      { key: "humidity", label: t("pieHumidity"), value: counts.humidity, color: theme.colors.accent }
    ].filter((item) => item.value > 0);
  }, [historyRows, t]);

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <ScreenHeader
        eyebrow={t("eyebrow")}
        badge={t("badge")}
        title={t("title")}
        subtitle={t("subtitle")}
      />

      <SectionCard title={t("language")} subtitle="">
        <View style={styles.langRow}>
          <View style={styles.langButton}>
            <PrimaryButton label={t("english")} onPress={() => setLanguage("en")} variant={language === "en" ? "primary" : "outline"} />
          </View>
          <View style={[styles.langButton, styles.langButtonLast]}>
            <PrimaryButton label={t("sinhala")} onPress={() => setLanguage("si")} variant={language === "si" ? "primary" : "outline"} />
          </View>
        </View>
      </SectionCard>

      <SectionCard
        title={t("summarySnapshot")}
        subtitle={lastUpdated ? `${t("updated")} ${lastUpdated.toLocaleTimeString()}` : t("latestSummary")}
      >
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile
              label={t("avgTemp")}
              value={formatValue(avg.temperature_c, "C")}
              hint={`${t("trendLabel")}: ${formatTrend(trend.temperature_c, "C")}`}
            />
          </View>
          <View style={[styles.gridItem, styles.gridItemLast]}>
            <StatTile
              label={t("avgHumidity")}
              value={formatValue(avg.humidity, "%")}
              hint={`${t("trendLabel")}: ${formatTrend(trend.humidity, "%")}`}
            />
          </View>
        </View>
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile
              label={t("avgSoil")}
              value={formatValue(avg.soil_moisture, "%")}
              hint={`${t("trendLabel")}: ${formatTrend(trend.soil_moisture, "%")}`}
            />
          </View>
          <View style={[styles.gridItem, styles.gridItemLast]}>
            <StatTile
              label={t("avgEc")}
              value={formatValue(avg.ec, "mS/cm")}
              hint={`${t("trendLabel")}: ${formatTrend(trend.ec, "mS/cm")}`}
            />
          </View>
        </View>
        <PrimaryButton label={loading ? t("refreshing") : t("refresh")} onPress={loadSummary} disabled={loading} />
      </SectionCard>

      <SectionCard
        title={chartTab === "line" ? t("lineChart") : t("rangeChart")}
        subtitle={chartTab === "line" ? t("lineChartSubtitle") : t("rangeChartSubtitle")}
      >
        <View style={styles.chartTabRow}>
          <View style={styles.chartTabButton}>
            <PrimaryButton
              label={t("chartTabLine")}
              onPress={() => setChartTab("line")}
              variant={chartTab === "line" ? "primary" : "outline"}
            />
          </View>
          <View style={[styles.chartTabButton, styles.chartTabButtonLast]}>
            <PrimaryButton
              label={t("chartTabRange")}
              onPress={() => setChartTab("range")}
              variant={chartTab === "range" ? "primary" : "outline"}
            />
          </View>
        </View>

        {chartTab === "line" ? (
          <MultiLineChart title={t("lineChart")} series={lineSeries} emptyLabel={t("chartEmpty")} />
        ) : (
          rangeMetrics.map((metric) => (
            <RangeBar
              key={metric.key}
              label={metric.label}
              unit={metric.unit}
              min={min[metric.key]}
              max={max[metric.key]}
              avg={avg[metric.key]}
              trend={trend[metric.key]}
              accentColor={metric.color}
            />
          ))
        )}
      </SectionCard>

      <SectionCard title={t("pieChart")} subtitle={t("pieChartSubtitle")}>
        {issueBreakdown.length ? (
          <View style={styles.pieRow}>
            <View style={styles.pieChart}>
              <PieChart data={issueBreakdown} size={170} />
            </View>
            <View style={styles.pieLegend}>
              {issueBreakdown.map((item) => (
                <View key={item.key} style={styles.pieLegendItem}>
                  <View style={[styles.pieLegendDot, { backgroundColor: item.color }]} />
                  <Text style={styles.pieLegendText}>
                    {item.label} ({item.value})
                  </Text>
                </View>
              ))}
            </View>
          </View>
        ) : (
          <Text style={styles.chartEmpty}>{t("chartEmpty")}</Text>
        )}
      </SectionCard>

      <SectionCard title={t("minMax")} subtitle={t("minMaxSubtitle")}>
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label={`${t("temp")} ${t("minLabel")}`} value={formatValue(min.temperature_c, "C")} />
          </View>
          <View style={[styles.gridItem, styles.gridItemLast]}>
            <StatTile label={`${t("temp")} ${t("maxLabel")}`} value={formatValue(max.temperature_c, "C")} />
          </View>
        </View>
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label={`${t("humidity")} ${t("minLabel")}`} value={formatValue(min.humidity, "%")} />
          </View>
          <View style={[styles.gridItem, styles.gridItemLast]}>
            <StatTile label={`${t("humidity")} ${t("maxLabel")}`} value={formatValue(max.humidity, "%")} />
          </View>
        </View>
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label={`${t("soil")} ${t("minLabel")}`} value={formatValue(min.soil_moisture, "%")} />
          </View>
          <View style={[styles.gridItem, styles.gridItemLast]}>
            <StatTile label={`${t("soil")} ${t("maxLabel")}`} value={formatValue(max.soil_moisture, "%")} />
          </View>
        </View>
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label={`${t("ec")} ${t("minLabel")}`} value={formatValue(min.ec, "mS/cm")} />
          </View>
          <View style={[styles.gridItem, styles.gridItemLast]}>
            <StatTile label={`${t("ec")} ${t("maxLabel")}`} value={formatValue(max.ec, "mS/cm")} />
          </View>
        </View>
      </SectionCard>

      <SectionCard title={t("exportReport")} subtitle={t("exportReportSubtitle")}>
        <Text style={styles.text}>{t("reportHelper")}</Text>
        <PrimaryButton label={downloadingReport ? `${t("openPdf")}...` : t("openPdf")} onPress={handleOpenReport} disabled={downloadingReport} />
      </SectionCard>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.lg },
  langRow: {
    flexDirection: "row"
  },
  langButton: {
    flex: 1,
    marginRight: theme.spacing.sm
  },
  langButtonLast: {
    marginRight: 0
  },
  grid: {
    flexDirection: "row",
    marginBottom: theme.spacing.sm
  },
  gridItem: {
    flex: 1,
    marginRight: theme.spacing.sm
  },
  gridItemLast: {
    marginRight: 0
  },
  rangeRow: {
    marginBottom: theme.spacing.md
  },
  rangeHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: theme.spacing.xs
  },
  rangeLabel: {
    color: theme.colors.text,
    fontFamily: theme.typography.medium,
    fontSize: 12
  },
  rangeMeta: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 11
  },
  rangeTrack: {
    height: 14,
    backgroundColor: theme.colors.surfaceAlt,
    borderRadius: 10,
    overflow: "hidden",
    position: "relative"
  },
  rangeBand: {
    position: "absolute",
    top: 0,
    bottom: 0
  },
  rangeMarker: {
    position: "absolute",
    top: 2,
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: theme.colors.surface,
    borderWidth: 2
  },
  rangeScale: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: theme.spacing.xs
  },
  rangeScaleText: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 10
  },
  chartTabRow: {
    flexDirection: "row",
    marginBottom: theme.spacing.sm
  },
  chartTabButton: {
    flex: 1,
    marginRight: theme.spacing.sm
  },
  chartTabButtonLast: {
    marginRight: 0
  },
  chartCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: theme.radius.lg,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    padding: theme.spacing.md
  },
  chartTitle: {
    color: theme.colors.muted,
    fontFamily: theme.typography.medium,
    fontSize: 12,
    marginBottom: theme.spacing.sm
  },
  chartEmpty: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 12
  },
  chartLegend: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: theme.spacing.sm
  },
  chartLegendItem: {
    flexDirection: "row",
    alignItems: "center",
    marginRight: theme.spacing.md,
    marginBottom: theme.spacing.xs
  },
  chartLegendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: theme.spacing.xs
  },
  chartLegendText: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body,
    fontSize: 11
  },
  pieRow: {
    flexDirection: "row",
    alignItems: "center"
  },
  pieChart: {
    width: 180,
    alignItems: "center",
    justifyContent: "center"
  },
  pieLegend: {
    flex: 1,
    paddingLeft: theme.spacing.md
  },
  pieLegendItem: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: theme.spacing.sm
  },
  pieLegendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    marginRight: theme.spacing.sm
  },
  pieLegendText: {
    color: theme.colors.text,
    fontFamily: theme.typography.body,
    fontSize: 12
  },
  text: {
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
    fontFamily: theme.typography.body
  }
});
