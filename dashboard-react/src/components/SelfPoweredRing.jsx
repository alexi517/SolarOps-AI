const RADIUS = 54;
const STROKE = 12;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

export default function SelfPoweredRing({ selfPoweredPct, gridDependencePct }) {
  const clamped = Math.max(0, Math.min(100, selfPoweredPct));
  const offset = CIRCUMFERENCE * (1 - clamped / 100);

  return (
    <div className="card">
      <p className="card-title">Self-powered</p>
      <div className="ring-card-body">
        <svg width="140" height="140" viewBox="0 0 140 140" role="img" aria-label={`${clamped.toFixed(0)}% self-powered`}>
          <circle
            cx="70"
            cy="70"
            r={RADIUS}
            fill="none"
            stroke="var(--accent-track)"
            strokeWidth={STROKE}
          />
          <circle
            cx="70"
            cy="70"
            r={RADIUS}
            fill="none"
            stroke="var(--accent)"
            strokeWidth={STROKE}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            transform="rotate(-90 70 70)"
            style={{ transition: "stroke-dashoffset 500ms ease" }}
          />
          <text
            x="70"
            y="66"
            textAnchor="middle"
            fontSize="26"
            fontWeight="700"
            fill="var(--text-primary)"
          >
            {clamped.toFixed(0)}%
          </text>
          <text x="70" y="86" textAnchor="middle" fontSize="11" fill="var(--text-muted)">
            of load
          </text>
        </svg>
        <div className="ring-figures">
          <div>
            <div className="ring-figure-label">Self-powered</div>
            <div className="ring-figure-value accent">{clamped.toFixed(0)}%</div>
          </div>
          <div>
            <div className="ring-figure-label">Grid dependence</div>
            <div className="ring-figure-value">{Math.max(0, Math.min(100, gridDependencePct)).toFixed(0)}%</div>
          </div>
        </div>
      </div>
    </div>
  );
}
