"""PolicyValidator — the operational-rules gate (Doc 8 §6.4, CESF §6).

Checks a planned action against the site's configurable ``Policy``. Distinct
from ``SafetyValidator``: this gate can be relaxed by an operator (maintenance
override, policy versions); the safety gate never can (A.1 of the Phase 5 brief).
"""

from __future__ import annotations

from solarops.safety.domain.command_intent import CommandIntent
from solarops.safety.domain.events import PolicyViolated
from solarops.safety.domain.policy_result import PolicyResult
from solarops.safety.domain.ports import PolicyRepository
from solarops.shared_kernel import ActionType, Clock, DomainEvent

# "maintenance mode (no charging)" — brief A.2, verbatim.
_MAINTENANCE_RESTRICTED_ACTIONS = frozenset({ActionType.CHARGE_BATTERY})


class PolicyValidator:
    def __init__(self, policy_repository: PolicyRepository, clock: Clock) -> None:
        self._policy_repository = policy_repository
        self._clock = clock

    def validate(self, intent: CommandIntent) -> tuple[PolicyResult, list[DomainEvent]]:
        policy = self._policy_repository.get_current(intent.site_id)

        if policy is None:
            # No policy configured -> fail closed. Same fail-safe spirit as
            # SafetyValidator: never assume an unconfigured site is permissive.
            violations = (f"no policy configured for {intent.site_id}",)
            return self._blocked(intent, violations)

        violations: list[str] = []

        if (
            policy.maintenance_mode
            and not policy.maintenance_override
            and intent.action in _MAINTENANCE_RESTRICTED_ACTIONS
        ):
            violations.append(f"maintenance mode is active: {intent.action} is not permitted")

        if intent.action is ActionType.SHED_LOAD:
            fraction = intent.params.get("fraction", 0.0)
            if fraction > policy.max_shed_fraction:
                violations.append(
                    f"requested shed fraction {fraction:.2f} exceeds "
                    f"policy ceiling {policy.max_shed_fraction:.2f}"
                )

        if intent.action is ActionType.CHARGE_BATTERY:
            target_soc = intent.params.get("target_soc")
            if target_soc is not None and target_soc > policy.max_battery_soc.value:
                violations.append(
                    f"target SOC {target_soc:.1f}% exceeds policy max "
                    f"{policy.max_battery_soc.value:.1f}%"
                )

        if intent.action is ActionType.DISCHARGE_BATTERY:
            target_soc = intent.params.get("target_soc")
            if target_soc is not None and target_soc < policy.min_battery_soc.value:
                violations.append(
                    f"target SOC {target_soc:.1f}% is below policy min "
                    f"{policy.min_battery_soc.value:.1f}%"
                )

        if not violations:
            result = PolicyResult(passed=True, evaluated_at=self._clock.now())
            return result, []

        return self._blocked(intent, tuple(violations))

    def _blocked(
        self, intent: CommandIntent, violations: tuple[str, ...]
    ) -> tuple[PolicyResult, list[DomainEvent]]:
        result = PolicyResult(passed=False, violations=violations, evaluated_at=self._clock.now())
        event = PolicyViolated(
            aggregate_id=str(intent.command_id),
            aggregate_type="Command",
            violations=violations,
        )
        return result, [event]
