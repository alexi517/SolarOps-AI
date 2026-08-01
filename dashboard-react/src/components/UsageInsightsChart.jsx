import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { motion } from "framer-motion";

// Session-only, same disclosed limitation as StoredEnergyChart — no
// historical-state API endpoint exists yet, so this only covers readings
// collected since this tab was opened.
export default function UsageInsightsChart({ points }) {
  const data = points.map((p) => ({
    time: p.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    solar: p.solarKw,
    load: p.loadKw,
  }));

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.05 }}
      className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
    >
      <div className="mb-3 flex items-center justify-between">
        <p className="text-sm font-semibold text-gray-700">Energy usage insights</p>
        <span className="text-xs text-gray-400">this session</span>
      </div>
      {data.length < 2 ? (
        <div className="flex h-[180px] items-center justify-center text-sm text-gray-400">
          Collecting readings — check back after a refresh or two.
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data} barGap={2}>
            <XAxis
              dataKey="time"
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              axisLine={{ stroke: "#e5e7eb" }}
              tickLine={false}
              interval="preserveStartEnd"
            />
            <Tooltip
              formatter={(value, name) => [`${value.toFixed(1)} kW`, name === "solar" ? "Solar" : "Load"]}
              contentStyle={{ borderRadius: 10, borderColor: "#e5e7eb", fontSize: 12 }}
            />
            <Bar dataKey="solar" name="solar" fill="var(--accent)" radius={[3, 3, 0, 0]} maxBarSize={14} />
            <Bar dataKey="load" name="load" fill="#cbd5e1" radius={[3, 3, 0, 0]} maxBarSize={14} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </motion.div>
  );
}
