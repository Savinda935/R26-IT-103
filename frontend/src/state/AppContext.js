import React, { createContext, useMemo, useReducer } from "react";

const initialState = {
  budget: null,
  land: null,
  sensors: {},
  growthStage: null,
  monitoringContext: {
    plotId: "plot-001",
    cropCycleId: "cycle-001",
    deviceId: "device-001",
    plantId: null
  },
  pestSeverity: null,
  activePlanId: "basic"
};

function reducer(state, action) {
  switch (action.type) {
    case "SET_BUDGET":
      return { ...state, budget: action.payload };
    case "SET_LAND":
      return { ...state, land: action.payload };
    case "SET_SENSORS":
      return { ...state, sensors: action.payload };
    case "SET_GROWTH_STAGE":
      return { ...state, growthStage: action.payload };
    case "SET_MONITORING_CONTEXT":
      return { ...state, monitoringContext: { ...state.monitoringContext, ...action.payload } };
    case "SET_PEST_SEVERITY":
      return { ...state, pestSeverity: action.payload };
    case "SET_PLAN":
      return { ...state, activePlanId: action.payload };
    default:
      return state;
  }
}

export const AppContext = createContext({
  state: initialState,
  dispatch: () => null
});

export function AppProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  const value = useMemo(() => ({ state, dispatch }), [state]);

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
