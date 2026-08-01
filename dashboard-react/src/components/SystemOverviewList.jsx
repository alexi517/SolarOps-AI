function Row({ label, value }) {
  return (
    <div className="list-row">
      <span className="list-row-label">{label}</span>
      <span className="list-row-value">{value}</span>
    </div>
  );
}

export default function SystemOverviewList({ state }) {
  return (
    <div className="card">
      <p className="card-title">System overview</p>
      <Row label="Solar production" value={`${state.solar_power_kw.toFixed(1)} kW`} />
      <Row label="Building load" value={`${state.building_load_kw.toFixed(1)} kW`} />
      <Row label="Battery SOC" value={`${state.battery_soc_pct.toFixed(1)} %`} />
      <Row label="Battery mode" value={state.battery_mode} />
      <Row label="Battery temp" value={`${state.battery_temp_c.toFixed(1)} °C`} />
      <Row label="Inverter status" value={state.inverter_status} />
      <Row label="Grid status" value={state.grid_status} />
      <Row
        label="Grid power"
        value={`${Math.abs(state.grid_power_kw).toFixed(1)} kW ${state.grid_power_kw >= 0 ? "importing" : "exporting"}`}
      />
    </div>
  );
}
