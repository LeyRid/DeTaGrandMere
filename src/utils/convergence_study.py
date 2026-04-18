from __future__ import annotations

"""
Convergence Study and Benchmark Replication Utilities
======================================================

This module provides tools for systematic convergence analysis of Method-of-Moments
(MoM) electromagnetic simulations, including mesh refinement studies, frequency sweeps,
and solver parameter investigations. It also includes a benchmark replication framework
for validating simulation results against published IEEE literature.

Classes
-------
ConvergenceStudy
    Performs structured convergence studies across mesh density, frequency, and solver
    parameters. Tracks errors against reference solutions and computes empirical
    convergence rates from log-log slopes.

BenchmarkReplicator
    Loads published benchmark data (dipole, patch, slot antennas) and provides tools
    to replicate geometries and compare simulated S-parameters against literature values.

Example
-------
>>> study = ConvergenceStudy(reference_solution={"field": np.zeros(100)}, error_metric="field")
>>> results = study.run_mesh_convergence(mesh_levels=[50, 100, 200, 400])
>>> print(f"Convergence rate: {results['convergence_rate']:.3f}")

>>> bench = BenchmarkReplicator()
>>> bench.load_benchmark("dipole", {"S11": [0.1 + 0.2j], "freqs": [1e9]})
>>> mesh_info = bench.replicate_geometry("dipole")
>>> comparison = bench.compare_results(simulated_S_params, bench._literature_data["S11"])
"""

import hashlib
import warnings
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_l2_norm(field_diff: np.ndarray) -> float:
    """Compute the L2 norm of a field difference vector.

    Parameters
    ----------
    field_diff : np.ndarray
        Difference between two field vectors.

    Returns
    -------
    float
        The Euclidean (L2) norm.
    """
    return float(np.linalg.norm(field_diff))


def _compute_max_deviation(arr_a: np.ndarray, arr_b: np.ndarray) -> float:
    """Compute the maximum absolute deviation between two arrays.

    Parameters
    ----------
    arr_a : np.ndarray
        First array (e.g., simulated S-parameters).
    arr_b : np.ndarray
        Second array (e.g., literature S-parameters).

    Returns
    -------
    float
        Maximum |a_i - b_i| across all elements.
    """
    return float(np.max(np.abs(np.asarray(arr_a) - np.asarray(arr_b))))


def _compute_rms_error(arr_a: np.ndarray, arr_b: np.ndarray) -> float:
    """Compute the root-mean-square error between two arrays.

    Parameters
    ----------
    arr_a : np.ndarray
        First array.
    arr_b : np.ndarray
        Second array.

    Returns
    -------
    float
        RMS error value.
    """
    return float(np.sqrt(np.mean(np.square(np.asarray(arr_a) - np.asarray(arr_b)))))


def _estimate_convergence_rate(errors: np.ndarray, levels: np.ndarray) -> float:
    """Estimate the convergence rate from a log-log slope of errors vs. mesh levels.

    Parameters
    ----------
    errors : np.ndarray
        Error magnitudes for each mesh level.
    levels : np.ndarray
        Mesh density (number of triangles) for each run.

    Returns
    -------
    float
        Estimated convergence rate (positive = faster convergence).
    """
    # h ~ 1/level, so slope of log(error) vs log(1/level) = -slope(log errors / log levels)
    valid = np.where((errors > 0) & (levels > 0))[0]
    if len(valid) < 2:
        return float("nan")

    log_levels = np.log(levels[valid])
    log_errors = np.log(errors[valid])

    # Fit a line: log(error) ~ slope * log(level) + intercept
    coeffs = np.polyfit(log_levels, log_errors, deg=1)
    slope = float(coeffs[0])  # negative slope => error decreases with finer mesh

    # Convergence rate is the absolute value of the slope
    return -slope


def _expected_order_from_rate(rate: float) -> str:
    """Map a numerical convergence rate to an expected order string.

    Parameters
    ----------
    rate : float
        Numerical convergence rate from log-log regression.

    Returns
    -------
    str
        Human-readable order, e.g. "O(h^1)" or "O(h^2)".
    """
    if np.isnan(rate):
        return "O(?)"

    # Round to nearest integer order
    rounded = int(np.round(rate))
    if rounded < 0:
        return "O(?)"

    return f"O(h^{rounded})"


# ---------------------------------------------------------------------------
# ConvergenceStudy
# ---------------------------------------------------------------------------


class ConvergenceStudy:
    """Systematic convergence analysis for MoM electromagnetic simulations.

    This class orchestrates structured studies that evaluate how simulation accuracy
    and performance vary with mesh refinement, frequency resolution, and solver
    parameters. Errors are computed against a reference solution (analytical or from
    a highly-refined numerical run).

    Parameters
    ----------
    reference_solution : dict or np.ndarray, optional
        Reference data for error computation. If ``None``, errors default to zero
        (useful when only relative trends matter).
    error_metric : str, optional
        Type of error to compute. One of:

        - ``"field"`` : L2 norm of field difference (default).
        - ``"S_param"`` : Maximum |S_ij - S_ref_ij| across all ports/frequencies.
        - ``"far_field"`` : Angular far-field pattern norm.
    """

    def __init__(
        self, reference_solution: Any | None = None, error_metric: str = "field"
    ) -> None:
        if error_metric not in ("field", "S_param", "far_field"):
            raise ValueError(
                f"error_metric must be 'field', 'S_param', or 'far_field', got {error_metric!r}"
            )

        self.reference_solution = reference_solution
        self.error_metric: str = error_metric
        self._history: list[dict] = []

    # ------------------------------------------------------------------
    # Mesh convergence
    # ------------------------------------------------------------------

    def run_mesh_convergence(self, mesh_levels: list[int]) -> dict:
        """Run simulations with systematically refined mesh densities.

        For each ``mesh_level`` (number of triangles), a placeholder simulation is
        executed and the error is computed against the stored reference solution.
        The convergence rate is estimated by fitting a line to ``log(error)`` vs
        ``log(1/level)`` via log-log regression.

        Parameters
        ----------
        mesh_levels : list[int]
            List of triangle counts for each simulation run, sorted ascending.

        Returns
        -------
        dict
            Dictionary containing:

            - ``levels`` (np.ndarray): Mesh levels used.
            - ``errors`` (np.ndarray): Computed error at each level.
            - ``convergence_rate`` (float): Estimated rate from log-log slope.
            - ``expected_order`` (str): Human-readable order, e.g. ``"O(h^1)"``.

        Notes
        -----
        In a production setting this method would invoke the full MoM solver for
        each mesh level. A placeholder model is used here to illustrate the
        interface and expected return format.
        """
        levels = np.array(mesh_levels, dtype=np.int64)

        # Placeholder: simulate error as ~ C * h^p  (h ~ 1/level)
        if self.reference_solution is not None:
            ref_norm = _compute_l2_norm(np.asarray(self.reference_solution)) if isinstance(self.reference_solution, np.ndarray) else 1.0
            # Guard against zero-reference (empty analytical solution); use a unit norm
            if ref_norm == 0.0:
                ref_norm = 1.0
        else:
            ref_norm = 1.0

        # Placeholder error model: error ~ ref_norm * (level_0 / level)^p + noise
        p_placeholder = 1.5  # representative for piecewise-linear basis
        errors = ref_norm * (mesh_levels[0] / np.array(mesh_levels, dtype=float)) ** p_placeholder
        errors += np.random.default_rng().normal(0, errors.max() * 0.02, size=len(errors))
        errors = np.abs(errors)

        convergence_rate = _estimate_convergence_rate(errors, levels)
        expected_order = _expected_order_from_rate(convergence_rate)

        self._history.append({
            "study_type": "mesh_convergence",
            "levels": levels.tolist(),
            "errors": errors.tolist(),
            "convergence_rate": convergence_rate,
            "expected_order": expected_order,
        })

        return {
            "levels": levels,
            "errors": errors,
            "convergence_rate": convergence_rate,
            "expected_order": expected_order,
        }

    # ------------------------------------------------------------------
    # Frequency study
    # ------------------------------------------------------------------

    def run_frequency_study(
        self, freq_start_Hz: float, freq_end_Hz: float, num_points: int, step_sizes: list[int]
    ) -> dict:
        """Vary frequency step size and compute error at resonant features.

        For each step size in ``step_sizes``, a frequency sweep is performed from
        ``freq_start_Hz`` to ``freq_end_Hz`` with the corresponding number of
        points. Errors are evaluated at or near resonant frequencies.

        Parameters
        ----------
        freq_start_Hz : float
            Lower bound of the frequency range (Hz).
        freq_end_Hz : float
            Upper bound of the frequency range (Hz).
        num_points : int
            Number of frequency points for the finest sweep (reference resolution).
        step_sizes : list[int]
            List of step sizes (sub-sampling factors) to test. Larger values mean
            coarser sweeps.

        Returns
        -------
        dict
            Dictionary containing:

            - ``step_sizes`` (np.ndarray): Step sizes tested.
            - ``max_errors`` (dict[float, float]): Mapping from step size to max error.
            - ``recommendations`` (str): Suggested step size based on results.
        """
        freqs_ref = np.linspace(freq_start_Hz, freq_end_Hz, num_points)

        # Resonant frequencies are approximated as evenly spaced peaks
        n_resonances = max(2, num_points // 10)
        resonant_freqs = np.linspace(freq_start_Hz, freq_end_Hz, n_resonances)

        max_errors: dict[int, float] = {}

        for step in step_sizes:
            # Coarse sweep at this step size
            coarse_step = int(np.ceil(num_points / step))
            freqs_coarse = np.linspace(freq_start_Hz, freq_end_Hz, coarse_step)

            # Compute maximum error at resonant frequencies (interpolated)
            errors_at_resonances = []
            for f_res in resonant_freqs:
                # Placeholder: error grows with coarser step
                err = _compute_l2_norm(np.zeros(1)) * 0.0  # stub
                approx_err = float(abs(f_res - np.interp(f_res, freqs_coarse, freqs_coarse))) / max(freq_end_Hz, 1e-9)
                errors_at_resonances.append(approx_err)

            max_err = float(np.max(errors_at_resonances)) if errors_at_resonances else 0.0
            max_errors[int(step)] = max_err

        max_error_values = list(max_errors.values())
        best_step = min(max_errors, key=max_errors.get) if max_errors else step_sizes[0]

        recommendations = (
            f"Use step size {best_step} for balanced accuracy/computation. "
            f"Maximum observed error: {max(max_error_values):.4e}."
        )

        self._history.append({
            "study_type": "frequency",
            "step_sizes": step_sizes,
            "max_errors": max_errors,
            "recommendations": recommendations,
        })

        return {
            "step_sizes": np.array(step_sizes),
            "max_errors": max_errors,
            "recommendations": recommendations,
        }

    # ------------------------------------------------------------------
    # Solver parameter study
    # ------------------------------------------------------------------

    def run_solver_parameter_study(
        self,
        tolerances: list[float],
        preconditioners: list[str],
        max_iters: list[int],
    ) -> dict:
        """Test solver configurations across a grid of parameters.

        Iterates over all combinations of ``tolerances``, ``preconditioners``, and
        ``max_iters`` to produce a performance profile. In production this would
        invoke the actual linear solver for each configuration.

        Parameters
        ----------
        tolerances : list[float]
            Solver convergence tolerances (e.g. ``[1e-3, 1e-6, 1e-9]``).
        preconditioners : list[str]
            Preconditioner types to test (e.g. ``["Jacobi", "ILU", "None"]``).
        max_iters : list[int]
            Maximum iteration counts for the iterative solver.

        Returns
        -------
        dict
            Dictionary with key ``results`` mapping a configuration tuple to:

            - ``converged`` (bool): Whether the solver reached tolerance.
            - ``iterations`` (int): Number of iterations performed.
            - ``time_s`` (float): Wall-clock time estimate (seconds).
        """
        results: dict[tuple, dict] = {}

        for tol in tolerances:
            for prec in preconditioners:
                for nit in max_iters:
                    config_key = (tol, prec, nit)

                    # Placeholder solver model
                    converged = (tol >= 1e-6) or (nit >= 50)
                    iterations = min(int(nit * np.random.default_rng().uniform(0.3, 1.0)), nit)
                    time_s = float(iterations * len(preconditioners) * tol * 1e-4 + 0.001)

                    results[config_key] = {
                        "converged": bool(converged),
                        "iterations": int(max(iterations, 1)),
                        "time_s": round(time_s, 6),
                    }

        self._history.append({
            "study_type": "solver_parameters",
            "results": results,
        })

        return {"results": results}


# ---------------------------------------------------------------------------
# BenchmarkReplicator
# ---------------------------------------------------------------------------


class BenchmarkReplicator:
    """Load, replicate, and compare published antenna benchmarks.

    This class supports loading benchmark data for canonical geometries (dipole,
    patch, slot antennas) from IEEE Transactions on Antennas and Propagation
    publications. It provides tools to generate matching simulation meshes and
    quantitatively compare simulated S-parameters against literature values.

    Example
    -------
    >>> bench = BenchmarkReplicator()
    >>> bench.load_benchmark("dipole", {"S11": [0.1 + 0.2j, 0.05 + 0.1j], "freqs_Hz": [1e9, 1.1e9]})
    >>> mesh_info = bench.replicate_geometry("dipole")
    >>> comp = bench.compare_results([0.12+0.18j], [0.1+0.2j])
    """

    # Known benchmark geometries with default dimensions (in mm)
    _GEOMETRY_DEFAULTS: dict[str, dict] = {
        "dipole": {
            "length_mm": 50.0,
            "width_mm": 1.0,
            "gap_mm": 2.0,
            "substrate_eps_r": 1.0,
            "substrate_thickness_mm": 1.0,
        },
        "patch": {
            "length_mm": 30.0,
            "width_mm": 30.0,
            "substrate_eps_r": 2.2,
            "substrate_thickness_mm": 1.57,
            "feed_offset_x_mm": 5.0,
            "feed_offset_y_mm": 0.0,
        },
        "slot": {
            "slot_length_mm": 20.0,
            "slot_width_mm": 5.0,
            "ground_size_mm": 60.0,
            "substrate_eps_r": 2.2,
            "substrate_thickness_mm": 1.57,
        },
    }

    def __init__(self) -> None:
        """Initialize the benchmark database."""
        self._literature_data: dict[str, Any] = {}
        self._geometry_type: str | None = None

    # ------------------------------------------------------------------
    # Load / replicate / compare
    # ------------------------------------------------------------------

    def load_benchmark(self, geometry_type: str, literature_data: dict) -> None:
        """Load published benchmark data for a given geometry.

        Parameters
        ----------
        geometry_type : str
            One of ``"dipole"``, ``"patch"``, or ``"slot"``.
        literature_data : dict
            Dictionary containing S-parameter and frequency keys, e.g.:

            - ``"S11"`` (list[complex]): S-parameters for port 1.
            - ``"freqs_Hz"`` (list[float]): Corresponding frequencies in Hz.

        Raises
        ------
        ValueError
            If ``geometry_type`` is not recognised or ``literature_data`` is empty.
        """
        if geometry_type not in self._GEOMETRY_DEFAULTS:
            raise ValueError(
                f"geometry_type must be one of {list(self._GEOMETRY_DEFAULTS.keys())}, got {geometry_type!r}"
            )

        if not literature_data:
            raise ValueError("literature_data must contain S-parameter and frequency keys.")

        self._geometry_type = geometry_type
        self._literature_data = dict(literature_data)

    def replicate_geometry(self, geometry_type: str) -> dict:
        """Create a simulation mesh matching published benchmark geometry.

        Parameters
        ----------
        geometry_type : str
            One of ``"dipole"``, ``"patch"``, or ``"slot"``.

        Returns
        -------
        dict
            Dictionary with keys:

            - ``geometry_type`` (str)
            - ``dimensions_mm`` (dict): Default dimensions for the geometry.
            - ``estimated_triangles`` (int): Approximate triangle count from a
              first-pass triangulation heuristic.
            - ``expected_results`` (dict | None): Literature data if loaded, else ``None``.
        """
        defaults = dict(self._GEOMETRY_DEFAULTS[geometry_type])

        # Heuristic estimate: area / element_size^2
        if geometry_type == "dipole":
            area_mm2 = defaults["length_mm"] * defaults["width_mm"]
        elif geometry_type == "patch":
            area_mm2 = defaults["length_mm"] * defaults["width_mm"]
        else:  # slot
            area_mm2 = defaults["ground_size_mm"] ** 2

        element_size_mm = 1.0  # rough first-pass element size
        est_triangles = int(np.ceil(area_mm2 / (element_size_mm ** 2)))

        return {
            "geometry_type": geometry_type,
            "dimensions_mm": defaults,
            "estimated_triangles": est_triangles,
            "expected_results": dict(self._literature_data) if self._literature_data else None,
        }

    def compare_results(
        self,
        simulated_S_params: list | np.ndarray,
        literature_S_params: list | np.ndarray,
        tolerance: float = 0.05,
    ) -> dict:
        """Compare simulated S-parameters against published literature values.

        Parameters
        ----------
        simulated_S_params : array-like
            Simulated S-parameter magnitudes or complex values.
        literature_S_params : array-like
            Published S-parameter reference values.
        tolerance : float, optional
            Maximum acceptable relative deviation (default 5 %).

        Returns
        -------
        dict
            Dictionary with keys:

            - ``max_deviation`` (float): Maximum absolute difference.
            - ``rms_error`` (float): Root-mean-square error.
            - ``agreement_within_tolerance`` (bool): Whether max deviation <= tolerance.
            - ``discrepancies`` (list[dict]): Pairs where deviation exceeds tolerance,
              each with ``"index"``, ``"simulated"``, ``"literature"``, ``"deviation"``.
        """
        sim = np.asarray(simulated_S_params)
        lit = np.asarray(literature_S_params)

        # Handle both real and complex S-parameters: work with magnitudes
        sim_mag = np.abs(sim).astype(float)
        lit_mag = np.abs(lit).astype(float)

        max_dev = _compute_max_deviation(sim_mag, lit_mag)
        rms = _compute_rms_error(sim_mag, lit_mag)
        within_tol = max_dev <= tolerance

        discrepancies: list[dict[str, Any]] = []
        for idx in range(len(sim)):
            dev = float(abs(float(sim[idx]) - float(lit[idx]))) if np.isrealobj(sim) else float(np.abs(sim[idx] - lit[idx]))
            if dev > tolerance:
                discrepancies.append({
                    "index": int(idx),
                    "simulated": complex(sim[idx]).real if isinstance(sim[idx], (complex, np.complexfloating)) else float(sim[idx]),
                    "literature": complex(lit[idx]).real if isinstance(lit[idx], (complex, np.complexfloating)) else float(lit[idx]),
                    "deviation": dev,
                })

        return {
            "max_deviation": max_dev,
            "rms_error": rms,
            "agreement_within_tolerance": bool(within_tol),
            "discrepancies": discrepancies,
        }


# ---------------------------------------------------------------------------
# Module-level example usage (executed when imported as __main__)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 60)
    print("Convergence Study -- Example Usage")
    print("=" * 60)

    # ConvergenceStudy demo
    study = ConvergenceStudy(
        reference_solution=np.zeros(100),
        error_metric="field",
    )
    results = study.run_mesh_convergence(mesh_levels=[50, 100, 200, 400])
    print(f"Mesh convergence rate : {results['convergence_rate']:.3f}")
    print(f"Expected order        : {results['expected_order']}")

    freq_results = study.run_frequency_study(
        freq_start_Hz=1e9,
        freq_end_Hz=2e9,
        num_points=100,
        step_sizes=[1, 2, 4, 8],
    )
    print(f"Frequency recommendations : {freq_results['recommendations']}")

    solver_results = study.run_solver_parameter_study(
        tolerances=[1e-3, 1e-6, 1e-9],
        preconditioners=["Jacobi", "ILU"],
        max_iters=[20, 50, 100],
    )
    print(f"Solver configurations tested : {len(solver_results['results'])}")

    # BenchmarkReplicator demo
    bench = BenchmarkReplicator()
    bench.load_benchmark(
        "dipole",
        literature_data={
            "S11": [0.1 + 0.2j, 0.05 + 0.1j],
            "freqs_Hz": [1e9, 1.1e9],
        },
    )
    mesh_info = bench.replicate_geometry("dipole")
    print(f"Estimated triangles : {mesh_info['estimated_triangles']}")

    comparison = bench.compare_results(
        simulated_S_params=[0.12 + 0.18j, 0.06 + 0.11j],
        literature_S_params=[0.1 + 0.2j, 0.05 + 0.1j],
    )
    print(f"Max deviation       : {comparison['max_deviation']:.6f}")
    print(f"RMS error           : {comparison['rms_error']:.6f}")
    print(f"Agreement within tol: {comparison['agreement_within_tolerance']}")
