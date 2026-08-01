import { IconRefresh } from "../icons.jsx";

export default function Topbar({ title, onRefresh, refreshing, onRunCycle, runningCycle }) {
  return (
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 bg-white px-4 py-4 lg:px-8">
      <h1 className="text-lg font-semibold text-gray-900">{title}</h1>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onRunCycle}
          disabled={runningCycle}
          className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {runningCycle ? "Running…" : "Run decision cycle"}
        </button>
        <button
          type="button"
          onClick={onRefresh}
          aria-label="Refresh reading"
          disabled={refreshing}
          className="flex h-9 w-9 items-center justify-center rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 disabled:opacity-60"
        >
          <IconRefresh className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
        </button>
        <div
          className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-200 text-xs font-semibold text-gray-600"
          title="Operator (placeholder)"
        >
          OP
        </div>
      </div>
    </header>
  );
}
