"""SystemComposition — the one long-lived, wired instance of the whole system
that the API serves requests against (Phase 7a brief §1).

Composition root: builds one real ``DigitalTwin`` plus every context's real
application services (Telemetry, Forecast, Anomaly, Decision, Execution),
mirroring exactly what ``scripts/run_*.py`` each do independently,
consolidated into one persistent bundle instead of a one-shot script.
Building this is itself just calling existing constructors and existing
service methods (the Solar forecaster training gate from 6a, the
Rule/Statistical detector gate from 6b) — no new domain logic, same as every
other file under ``platform/``.
"""

from __future__ import annotations

import contextlib
import threading
import time
from collections import deque
from datetime import UTC, datetime, timedelta

import redis
from sqlalchemy import create_engine

from solarops.anomaly.application.evaluation.anomaly_evaluator import AnomalyEvaluator
from solarops.anomaly.application.rule_detector import RuleDetector
from solarops.anomaly.application.scoring_service import AnomalyScoringService
from solarops.anomaly.application.statistical_detector import StatisticalDetector
from solarops.anomaly.application.training.detector_training_service import (
    DetectorTrainingService,
)
from solarops.anomaly.domain.events import AnomalyDetected
from solarops.anomaly.infrastructure.detector_registry import (
    InMemoryDetectorRegistry,
    MLflowDetectorRegistry,
)
from solarops.anomaly.infrastructure.in_memory_alert_publisher import InMemoryAlertPublisher
from solarops.anomaly.infrastructure.in_memory_anomaly_repository import (
    InMemoryAnomalyRepository,
)
from solarops.decision.application.rule_based_optimiser import RuleBasedOptimiser
from solarops.decision.domain.decision_context import DecisionContext
from solarops.decision.domain.ranked_recommendations import RankedRecommendations
from solarops.decision.infrastructure.config import RuleEngineConfig
from solarops.execution.application.approval_engine import ApprovalEngine
from solarops.execution.application.command_planner import CommandPlanner
from solarops.execution.application.execution_manager import ExecutionManager
from solarops.execution.application.execution_pipeline import ExecutionPipeline
from solarops.execution.application.verification_service import VerificationService
from solarops.execution.domain.command import Command
from solarops.execution.infrastructure.in_memory_approval_request_repository import (
    InMemoryApprovalRequestRepository,
)
from solarops.execution.infrastructure.in_memory_audit_log import InMemoryAuditLog
from solarops.execution.infrastructure.in_memory_command_repository import (
    InMemoryCommandRepository,
)
from solarops.execution.infrastructure.postgres_audit_log import PostgresAuditLog
from solarops.forecast.application.evaluation.forecast_evaluator import ForecastEvaluator
from solarops.forecast.application.forecasting_service import ForecastingService
from solarops.forecast.application.solar_generation_forecaster import SolarGenerationForecaster
from solarops.forecast.application.training.training_service import TrainingService
from solarops.forecast.domain.events import ForecastGenerated
from solarops.forecast.domain.exceptions import NoRegisteredModel
from solarops.forecast.domain.forecast_kind import ForecastKind
from solarops.forecast.infrastructure.in_memory_forecast_repository import (
    InMemoryForecastRepository,
)
from solarops.forecast.infrastructure.model_registry import (
    InMemoryModelRegistry,
    MLflowModelRegistry,
)
from solarops.forecast.infrastructure.models.solar_baseline import SolarBaseline
from solarops.observability.metrics import (
    PIPELINE_METRICS,
    anomalies_detected_total,
    forecasts_produced_total,
    recommendation_latency_seconds,
    registered_model_versions,
    telemetry_updates_total,
)
from solarops.platform.anomaly_wiring import (
    build_anomaly_config,
    build_twin_fault_scenario_source,
)
from solarops.platform.decision_wiring import build_operating_constraints
from solarops.platform.forecast_wiring import (
    build_forecast_config,
    build_twin_benchmark_scenario_source,
)
from solarops.platform.forecast_wiring import (
    build_twin_historical_data_source as build_forecast_historical_data_source,
)
from solarops.platform.notifications import NullNotifier, WhatsAppNotifier
from solarops.platform.safety_wiring import build_policy, build_safety_limits
from solarops.platform.settings import PlatformSettings
from solarops.platform.twin_hardware_interface import SimulatedHardwareInterface
from solarops.platform.twin_telemetry_source import TwinTelemetrySource
from solarops.safety.application.policy_validator import PolicyValidator
from solarops.safety.application.risk_assessor import RiskAssessor
from solarops.safety.application.safety_validator import SafetyValidator
from solarops.safety.infrastructure.in_memory_policy_repository import InMemoryPolicyRepository
from solarops.safety.infrastructure.static_safety_limits_provider import (
    StaticSafetyLimitsProvider,
)
from solarops.shared_kernel import Clock, GridStatus, SiteId, SystemClock
from solarops.simulation.domain.digital_twin import DigitalTwin
from solarops.simulation.infrastructure.config import SimulatorConfig, SiteConfig
from solarops.telemetry.application.ingestion_service import TelemetryIngestionService
from solarops.telemetry.application.state_manager import StateManager
from solarops.telemetry.domain.energy_state import EnergyState
from solarops.telemetry.domain.events import TelemetryIngested
from solarops.telemetry.infrastructure.in_memory_state_store import InMemoryStateStore
from solarops.telemetry.infrastructure.redis_state_store import RedisStateStore

__all__ = ["SystemComposition", "build_system_composition"]

_HISTORY_LENGTH = 50

# Phase 6d: how recent an anomaly must be to count toward confidence
# estimation's "is something wrong right now" signal — deliberately shorter
# than the 24h window the /anomalies API endpoint displays for humans, since
# this answers a different question (current reliability of the reasoning
# inputs, not "what happened recently").
_ANOMALY_RELEVANCE_WINDOW = timedelta(minutes=15)



class SystemComposition:
    """One process-lifetime instance of the whole wired system."""

    def __init__(
        self, site_config: SiteConfig, clock: Clock, settings: PlatformSettings | None = None
    ) -> None:
        self.site_id = SiteId(site_config.site_id)
        self.site_config = site_config
        self.clock = clock
        self.settings = settings or PlatformSettings()
        # Guards run_decision_cycle() so a manual click (POST /decision-cycle,
        # handled on its own thread) and an automatic scheduler tick never run
        # concurrently against the same in-memory state/repositories.
        self._decision_cycle_lock = threading.Lock()

        # --- Simulation + Telemetry (Phases 2-3) ---
        self.twin = DigitalTwin(
            site_config=site_config,
            simulator_config=SimulatorConfig(),
            start_time=datetime.now(UTC),
        )
        self.telemetry_source = TwinTelemetrySource(self.twin)
        # check_staleness=False: the twin's simulated clock and the real
        # clock are intentionally independent (the twin only advances when
        # ticked, not with real elapsed time) — comparing them would flag
        # every reading "stale"/offline the moment more than
        # staleness_threshold of real time passes between decision cycles,
        # which is virtually every real-world click. A twin reading is
        # synchronous and always current by construction; this check only
        # means something once a real hardware source is wired in instead.
        self.ingestion = TelemetryIngestionService(
            self.telemetry_source, clock, check_staleness=False
        )
        self.state_store = (
            RedisStateStore(redis.Redis.from_url(self.settings.redis_url))
            if self.settings.use_real_infra
            else InMemoryStateStore()
        )
        self.state_manager = StateManager(self.state_store)
        self._history: deque[EnergyState] = deque(maxlen=_HISTORY_LENGTH)

        # --- Safety wiring (Phase 5) — the numbers Decision/Execution both read ---
        self.policy = build_policy(site_config)
        self.safety_limits = build_safety_limits(site_config)
        self.policy_repository = InMemoryPolicyRepository()
        self.policy_repository.save(self.policy)
        self.safety_limits_provider = StaticSafetyLimitsProvider(self.safety_limits)

        # --- Forecast (6a): Solar registered via the real gate; Load/Battery
        # are deliberately not trained here — 6a already established neither
        # passes, and re-running that training on every boot would be slow
        # and pointless. Reflected honestly (never faked) by /forecasts
        # simply not finding them registered. ---
        self.forecast_config = build_forecast_config(site_config)
        self.forecast_repository = InMemoryForecastRepository()
        self.forecast_registry = (
            MLflowModelRegistry(self.settings.mlflow_tracking_uri)
            if self.settings.use_real_infra
            else InMemoryModelRegistry()
        )
        forecast_history_source = build_forecast_historical_data_source(
            site_config, self.forecast_config
        )
        forecast_scenario_source = build_twin_benchmark_scenario_source(
            site_config, self.forecast_config
        )
        forecast_evaluator = ForecastEvaluator(forecast_scenario_source, self.forecast_config)
        forecast_training_service = TrainingService(forecast_evaluator, self.forecast_registry)
        forecast_training_service.evaluate_and_register(
            SolarBaseline(
                capacity_kw=self.forecast_config.solar_capacity_kw,
                resolution_minutes=self.forecast_config.resolution_minutes,
            )
        )
        forecasting_service = ForecastingService(self.forecast_repository, clock)
        self.solar_forecaster = SolarGenerationForecaster(
            forecasting_service,
            self.forecast_registry,
            forecast_history_source,
            self.forecast_config,
        )

        # --- Anomaly (6b): Rule + Statistical registered via the real
        # per-type gate (6b cleanup pass) — Isolation Forest is not
        # registered here (never passed the gate). ---
        self.anomaly_config = build_anomaly_config(site_config)
        self.anomaly_repository = InMemoryAnomalyRepository()
        self.anomaly_registry = (
            MLflowDetectorRegistry(self.settings.mlflow_tracking_uri)
            if self.settings.use_real_infra
            else InMemoryDetectorRegistry()
        )
        self.alert_publisher = InMemoryAlertPublisher()
        anomaly_scenario_source = build_twin_fault_scenario_source(site_config)
        anomaly_evaluator = AnomalyEvaluator(anomaly_scenario_source, self.anomaly_config)
        detector_training_service = DetectorTrainingService(
            anomaly_evaluator, self.anomaly_registry
        )
        detector_training_service.evaluate_and_register(RuleDetector(self.anomaly_config))
        detector_training_service.evaluate_and_register(StatisticalDetector(self.anomaly_config))
        self.anomaly_scoring_service = AnomalyScoringService(
            self.anomaly_registry, self.anomaly_repository, self.anomaly_config
        )

        # --- Decision (6c) ---
        self.operating_constraints = build_operating_constraints(self.policy, self.safety_limits)
        self.decision_engine = RuleBasedOptimiser(RuleEngineConfig(), clock)

        # --- Execution (Phase 5) ---
        self.hardware = SimulatedHardwareInterface(self.twin)
        # Phase 8 marked seam: Command and ApprovalRequest are rich
        # state-machine aggregates (Command alone carries 6 nested
        # gate-outcome objects behind a strict forward-only transition API,
        # with no "rehydrate to arbitrary state" path). Persisting them
        # faithfully needs transition-replay logic that couldn't be verified
        # against a real Postgres in the environment this was built in — so
        # they stay in-memory rather than ship an unverified reconstruction
        # of a safety-critical aggregate. Disclosed, not hidden: an API
        # restart still loses in-flight commands/approvals even with
        # SOLAROPS_ENV=production.
        self.approval_repository = InMemoryApprovalRequestRepository()
        self.command_repository = InMemoryCommandRepository()
        self.audit_log = (
            PostgresAuditLog(create_engine(self.settings.postgres_dsn))
            if self.settings.use_real_infra
            else InMemoryAuditLog()
        )
        self.notifier = (
            WhatsAppNotifier(self.settings.whatsapp_phone, self.settings.whatsapp_api_key)
            if self.settings.whatsapp_configured
            else NullNotifier()
        )
        # None until the first reading — a first reading isn't a "change",
        # so it must never itself trigger notify_grid_status_changed().
        self._last_grid_status: GridStatus | None = None

        self.execution_pipeline = ExecutionPipeline(
            command_planner=CommandPlanner(clock),
            policy_validator=PolicyValidator(self.policy_repository, clock),
            safety_validator=SafetyValidator(self.safety_limits_provider, self.state_store, clock),
            risk_assessor=RiskAssessor(clock),
            approval_engine=ApprovalEngine(self.approval_repository, clock),
            execution_manager=ExecutionManager(self.hardware, clock),
            verification_service=VerificationService(self.state_manager, clock),
            command_repository=self.command_repository,
            approval_repository=self.approval_repository,
            audit_log=self.audit_log,
            state_store=self.state_store,
            policy_repository=self.policy_repository,
            safety_limits_provider=self.safety_limits_provider,
            clock=clock,
            telemetry_refresh=self.refresh_telemetry,
            metrics=PIPELINE_METRICS,
            notifier=self.notifier,
        )

        self.refresh_telemetry()  # a real reading before any request arrives

    def refresh_telemetry(self) -> EnergyState:
        """Pull one fresh reading, update state, and let it flow through the
        currently-registered forecaster/detectors — exactly the calls
        ``scripts/run_*.py`` already make, just repeatable per-request instead
        of scripted once.

        Phase 7c: this already captured every event these three calls
        produce — ``telemetry_events``/the forecaster's own return value/the
        scorer's own return value — and threw all of them away. Recording
        metrics here is just no longer discarding data already produced,
        not new instrumentation inside Telemetry/Forecast/Anomaly themselves.
        """
        state, telemetry_events = self.ingestion.ingest(self.site_id)
        self.state_manager.update(state)
        history_before = list(self._history)
        self._history.append(state)

        for event in telemetry_events:
            if isinstance(event, TelemetryIngested):
                telemetry_updates_total.inc()

        with contextlib.suppress(NoRegisteredModel):
            _forecast, forecast_event = self.solar_forecaster.forecast(state)
            if isinstance(forecast_event, ForecastGenerated):
                forecasts_produced_total.labels(kind=forecast_event.kind.value).inc()

        _anomalies, anomaly_events = self.anomaly_scoring_service.score(state, history_before)
        for event in anomaly_events:
            if isinstance(event, AnomalyDetected):
                anomalies_detected_total.labels(
                    anomaly_type=event.anomaly_type.value, severity=event.severity.value
                ).inc()
                self.notifier.notify_anomaly_detected(event)

        # None on the very first reading — that's not a "change", so it must
        # never itself trigger a notification.
        if self._last_grid_status is not None and self._last_grid_status is not state.grid_status:
            self.notifier.notify_grid_status_changed(self._last_grid_status, state.grid_status)
        self._last_grid_status = state.grid_status

        return state

    def refresh_model_version_gauges(self) -> None:
        """Phase 7c: computed on scrape (called from the /metrics route),
        not incremented reactively — reads whatever's actually registered
        right now from the same registries every other read endpoint uses."""
        registered_model_versions.clear()
        for kind in ForecastKind:
            model = self.forecast_registry.get_current(kind)
            if model is not None:
                registered_model_versions.labels(
                    context="forecast", model_name=model.name, version=model.version
                ).set(1)
        for detector in self.anomaly_registry.get_active():
            registered_model_versions.labels(
                context="anomaly", model_name=detector.name, version=detector.version
            ).set(1)

    def current_decision_context(self) -> DecisionContext | None:
        """Build a DecisionContext from whatever is currently on hand — read-only,
        no refresh, no side effects. Returns None if telemetry has never landed.

        Phase 6d: this is the composition-root pass-through the confidence
        brief asked for — queries the anomaly repository it already legitimately
        holds and hands Decision a plain count, never an Anomaly/AnomalyType
        object, so Decision still never imports the Anomaly context.
        """
        state = self.state_manager.get_current(self.site_id)
        if state is None:
            return None
        available_forecasts = {}
        solar_forecast = self.forecast_repository.get_latest(
            self.site_id, ForecastKind.SOLAR_GENERATION
        )
        if solar_forecast is not None:
            available_forecasts[ForecastKind.SOLAR_GENERATION] = solar_forecast
        recent_anomalies = self.anomaly_repository.list_recent(
            self.site_id, since=self.clock.now() - _ANOMALY_RELEVANCE_WINDOW
        )
        return DecisionContext(
            energy_state=state,
            operating_constraints=self.operating_constraints,
            available_forecasts=available_forecasts,
            active_anomaly_count=len(recent_anomalies),
        )

    def recommend(self, context: DecisionContext) -> RankedRecommendations:
        """The one place ``decision_engine.recommend()`` is actually called
        from the API/composition side — both this and the plain read-only
        GET /recommendations route go through here, so recommendation
        latency is timed once, not duplicated at each call site."""
        started_at = time.perf_counter()
        ranked = self.decision_engine.recommend(context)
        recommendation_latency_seconds.observe(time.perf_counter() - started_at)
        return ranked

    def run_decision_cycle(self) -> tuple[RankedRecommendations, Command]:
        """Refresh telemetry, reason over it, and run the top recommendation
        through the real Phase 5 pipeline — the engine never touches the twin
        or builds a command itself (ADR-010); this is the pipeline doing that,
        exactly as every prior script already demonstrates.

        Locked (``_decision_cycle_lock``) so a manual trigger and an
        automatic scheduler tick (``platform/auto_decision_cycle.py``) can
        never run concurrently against the same in-memory state — whichever
        arrives second simply waits its turn rather than racing.
        """
        with self._decision_cycle_lock:
            self.refresh_telemetry()
            context = self.current_decision_context()
            assert context is not None, "refresh_telemetry() just ran; state must exist"

            ranked = self.recommend(context)
            command = self.execution_pipeline.run(ranked.top)
            self.notifier.notify_decision_cycle_result(ranked.top, command)
            return ranked, command


def build_system_composition(
    site_config: SiteConfig | None = None, settings: PlatformSettings | None = None
) -> SystemComposition:
    return SystemComposition(site_config or SiteConfig(), SystemClock(), settings)
