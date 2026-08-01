export default function StatusPills({ state }) {
  const pills = [];
  if (state.grid_status !== "CONNECTED") {
    pills.push({ key: "grid", tone: "critical", text: `Grid status: ${state.grid_status}` });
  }
  if (state.any_asset_offline) {
    pills.push({ key: "offline", tone: "warning", text: "At least one asset is offline" });
  }
  if (state.fault_codes.length > 0) {
    pills.push({ key: "faults", tone: "critical", text: `Active faults: ${state.fault_codes.join(", ")}` });
  }
  if (pills.length === 0) {
    pills.push({ key: "ok", tone: "good", text: "All systems normal" });
  }

  return (
    <div className="status-row">
      {pills.map((pill) => (
        <span key={pill.key} className={`pill ${pill.tone}`}>
          {pill.text}
        </span>
      ))}
    </div>
  );
}
