import { Cell, Pie, PieChart, ResponsiveContainer } from "recharts";
import { motion } from "framer-motion";

// Splits current building load into "covered by solar" vs "covered by
// grid/battery" — a real, computed split from live state, not a guess.
export default function ConsumptionCard({ state }) {
  const load = state.building_load_kw;
  const solarShare = load > 0 ? Math.min(load, Math.max(state.solar_power_kw, 0)) : 0;
  const otherShare = Math.max(load - solarShare, 0);
  const data = [
    { name: "Solar", value: solarShare, fill: "var(--accent)" },
    { name: "Grid / battery", value: otherShare, fill: "#fbbf24" },
  ];
  const solarPct = load > 0 ? Math.round((solarShare / load) * 100) : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.15 }}
      className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
    >
      <p className="mb-1 text-sm font-semibold text-gray-700">Consumption</p>
      <p className="text-2xl font-bold text-gray-900">{load.toFixed(1)} kW</p>
      <div className="relative mt-2">
        <ResponsiveContainer width="100%" height={120}>
          <PieChart>
            <Pie data={data} dataKey="value" innerRadius={38} outerRadius={54} paddingAngle={2} stroke="none">
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.fill} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-lg font-bold text-gray-900">{solarPct}%</span>
          <span className="text-[10px] text-gray-500">solar</span>
        </div>
      </div>
      <div className="mt-3 flex items-center justify-center gap-4 text-xs">
        <span className="flex items-center gap-1.5 text-gray-600">
          <span className="h-2 w-2 rounded-full" style={{ background: "var(--accent)" }} /> Solar
        </span>
        <span className="flex items-center gap-1.5 text-gray-600">
          <span className="h-2 w-2 rounded-full bg-amber-400" /> Grid / battery
        </span>
      </div>
    </motion.div>
  );
}
