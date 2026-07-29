from pydantic_settings import BaseSettings, SettingsConfigDict


class SiteConfig(BaseSettings):
    """Physical/operational parameters for a simulated C&I solar site."""

    model_config = SettingsConfigDict(env_prefix="SITE_", env_file=".env", extra="ignore")

    site_id: str = "site-001"

    solar_capacity_kw: float = 100.0
    solar_panel_efficiency: float = 0.20

    battery_capacity_kwh: float = 200.0
    battery_max_charge_kw: float = 50.0
    battery_max_discharge_kw: float = 50.0
    battery_min_soc_pct: float = 10.0
    battery_max_soc_pct: float = 95.0
    battery_starting_soc_pct: float = 50.0
    battery_max_temp_c: float = 45.0
    battery_round_trip_efficiency: float = 0.92

    inverter_rated_capacity_kw: float = 120.0
    inverter_efficiency: float = 0.97

    # Match GridModel's hardcoded constants (models/grid.py) exactly — these
    # exist so the Safety context's tolerance checks stay consistent with what
    # the twin actually produces, not a separately invented set of numbers.
    grid_nominal_voltage_v: float = 415.0
    grid_nominal_frequency_hz: float = 50.0
    grid_voltage_tolerance_v: float = 2.0
    grid_frequency_tolerance_hz: float = 0.05

    building_baseline_load_kw: float = 20.0
    building_peak_load_kw: float = 60.0

    update_interval_seconds: int = 5


class SimulatorConfig(BaseSettings):
    """Controls for the simulation clock itself, independent of site physics."""

    model_config = SettingsConfigDict(env_prefix="SIM_", env_file=".env", extra="ignore")

    random_seed: int | None = 42
    timezone_offset_hours: float = 0.0
