import { motion } from "framer-motion";
import { IconHome, IconSun, IconBattery, IconBolt } from "../icons.jsx";

// Fixed layout for the 3-spoke hub: Home in the center, Solar/Battery/Grid
// arranged around it. Coordinates are hand-placed (not computed from data —
// there are always exactly these 4 nodes), viewBox 320x260.
const HOME = { cx: 160, cy: 150, r: 32 };
const SOLAR = { cx: 160, cy: 40, r: 26 };
const BATTERY = { cx: 55, cy: 230, r: 26 };
const GRID = { cx: 265, cy: 230, r: 26 };

// Edge-to-edge line endpoints (circle centers minus their radius along the
// connecting direction), pre-computed since the layout never changes.
const LINES = {
  solar: { x1: 160, y1: 118, x2: 160, y2: 66 },
  battery: { x1: 134.6, y1: 169.4, x2: 75.7, y2: 214.2 },
  grid: { x1: 185.4, y1: 169.4, x2: 244.3, y2: 214.2 },
};

function pct(x, y) {
  return { left: `${(x / 320) * 100}%`, top: `${(y / 260) * 100}%` };
}

function Node({ node, icon: Icon, label, sublabel }) {
  return (
    <div className="absolute flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-1" style={pct(node.cx, node.cy)}>
      <div className="flex h-12 w-12 items-center justify-center rounded-full border border-gray-200 bg-white text-gray-700 shadow-sm">
        <Icon className="h-5 w-5" />
      </div>
      <span className="text-[11px] font-semibold text-gray-700">{label}</span>
      {sublabel && <span className="text-[10px] text-gray-400">{sublabel}</span>}
    </div>
  );
}

function Spoke({ line, valueKw, direction, color }) {
  const isActive = direction !== "idle" && Math.abs(valueKw) > 0.05;
  const [fromX, fromY, toX, toY] =
    direction === "reverse" ? [line.x2, line.y2, line.x1, line.y1] : [line.x1, line.y1, line.x2, line.y2];
  const midX = (line.x1 + line.x2) / 2;
  const midY = (line.y1 + line.y2) / 2;

  return (
    <>
      <line x1={line.x1} y1={line.y1} x2={line.x2} y2={line.y2} stroke="#e5e7eb" strokeWidth={2} />
      {isActive && (
        <motion.circle
          r={4.5}
          fill={color}
          animate={{ cx: [fromX, toX], cy: [fromY, toY] }}
          transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }}
        />
      )}
      <foreignObject x={midX - 28} y={midY - 10} width={56} height={20}>
        <div
          className="flex h-full items-center justify-center rounded-full bg-white text-[10px] font-semibold"
          style={{ color: isActive ? color : "#9ca3af", border: "1px solid #e5e7eb" }}
        >
          {Math.abs(valueKw).toFixed(1)} kW
        </div>
      </foreignObject>
    </>
  );
}

export default function EnergyFlowDiagram({
  solarKw,
  batteryPowerKw,
  batteryMode,
  batterySocPct,
  gridPowerKw,
  gridStatus,
}) {
  // Every line's (x1,y1) is the Home-side edge, (x2,y2) the outer-node edge
  // (see LINES above) — so "forward" always means Home -> outer, "reverse"
  // always means outer -> Home, consistently across all three spokes.
  //
  // battery_power_kw: positive = charging = Home -> Battery = "forward";
  // negative = discharging = Battery -> Home = "reverse". Matches
  // DigitalTwin.tick()'s sign convention.
  const batteryDirection = batteryPowerKw > 0.05 ? "forward" : batteryPowerKw < -0.05 ? "reverse" : "idle";
  // grid_power_kw: positive = importing = Grid -> Home = "reverse"; negative
  // = exporting = Home -> Grid = "forward".
  const gridDirection = gridPowerKw > 0.05 ? "reverse" : gridPowerKw < -0.05 ? "forward" : "idle";
  const gridActive = gridStatus === "CONNECTED" ? gridDirection : "idle";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
    >
      <p className="mb-2 text-sm font-semibold text-gray-700">Energy flow</p>
      <div className="relative w-full" style={{ aspectRatio: "320 / 260" }}>
        <svg viewBox="0 0 320 260" className="absolute inset-0 h-full w-full">
          <Spoke line={LINES.solar} valueKw={solarKw} direction={solarKw > 0.05 ? "reverse" : "idle"} color="#0ca30c" />
          <Spoke line={LINES.battery} valueKw={batteryPowerKw} direction={batteryDirection} color="var(--accent)" />
          <Spoke line={LINES.grid} valueKw={gridPowerKw} direction={gridActive} color="#f59e0b" />
        </svg>
        <Node node={HOME} icon={IconHome} label="Home" />
        <Node node={SOLAR} icon={IconSun} label="Solar" />
        <Node node={BATTERY} icon={IconBattery} label="Battery" sublabel={`${batterySocPct.toFixed(0)}% · ${batteryMode}`} />
        <Node node={GRID} icon={IconBolt} label="Grid" sublabel={gridStatus !== "CONNECTED" ? gridStatus : undefined} />
      </div>
    </motion.div>
  );
}
