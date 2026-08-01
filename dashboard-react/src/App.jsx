import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, ApiUnreachable, BASE_URL, getState, runDecisionCycle } from "./api.js";
import StatusPills from "./components/StatusPills.jsx";
import SelfPoweredRing from "./components/SelfPoweredRing.jsx";
import EnergyFlowDiagram from "./components/EnergyFlowDiagram.jsx";
import StoredEnergyChart from "./components/StoredEnergyChart.jsx";
import SystemOverviewList from "./components/SystemOverviewList.jsx";
import PendingApprovals from "./components/PendingApprovals.jsx";

const POLL_INTERVAL_MS = 15000;
const MAX_HISTORY_POINTS = 60;

function selfPoweredFromState(state) {
  if (state.building_load_kw <= 0) return 100;
  if (state.grid_power_kw <= 0) return 100; // not importing at all
  const pct = 100 * (1 - state.grid_power_kw / state.building_load_kw);
  return Math.max(0, Math.min(100, pct));
}

export default function App() {
  const [state, setState] = useState(null);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [runningCycle, setRunningCycle] = useState(false);
  const [approvalsRefreshKey, setApprovalsRefreshKey] = useState(0);
  const historyRef = useRef([]);
  const [history, setHistory] = useState([]);

  const applyState = useCallback((next) => {
    setState(next);
    setError(null);
    const point = { timestamp: new Date(next.timestamp), value: next.battery_soc_pct };
    const updated = [...historyRef.current, point].slice(-MAX_HISTORY_POINTS);
    historyRef.current = updated;
    setHistory(updated);
  }, []);

  const refresh = useCallback(async () => {
    setRefreshing(true);
    try {
      applyState(await getState());
    } catch (err) {
      setError(err);
    } finally {
      setRefreshing(false);
    }
  }, [applyState]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [refresh]);

  const handleRunDecisionCycle = async () => {
    setRunningCycle(true);
    try {
      // The decision-cycle response carries recommendations + the resulting
      // command, not the refreshed EnergyState itself — fetch that separately.
      await runDecisionCycle();
      applyState(await getState());
      setApprovalsRefreshKey((k) => k + 1);
    } catch (err) {
      setError(err);
    } finally {
      setRunningCycle(false);
    }
  };

  if (error && !state) {
    const message =
      error instanceof ApiUnreachable
        ? `Cannot reach the API at ${BASE_URL}. Is it running?`
        : error instanceof ApiError
          ? `API error ${error.statusCode}: ${error.detail}`
          : error.message;
    return (
      <div className="app-shell">
        <div className="app-header">
          <div className="app-brand">
            <span className="app-brand-icon">⚡</span> SolarOps AI
          </div>
        </div>
        <div className="error-banner">{message}</div>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="app-shell">
        <div className="app-header">
          <div className="app-brand">
            <span className="app-brand-icon">⚡</span> SolarOps AI
          </div>
        </div>
        <div className="loading-hint">Loading current reading…</div>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="app-header">
        <div className="app-brand">
          <span className="app-brand-icon">⚡</span> SolarOps AI
        </div>
        <button className="icon-button" data-spinning={refreshing} onClick={refresh} aria-label="Refresh reading">
          ↻
        </button>
      </div>

      <StatusPills state={state} />

      <SelfPoweredRing selfPoweredPct={selfPoweredFromState(state)} gridDependencePct={100 - selfPoweredFromState(state)} />

      <EnergyFlowDiagram
        solarKw={state.solar_power_kw}
        batteryPowerKw={state.battery_power_kw}
        batteryMode={state.battery_mode}
        gridPowerKw={state.grid_power_kw}
        gridStatus={state.grid_status}
      />

      <StoredEnergyChart points={history} label="Battery SOC" unit="%" />

      <SystemOverviewList state={state} />

      <PendingApprovals refreshKey={approvalsRefreshKey} />

      <div className="bottom-bar">
        <button className="primary-button" onClick={handleRunDecisionCycle} disabled={runningCycle}>
          {runningCycle ? "Running decision cycle…" : "Run decision cycle"}
        </button>
      </div>
    </div>
  );
}
