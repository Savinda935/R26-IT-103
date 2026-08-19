import React, { useState } from "react";
import { ActivityIndicator, Image, ScrollView, StyleSheet, Text, View } from "react-native";
import * as ImagePicker from "expo-image-picker";
import SectionCard from "../components/ui/SectionCard";
import PrimaryButton from "../components/ui/PrimaryButton";
import ScreenHeader from "../components/ui/ScreenHeader";
import StatTile from "../components/ui/StatTile";
import { theme } from "../config/theme";
import { analyzeGrowthStageImage } from "../features/monitoring/api/monitoringApi";

export default function GrowthMonitoringScreen() {
  const [selectedImage, setSelectedImage] = useState(null);
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const pickImage = async () => {
    setErrorMessage("");
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setErrorMessage("Photo library permission is required to upload a growth image.");
      return;
    }

    const picked = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: false,
      quality: 0.9
    });

    if (picked.canceled || !picked.assets?.length) {
      return;
    }

    setSelectedImage(picked.assets[0]);
    setResult(null);
  };

  const runAnalysis = async () => {
    if (!selectedImage) {
      setErrorMessage("Please select a plant image first.");
      return;
    }

    setIsLoading(true);
    setErrorMessage("");
    try {
      const response = await analyzeGrowthStageImage({ imageAsset: selectedImage });
      setResult(response);
    } catch (error) {
      const detail = error?.response?.data?.detail;
      setErrorMessage(typeof detail === "string" ? detail : "Unable to analyze image right now.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <ScreenHeader
        eyebrow="Stage 2"
        badge="AI Growth"
        title="Growth monitoring"
        subtitle="Weekly AI checks with stage-based irrigation and fertilizer guidance."
      />

      <SectionCard title="Weekly image upload" subtitle="Capture plant canopy and stem health">
        {selectedImage ? (
          <Image source={{ uri: selectedImage.uri }} style={styles.previewImage} resizeMode="cover" />
        ) : (
          <View style={styles.emptyPreview}>
            <Text style={styles.emptyPreviewText}>No image selected</Text>
          </View>
        )}

        <View style={styles.buttonRow}>
          <View style={styles.buttonCell}>
            <PrimaryButton label="Pick image" variant="outline" onPress={pickImage} disabled={isLoading} />
          </View>
          <View style={styles.buttonCell}>
            <PrimaryButton label={isLoading ? "Analyzing..." : "Analyze"} onPress={runAnalysis} disabled={isLoading} />
          </View>
        </View>

        {isLoading ? (
          <View style={styles.loadingRow}>
            <ActivityIndicator color={theme.colors.primary} />
            <Text style={styles.loadingText}>Classifying the whole-plant growth stage...</Text>
          </View>
        ) : null}

        {errorMessage ? <Text style={styles.errorText}>{errorMessage}</Text> : null}
      </SectionCard>

      <SectionCard title="Stage guidance" subtitle="Localized for Sri Lankan wet zone">
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label="Observed Stage" value={result?.predicted_stage || "Uncertain"} tone="accent" />
          </View>
          <View style={styles.gridItem}>
            <StatTile label="Confidence" value={result ? `${Math.round(result.confidence * 100)}%` : "--"} hint={result?.model_version || "Model version"} />
          </View>
        </View>
        <View style={styles.grid}>
          <View style={styles.gridItem}>
            <StatTile label="Decision" value={result?.decision || "--"} />
          </View>
          <View style={styles.gridItem}>
            <StatTile label="Leaf Check" value={result ? (result.leaf_prediction ? "Detected" : "Not detected") : "--"} />
          </View>
        </View>
        <Text style={styles.text}>Result: {result?.message || "Upload a standardized weekly whole-plant image."}</Text>
      </SectionCard>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.lg },
  previewImage: {
    width: "100%",
    height: 220,
    borderRadius: theme.radius.md,
    marginBottom: theme.spacing.md
  },
  emptyPreview: {
    height: 180,
    borderRadius: theme.radius.md,
    borderWidth: 1,
    borderColor: theme.colors.borderStrong,
    backgroundColor: theme.colors.surfaceAlt,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: theme.spacing.md
  },
  emptyPreviewText: {
    color: theme.colors.muted,
    fontFamily: theme.typography.body
  },
  buttonRow: {
    flexDirection: "row",
    marginHorizontal: -theme.spacing.xs,
    marginBottom: theme.spacing.sm
  },
  buttonCell: {
    flex: 1,
    paddingHorizontal: theme.spacing.xs
  },
  loadingRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: theme.spacing.sm
  },
  loadingText: {
    color: theme.colors.muted,
    marginLeft: theme.spacing.sm,
    fontFamily: theme.typography.body
  },
  errorText: {
    color: theme.colors.danger,
    marginTop: theme.spacing.xs,
    fontFamily: theme.typography.body
  },
  text: { color: theme.colors.text, marginBottom: theme.spacing.sm, fontFamily: theme.typography.body },
  grid: {
    flexDirection: "row",
    marginBottom: theme.spacing.md
  },
  gridItem: {
    flex: 1,
    marginRight: theme.spacing.sm
  }
});
