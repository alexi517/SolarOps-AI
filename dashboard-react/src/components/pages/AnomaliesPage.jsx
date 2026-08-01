import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getAnomalies } from "../../api.js";

// Matches GET /sites/{id}/anomalies' own window exactly (anomalies.py:
// `_RECENT_WINDOW = timedelta(hours=24)`) — stated here so the UI doesn't
// silently imply "all anomalies ever."
const WINDOW_LABEL = "last 24 hours";

const SEVERITY_CLASS = {
  CRITICAL: "bg-red-50 text-red-700 border-red-100",
  HIGH: "bg-orange-50 text-orange-700 border-orange-100",
  MEDIUM: "bg-amber-50 text-amber-700 border-amber-100",
  LOW: "bg-gray-100 text-gray-600 border-gray-200",
};

function AnomalyCard({ anomaly, index }) {
  const badgeClass = SEVERITY_CLASS[anomaly.severity] ?? SEVERITY_CLASS.LOW;
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
      className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-gray-800">{anomaly.anomaly_type}</p>
          <p className="text-xs text-gray-400">{anomaly.affected_asset}</p>
        </div>
        <span className={`shrink-0 rounded-full border px-2.5 py-1 text-[11px] font-semibold ${badgeClass}`}>
          {anomaly.severity}
        </span>
      </div>
      <p className="mt-3 text-sm text-gray-600">{anomaly.recommended_action}</p>
      {anomaly.supporting_evidence.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 pl-4 text-xs text-gray-500">
          {anomaly.supporting_evidence.map((e, i) => (
            <li key={i}>{e}</li>
          ))}
        </ul>
      )}
      <div className="mt-3 flex items-center justify-between text-xs text-gray-400">
        <span>{(anomaly.confidence * 100).toFixed(0)}% confidence</span>
        <span>{new Date(anomaly.detected_at).toLocaleString()}</span>
      </div>
    </motion.div>
  );
}

export default function AnomaliesPage() {
  const [anomalies, setAnomalies] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getAnomalies()
      .then(setAnomalies)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!anomalies) return <p className="loading-hint">Loading anomalies…</p>;

  return (
    <div>
      <p className="mb-4 text-xs text-gray-400">Detected in the {WINDOW_LABEL}</p>
      {anomalies.length === 0 ? (
        <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center text-sm text-gray-500 shadow-sm">
          No anomalies detected in the {WINDOW_LABEL}.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-3">
          {anomalies.map((a, i) => (
            <AnomalyCard key={a.anomaly_id} anomaly={a} index={i} />
          ))}
        </div>
      )}
    </div>
  );
}
