import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { getCommand, getCommands } from "../../api.js";

// Status names aren't hardcoded from the domain enum here (avoids asserting
// false precision about the exact list) — colored by keyword pattern instead.
function statusClass(status) {
  const s = status.toUpperCase();
  if (s.includes("REJECTED") || s.includes("FAILED")) return "bg-red-50 text-red-700 border-red-100";
  if (s.includes("APPROVAL") || s.includes("PENDING")) return "bg-amber-50 text-amber-700 border-amber-100";
  if (s.includes("COMPLETED") || s.includes("APPROVED") || s.includes("DISPATCHED"))
    return "bg-[var(--accent-soft)] text-[var(--accent)] border-transparent";
  return "bg-gray-100 text-gray-600 border-gray-200";
}

function Stage({ title, result, render }) {
  return (
    <div className="rounded-lg bg-gray-50 px-3 py-2.5">
      <p className="text-xs font-semibold text-gray-500">{title}</p>
      {result ? (
        <div className="mt-1 text-sm text-gray-700">{render(result)}</div>
      ) : (
        <p className="mt-1 text-sm text-gray-400">Not reached</p>
      )}
    </div>
  );
}

function CommandDetail({ commandId }) {
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getCommand(commandId)
      .then(setDetail)
      .catch((err) => setError(err.message));
  }, [commandId]);

  if (error) return <p className="px-4 py-3 text-sm text-red-600">{error}</p>;
  if (!detail) return <p className="px-4 py-3 text-sm text-gray-400">Loading detail…</p>;

  return (
    <div className="space-y-2 border-t border-gray-100 bg-gray-50/50 px-4 py-4">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <Stage title="Policy" result={detail.policy_result} render={(r) => (r.passed ? "Passed" : r.violations.join("; "))} />
        <Stage
          title="Safety"
          result={detail.safety_assessment}
          render={(r) => (r.passed ? "Passed" : r.failed_checks.join("; "))}
        />
        <Stage title="Risk" result={detail.risk_assessment} render={(r) => `${r.level} — ${r.factors.join("; ")}`} />
        <Stage
          title="Approval"
          result={detail.approval_decision}
          render={(r) => `${r.outcome}${r.operator_id ? ` by ${r.operator_id}` : ""}`}
        />
        <Stage
          title="Execution"
          result={detail.execution_result}
          render={(r) => `${r.outcome}${r.retry_count ? ` (${r.retry_count} retries)` : ""}`}
        />
        <Stage
          title="Verification"
          result={detail.verification_result}
          render={(r) => (r.passed ? "Passed" : `expected ${r.expected}, observed ${r.observed}`)}
        />
      </div>
    </div>
  );
}

export default function CommandsPage() {
  const [commands, setCommands] = useState(null);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    getCommands()
      .then(setCommands)
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="error-banner">{error}</div>;
  if (!commands) return <p className="loading-hint">Loading commands…</p>;
  if (commands.length === 0) {
    return (
      <div className="rounded-2xl border border-gray-100 bg-white p-10 text-center text-sm text-gray-500 shadow-sm">
        No commands recorded for this site yet.
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="overflow-hidden rounded-2xl border border-gray-100 bg-white shadow-sm"
    >
      {commands.map((cmd) => (
        <div key={cmd.command_id} className="border-b border-gray-100 last:border-0">
          <button
            type="button"
            onClick={() => setExpanded(expanded === cmd.command_id ? null : cmd.command_id)}
            className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium text-gray-800">{cmd.action.replaceAll("_", " ")}</p>
              <p className="text-xs text-gray-400">{cmd.asset_id}</p>
            </div>
            <div className="flex shrink-0 items-center gap-3">
              <span className="hidden text-xs text-gray-400 sm:inline">
                {new Date(cmd.created_at).toLocaleString()}
              </span>
              <span className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${statusClass(cmd.status)}`}>
                {cmd.status}
              </span>
              <span className="text-gray-300">{expanded === cmd.command_id ? "▲" : "▼"}</span>
            </div>
          </button>
          {expanded === cmd.command_id && <CommandDetail commandId={cmd.command_id} />}
        </div>
      ))}
    </motion.div>
  );
}
