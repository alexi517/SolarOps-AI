import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getRecommendations } from "../../api.js";

function List({ title, items }) {
  if (items.length === 0) return null;
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">{title}</p>
      <ul className="mt-1 list-disc space-y-0.5 pl-4 text-sm text-gray-600">
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function RecommendationCard({ rec, rank }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: rank * 0.05 }}
      className="rounded-2xl border border-gray-100 bg-white p-5 shadow-sm"
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold text-gray-400">#{rank + 1}</p>
          <p className="text-base font-bold text-gray-900">{rec.action.replaceAll("_", " ")}</p>
        </div>
        <span className="shrink-0 rounded-full bg-[var(--accent-soft)] px-3 py-1 text-xs font-semibold text-[var(--accent)]">
          {(rec.confidence * 100).toFixed(0)}% confidence
        </span>
      </div>

      {Object.keys(rec.params).length > 0 && (
        <p className="mt-2 font-mono text-xs text-gray-500">{JSON.stringify(rec.params)}</p>
      )}

      <p className="mt-3 text-sm text-gray-700">{rec.reason}</p>
      <p className="mt-1 text-xs text-gray-400">{rec.expected_benefit}</p>

      <div className="mt-3 rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-500">
        <span className="font-semibold text-gray-600">Why now: </span>
        {rec.why_now}
      </div>

      <List title="Evidence" items={rec.evidence} />
      <List title="Alternatives considered" items={rec.alternatives} />
      <List title="Risks" items={rec.risks} />
    </motion.div>
  );
}

export default function RecommendationsPage() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getRecommendations()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!data) return <p className="loading-hint">Loading recommendations…</p>;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {data.recommendations.map((rec, i) => (
        <RecommendationCard key={rec.recommendation_id} rec={rec} rank={i} />
      ))}
    </div>
  );
}
