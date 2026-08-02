"""AutoDecisionCycleScheduler — no pytest-asyncio/anyio pytest mode is set up
in this project, so async behavior is driven with plain asyncio.run() inside
ordinary sync test functions rather than pulling in a new test dependency
for one file."""

from __future__ import annotations

import asyncio

from solarops.platform.auto_decision_cycle import AutoDecisionCycleScheduler


class FakeComposition:
    """Duck-types the one method the scheduler actually calls — matches this
    codebase's existing fake-object test style (e.g. FakeTelemetrySource)."""

    def __init__(self, fail_first_n: int = 0) -> None:
        self.call_count = 0
        self._fail_first_n = fail_first_n

    def run_decision_cycle(self):
        self.call_count += 1
        if self.call_count <= self._fail_first_n:
            raise RuntimeError("simulated transient failure")
        return None


def test_zero_interval_never_starts_a_task():
    composition = FakeComposition()
    scheduler = AutoDecisionCycleScheduler(composition, interval_seconds=0.0)
    scheduler.start()
    assert scheduler._task is None


def test_runs_the_cycle_after_the_interval_elapses():
    async def scenario():
        composition = FakeComposition()
        scheduler = AutoDecisionCycleScheduler(composition, interval_seconds=0.01)
        scheduler.start()
        # Generous margin over the interval — asyncio.to_thread()'s first
        # call pays a real, one-off thread-pool-executor startup cost that
        # can otherwise eat a tight budget on its own and flake this test.
        await asyncio.sleep(0.3)
        await scheduler.stop()
        return composition.call_count

    call_count = asyncio.run(scenario())
    assert call_count >= 2  # ran more than once — it's a loop, not a one-shot


def test_stop_cancels_cleanly_and_is_safe_to_call_when_never_started():
    async def scenario():
        composition = FakeComposition()
        scheduler = AutoDecisionCycleScheduler(composition, interval_seconds=0.01)
        scheduler.start()
        await asyncio.sleep(0.02)
        await scheduler.stop()
        assert scheduler._task is None
        await scheduler.stop()  # calling stop() again must not raise

        never_started = AutoDecisionCycleScheduler(composition, interval_seconds=5.0)
        await never_started.stop()  # stop() before start() must not raise either

    asyncio.run(scenario())


def test_a_failed_cycle_does_not_kill_the_loop():
    async def scenario():
        composition = FakeComposition(fail_first_n=1)
        scheduler = AutoDecisionCycleScheduler(composition, interval_seconds=0.01)
        scheduler.start()
        await asyncio.sleep(0.3)  # long enough for the failing tick plus at least one more
        await scheduler.stop()
        return composition.call_count

    call_count = asyncio.run(scenario())
    assert call_count >= 2  # survived the first failure and kept going
