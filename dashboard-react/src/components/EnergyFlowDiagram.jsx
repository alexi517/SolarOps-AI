function FlowRow({ fromIcon, fromLabel, toIcon, toLabel, valueKw, direction, activeColor }) {
  // direction: "forward" (from -> to), "reverse" (to -> from), or "idle" (no flow)
  const isActive = direction !== "idle" && Math.abs(valueKw) > 0.05;
  const dotStyle = isActive
    ? {
        animation: `flow-dot 1.6s linear infinite`,
        animationDirection: direction === "reverse" ? "reverse" : "normal",
        background: activeColor,
      }
    : { display: "none" };

  return (
    <div className="flow-row">
      <div className="flow-endpoint">
        <span className="flow-endpoint-icon">{fromIcon}</span>
        <span className="flow-endpoint-label">{fromLabel}</span>
      </div>
      <div className="flow-track">
        <span className="flow-track-line" />
        <span className="flow-dot" style={dotStyle} />
        <span className="flow-track-value" style={{ color: isActive ? activeColor : "var(--text-muted)" }}>
          {Math.abs(valueKw).toFixed(1)} kW
        </span>
      </div>
      <div className="flow-endpoint">
        <span className="flow-endpoint-icon">{toIcon}</span>
        <span className="flow-endpoint-label">{toLabel}</span>
      </div>
    </div>
  );
}

export default function EnergyFlowDiagram({ solarKw, batteryPowerKw, batteryMode, gridPowerKw, gridStatus }) {
  // battery_power_kw: positive = charging (Home -> Battery, shown as "reverse"
  // since the row runs Battery -> Home left to right); negative = discharging
  // (Battery -> Home, "forward"). Matches DigitalTwin.tick()'s sign convention.
  const batteryDirection = batteryPowerKw > 0.05 ? "reverse" : batteryPowerKw < -0.05 ? "forward" : "idle";
  // grid_power_kw: positive = importing (Grid -> Home, "forward"); negative =
  // exporting (Home -> Grid, "reverse").
  const gridDirection = gridPowerKw > 0.05 ? "forward" : gridPowerKw < -0.05 ? "reverse" : "idle";

  return (
    <div className="card">
      <p className="card-title">Energy flow</p>
      <div className="flow-rows">
        <FlowRow
          fromIcon="☀️"
          fromLabel="Solar"
          toIcon="🏠"
          toLabel="Home"
          valueKw={solarKw}
          direction={solarKw > 0.05 ? "forward" : "idle"}
          activeColor="var(--status-good)"
        />
        <FlowRow
          fromIcon="🔋"
          fromLabel={`Battery (${batteryMode})`}
          toIcon="🏠"
          toLabel="Home"
          valueKw={batteryPowerKw}
          direction={batteryDirection}
          activeColor="var(--accent)"
        />
        <FlowRow
          fromIcon="⚡"
          fromLabel={gridStatus === "CONNECTED" ? "Grid" : `Grid (${gridStatus})`}
          toIcon="🏠"
          toLabel="Home"
          valueKw={gridPowerKw}
          direction={gridStatus === "CONNECTED" ? gridDirection : "idle"}
          activeColor="var(--status-warning)"
        />
      </div>
    </div>
  );
}
