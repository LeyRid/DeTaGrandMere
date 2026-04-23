"""Performance monitoring and optimization utilities for solver workflows.

This module provides the :class:`PerformanceMonitor` class for tracking
solver performance metrics including timing, memory usage, and convergence
behavior. It includes regression detection and baseline comparison.

Key features:
- Solver timing and memory profiling
- Memory leak detection and reporting
- Performance regression detection against baselines
- Baseline persistence to JSON files
"""

from __future__ import annotations

import os
import json
import time
import psutil
from typing import Optional, List, Dict


class PerformanceMonitor:
    """Monitor solver performance metrics.

    This class provides methods for timing operations, tracking memory
    usage, and detecting performance regressions. It maintains baselines
    for comparison against current runs.

    Parameters
    ----------
    baseline_file : str, default="performance_baseline.json"
        Path to the JSON file containing baseline metrics.
    regression_threshold : float, default=0.1
        Threshold for regression detection (10% slowdown triggers warning).
    """

    def __init__(
        self,
        baseline_file: str = "performance_baseline.json",
        regression_threshold: float = 0.1,
    ) -> None:
        """Initialise the performance monitor."""
        self.baseline_file = baseline_file
        self.regression_threshold = regression_threshold
        self._timers: Dict[str, float] = {}
        self._memory_samples: List[float] = []

    # -------------------------------------------------------------------
    # Timing utilities
    # ----------------------------------------------------------------

    def start_timer(self, name: str) -> None:
        """Start a named timer.

        Parameters
        ----------
        name : str
            Timer name (e.g., "matrix_assembly", "linear_solve").
        """
        self._timers[name] = time.time()

    def stop_timer(self, name: str) -> float:
        """Stop a named timer and return elapsed time.

        Parameters
        ----------
        name : str
            Timer name to stop.

        Returns
        -------
        float
            Elapsed time in seconds.

        Raises
        ------
        ValueError
            If the timer was not started.
        """
        if name not in self._timers:
            raise ValueError(f"Timer '{name}' was not started")

        elapsed = time.time() - self._timers[name]
        del self._timers[name]  # Remove to prevent double-stop
        return elapsed

    def get_summary(self) -> dict:
        """Get a summary of all measured timings.

        Returns
        -------
        dict
            Dictionary mapping timer names to elapsed times in seconds.
        """
        summary = {}
        for name, start_time in self._timers.items():
            elapsed = time.time() - start_time
            summary[name] = elapsed
        return summary

    # -------------------------------------------------------------------
    # Memory monitoring
#    ----------------------------------------------------------------

    def record_memory(self) -> float:
        """Record current memory usage and return RSS in MB.

        Returns
        -------
        float
            Resident set size (RSS) in megabytes.
        """
        try:
            process = psutil.Process(os.getpid())
            rss_mb = process.memory_info().rss / (1024 * 1024)
            self._memory_samples.append(rss_mb)
            return rss_mb
        except Exception:
            # Fallback: estimate from /proc/self/status on Linux
            try:
                with open("/proc/self/status", "r") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            kb = int(line.split()[1])
                            mb = kb / 1024.0
                            self._memory_samples.append(mb)
                            return mb
            except FileNotFoundError:
                pass

            # Ultimate fallback: use Python's gc module estimate
            import sys
            total = sum(sys.getsizeof(obj) for obj in gc.get_objects())
            self._memory_samples.append(total / (1024 * 1024))
            return total / (1024 * 1024)

    def get_memory_summary(self) -> dict:
        """Get memory usage statistics.

        Returns
        -------
        dict
            Memory statistics with keys:
            - 'samples': list of RSS values in MB
            - 'min_mb': minimum RSS observed
            - 'max_mb': maximum RSS observed
            - 'avg_mb': average RSS
        """
        if not self._memory_samples:
            return {"samples": [], "min_mb": 0, "max_mb": 0, "avg_mb": 0}

        return {
            "samples": list(self._memory_samples),
            "min_mb": float(min(self._memory_samples)),
            "max_mb": float(max(self._memory_samples)),
            "avg_mb": float(sum(self._memory_samples) / len(self._memory_samples)),
        }

    # -------------------------------------------------------------------
    # Regression detection
#    ----------------------------------------------------------------

    def check_regression(
        self,
        metric_name: str,
        current_value: float,
        baseline_file: Optional[str] = None,
    ) -> dict:
        """Check if a metric shows regression against baseline.

        Parameters
        ----------
        metric_name : str
            Name of the metric to check (e.g., "solve_time", "memory_peak").
        current_value : float
            Current measured value.
        baseline_file : str, optional
            Path to baseline file. Uses self.baseline_file if None.

        Returns
        -------
        dict
            Regression check result with keys:
            - 'baseline': previous baseline value
            - 'current': current measured value
            - 'deviation_pct': percentage deviation from baseline
            - 'is_regression': True if deviation exceeds threshold

        Raises
        ------
        FileNotFoundError
            If no baseline file exists.
        """
        bf = baseline_file or self.baseline_file

        if not os.path.exists(bf):
            raise FileNotFoundError(f"Baseline file not found: {bf}")

        with open(bf, "r") as f:
            baselines = json.load(f)

        if metric_name not in baselines:
            raise KeyError(f"No baseline for metric: {metric_name}")

        baseline_value = baselines[metric_name]
        deviation_pct = (current_value - baseline_value) / max(baseline_value, 1e-10) * 100
        is_regression = deviation_pct > self.regression_threshold * 100

        return {
            "baseline": baseline_value,
            "current": current_value,
            "deviation_pct": float(deviation_pct),
            "is_regression": bool(is_regression),
        }


class MemoryOptimizer:
    """Optimize memory usage for large MoM simulations.

    This class provides methods for caching static matrix elements,
    invalidating cached data on geometry changes, and estimating
    memory requirements for problem sizes.
    """

    def __init__(self) -> None:
        """Initialise the memory optimizer."""
        self._cache: Dict[str, object] = {}

    def cache_static_elements(
        self,
        elements: dict,
        cache_key: str,
    ) -> None:
        """Cache static matrix elements that don't change with frequency.

        Parameters
        ----------
        elements : dict
            Matrix elements to cache (e.g., geometric terms).
        cache_key : str
            Unique identifier for the cached data.
        """
        self._cache[cache_key] = elements

    def invalidate_cache(self, cache_key: Optional[str] = None) -> int:
        """Invalidate cached matrix elements.

        Parameters
        ----------
        cache_key : str, optional
            Specific cache key to invalidate. If None, clears all caches.

        Returns
        -------
        int
            Number of cache entries invalidated.
        """
        if cache_key is not None:
            if cache_key in self._cache:
                del self._cache[cache_key]
                return 1
            return 0

        count = len(self._cache)
        self._cache.clear()
        return count

    def estimate_memory_requirement(
        self,
        n_unknowns: int,
        density: float = 0.3,
    ) -> dict:
        """Estimate memory requirements for a MoM problem.

        Parameters
        ----------
        n_unknowns : int
            Number of RWG basis function unknowns (matrix dimension).
        density : float, default=0.3
            Expected matrix fill percentage (sparse matrix density).

        Returns
        -------
        dict
            Memory estimates with keys:
            - 'dense_matrix_mb': memory for dense matrix in MB
            - 'sparse_matrix_mb': memory for sparse matrix in MB
            - 'rhs_vector_mb': memory for RHS vector in MB
            - 'total_estimate_mb': total memory estimate in MB
        """
        # Estimate matrix size
        n = n_unknowns
        nnz = int(n * n * density)  # Number of non-zero elements

        # Memory estimates (complex128 = 16 bytes per element)
        dense_bytes = n * n * 16
        sparse_bytes = nnz * 16 + n * (8 + 8)  # CSR format overhead
        rhs_bytes = n * 16

        return {
            "dense_matrix_mb": float(dense_bytes / (1024 * 1024)),
            "sparse_matrix_mb": float(sparse_bytes / (1024 * 1024)),
            "rhs_vector_mb": float(rhs_bytes / (1024 * 1024)),
            "total_estimate_mb": float((dense_bytes + sparse_bytes + rhs_bytes) / (1024 * 1024)),
        }


class BenchmarkRunner:
    """Run performance benchmarks and compare against baselines.

    This class provides methods for running timing benchmarks on solver
    operations and comparing results against stored baselines.
    """

    def __init__(self, monitor: Optional[PerformanceMonitor] = None) -> None:
        """Initialise the benchmark runner."""
        self.monitor = monitor or PerformanceMonitor()

    def benchmark_matrix_assembly(
        self,
        n_unknowns: int,
        iterations: int = 5,
    ) -> dict:
        """Benchmark matrix assembly time.

        Parameters
        ----------
        n_unknowns : int
            Number of unknowns for the test problem.
        iterations : int, default=5
            Number of iterations to average over.

        Returns
        -------
        dict
            Benchmark results with keys:
            - 'n_unknowns': problem size
            - 'mean_time_s': mean assembly time in seconds
            - 'min_time_s': minimum assembly time
            - 'max_time_s': maximum assembly time
        """
        times = []

        for _ in range(iterations):
            self.monitor.start_timer("matrix_assembly")

            # Simulate matrix assembly (stub: O(N^2) dense assembly)
            import numpy as np
            Z = np.random.randn(n_unknowns, n_unknowns) + 1j * np.random.randn(
                n_unknowns, n_unknowns
            )

            elapsed = self.monitor.stop_timer("matrix_assembly")
            times.append(elapsed)

        return {
            "n_unknowns": n_unknowns,
            "mean_time_s": float(np.mean(times)),
            "min_time_s": float(min(times)),
            "max_time_s": float(max(times)),
        }

    def benchmark_linear_solve(
        self,
        n_unknowns: int,
        iterations: int = 5,
    ) -> dict:
        """Benchmark linear solve time.

        Parameters
        ----------
        n_unknowns : int
            Number of unknowns for the test problem.
        iterations : int, default=5
            Number of iterations to average over.

        Returns
        -------
        dict
            Benchmark results with keys:
            - 'n_unknowns': problem size
            - 'mean_time_s': mean solve time in seconds
            - 'min_time_s': minimum solve time
            - 'max_time_s': maximum solve time
        """
        times = []

        for _ in range(iterations):
            self.monitor.start_timer("linear_solve")

            # Simulate linear solve (stub: direct solve)
            import numpy as np
            A = np.eye(n_unknowns) + 0.1 * np.random.randn(
                n_unknowns, n_unknowns
            )
            b = np.random.randn(n_unknowns) + 1j * np.random.randn(n_unknowns)
            x = np.linalg.solve(A, b)

            elapsed = self.monitor.stop_timer("linear_solve")
            times.append(elapsed)

        return {
            "n_unknowns": n_unknowns,
            "mean_time_s": float(np.mean(times)),
            "min_time_s": float(min(times)),
            "max_time_s": float(max(times)),
        }


import gc  # Import at module level for fallback memory estimation


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

def profile_solver(workflow, frequency: float = 1e9) -> dict:
    """Profile a solver workflow and return timing statistics.

    Parameters
    ----------
    workflow : SimulationWorkflow
        The workflow instance to profile.
    frequency : float, optional
        Operating frequency in Hz. Default is 1 GHz.

    Returns
    -------
    dict
        Timing statistics with keys:
        - 'total_time_s': total wall-clock time
        - 'steps': dict of per-step timing
    """
    monitor = PerformanceMonitor()
    import time

    start = time.time()
    result = workflow.run(frequency=frequency)
    elapsed = time.time() - start

    return {
        "total_time_s": elapsed,
        "result": result,
    }


def benchmark_solver(workflow, frequencies: list[float]) -> dict:
    """Benchmark a solver across multiple frequencies.

    Parameters
    ----------
    workflow : SimulationWorkflow
        The workflow instance to benchmark.
    frequencies : list[float]
        List of frequencies in Hz to test.

    Returns
    -------
    dict
        Benchmark results indexed by frequency.
    """
    results = {}
    for f in frequencies:
        start = time.time()
        result = workflow.run(frequency=f)
        elapsed = time.time() - start
        results[f] = {"time_s": elapsed, "result": result}
    return results
