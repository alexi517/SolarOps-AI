# Connecting real hardware — a guide for when you have equipment in hand

This system runs entirely against a simulated Digital Twin today (see
`PROJECT_DEEP_DIVE.md` and `ONBOARDING.md` for the full architecture). This
doc is the practical, sequential guide for replacing that simulation with a
real solar/battery/inverter site — written *before* any real hardware was
available, so treat every code sample here as a template to adapt against
your actual vendor's documentation, not copy-paste-ready code.

Nothing described here has been tested against real equipment. That's the
honest starting point for this document.

## The one thing that doesn't change

Everything downstream of Telemetry and Execution — Forecast, Anomaly,
Decision, Safety, the API, the dashboard — never has to change at all. They
were built against two `Protocol`s (`TelemetrySource`, `HardwareInterface`),
never against the simulated Digital Twin directly. Real hardware is a
**contained addition**: two new adapter classes and one wiring change, not
a rewrite.

## Phase 0 — pick real hardware, get the register map

You need an inverter/BMS with a **documented communication interface**.
Modbus (RTU over RS485, or Modbus TCP over Ethernet/WiFi) is the most
common and best-supported choice — brands like Deye, Luxpower, and Growatt
generally support it.

The one non-negotiable artifact to get from the vendor: the **register
map** — which register holds which value, at what scale/units, and which
registers accept write commands. Nothing in Phase 2 onward is possible
without this.

## Phase 1 — prove comms work, outside this codebase entirely

Before touching `solarops/`, write a throwaway script with `pymodbus` that
reads one register and prints it:

```python
from pymodbus.client import ModbusSerialClient
client = ModbusSerialClient(port="/dev/ttyUSB0", baudrate=9600)
client.connect()
result = client.read_holding_registers(0x3100, count=1)
print(result.registers)   # should print the battery SOC
```

Get this working standalone first. Debugging register mapping issues is
much harder once it's tangled up with the rest of the pipeline.

## Phase 2 — `RealTelemetrySource` (the reading side)

New file, same shape as `platform/twin_telemetry_source.py`, implementing
Telemetry's `TelemetrySource` Protocol:

```python
# platform/real_telemetry_source.py
class RealTelemetrySource:
    def __init__(self, modbus_client, site_id: SiteId) -> None:
        self._client = modbus_client
        self._site_id = site_id

    def read(self, site_id: SiteId) -> Telemetry:
        # every field below: read a register, apply its scale factor,
        # wrap in the matching shared-kernel type
        return Telemetry(
            site_id=self._site_id,
            timestamp=datetime.now(UTC),
            battery_soc=StateOfCharge(raw_soc_register * 0.1),
            grid_status=GridStatus.CONNECTED if raw_grid_flag else GridStatus.OUTAGE,
            ...
        )
```

All unit conversion (raw register integer → real `Power`/`StateOfCharge`/
etc.) happens here, once, in one place.

## Phase 3 — `RealHardwareInterface` (the acting side)

Mirrors `platform/twin_hardware_interface.py`, implementing Execution's
`HardwareInterface` Protocol:

```python
# platform/real_hardware_interface.py
class RealHardwareInterface:
    def send(self, *, asset_id, action, params) -> ExecutionOutcome:
        try:
            match action:
                case ActionType.DISCHARGE_BATTERY:
                    self._client.write_register(0x4000, encode_discharge(params["power_kw"]))
                case ActionType.CHARGE_BATTERY:
                    self._client.write_register(0x4000, encode_charge(params["power_kw"]))
                ...
        except ModbusIOException:
            return ExecutionOutcome.TIMED_OUT
        except Exception:
            return ExecutionOutcome.FAILED
        return ExecutionOutcome.SUCCESS
```

Genuinely harder than the simulated version: real comms actually fail
(dropped connection, timeout) in ways the twin never does. Map every
realistic failure to the right `ExecutionOutcome` rather than letting an
exception escape uncaught.

## Phase 4 — wire it in

Add one field to `platform/settings.py::PlatformSettings`:

```python
hardware_mode: str = "simulated"   # "simulated" | "real"
```

And in `SystemComposition.__init__`, the same ternary shape already used
for Redis/Postgres/MLflow:

```python
self.telemetry_source = (
    RealTelemetrySource(...) if self.settings.hardware_mode == "real"
    else TwinTelemetrySource(self.twin)
)
self.hardware = (
    RealHardwareInterface(...) if self.settings.hardware_mode == "real"
    else SimulatedHardwareInterface(self.twin)
)
```

No other file changes. That's the payoff of the Protocol/port design
actually cashing out.

## Phase 5 — stage it before it's live

- Test against a **bench unit**, not the energized live site.
- Build the real adapters with an optional "dry run" mode that logs what it
  *would* write without writing it — cheap insurance while debugging
  register mappings.
- Get real physical safeguards independent of this software: an E-stop,
  the BMS's own hardware overcurrent protection, an electrician's sign-off.
  Every safety gate in this codebase is software (Policy/Safety/Risk) —
  a real deployment needs hardware-level protection too, as genuine
  defense in depth, not a replacement for it.

## Phase 6 — go live in two steps

1. **Telemetry-only first.** Wire up `RealTelemetrySource` alone, leave
   `HardwareInterface` simulated. Watch real data flow through
   Forecast/Anomaly/Decision and confirm it looks sane — this validates
   the register map with zero risk of a bad write to real equipment.
2. **Then enable execution** — ideally with `SafetyLimits` set *tighter*
   than the real design limits at first (smaller max charge/discharge
   power, narrower SOC band), so a mistake in the register mapping can
   only produce a small, safe action while confidence builds, not a large
   one.

## How data actually reaches you, once real hardware is live

See the "How data actually reaches you" section of the conversation this
doc came from, or trace it yourself: `RealTelemetrySource.read()` →
`TelemetryIngestionService.ingest()` → `EnergyState` → `StateStore` (Redis,
if `SOLAROPS_ENV=production`) → `GET /sites/{id}/state` → the dashboard's
Overview page. Nothing in that chain cares whether the reading originated
from a real inverter or the twin — that's the same "one published object,
read by everyone downstream" pattern from `ONBOARDING.md`.
