// Honest placeholder for nav items whose API calls already exist in api.js
// (forecasts/anomalies/recommendations/commands) but have no UI built yet —
// shows real absence rather than fabricating data for the shell.
export default function ComingSoon({ label }) {
  return (
    <div className="card">
      <p className="card-title">{label}</p>
      <p style={{ color: "var(--text-muted)", fontSize: 13, margin: 0 }}>
        This section isn't wired up yet — the API endpoint exists, the UI for it doesn't yet. Coming in a later pass.
      </p>
    </div>
  );
}
