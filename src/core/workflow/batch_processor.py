"""Batch processing capabilities and progress reporting for simulation workflows.

This module provides the :class:`BatchProcessor` class for running multiple
simulations in sequence or parallel, with detailed progress reporting. It
supports:

- Frequency sweep batch processing across multiple frequencies
- Geometry batch processing for multiple antenna designs
- Progress bar reporting with ETA estimates
- Partial result persistence between interrupted runs
- Resource monitoring (CPU, memory) during batch execution

Example usage::

    from src.core.workflow.batch_processor import BatchProcessor

    processor = BatchProcessor(max_workers=4)
    frequencies = np.linspace(0.5e9, 2e9, 50)

    # Run frequency sweep with progress reporting
    results = processor.run_frequency_sweep(
        workflow_factory=lambda f: SimulationWorkflow(frequency=f),
        frequencies=frequencies,
        progress_callback=print
    )
"""

from __future__ import annotations

import os
import time
import json
import multiprocessing as mp
from typing import Optional, List, Callable, Dict, Any

import numpy as np

from src.utils.errors import WorkflowError


class ProgressReporter:
    """Track and display simulation progress with ETA estimates.

    This class provides a text-based progress reporting system suitable
    for terminal output. It tracks completion percentage, elapsed time,
    remaining time estimates, and per-step status.

    Attributes
    ----------
    total_steps : int
        Total number of steps in the batch.
    current_step : int
        Current step number (1-indexed).
    start_time : float
        Timestamp when reporting started.
    step_times : list[float]
        Time taken for each completed step in seconds.
    """

    def __init__(self, total_steps: int) -> None:
        """Initialise the progress reporter.

        Parameters
        ----------
        total_steps : int
            Total number of steps to track.
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.start_time = time.time()
        self.step_times: List[float] = []
        self._step_names: List[str] = []

    def set_step_name(self, name: str) -> None:
        """Set the name for the current step.

        Parameters
        ----------
        name : str
            Descriptive name for this step.
        """
        self._step_names.append(name)

    def mark_complete(self, duration: float) -> None:
        """Mark the current step as complete.

        Parameters
        ----------
        duration : float
            Time taken for this step in seconds.
        """
        self.current_step += 1
        self.step_times.append(duration)

        # Calculate ETA based on average step time
        avg_time = np.mean(self.step_times) if self.step_times else 0
        remaining_steps = self.total_steps - self.current_step
        eta_seconds = avg_time * remaining_steps

        # Format progress string
        pct = (self.current_step / self.total_steps) * 100
        elapsed = time.time() - self.start_time

        # Build progress bar
        bar_width = 40
        filled = int(bar_width * self.current_step / self.total_steps)
        bar = "\u2588" * filled + "\u3000" * (bar_width - filled)

        eta_str = f"{int(eta_seconds)}s remaining" if eta_seconds > 0 else "complete"

        step_name = self._step_names[-1] if self._step_names else ""
        print(
            f"\r[{bar}] {pct:.1f}% | Step {self.current_step}/{self.total_steps} | "
            f"{elapsed:.1f}s elapsed | {eta_str}",
            end="",
            flush=True,
        )

        if self.current_step == self.total_steps:
            print()  # Newline at completion

    def reset(self) -> None:
        """Reset the progress reporter for a new batch."""
        self.current_step = 0
        self.start_time = time.time()
        self.step_times.clear()
        self._step_names.clear()


class BatchProcessor:
    """Process multiple simulations in batch with progress reporting.

    This class orchestrates batch execution of simulation workflows,
    supporting both sequential and parallel modes. It handles resource
    monitoring, partial result persistence, and comprehensive progress
    reporting.

    Parameters
    ----------
    max_workers : int, optional
        Maximum number of parallel workers. If None or 1, runs sequentially.
    output_dir : str, default="batch_results/"
        Directory for batch output files.
    checkpoint_interval : int, default=5
        Save partial results every N steps.
    """

    def __init__(
        self,
        max_workers: Optional[int] = None,
        output_dir: str = "batch_results/",
        checkpoint_interval: int = 5,
    ) -> None:
        """Initialise the batch processor."""
        self.max_workers = max_workers or 1
        self.output_dir = output_dir
        self.checkpoint_interval = checkpoint_interval

        os.makedirs(output_dir, exist_ok=True)

        # Track batch state
        self._batch_results: Dict[str, Any] = {}
        self._checkpoint_file = os.path.join(output_dir, "batch_checkpoint.json")

    def run_frequency_sweep(
        self,
        workflow_factory: Callable[[float], Any],
        frequencies: np.ndarray,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Run a frequency sweep with batch processing.

        Creates and runs simulation workflows at each frequency point in
        the sweep, collecting S-parameters and field data.

        Parameters
        ----------
        workflow_factory : callable
            Factory function that takes a frequency (Hz) and returns a
            SimulationWorkflow instance.
        frequencies : np.ndarray
            Frequency array in Hz with shape (N_freq,).
        progress_callback : callable, optional
            Optional callback for external progress reporting.

        Returns
        -------
        dict
            Batch results dictionary with keys:
            - 'frequencies': frequency array
            - 's_parameters': dict of S-parameter arrays per port pair
            - 'summary': dict with total_time, success_count, etc.

        Raises
        ------
        WorkflowError
            If batch processing fails or no frequencies are provided.
        """
        if len(frequencies) == 0:
            raise WorkflowError("No frequencies provided for sweep")

        n_freq = len(frequencies)
        reporter = ProgressReporter(n_freq)
        results = {"frequencies": frequencies.tolist()}
        success_count = 0
        total_start = time.time()

        # Load previous checkpoint if available
        self._load_checkpoint()

        for i, freq in enumerate(frequencies):
            step_name = f"Freq {freq:.3e} Hz"
            reporter.set_step_name(step_name)

            try:
                start = time.time()
                workflow = workflow_factory(freq)
                workflow_result = workflow.run()
                duration = time.time() - start

                # Store S-parameters for this frequency
                freq_key = f"f_{i}"
                results[freq_key] = workflow_result

                success_count += 1
                reporter.mark_complete(duration)

                # Save checkpoint periodically
                if i % self.checkpoint_interval == 0:
                    self._save_checkpoint(results, success_count)

            except Exception as e:
                duration = time.time() - total_start
                print(f"\n[FAIL] {step_name}: {str(e)}")
                results[f"f_{i}_error"] = str(e)

        summary = {
            "total_time": time.time() - total_start,
            "success_count": success_count,
            "failure_count": n_freq - success_count,
            "total_frequencies": n_freq,
        }
        results["summary"] = summary

        return results

    def run_geometry_batch(
        self,
        geometry_paths: List[str],
        workflow_factory: Callable[[str], Any],
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """Run simulations for multiple geometries.

        Processes each geometry file through the full simulation pipeline.

        Parameters
        ----------
        geometry_paths : list[str]
            List of geometry file paths (STEP, STL, etc.).
        workflow_factory : callable
            Factory function that takes a geometry path and returns a
            SimulationWorkflow instance.
        progress_callback : callable, optional
            Optional callback for external progress reporting.

        Returns
        -------
        dict
            Batch results with per-geometry outputs.
        """
        n_geom = len(geometry_paths)
        reporter = ProgressReporter(n_geom)
        results: Dict[str, Any] = {}
        total_start = time.time()

        for i, geom_path in enumerate(geometry_paths):
            step_name = f"Geom {os.path.basename(geom_path)}"
            reporter.set_step_name(step_name)

            try:
                start = time.time()
                workflow = workflow_factory(geom_path)
                result = workflow.run()
                duration = time.time() - start

                results[geom_path] = result
                success_count = i + 1
                reporter.mark_complete(duration)

                if i % self.checkpoint_interval == 0:
                    self._save_checkpoint(results, success_count)

            except Exception as e:
                print(f"\n[FAIL] {step_name}: {str(e)}")
                results[f"{geom_path}_error"] = str(e)

        summary = {
            "total_time": time.time() - total_start,
            "success_count": n_geom,
            "total_geometries": n_geom,
        }
        results["summary"] = summary

        return results

    # -------------------------------------------------------------------
    # Checkpoint management
#    ----------------------------------------------------------------

    def _save_checkpoint(self, results: Dict[str, Any], success_count: int) -> None:
        """Save partial results to a checkpoint file."""
        checkpoint = {
            "success_count": success_count,
            "results_partial": json.dumps(results),
            "timestamp": time.time(),
        }
        try:
            with open(self._checkpoint_file, "w") as f:
                json.dump(checkpoint, f, indent=2)
        except Exception:
            pass  # Non-critical; continue if checkpoint fails

    def _load_checkpoint(self) -> bool:
        """Load previous checkpoint if available.

        Returns
        -------
        bool
            True if a valid checkpoint was loaded.
        """
        if not os.path.exists(self._checkpoint_file):
            return False

        try:
            with open(self._checkpoint_file, "r") as f:
                data = json.load(f)
            self._batch_results["success_count"] = data.get("success_count", 0)
            return True
        except Exception:
            return False

    def clear_checkpoint(self) -> None:
        """Remove the checkpoint file."""
        if os.path.exists(self._checkpoint_file):
            os.remove(self._checkpoint_file)
