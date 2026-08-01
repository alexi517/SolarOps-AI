import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, ApiUnreachable, BASE_URL, getState, runDecisionCycle } from "./api.js";
import { NAV_ITEMS } from "./nav.js";
import Sidebar from "./components/Sidebar.jsx";
import Topbar from "./components/Topbar.jsx";
import StatusPills from "./components/StatusPills.jsx";
import EnergyFlowDiagram from "./components/EnergyFlowDiagram.jsx";
import StoredEnergyChart from "./components/StoredEnergyChart.jsx";
import SystemOverviewList from "./components/SystemOverviewList.jsx";
import PendingApprovals from "./components/PendingApprovals.jsx";
import HeroCard from "./components/HeroCard.jsx";
import UsageInsightsChart from "./components/UsageInsightsChart.jsx";
import PowerGaugeCard from "./components/PowerGaugeCard.jsx";
import ConsumptionCard from "./components/ConsumptionCard.jsx";
import AlertsCard from "./components/AlertsCard.jsx";
import ForecastsPage from "./components/pages/ForecastsPage.jsx";
import AnomaliesPage from "./components/pages/AnomaliesPage.jsx";
import RecommendationsPage from "./components/pages/RecommendationsPage.jsx";
import CommandsPage from "./components/pages/CommandsPage.jsx";

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
  const [activeTab, setActiveTab] = useState("overview");
  const historyRef = useRef([]);
  const [history, setHistory] = useState([]);

  const applyState = useCallback((next) => {
    setState(next);
    setError(null);
    // Session-only history (no historical-state API endpoint exists yet —
    // same disclosed limitation as before). Carries solar/load now too, for
    // the Overview "Energy Usage Insights" chart, not just battery SOC.
    const point = {
      timestamp: new Date(next.timestamp),
      value: next.battery_soc_pct,
      solarKw: next.solar_power_kw,
      loadKw: next.building_load_kw,
    };
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

  const activeLabel = NAV_ITEMS.find((item) => item.key === activeTab)?.label ?? "Overview";

  if (error && !state) {
    const message =
      error instanceof ApiUnreachable
        ? `Cannot reach the API at ${BASE_URL}. Is it running?`
        : error instanceof ApiError
          ? `API error ${error.statusCode}: ${error.detail}`
          : error.message;
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50 p-6">
        <div className="error-banner max-w-md">{message}</div>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <p className="loading-hint">Loading current reading…</p>
      </div>
    );
  }

  const selfPoweredPct = selfPoweredFromState(state);

  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar items={NAV_ITEMS} active={activeTab} onSelect={setActiveTab} />

      <div className="flex min-w-0 flex-1 flex-col">
        {/* mobile nav — sidebar is hidden below lg, this takes its place */}
        <div className="flex items-center gap-2 overflow-x-auto border-b border-gray-200 bg-white px-4 py-2 lg:hidden">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                type="button"
                onClick={() => setActiveTab(item.key)}
                className={
                  "flex shrink-0 items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-semibold " +
                  (item.key === activeTab ? "bg-gray-900 text-white" : "bg-gray-100 text-gray-600")
                }
              >
                <Icon className="h-3.5 w-3.5" />
                {item.label}
              </button>
            );
          })}
        </div>

        <Topbar
          title={activeLabel}
          onRefresh={refresh}
          refreshing={refreshing}
          onRunCycle={handleRunDecisionCycle}
          runningCycle={runningCycle}
        />

        <main className="flex-1 overflow-y-auto p-4 lg:p-8">
          <div className="mb-4">
            <StatusPills state={state} />
          </div>

          {activeTab === "overview" && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                <div className="xl:col-span-2">
                  <HeroCard
                    selfPoweredPct={selfPoweredPct}
                    gridStatus={state.grid_status}
                    batteryMode={state.battery_mode}
                  />
                </div>
                <UsageInsightsChart points={history} />
              </div>

              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
                <PowerGaugeCard selfPoweredPct={selfPoweredPct} state={state} />
                <ConsumptionCard state={state} />
                <AlertsCard state={state} />
              </div>

              <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
                <div className="xl:col-span-2">
                  <SystemOverviewList state={state} />
                </div>
                <PendingApprovals refreshKey={approvalsRefreshKey} />
              </div>
            </div>
          )}

          {activeTab === "energy-flow" && (
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <EnergyFlowDiagram
                solarKw={state.solar_power_kw}
                batteryPowerKw={state.battery_power_kw}
                batteryMode={state.battery_mode}
                batterySocPct={state.battery_soc_pct}
                gridPowerKw={state.grid_power_kw}
                gridStatus={state.grid_status}
              />
              <StoredEnergyChart points={history} label="Battery SOC" unit="%" />
            </div>
          )}

          {activeTab === "approvals" && (
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
              <PendingApprovals refreshKey={approvalsRefreshKey} />
            </div>
          )}

          {activeTab === "forecasts" && <ForecastsPage />}
          {activeTab === "anomalies" && <AnomaliesPage />}
          {activeTab === "recommendations" && <RecommendationsPage />}
          {activeTab === "commands" && <CommandsPage />}
        </main>
      </div>
    </div>
  );
}
