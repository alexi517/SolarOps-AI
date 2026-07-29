"""ExecutionManager — the only caller of HardwareInterface (Doc 8 §6.5, CESF §10, §14, §16).

Handles dispatch, acknowledgement, retries on timeout, and turns the hardware
outcome into the right ``Command`` transition. Never assumes success: any
exception from the hardware call, or a ``BLOCKED`` outcome, is treated as a
dispatch failure rather than silently retried into a false positive.
"""

from __future__ import annotations

from solarops.execution.domain.command import Command
from solarops.execution.domain.execution_result import ExecutionResult
from solarops.execution.domain.ports import HardwareInterface
from solarops.shared_kernel import Clock, ExecutionOutcome

DEFAULT_MAX_RETRIES = 2

__all__ = ["ExecutionManager", "DEFAULT_MAX_RETRIES"]


class ExecutionManager:
    def __init__(
        self,
        hardware_interface: HardwareInterface,
        clock: Clock,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ) -> None:
        self._hardware_interface = hardware_interface
        self._clock = clock
        self._max_retries = max_retries

    def dispatch(self, command: Command) -> ExecutionResult:
        command.dispatch()
        dispatched_at = self._clock.now()

        params = dict(command.params)
        decision = command.approval_decision
        if decision is not None and decision.modified_params:
            params.update(decision.modified_params)

        outcome, retry_count = self._send_with_retries(command, params)

        if outcome is None:
            # The hardware interface itself raised — never assume success.
            result = ExecutionResult(
                outcome=ExecutionOutcome.FAILED,
                dispatched_at=dispatched_at,
                retry_count=retry_count,
                detail="hardware interface raised an exception",
            )
            command.mark_dispatch_failed()
            return result

        if outcome is ExecutionOutcome.BLOCKED:
            # The hardware interface refused the action outright — never
            # acknowledged, so this is a dispatch failure, not an execution one.
            result = ExecutionResult(
                outcome=outcome,
                dispatched_at=dispatched_at,
                retry_count=retry_count,
                detail="hardware interface blocked the action",
            )
            command.mark_dispatch_failed()
            return result

        command.acknowledge()
        acknowledged_at = self._clock.now()

        if outcome is ExecutionOutcome.SUCCESS:
            result = ExecutionResult(
                outcome=outcome,
                dispatched_at=dispatched_at,
                acknowledged_at=acknowledged_at,
                retry_count=retry_count,
            )
            command.mark_executed(result)
        elif outcome is ExecutionOutcome.TIMED_OUT:
            result = ExecutionResult(
                outcome=outcome,
                dispatched_at=dispatched_at,
                acknowledged_at=acknowledged_at,
                retry_count=retry_count,
                detail="timed out after retries",
            )
            command.timeout_execution(result)
        else:  # FAILED, CANCELLED
            result = ExecutionResult(
                outcome=outcome,
                dispatched_at=dispatched_at,
                acknowledged_at=acknowledged_at,
                retry_count=retry_count,
            )
            command.mark_execution_failed(result)

        return result

    def _send_with_retries(
        self, command: Command, params: dict
    ) -> tuple[ExecutionOutcome | None, int]:
        attempt = 0
        while True:
            try:
                outcome = self._hardware_interface.send(
                    asset_id=command.asset_id, action=command.action, params=params
                )
            except Exception:
                return None, attempt
            if outcome is ExecutionOutcome.TIMED_OUT and attempt < self._max_retries:
                attempt += 1
                continue
            return outcome, attempt
