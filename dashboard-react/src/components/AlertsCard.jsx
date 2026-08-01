import { motion } from "framer-motion";

// Real alerts derived from live EnergyState (grid status, fault codes,
// offline assets) — a separate, real-time source from the anomaly detector's
// findings, which live on the Anomalies page instead. Kept apart rather than
// merged, so each stays traceable to what actually produced it.
function humanizeFaultCode(code) {
  return code.replaceAll("_", " ").toLowerCase().replace(/^./, (c) => c.toUpperCase());
}

function buildAlerts(state) {
  const alerts = [];
  if (state.grid_status !== "CONNECTED") {
    alerts.push({ id: "grid", severity: "critical", text: `Grid status: ${state.grid_status.toLowerCase()}` });
  }
  if (state.any_asset_offline) {
    alerts.push({ id: "offline", severity: "warning", text: "At least one asset is offline" });
  }
  for (const code of state.fault_codes) {
    alerts.push({ id: `fault-${code}`, severity: "critical", text: humanizeFaultCode(code) });
  }
  if (state.battery_soc_pct <= 15) {
    alerts.push({ id: "low-soc", severity: "warning", text: `Battery SOC low (${state.battery_soc_pct.toFixed(0)}%)` });
  }
  return alerts;
}

const DOT_CLASS = {
  critical: "bg-red-500",
  warning: "bg-amber-400",
};

export default function AlertsCard({ state }) {
  const alerts = buildAlerts(state);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.2 }}
      className="flex flex-col rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
    >
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm font-semibold text-gray-700">Alerts</p>
        <span className="text-xs text-gray-400">{alerts.length} active</span>
      </div>
      {alerts.length === 0 ? (
        <div className="flex flex-1 items-center justify-center py-8 text-sm text-gray-400">
          No active alerts — all systems normal.
        </div>
      ) : (
        <ul className="flex-1 space-y-2">
          {alerts.map((alert) => (
            <li key={alert.id} className="flex items-start gap-2.5 rounded-lg bg-gray-50 px-3 py-2.5 text-sm">
              <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${DOT_CLASS[alert.severity]}`} />
              <span className="text-gray-700">{alert.text}</span>
            </li>
          ))}
        </ul>
      )}
    </motion.div>
  );
}
