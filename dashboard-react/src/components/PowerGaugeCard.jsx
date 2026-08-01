import { RadialBar, RadialBarChart, ResponsiveContainer } from "recharts";
import { motion } from "framer-motion";

function MiniStat({ label, value }) {
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2">
      <p className="text-[11px] text-gray-500">{label}</p>
      <p className="text-sm font-semibold text-gray-800">{value}</p>
    </div>
  );
}

export default function PowerGaugeCard({ selfPoweredPct, state }) {
  const data = [{ name: "self-powered", value: Math.max(0, Math.min(100, selfPoweredPct)), fill: "var(--accent)" }];

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay: 0.1 }}
      className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
    >
      <p className="mb-1 text-sm font-semibold text-gray-700">Current power</p>
      <div className="relative">
        <ResponsiveContainer width="100%" height={140}>
          <RadialBarChart
            innerRadius="70%"
            outerRadius="100%"
            barSize={12}
            data={data}
            startAngle={90}
            endAngle={-270}
          >
            <RadialBar dataKey="value" background={{ fill: "#f1f5f9" }} cornerRadius={8} />
          </RadialBarChart>
        </ResponsiveContainer>
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-bold text-gray-900">{selfPoweredPct.toFixed(0)}%</span>
          <span className="text-[11px] text-gray-500">self-powered</span>
        </div>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <MiniStat label="Solar" value={`${state.solar_power_kw.toFixed(1)} kW`} />
        <MiniStat label="Grid" value={`${Math.abs(state.grid_power_kw).toFixed(1)} kW`} />
        <MiniStat label="Inverter out" value={`${state.inverter_output_kw.toFixed(1)} kW`} />
        <MiniStat label="Battery" value={`${state.battery_soc_pct.toFixed(0)}%`} />
      </div>
    </motion.div>
  );
}
