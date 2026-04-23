"""Batch processing and progress reporting for simulation workflows.

Provides the :class:`BatchProcessor` class for running multiple simulations
sequentially or in parallel with detailed progress reporting including
percentage bars, ETA estimates, and per-simulation timing.

Example usage ::

    from src.core.batch_processor import BatchProcessor

    processor = BatchProcessor(max_workers=2)
    results = processor.run_batch(
        workflows=[workflow1, workflow2, workflow3],
        report_interval=5,  # seconds between progress updates
    )
"""

from __future__ import annotations

import logging
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Result of a single simulation run.

    Attributes
    ----------
    workflow_index : int
        Index of the workflow in the batch (0-based).
    success : bool
        Whether the simulation completed successfully.
    status_code : str | None
        Status code from the workflow (e.g., 'SUCCESS', 'FAILED').
    message : str | None
        Human-readable summary from the workflow.
    total_time_seconds : float
        Total wall-clock time for this simulation.
    errors : list[str]
        List of error messages if the simulation failed.
    """

    workflow_index: int
    success: bool = False
    status_code: Optional[str] = None
    message: Optional[str] = None
    total_time_seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


class ProgressReporter:
    """Console-based progress reporter with percentage bars and ETA estimates.

    Parameters
    ----------
    total : int
        Total number of items to process.
    verbose : bool, default=False
        Whether to print detailed per-item messages.
    """

    def __init__(self, total: int, verbose: bool = False) -> None:
        """Initialise the progress reporter."""
        self.total = total
        self.verbose = verbose
        self._completed = 0
        self._start_time = time.time()
        self._last_update_time = 0.0

    def update(self, index: int, message: str = "") -> None:
        """Update progress after completing an item.

        Parameters
        ----------
        index : int
            Index of the completed item (0-based).
        message : str, default=""
            Optional status message for this item.
        """
        self._completed += 1
        now = time.time()

        # Throttle output to once per second
        if now - self._last_update_time < 1.0:
            return
        self._last_update_time = now

        progress = self._completed / self.total * 100
        elapsed = now - self._start_time
        eta_seconds = (elapsed / self._completed) * (self.total - self._completed) if self._completed > 0 else 0.0

        # Draw progress bar
        bar_width = 40
        filled = int(bar_width * self._completed / self.total)
        bar = "\u2588" * filled + "\u2591" * (bar_width - filled)

        eta_str = f"{self._format_time(eta_seconds)} ETA" if self._completed > 0 else "calculating..."

        sys.stdout.write(
            f"\r[{bar}] {progress:.1f}% | "
            f"{self._completed}/{self.total} completed | "
            f"{self._format_time(elapsed)} elapsed | "
            f"{eta_str}"
        )
        sys.stdout.flush()

        if self.verbose and message:
            print(f"\n  [{self._completed}/{self.total}] {message}")

    def finish(self) -> None:
        """Finalize the progress report."""
        elapsed = time.time() - self._start_time
        print(f"\n\nBatch completed in {self._format_time(elapsed)}")
        sys.stdout.flush()

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as HH:MM:SS or MM:SS."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


class BatchProcessor:
    """Process multiple simulation workflows in batch mode.

    Supports both sequential and parallel execution with detailed progress
    reporting.  Workflows are executed either sequentially (one after another)
    or concurrently using a thread pool.

    Parameters
    ----------
    max_workers : int, default=1
        Maximum number of concurrent workers. Set to 1 for sequential mode.
    verbose : bool, default=False
        Enable detailed logging and progress messages.
    report_interval : float, default=5.0
        Minimum time interval (seconds) between progress report updates.
    """

    def __init__(
        self,
        max_workers: int = 1,
        verbose: bool = False,
        report_interval: float = 5.0,
    ) -> None:
        """Initialise the batch processor."""
        if max_workers < 1:
            raise ValueError("max_workers must be >= 1")

        self.max_workers = max_workers
        self.verbose = verbose
        self.report_interval = report_interval
        self._progress: Optional[ProgressReporter] = None

    def run_batch(
        self,
        workflows: list[Any],
        report_interval: Optional[float] = None,
    ) -> list[SimulationResult]:
        """Run multiple workflows and collect results.

        Parameters
        ----------
        workflows : list
            List of workflow objects (each must have a ``run()`` method).
        report_interval : float, optional
            Override the default report interval for this batch.

        Returns
        -------
        list[SimulationResult]
            Results for each workflow in order.
        """
        n = len(workflows)
        if n == 0:
            logger.warning("No workflows to process")
            return []

        if report_interval is not None:
            self.report_interval = report_interval

        # Set up progress reporter
        self._progress = ProgressReporter(n, verbose=self.verbose)

        results: list[SimulationResult] = [None] * n  # type: ignore[var-annotated]

        logger.info("Starting batch processing of %d workflows (max_workers=%d)", n, self.max_workers)

        if self.max_workers == 1:
            # Sequential mode
            for idx, wf in enumerate(workflows):
                start = time.time()
                try:
                    result = wf.run()
                    elapsed = time.time() - start
                    results[idx] = SimulationResult(
                        workflow_index=idx,
                        success=True,
                        status_code=result.get("status_code") if isinstance(result, dict) else None,
                        message=result.get("message", "") if isinstance(result, dict) else "Completed",
                        total_time_seconds=elapsed,
                    )
                    self._progress.update(idx + 1, f"Workflow {idx}: SUCCESS ({elapsed:.2f}s)")
                except Exception as exc:
                    elapsed = time.time() - start
                    results[idx] = SimulationResult(
                        workflow_index=idx,
                        success=False,
                        status_code="FAILED",
                        message=str(exc),
                        total_time_seconds=elapsed,
                        errors=[str(exc)],
                    )
                    self._progress.update(idx + 1, f"Workflow {idx}: FAILED ({elapsed:.2f}s) - {exc}")
        else:
            # Parallel mode
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures: dict[Future, int] = {}
                for idx, wf in enumerate(workflows):
                    future = executor.submit(self._run_single_workflow, wf)
                    futures[future] = idx

                # Collect results as they complete
                while futures:
                    done, _ = [], []
                    for f in list(futures.keys()):
                        if f.done():
                            done.append(f)

                    for future in done:
                        idx = futures.pop(future)
                        try:
                            result_data = future.result()
                            results[idx] = SimulationResult(
                                workflow_index=idx,
                                success=result_data["success"],
                                status_code=result_data.get("status_code"),
                                message=result_data.get("message", ""),
                                total_time_seconds=result_data.get("total_time_seconds", 0.0),
                                errors=result_data.get("errors", []),
                            )
                        except Exception as exc:
                            results[idx] = SimulationResult(
                                workflow_index=idx,
                                success=False,
                                status_code="FAILED",
                                message=str(exc),
                                total_time_seconds=0.0,
                                errors=[str(exc)],
                            )

                    # Update progress for all completed items
                    completed_count = sum(1 for r in results if r is not None)
                    self._progress.update(completed_count, f"{completed_count}/{n} complete")

        self._progress.finish()

        success_count = sum(1 for r in results if r and r.success)
        logger.info("Batch completed: %d/%d successful", success_count, n)

        return results

    def _run_single_workflow(self, workflow: Any) -> dict[str, Any]:
        """Run a single workflow and return result data.

        Parameters
        ----------
        workflow : Any
            Workflow object with a ``run()`` method.

        Returns
        -------
        dict
            Result dictionary with success status, timing, and messages.
        """
        start = time.time()
        try:
            result = workflow.run()
            elapsed = time.time() - start
            return {
                "success": True,
                "status_code": result.get("status_code") if isinstance(result, dict) else None,
                "message": result.get("message", "") if isinstance(result, dict) else "Completed",
                "total_time_seconds": elapsed,
                "errors": [],
            }
        except Exception as exc:
            elapsed = time.time() - start
            return {
                "success": False,
                "status_code": "FAILED",
                "message": str(exc),
                "total_time_seconds": elapsed,
                "errors": [str(exc)],
            }

    def get_summary(self, results: list[SimulationResult]) -> dict[str, Any]:
        """Generate a summary of batch processing results.

        Parameters
        ----------
        results : list[SimulationResult]
            Results from :meth:`run_batch`.

        Returns
        -------
        dict
            Summary dictionary with counts, total time, and per-workflow details.
        """
        success_count = sum(1 for r in results if r and r.success)
        failure_count = sum(1 for r in results if r and not r.success)
        total_time = sum(r.total_time_seconds for r in results if r)

        return {
            "total_workflows": len(results),
            "successful": success_count,
            "failed": failure_count,
            "total_time_seconds": round(total_time, 3),
            "success_rate": round(success_count / len(results) * 100 if results else 0, 1),
            "per_workflow": [
                {
                    "index": r.workflow_index,
                    "success": r.success,
                    "status_code": r.status_code,
                    "message": r.message,
                    "time_seconds": round(r.total_time_seconds, 3),
                    "errors": r.errors,
                }
                for r in results if r
            ],
        }
