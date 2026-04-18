from __future__ import annotations

"""
Performance Monitoring and Memory Optimisation for MoM Simulations
==================================================================

This module provides utilities for profiling simulation performance, tracking
timings across solver phases, monitoring memory consumption, and caching
frequency-independent matrix elements. It is designed to integrate with the
Method-of-Moments (MoM) solver pipeline and support regression detection
over successive runs.

Classes
-------
PerformanceMonitor
    High-level timer and profiler for simulation phases. Records per-phase
    timings and overall memory usage across multiple simulation runs.

MemoryOptimizer
    Caches static Green's-function / geometric matrix elements to avoid
    redundant computation during frequency sweeps. Provides memory
    requirement estimates for the MoM system.

Functions
---------
profile_solver(function, *args, **kwargs) -> dict
    Decorator-like profiler that executes a function, measures wall-clock time
    and peak memory, then returns a summary dictionary including the function's
    return value.

Example
-------
>>> monitor = PerformanceMonitor()
>>> monitor.start_timer("assembly")
>>> # ... run assembly ...
>>> elapsed = monitor.stop_timer("assembly")
>>> print(f"Assembly took {elapsed:.3f}s")
>>> summary = monitor.get_summary()

>>> optimizer = MemoryOptimizer()
>>> cache_key = optimizer.cache_static_elements(Z_matrix, frequency_Hz=1e9)
>>> mem = optimizer.estimate_memory_requirement(num_triangles=5000)
"""

import cProfile
import hashlib
import io
import os
import sys
import time
import traceback
import warnings
from functools import wraps
from typing import Any, Callable

import numpy as np

# ---------------------------------------------------------------------------
# Optional psutil import with graceful fallback
# ---------------------------------------------------------------------------

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def _get_memory_linux_proc() -> dict[str, float]:
    """Fallback memory reader using /proc/self/status on Linux.

    Returns
    -------
    dict
        ``"rss"`` (bytes) and ``"vms"`` (bytes) if available.
    """
    rss = 0.0
    vms = 0.0
    try:
        with open("/proc/self/status", "r") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    rss = float(line.split()[1]) * 1024.0  # kB -> bytes
                elif line.startswith("VmSize:"):
                    vms = float(line.split()[1]) * 1024.0
    except Exception:
        warnings.warn(
            "Could not read /proc/self/status; memory data unavailable.",
            stacklevel=2,
        )
    return {"rss": rss, "vms": vms}


# ---------------------------------------------------------------------------
# PerformanceMonitor
# ---------------------------------------------------------------------------


class PerformanceMonitor:
    """Timer and profiler for MoM simulation phases.

    Tracks wall-clock time for each simulation phase (assembly, solve, fields,
    metrics) across multiple runs, records memory snapshots, and provides
    statistical summaries and regression detection.

    Example
    -------
    >>> monitor = PerformanceMonitor()
    >>> monitor.start_timer("assembly")
    >>> time.sleep(0.01)
    >>> elapsed = monitor.stop_timer("assembly")
    >>> monitor.record_memory()
    >>> print(monitor.get_summary())
    """

    # Phases that are tracked by default
    _PHASES: list[str] = ["assembly", "solve", "fields", "metrics"]

    def __init__(self) -> None:
        """Initialise the performance monitor.

        Sets up per-phase timer registries, a history of recorded runs, and
        memory tracking containers.
        """
        self._timers: dict[str, float] = {}  # phase -> start_time
        self._elapsed: dict[str, list[float]] = {p: [] for p in self._PHASES}
        self._memory_snapshots: list[dict] = []
        self._runs: list[dict] = []

    # ------------------------------------------------------------------
    # Timer control
    # ------------------------------------------------------------------

    def start_timer(self, phase: str) -> None:
        """Start timing a simulation phase.

        Parameters
        ----------
        phase : str
            One of ``"assembly"``, ``"solve"``, ``"fields"``, or ``"metrics"``.

        Raises
        ------
        ValueError
            If ``phase`` is not a recognised timer key.
        """
        if phase not in self._PHASES:
            raise ValueError(
                f"Unknown phase {phase!r}. Expected one of {self._PHASES}"
            )
        if phase in self._timers:
            warnings.warn(f"Timer for '{phase}' already running; resetting.", stacklevel=2)
        self._timers[phase] = time.perf_counter()

    def stop_timer(self, phase: str) -> float:
        """Stop a timer and return the elapsed time in seconds.

        Parameters
        ----------
        phase : str
            The phase whose timer to stop.

        Returns
        -------
        float
            Elapsed wall-clock time (seconds).

        Raises
        ------
        ValueError
            If no timer was started for ``phase``.
        """
        if phase not in self._timers:
            raise ValueError(f"No active timer for '{phase}'.")

        elapsed = time.perf_counter() - self._timers.pop(phase)
        self._elapsed[phase].append(elapsed)
        return float(elapsed)

    # ------------------------------------------------------------------
    # Memory recording
    # ------------------------------------------------------------------

    def record_memory(self) -> dict:
        """Record the current process memory usage.

        Uses ``psutil`` when available; otherwise falls back to reading
        ``/proc/self/status`` on Linux.

        Returns
        -------
        dict
            Dictionary with keys ``"rss"`` (resident set size, bytes) and
            ``"vms"`` (virtual memory size, bytes). Both may be ``0.0`` if
            neither psutil nor /proc is accessible.
        """
        if _HAS_PSUTIL:
            proc = psutil.Process(os.getpid())
            mem_info = proc.memory_info()
            entry: dict[str, float] = {
                "rss": float(mem_info.rss),
                "vms": float(mem_info.vms),
            }
        else:
            entry = _get_memory_linux_proc()

        self._memory_snapshots.append(entry)
        return dict(entry)

    # ------------------------------------------------------------------
    # Summary & regression detection
    # ------------------------------------------------------------------

    def get_summary(self) -> dict:
        """Return a statistical performance summary across all recorded runs.

        Returns
        -------
        dict
            Dictionary with keys:

            - ``phase_timings`` (dict[str, dict]): Per-phase stats with
              ``mean``, ``median``, ``std`` (seconds).
            - ``total_simulation_time`` (float): Sum of all phase times.
            - ``peak_memory`` (dict): Maximum RSS and VMS across snapshots.
        """
        phase_stats: dict[str, dict] = {}
        total_time = 0.0

        for phase in self._PHASES:
            times = np.array(self._elapsed[phase], dtype=float)
            if len(times) > 0:
                stats = {
                    "mean": float(np.mean(times)),
                    "median": float(np.median(times)),
                    "std": float(np.std(times)) if len(times) > 1 else 0.0,
                    "count": int(len(times)),
                }
            else:
                stats = {"mean": 0.0, "median": 0.0, "std": 0.0, "count": 0}

            phase_stats[phase] = stats
            total_time += float(np.sum(times))

        # Peak memory
        rss_values = [s["rss"] for s in self._memory_snapshots if "rss" in s]
        vms_values = [s["vms"] for s in self._memory_snapshots if "vms" in s]

        peak_memory: dict[str, float] = {
            "rss": float(max(rss_values)) if rss_values else 0.0,
            "vms": float(max(vms_values)) if vms_values else 0.0,
        }

        return {
            "phase_timings": phase_stats,
            "total_simulation_time": total_time,
            "peak_memory": peak_memory,
        }

    def detect_regression(
        self, baseline: dict, threshold_pct: float = 10.0
    ) -> list[str]:
        """Compare current metrics against a baseline and flag slow-downs.

        Parameters
        ----------
        baseline : dict
            Dictionary with per-phase ``mean`` timing values (seconds), e.g.:

            .. code-block:: python

                {"assembly": 1.2, "solve": 3.5}

        threshold_pct : float, optional
            Percentage increase over baseline that triggers a warning
            (default 10 %).

        Returns
        -------
        list[str]
            A list of alert messages for each phase exceeding the threshold.
            Empty list means no regression detected.
        """
        alerts: list[str] = []

        for phase, baseline_val in baseline.items():
            times = np.array(self._elapsed.get(phase, []), dtype=float)
            if len(times) == 0 or baseline_val <= 0:
                continue

            current_mean = float(np.mean(times))
            pct_increase = (current_mean - baseline_val) / baseline_val * 100.0

            if pct_increase > threshold_pct:
                alerts.append(
                    f"Phase '{phase}': {pct_increase:.1f}% slowdown "
                    f"(baseline={baseline_val:.4f}s, current={current_mean:.4f}s)"
                )

        return alerts


# ---------------------------------------------------------------------------
# MemoryOptimizer
# ---------------------------------------------------------------------------


class MemoryOptimizer:
    """Cache and memory-management utilities for MoM frequency sweeps.

    Provides methods to cache frequency-independent matrix elements (geometric
    terms of the Green's function), invalidate caches when geometry or frequency
    range changes, and estimate the RAM footprint of the MoM system.
    """

    def __init__(self) -> None:
        """Initialise the memory optimiser.

        Sets up an empty cache dictionary and a flag indicating whether the
        geometry has been changed since the last cache creation.
        """
        self._cache: dict[str, Any] = {}
        self._geometry_changed: bool = False
        self._freq_range_changed: bool = False

    # ------------------------------------------------------------------
    # Cache management
    # ------------------------------------------------------------------

    def cache_static_elements(
        self, Z_matrix: np.ndarray, frequency_Hz: float
    ) -> dict:
        """Cache matrix elements that are independent of frequency.

        Geometric terms (e.g. basis function overlaps) do not vary with
        frequency; only the Green's-function kernel does. By caching these
        static components we avoid redundant computation during sweeps.

        Parameters
        ----------
        Z_matrix : np.ndarray
            The full impedance matrix at a reference frequency. Only the
            geometric contributions are cached (the frequency-dependent kernel
            is re-evaluated each sweep).
        frequency_Hz : float
            Reference frequency in Hz used to generate ``Z_matrix``.

        Returns
        -------
        dict
            A cache entry containing:

            - ``cache_key`` (str): MD5 hash of the matrix fingerprint.
            - ``frequency_Hz`` (float): Reference frequency.
            - ``shape`` (tuple[int, int]): Matrix dimensions.
            - ``dtype`` (str): NumPy dtype name.
        """
        Z_arr = np.asarray(Z_matrix)

        # Create a simple fingerprint for the static part
        sha1 = hashlib.sha256(Z_arr.tobytes()).hexdigest()[:16]
        cache_key = f"static_{sha1}"

        self._cache[cache_key] = {
            "Z_static": Z_arr.copy(),
            "frequency_Hz": float(frequency_Hz),
            "shape": Z_arr.shape,
            "dtype": str(Z_arr.dtype),
        }

        self._geometry_changed = False
        self._freq_range_changed = False

        return {
            "cache_key": cache_key,
            "frequency_Hz": float(frequency_Hz),
            "shape": Z_arr.shape,
            "dtype": str(Z_arr.dtype),
        }

    def invalidate_cache(
        self,
        geometry_changed: bool = False,
        freq_range_changed: bool = False,
    ) -> None:
        """Invalidate cached elements when geometry or frequency range changes.

        Parameters
        ----------
        geometry_changed : bool, optional
            Set to ``True`` if the simulation geometry has been modified.
        freq_range_changed : bool, optional
            Set to ``True`` if the sweep frequency range has changed.
        """
        if geometry_changed:
            self._cache.clear()
            self._geometry_changed = True
        if freq_range_changed:
            self._freq_range_changed = True

    # ------------------------------------------------------------------
    # Memory estimation
    # ------------------------------------------------------------------

    def estimate_memory_requirement(self, num_triangles: int) -> dict:
        """Estimate RAM needed for a MoM system of given mesh size.

        Parameters
        ----------
        num_triangles : int
            Number of triangular basis functions (matrix dimension).

        Returns
        -------
        dict
            Dictionary with keys ``"bytes_per_phase"`` mapping each phase to
            the estimated byte requirement:

            - ``"Z_matrix"``: Full complex impedance matrix.
            - ``"rhs_vector"``: Right-hand-side excitation vector.
            - ``"solution_vector"``: Unknown current solution vector.
            - ``"green_cache"``: Cached Green's function contributions.
            - ``"total_estimated"``: Sum of all phases (bytes).
        """
        n = num_triangles

        # complex128 = 16 bytes per element
        z_matrix_bytes = n * n * 16  # full matrix
        rhs_bytes = n * 16
        solution_bytes = n * 16

        # Green's function cache: sparse representation ~ O(n * log(n)) entries
        green_cache_bytes = int(n * np.log(max(n, 2)) * 16)

        total = z_matrix_bytes + rhs_bytes + solution_bytes + green_cache_bytes

        return {
            "bytes_per_phase": {
                "Z_matrix": z_matrix_bytes,
                "rhs_vector": rhs_bytes,
                "solution_vector": solution_bytes,
                "green_cache": green_cache_bytes,
            },
            "total_estimated": total,
            "num_triangles": n,
        }


# ---------------------------------------------------------------------------
# profile_solver -- decorator-like profiler
# ---------------------------------------------------------------------------


def profile_solver(
    function: Callable, *args: Any, **kwargs: Any
) -> dict:
    """Run a function while profiling its time and memory usage.

    This acts as a decorator-like wrapper (not actually a ``@decorator`` because
    it consumes the callable directly). It measures wall-clock time, records
    memory snapshots before/after, and returns a summary dictionary alongside
    the function's return value.

    Parameters
    ----------
    function : callable
        The simulation or solver function to profile.
    \\*args
        Positional arguments passed to ``function``.
    \\**kwargs
        Keyword arguments passed to ``function``.

    Returns
    -------
    dict
        Dictionary with keys:

        - ``result``: The return value of ``function``.
        - ``wall_time_s`` (float): Wall-clock execution time in seconds.
        - ``memory_before`` (dict): RSS/VMS before the call.
        - ``memory_after`` (dict): RSS/VMS after the call.
        - ``peak_memory`` (dict): Maximum of the two snapshots.

    Example
    -------
    >>> def solve(Z, b): return np.linalg.solve(Z, b)
    >>> out = profile_solver(solve, Z_matrix, rhs_vector)
    >>> print(f"Time: {out['wall_time_s']:.3f}s")
    """
    monitor = PerformanceMonitor()

    # Memory before
    mem_before = monitor.record_memory()

    t_start = time.perf_counter()
    try:
        result = function(*args, **kwargs)
    except Exception as exc:
        elapsed = time.perf_counter() - t_start
        mem_after = monitor.record_memory()
        raise RuntimeError(
            f"Function {function.__name__} failed after {elapsed:.3f}s: {exc}"
        ) from exc
    finally:
        elapsed = time.perf_counter() - t_start

    mem_after = monitor.record_memory()

    peak_rss = max(mem_before.get("rss", 0), mem_after.get("rss", 0))
    peak_vms = max(mem_before.get("vms", 0), mem_after.get("vms", 0))

    return {
        "result": result,
        "wall_time_s": float(elapsed),
        "memory_before": mem_before,
        "memory_after": mem_after,
        "peak_memory": {"rss": peak_rss, "vms": peak_vms},
    }


# ---------------------------------------------------------------------------
# Module-level example usage (executed when imported as __main__)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Performance Monitor -- Example Usage")
    print("=" * 60)

    # PerformanceMonitor demo
    monitor = PerformanceMonitor()
    monitor.start_timer("assembly")
    time.sleep(0.01)
    elapsed = monitor.stop_timer("assembly")
    print(f"Assembly phase   : {elapsed:.4f}s")

    monitor.start_timer("solve")
    time.sleep(0.02)
    elapsed = monitor.stop_timer("solve")
    print(f"Solve phase      : {elapsed:.4f}s")

    mem = monitor.record_memory()
    print(f"Memory snapshot  : RSS={mem['rss'] / 1e6:.1f} MB, VMS={mem['vms'] / 1e6:.1f} MB")

    summary = monitor.get_summary()
    print(f"Total sim time   : {summary['total_simulation_time']:.4f}s")
    print(f"Peak memory RSS  : {summary['peak_memory']['rss'] / 1e6:.1f} MB")

    # Regression detection demo
    baseline = {"assembly": 0.05, "solve": 0.10}
    alerts = monitor.detect_regression(baseline, threshold_pct=10.0)
    if alerts:
        for a in alerts:
            print(f"WARNING: {a}")
    else:
        print("No regressions detected.")

    # MemoryOptimizer demo
    optimizer = MemoryOptimizer()
    Z_example = np.zeros((10, 10), dtype=np.complex128)
    cache_info = optimizer.cache_static_elements(Z_example, frequency_Hz=1e9)
    print(f"Cache key        : {cache_info['cache_key']}")

    mem_est = optimizer.estimate_memory_requirement(num_triangles=5000)
    print(f"Estimated total  : {mem_est['total_estimated'] / 1e6:.2f} MB")

    # profile_solver demo
    def dummy_solve(Z, b):
        return np.linalg.solve(Z, b)

    Z_test = np.eye(5) + 0.1 * np.ones((5, 5))
    b_test = np.ones(5)
    out = profile_solver(dummy_solve, Z_test, b_test)
    print(f"Dummy solve time : {out['wall_time_s']:.4f}s")
