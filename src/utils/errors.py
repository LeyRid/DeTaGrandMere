"""
DeTaGrandMere Antenna Simulation Software -- Error Handling Module

Provides a structured exception hierarchy for the entire simulation
stack: CAD operations, solvers, field calculations, and configuration
validation.  Every exception accepts an optional ``context`` dict that
is included in the string representation for richer diagnostics.

Example::

    from src.utils.errors import ConfigError

    try:
        cfg = load_config(path)
    except FileNotFoundError as exc:
        raise ConfigError(
            "Could not read configuration file",
            context={"path": str(path), "errno": exc.errno},
        ) from exc
"""

from __future__ import annotations

import textwrap
from typing import Any, Dict, Mapping, Optional


__all__: list[str] = [
    # Base
    "AntennaSimulationError",
    # CAD
    "CADError",
    "GeometryError",
    "MeshError",
    # Solver
    "SolverError",
    "ConvergenceError",
    # Fields
    "FieldCalculationError",
    # Configuration
    "ConfigError",
    # Visualization / I/O
    "VisualizationError",
]


# ---------------------------------------------------------------------------
# Base exception
# ---------------------------------------------------------------------------

class AntennaSimulationError(Exception):
    """Base exception for all DeTaGrandMere simulation errors.

    Every application-level error should inherit from this class so that
    callers can catch a single type to handle *all* simulation failures.

    Attributes:
        message:  Human-readable description of the problem.
        context:  Optional mapping of extra diagnostic information
                  (e.g. parameter values, file paths) included in the
                  formatted output.
    """

    def __init__(self, message: str, context: Optional[Mapping[str, Any]] = None) -> None:
        self.message = message
        self.context: Mapping[str, Any] = context or {}

    def __str__(self) -> str:
        if not self.context:
            return self.message

        lines = [self.message]
        # Indent each context entry so it wraps nicely.
        for key, value in self.context.items():
            lines.append(f"  {key}: {value!r}")
        return textwrap.dedent("\n".join(lines))


# ---------------------------------------------------------------------------
# CAD exceptions
# ---------------------------------------------------------------------------

class CADError(AntennaSimulationError):
    """Raised when a CAD operation fails.

    Covers errors that arise while building, modifying, or exporting
    the antenna geometry in the CAD kernel.
    """


class GeometryError(CADError):
    """Raised when geometric operations fail.

    Specific to invalid shapes, self-intersections, degenerate
    primitives, or other geometry-level problems.
    """


class MeshError(CADError):
    """Raised when meshing operations fail.

    Includes invalid element types, excessive aspect ratios,
    and failures to generate a conforming mesh.
    """


# ---------------------------------------------------------------------------
# Solver exceptions
# ---------------------------------------------------------------------------

class SolverError(AntennaSimulationError):
    """Raised when the numerical solver encounters a fatal error.

    Covers linear/non-linear solver failures, memory exhaustion,
    or internal solver inconsistencies.
    """


class ConvergenceError(SolverError):
    """Raised when an iterative solver fails to converge.

    The exception carries details about the number of iterations
    performed and the final residual if available.
    """


# ---------------------------------------------------------------------------
# Field calculation exceptions
# ---------------------------------------------------------------------------

class FieldCalculationError(AntennaSimulationError):
    """Raised when post-processing field data fails.

    Includes integration errors, invalid observation points,
    or failures to evaluate near/far-field quantities.
    """


# ---------------------------------------------------------------------------
# Configuration exceptions
# ---------------------------------------------------------------------------

class ConfigError(AntennaSimulationError):
    """Raised when configuration validation fails.

    Covers missing keys, incorrect types, out-of-range values,
    and other problems with user-provided settings.
    """


# ---------------------------------------------------------------------------
# Visualization / I/O exceptions
# ---------------------------------------------------------------------------

class VisualizationError(AntennaSimulationError):
    """Raised when visualization or plot export operations fail.

    Covers rendering errors, unsupported formats, missing dependencies,
    and file write failures in the post-processing pipeline.
    """
