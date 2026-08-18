import React, { useEffect, useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import SectionCard from "../components/ui/SectionCard";
import StatTile from "../components/ui/StatTile";
import ScreenHeader from "../components/ui/ScreenHeader";
import { theme } from "../config/theme";
import { getMonitoringDeviceStatuses, getRealtimeSensorSnapshot } from "../features/monitoring/iotMonitor";
import { appendLocalArray, loadLocal } from "../services/storage";

export default function IoTDashboardScreen() {
  const [snapshot, setSnapshot] = useState(null);
  const [history, setHistory] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [deviceStatus, setDeviceStatus] = useState(null);

  const toNumber = (value) => {
    const numeric = typeof value === "number" ? value : Number(value);
    return Number.isFinite(numeric) ? numeric : null;
  };

  const formatValue = (value) => {
    if (typeof value !== "number") {
      return "--";
    }

    return value.toFixed(2);
  };

  useEffect(() => {
    let isMounted = true;

    const loadHistory = async () => {
      const storedHistory = await loadLocal("iotHistory", []);
      if (isMounted && Array.isArray(storedHistory)) {
        setHistory(storedHistory);
      }
    };

    loadHistory();

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;

    const loadSnapshot = async () => {
      try {
        const [data, statuses] = await Promise.all([
          getRealtimeSensorSnapshot(),
          getMonitoringDeviceStatuses()
        ]);
        if (isMounted) {
          setSnapshot(data);
          setDeviceStatus(statuses[0] || null);
          setHistory((prevHistory) => {
            const nextEntry = {
              humidity: toNumber(data?.humidity),
              temperature: toNumber(data?.temperature_c),
              heatIndex: toNumber(data?.heat_index_c),
              soil: toNumber(data?.soil_moisture),
              timestamp: Date.now()
            };

            const nextHistory = [...prevHistory, nextEntry];
            const trimmed = nextHistory.length > 60 ? nextHistory.slice(-60) : nextHistory;
            appendLocalArray("iotHistory", nextEntry, 60).catch((error) => {
              console.warn("Failed to save IoT history", error);
            });
            return trimmed;
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

  const humidity = formatValue(snapshot?.humidity);
  const temperature = formatValue(snapshot?.temperature_c);
  const heatIndex = formatValue(snapshot?.heat_index_c);
  const soilMoisture = formatValue(snapshot?.soil_moisture);

  const averageOf = (key) => {
    const values = history.map((entry) => entry[key]).filter((value) => typeof value === "number");
    if (!values.length) {
      return null;
    }

    const sum = values.reduce((total, value) => total + value, 0);
    return sum / values.length;
  };

  const trendOf = (key) => {
    if (history.length < 2) {
      return "--";
    }

    const latest = history[history.length - 1][key];
    const previous = history[history.length - 2][key];
    if (typeof latest !== "number" || typeof previous !== "number") {
      return "--";
    }

    const delta = latest - previous;
    if (Math.abs(delta) < 0.05) {
      return "flat";
    }

    const direction = delta > 0 ? "up" : "down";
    return `${direction} ${Math.abs(delta).toFixed(2)}`;
  };

  const averageHumidity = formatValue(averageOf("humidity"));
  const averageTemperature = formatValue(averageOf("temperature"));
  const averageHeatIndex = formatValue(averageOf("heatIndex"));
  const averageSoil = formatValue(averageOf("soil"));

  const chartBars = [
    {
      label: "Humidity",
      value: toNumber(snapshot?.humidity),
      max: 100,
      color: theme.colors.accent
    },
    {
      label: "Temp",
      value: toNumber(snapshot?.temperature_c),
      max: 50,
      color: theme.colors.primary
    },
    {
      label: "Heat",
      value: toNumber(snapshot?.heat_index_c),
      max: 50,
      color: theme.colors.primaryDark
    },
    {
      label: "Soil",
      value: toNumber(snapshot?.soil_moisture),
      max: 100,
      color: theme.colors.text
    }
  ];

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <ScreenHeader
        eyebrow="Stage 2"
        badge="IoT Live"
        title="Sensor dashboard"
        subtitle="Monitor soil and climate signals in real time."
      />

      <SectionCard title="Device connection" subtitle="Backend heartbeat and five-minute storage status">
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile
              label="Device"
              value={deviceStatus?.device_code || snapshot?.device_id || "--"}
              hint={deviceStatus?.plot_id ? `Plot: ${deviceStatus.plot_id}` : "Waiting for setup"}
            />
          </View>
          <View style={styles.gridItem}>
            <StatTile
              label="Connection"
              value={(deviceStatus?.status || "unknown").toUpperCase()}
              hint={
                typeof deviceStatus?.seconds_since_seen === "number"
                  ? `Last seen ${Math.round(deviceStatus.seconds_since_seen)} seconds ago`
                  : "No reading received yet"
              }
              tone={deviceStatus?.status === "online" ? "accent" : "default"}
            />
          </View>
        </View>
      </SectionCard>

      <SectionCard title="Real-time sensors" subtitle="Wet-zone thresholds">
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label="Soil" value={`${soilMoisture}%`} tone="accent" />
          </View>
          <View style={styles.gridItem}>
            <StatTile label="Temperature" value={`${temperature} C`} />
          </View>
        </View>
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label="Humidity" value={`${humidity}%`} />
          </View>
          <View style={styles.gridItem}>
            <StatTile label="Heat Index" value={`${heatIndex} C`} />
          </View>
        </View>
      </SectionCard>

      <SectionCard
        title="Snapshot chart"
        subtitle={`Last ${history.length} readings${lastUpdated ? ` • Updated ${lastUpdated.toLocaleTimeString()}` : ""}`}
      >
        <View style={styles.chartRow}>
          {chartBars.map((bar) => {
            const heightRatio = typeof bar.value === "number" ? Math.min(bar.value / bar.max, 1) : 0;
            return (
              <View key={bar.label} style={styles.chartItem}>
                <View style={styles.chartBarTrack}>
                  <View style={[styles.chartBarFill, { height: `${heightRatio * 100}%`, backgroundColor: bar.color }]} />
                </View>
                <Text style={styles.chartValue}>{formatValue(bar.value)}</Text>
                <Text style={styles.chartLabel}>{bar.label}</Text>
              </View>
            );
          })}
        </View>
      </SectionCard>

      <SectionCard title="Data analysis" subtitle="Live averages and short-term trends">
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label="Avg temp" value={`${averageTemperature} C`} hint={`Trend: ${trendOf("temperature")}`} />
          </View>
          <View style={styles.gridItem}>
            <StatTile label="Avg humidity" value={`${averageHumidity}%`} hint={`Trend: ${trendOf("humidity")}`} />
          </View>
        </View>
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label="Avg heat index" value={`${averageHeatIndex} C`} hint={`Trend: ${trendOf("heatIndex")}`} />
          </View>
          <View style={styles.gridItem}>
            <StatTile label="Avg soil" value={`${averageSoil}%`} hint={`Trend: ${trendOf("soil")}`} />
          </View>
        </View>
      </SectionCard>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.lg },
  grid: {
    flexDirection: "row",
    marginBottom: theme.spacing.sm
  },
  gridItem: {
    flex: 1,
    marginRight: theme.spacing.sm
  },
  chartRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    marginBottom: theme.spacing.sm
  },
  chartItem: {
    flex: 1,
    alignItems: "center",
    marginHorizontal: theme.spacing.xs
  },
  chartBarTrack: {
    height: 140,
    width: "100%",
    backgroundColor: theme.colors.surfaceAlt,
    borderRadius: theme.radius.sm,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    overflow: "hidden",
    justifyContent: "flex-end"
  },
  chartBarFill: {
    width: "100%",
    borderRadius: theme.radius.sm
  },
  chartLabel: {
    marginTop: theme.spacing.xs,
    fontSize: 11,
    color: theme.colors.muted,
    fontFamily: theme.typography.medium
  },
  chartValue: {
    marginTop: theme.spacing.xs,
    fontSize: 12,
    color: theme.colors.text,
    fontFamily: theme.typography.body
  }
});
