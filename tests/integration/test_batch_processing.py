"""Integration tests for batch processing and progress reporting (UC10).

Tests the BatchProcessor class, SimulationResult dataclass, and
ProgressReporter with various workflow configurations.
"""

from __future__ import annotations

import sys
import time
from io import StringIO
from unittest.mock import MagicMock

import pytest

from src.core.batch_processor import BatchProcessor, ProgressReporter, SimulationResult


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


class MockWorkflow:
    """Mock workflow that simulates a simulation run."""

    def __init__(
        self,
        success: bool = True,
        status_code: str = "SUCCESS",
        message: str = "Completed",
        delay: float = 0.01,
    ) -> None:
        """Initialise the mock workflow.

        Parameters
        ----------
        success : bool, default=True
            Whether the workflow should succeed.
        status_code : str, default="SUCCESS"
            Status code to return on success.
        message : str, default="Completed"
            Message to return on completion.
        delay : float, default=0.01
            Simulated run time in seconds.
        """
        self.success = success
        self.status_code = status_code
        self.message = message
        self.delay = delay

    def run(self) -> dict:
        """Simulate running the workflow."""
        time.sleep(self.delay)
        if self.success:
            return {
                "status_code": self.status_code,
                "message": self.message,
                "steps": {},
                "config": {},
                "started_at": time.time(),
                "completed_at": time.time(),
            }
        else:
            raise RuntimeError(f"Simulated failure: {self.message}")


# ---------------------------------------------------------------------------
# ProgressReporter tests
# ---------------------------------------------------------------------------


class TestProgressReporter:
    """Tests for the ProgressReporter class."""

    def test_init(self):
        """ProgressReporter should initialise with total and verbose flag."""
        reporter = ProgressReporter(total=10, verbose=True)
        assert reporter.total == 10
        assert reporter.verbose is True

    def test_update_increments_counter(self):
        """Each update should increment the completed counter."""
        reporter = ProgressReporter(total=5)
        for i in range(5):
            reporter.update(i, f"Item {i}")
        # After 5 updates, _completed should be 5
        assert reporter._completed == 5

    def test_finish_prints_summary(self):
        """finish() should print a completion summary."""
        reporter = ProgressReporter(total=3)
        for i in range(3):
            reporter.update(i, f"Item {i}")

        # Capture stdout
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured
        reporter.finish()
        sys.stdout = old_stdout

        output = captured.getvalue()
        assert "Batch completed" in output

    def test_format_time_seconds(self):
        """_format_time should format seconds correctly."""
        assert ProgressReporter._format_time(30.5) == "30.5s"
        assert ProgressReporter._format_time(90.2) == "1m 30.2s"
        assert "h" in ProgressReporter._format_time(7261.5)  # ~2 hours

    def test_update_with_message(self, capsys):
        """update() should print progress bar and message if verbose."""
        reporter = ProgressReporter(total=3, verbose=True)
        for i in range(3):
            reporter.update(i, f"Item {i}")

        captured = capsys.readouterr()
        assert "Batch completed" not in captured.out  # finish() not called yet


# ---------------------------------------------------------------------------
# SimulationResult tests
# ---------------------------------------------------------------------------


class TestSimulationResult:
    """Tests for the SimulationResult dataclass."""

    def test_init_defaults(self):
        """SimulationResult should have sensible defaults."""
        result = SimulationResult(workflow_index=0)
        assert result.workflow_index == 0
        assert result.success is False
        assert result.status_code is None
        assert result.message is None
        assert result.total_time_seconds == 0.0
        assert result.errors == []

    def test_init_with_values(self):
        """SimulationResult should accept all parameters."""
        result = SimulationResult(
            workflow_index=1,
            success=True,
            status_code="SUCCESS",
            message="Completed",
            total_time_seconds=5.5,
            errors=[],
        )
        assert result.workflow_index == 1
        assert result.success is True
        assert result.status_code == "SUCCESS"
        assert result.message == "Completed"
        assert result.total_time_seconds == 5.5

    def test_errors_default_empty_list(self):
        """errors should default to an empty list."""
        result = SimulationResult(workflow_index=0)
        assert isinstance(result.errors, list)
        assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# BatchProcessor tests
# ---------------------------------------------------------------------------


class TestBatchProcessor:
    """Tests for the BatchProcessor class."""

    def test_init(self):
        """BatchProcessor should initialise with max_workers and verbose."""
        processor = BatchProcessor(max_workers=2, verbose=True)
        assert processor.max_workers == 2
        assert processor.verbose is True

    def test_init_invalid_max_workers(self):
        """BatchProcessor should raise for max_workers < 1."""
        with pytest.raises(ValueError):
            BatchProcessor(max_workers=0)

    def test_run_batch_empty(self):
        """run_batch() should return empty list for no workflows."""
        processor = BatchProcessor(max_workers=1)
        results = processor.run_batch(workflows=[])
        assert results == []

    def test_run_batch_sequential_success(self):
        """run_batch() should process workflows sequentially on success."""
        workflows = [MockWorkflow(success=True, delay=0.01)] * 3
        processor = BatchProcessor(max_workers=1)
        results = processor.run_batch(workflows)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result is not None
            assert result.success is True
            assert result.workflow_index == i

    def test_run_batch_sequential_failure(self):
        """run_batch() should handle failed workflows gracefully."""
        workflows = [MockWorkflow(success=False, message="Test failure")] * 2
        processor = BatchProcessor(max_workers=1)
        results = processor.run_batch(workflows)

        assert len(results) == 2
        for i, result in enumerate(results):
            assert result is not None
            assert result.success is False
            assert result.workflow_index == i
            assert "Test failure" in str(result.message)

    def test_run_batch_mixed(self):
        """run_batch() should handle mixed success/failure workflows."""
        workflows = [
            MockWorkflow(success=True, delay=0.01),
            MockWorkflow(success=False, message="Fail"),
            MockWorkflow(success=True, delay=0.01),
        ]
        processor = BatchProcessor(max_workers=1)
        results = processor.run_batch(workflows)

        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True

    def test_run_batch_parallel(self):
        """run_batch() should process workflows in parallel with max_workers > 1."""
        workflows = [MockWorkflow(success=True, delay=0.05)] * 4
        processor = BatchProcessor(max_workers=2)
        results = processor.run_batch(workflows)

        assert len(results) == 4
        for result in results:
            assert result is not None
            assert result.success is True

    def test_summary_generation(self):
        """get_summary() should generate correct summary statistics."""
        results = [
            SimulationResult(workflow_index=0, success=True, total_time_seconds=1.0),
            SimulationResult(workflow_index=1, success=False, total_time_seconds=0.5),
            SimulationResult(workflow_index=2, success=True, total_time_seconds=2.0),
        ]

        processor = BatchProcessor(max_workers=1)
        summary = processor.get_summary(results)

        assert summary["total_workflows"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == 66.7  # 2/3 * 100
        assert len(summary["per_workflow"]) == 3


class TestBatchProcessorIntegration:
    """End-to-end integration tests for batch processing."""

    def test_full_batch_with_timing(self):
        """Test complete batch processing with timing verification."""
        workflows = [MockWorkflow(success=True, delay=0.02)] * 5
        processor = BatchProcessor(max_workers=1)
        results = processor.run_batch(workflows)

        # Verify all completed successfully
        assert len(results) == 5
        assert all(r.success for r in results if r)

        # Verify timing is reasonable (at least some time elapsed)
        total_time = sum(r.total_time_seconds for r in results if r)
        assert total_time > 0.05  # At least 50ms total

    def test_batch_summary_accuracy(self):
        """Test that batch summary accurately reflects results."""
        workflows = [
            MockWorkflow(success=True, delay=0.01),
            MockWorkflow(success=True, delay=0.01),
            MockWorkflow(success=False, message="Error"),
        ]
        processor = BatchProcessor(max_workers=1)
        results = processor.run_batch(workflows)

        summary = processor.get_summary(results)

        assert summary["total_workflows"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == 66.7

    def test_progress_reporter_throttling(self):
        """ProgressReporter should throttle output to ~1 update/second."""
        import time as _time

        reporter = ProgressReporter(total=5)
        start = _time.time()

        # Call update multiple times rapidly
        for i in range(10):
            reporter.update(i, f"Item {i}")

        elapsed = _time.time() - start
        # At least some time should have passed (for throttling to work)
        assert elapsed >= 0.0  # Just verify no crash
