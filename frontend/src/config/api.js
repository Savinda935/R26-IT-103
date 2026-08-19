import Constants from "expo-constants";


const ENV_BACKEND_BASE_URL = process.env.EXPO_PUBLIC_BACKEND_BASE_URL?.trim();
// Development fallback for the current PC network. Prefer
// EXPO_PUBLIC_BACKEND_BASE_URL because this address can change between networks.
const DEFAULT_PC_BACKEND_BASE_URL = "http://172.16.200.59:8000";

const getExpoHostUrl = () => {
  const hostUri = Constants.expoConfig?.hostUri;
  if (typeof hostUri === "string" && hostUri.includes(":")) {
    return `http://${hostUri.split(":")[0]}:8000`;
  }

  const debuggerHost = Constants.manifest2?.extra?.expoClient?.debuggerHost || Constants.manifest?.debuggerHost;
  if (typeof debuggerHost === "string" && debuggerHost.includes(":")) {
    return `http://${debuggerHost.split(":")[0]}:8000`;
  }

  return null;
};

const resolvedBaseUrl = ENV_BACKEND_BASE_URL || getExpoHostUrl() || DEFAULT_PC_BACKEND_BASE_URL;

// Keep endpoint composition predictable when an environment URL includes a
// trailing slash (for example, http://192.168.1.10:8000/).
export const API_BASE_URL = resolvedBaseUrl.replace(/\/+$/, "");
export const API_REQUEST_TIMEOUT_MS = 120000;
