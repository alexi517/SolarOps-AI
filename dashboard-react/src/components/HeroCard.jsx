import { motion } from "framer-motion";

// Simple inline SVG illustration (house + panel + sun) — not a stock photo,
// but real and brand-consistent rather than faking an asset we don't have.
function HouseIllustration() {
  return (
    <svg viewBox="0 0 200 140" className="h-full w-full" role="presentation" aria-hidden="true">
      <circle cx="164" cy="30" r="18" fill="#fde68a" />
      <path d="M30 90 L100 40 L170 90 Z" fill="#166534" opacity="0.15" />
      <rect x="45" y="90" width="110" height="40" rx="4" fill="#ffffff" />
      <rect x="45" y="90" width="110" height="40" rx="4" fill="var(--accent)" opacity="0.08" />
      <rect x="55" y="60" width="90" height="34" rx="3" fill="#0f172a" opacity="0.85" />
      {Array.from({ length: 6 }).map((_, i) => (
        <rect key={i} x={58 + i * 14.5} y="63" width="12" height="28" fill="#1e293b" stroke="#334155" strokeWidth="0.5" />
      ))}
      <rect x="90" y="102" width="20" height="28" fill="var(--accent)" opacity="0.8" />
    </svg>
  );
}

export default function HeroCard({ selfPoweredPct, gridStatus, batteryMode }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="relative overflow-hidden rounded-2xl border border-gray-100 bg-white p-6 shadow-sm"
    >
      <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
        <div className="h-28 w-40 shrink-0 sm:h-32 sm:w-48">
          <HouseIllustration />
        </div>
        <div className="min-w-0">
          <p className="text-sm font-medium text-gray-500">Site status</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">
            {selfPoweredPct.toFixed(0)}%{" "}
            <span className="text-base font-medium text-gray-500">self-powered right now</span>
          </p>
          <p className="mt-2 text-sm text-gray-500">
            Grid <span className="font-semibold text-gray-700">{gridStatus}</span> · Battery{" "}
            <span className="font-semibold text-gray-700">{batteryMode}</span>
          </p>
        </div>
      </div>
    </motion.div>
  );
}
