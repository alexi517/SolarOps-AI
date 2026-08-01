import { useMemo, useState } from "react";

const WIDTH = 300;
const HEIGHT = 120;
const PAD_Y = 12;

// A session-only sparkline: the API has no historical-state endpoint yet
// (Layer 2 operational history isn't built — see docs/CODE-WALKTHROUGH.md),
// so this only ever shows what's been read since this tab was opened. That's
// disclosed in the empty-state copy rather than pretending it's a real
// history chart.
export default function StoredEnergyChart({ points, label = "Battery SOC", unit = "%" }) {
  const [hoverIndex, setHoverIndex] = useState(null);

  const { linePath, areaPath, scaleX, scaleY, minV, maxV } = useMemo(() => {
    if (points.length < 2) return {};
    const values = points.map((p) => p.value);
    const minV = Math.min(...values);
    const maxV = Math.max(...values);
    const range = maxV - minV || 1;
    const scaleX = (i) => (i / (points.length - 1)) * WIDTH;
    const scaleY = (v) => HEIGHT - PAD_Y - ((v - minV) / range) * (HEIGHT - PAD_Y * 2);

    const coords = points.map((p, i) => [scaleX(i), scaleY(p.value)]);
    const linePath = coords.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
    const areaPath = `${linePath} L${WIDTH},${HEIGHT} L0,${HEIGHT} Z`;

    return { linePath, areaPath, scaleX, scaleY, minV, maxV };
  }, [points]);

  if (points.length < 2) {
    return (
      <div className="card">
        <p className="card-title">{label}</p>
        <div className="chart-empty">Collecting readings this session — check back after a refresh or two.</div>
      </div>
    );
  }

  const handleMove = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const relX = ((event.clientX - rect.left) / rect.width) * WIDTH;
    const index = Math.round((relX / WIDTH) * (points.length - 1));
    setHoverIndex(Math.max(0, Math.min(points.length - 1, index)));
  };

  const hovered = hoverIndex !== null ? points[hoverIndex] : points[points.length - 1];
  const hoveredIndex = hoverIndex !== null ? hoverIndex : points.length - 1;

  return (
    <div className="card">
      <p className="card-title">
        {label}
        <span className="updated-at">this session</span>
      </p>
      <div className="chart-wrap">
        <svg
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          width="100%"
          height={HEIGHT}
          onMouseMove={handleMove}
          onMouseLeave={() => setHoverIndex(null)}
          role="img"
          aria-label={`${label} over this session, from ${minV.toFixed(1)}${unit} to ${maxV.toFixed(1)}${unit}`}
        >
          <defs>
            <linearGradient id="storedEnergyFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.25" />
              <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
            </linearGradient>
          </defs>
          <path d={areaPath} fill="url(#storedEnergyFill)" stroke="none" />
          <path d={linePath} fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinejoin="round" />
          <line
            x1={scaleX(hoveredIndex)}
            x2={scaleX(hoveredIndex)}
            y1="0"
            y2={HEIGHT}
            stroke="var(--border)"
            strokeWidth="1"
          />
          <circle cx={scaleX(hoveredIndex)} cy={scaleY(hovered.value)} r="4" fill="var(--accent)" />
        </svg>
        <div
          className="chart-tooltip"
          style={{
            left: `${(scaleX(hoveredIndex) / WIDTH) * 100}%`,
            top: `${(scaleY(hovered.value) / HEIGHT) * 100}%`,
          }}
        >
          {hovered.value.toFixed(1)}
          {unit} · {hovered.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </div>
      </div>
    </div>
  );
}
