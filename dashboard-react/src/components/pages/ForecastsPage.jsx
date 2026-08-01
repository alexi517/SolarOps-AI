import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { motion } from "framer-motion";
import { getForecasts } from "../../api.js";

const KIND_LABEL = {
  SOLAR_GENERATION: "Solar generation",
  BUILDING_LOAD: "Building load",
  BATTERY_SOC: "Battery SOC",
};

// The API's "unavailable" reason is written for engineers/logs (references
// internal doc/phase numbers) — translated to plain language here rather
// than changing the API's own text, which stays precise for that audience.
function humanizeUnavailableReason(reason) {
  if (reason.includes("evaluation gate")) {
    return "Not available yet — this forecast hasn't been trained and validated for this site.";
  }
  return "This forecast isn't available right now.";
}

function ForecastChart({ forecast }) {
  const data = forecast.points.map((p) => ({
    time: new Date(p.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    value: p.value,
    low: p.interval_low,
    high: p.interval_high,
  }));
  const hasInterval = data.some((d) => d.low != null && d.high != null);

  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis dataKey="time" tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={{ stroke: "#e5e7eb" }} tickLine={false} />
        <YAxis tick={{ fontSize: 11, fill: "#9ca3af" }} axisLine={false} tickLine={false} width={36} />
        <Tooltip contentStyle={{ borderRadius: 10, borderColor: "#e5e7eb", fontSize: 12 }} />
        {hasInterval && (
          <>
            <Line dataKey="low" stroke="#cbd5e1" strokeDasharray="4 3" dot={false} name="low" />
            <Line dataKey="high" stroke="#cbd5e1" strokeDasharray="4 3" dot={false} name="high" />
          </>
        )}
        <Area dataKey="value" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.15} strokeWidth={2} name="forecast" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

function ForecastCard({ entry, index }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
    >
      <p className="text-sm font-semibold text-gray-700">{KIND_LABEL[entry.kind] ?? entry.kind}</p>
      {entry.available ? (
        <>
          <p className="mt-0.5 text-xs text-gray-400">
            {entry.forecast.model_name} v{entry.forecast.model_version} · {entry.forecast.horizon_minutes}min horizon
            {entry.forecast.confidence != null && ` · ${(entry.forecast.confidence * 100).toFixed(0)}% confidence`}
          </p>
          <div className="mt-3">
            <ForecastChart forecast={entry.forecast} />
          </div>
        </>
      ) : (
        <div className="mt-4 rounded-lg bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">
          {humanizeUnavailableReason(entry.reason)}
        </div>
      )}
    </motion.div>
  );
}

export default function ForecastsPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getForecasts()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <p className="loading-hint">Loading forecasts…</p>;

  return (
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
      {data.forecasts.map((entry, i) => (
        <ForecastCard key={entry.kind} entry={entry} index={i} />
      ))}
    </div>
  );
}
