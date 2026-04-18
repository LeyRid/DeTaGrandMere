"""Green's function evaluation for MoM matrix assembly.

This module provides the free-space dyadic Green's function used in the
Method of Moments impedance matrix computation:

    G(r, r') = (e^{-j k |r - r'|}) / (4 pi |r - r'|) I

where k is the wavenumber and I is the identity tensor.  Singularity at
|r - r'| = 0 is handled via principal-value integration.

For higher-frequency or layered-media problems this stub can be extended
with stratified-medium Green's functions (Sylvester-type integral
representations).

Example usage::

    from src.core.mom_solver.green_function import GreensFunction, GreenEvaluator

    gf = GreensFunction()
    evaluator = GreenEvaluator(gf)

    value = evaluator.evaluate(
        source_point=[0.0, 0.0, 0.0],
        observation_point=[0.01, 0.01, 0.0],
        frequency=1e9
    )
"""

from __future__ import annotations

import numpy as np
from typing import Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
C_SPEED = 299792458.0       # Speed of light [m/s]
MU_0 = 4 * np.pi * 1e-7     # Permeability of free space [H/m]
EPS_0 = 8.854187812e-12    # Permittivity of free space [F/m]


# ===================================================================
# GreensFunction class
# ===================================================================

class GreensFunction:
    """Free-space scalar Green's function and its derivatives.

    The Green's function for the Helmholtz equation in free space is:

        G(r, r') = e^{-j k |r - r'|} / (4 pi |r - r'|)

    where k = omega / c = 2 pi f / c.
    """

    def __init__(self, frequency: float = 1e9) -> None:
        """Initialise the Green's function at a reference frequency.

        Parameters
        ----------
        frequency : float, optional
            Reference frequency in Hz. Default is 1 GHz.
        """
        self.frequency = frequency
        self._k = self._compute_wavenumber(frequency)

    def _compute_wavenumber(self, frequency: float) -> float:
        """Compute the wavenumber k = 2*pi*f/c.

        Parameters
        ----------
        frequency : float
            Frequency in Hz.

        Returns
        -------
        float
            Wavenumber in rad/m.
        """
        return 2 * np.pi * frequency / C_SPEED

    def set_frequency(self, frequency: float) -> None:
        """Update the Green's function to a new frequency.

        Parameters
        ----------
        frequency : float
            New operating frequency in Hz.
        """
        self.frequency = frequency
        self._k = self._compute_wavenumber(frequency)

    def evaluate(self, r_mag: float) -> complex:
        """Evaluate the Green's function for a given separation distance.

        Parameters
        ----------
        r_mag : float
            Distance |r - r'| in metres. Must be > 0.

        Returns
        -------
        complex
            Green's function value G(r, r').

        Raises
        ------
        ValueError
            If *r_mag* <= 0 (singularity).
        """
        if r_mag <= 0:
            raise ValueError(
                f"Green's function singularity at r_mag={r_mag}. "
                "Use principal_value() for self-term evaluation."
            )
        return np.exp(-1j * self._k * r_mag) / (4 * np.pi * r_mag)

    def principal_value(self) -> complex:
        """Return the principal-value contribution for the self-term (R=0).

        For the diagonal element of the impedance matrix, the Green's function
        integral diverges.  The principal value gives a finite reactive term:

            PV = -j * k / (8 pi)

        Returns
        -------
        complex
            Principal-value Green's function contribution.
        """
        return -1j * self._k / (8 * np.pi)

    def derivative(self, r_mag: float) -> complex:
        """Compute the radial derivative dG/dr.

        .. math:: \\frac{dG}{dr} = G(r) \\\\cdot \\\\left(-\\\\frac{1}{r} - j k\\\\right)

        Parameters
        ----------
        r_mag : float
            Distance |r - r'| in metres. Must be > 0.

        Returns
        -------
        complex
            Radial derivative value.

        Raises
        ------
        ValueError
            If *r_mag* <= 0.
        """
        if r_mag <= 0:
            raise ValueError("Derivative requires non-zero distance")
        g = self.evaluate(r_mag)
        return g * (-1.0 / r_mag - 1j * self._k)


# ===================================================================
# GreenEvaluator class
# ===================================================================

class GreenEvaluator:
    """Evaluate Green's function for matrix assembly with caching.

    Caches previously computed values to speed up frequency sweeps where
    the same source/test pairs are re-evaluated at different frequencies.

    Parameters
    ----------
    greens_function : GreensFunction, optional
        Pre-configured Green's function instance.  A new one is created
        internally if not provided.
    cache_size : int, optional
        Maximum number of cached (distance, frequency) entries. Default 10000.
    """

    def __init__(
        self,
        greens_function: Optional[GreensFunction] = None,
        cache_size: int = 10000,
    ) -> None:
        self.gf = greens_function if greens_function is not None else GreensFunction()
        self._cache: dict[tuple[float, float], complex] = {}
        self._cache_size = cache_size

    def evaluate(
        self,
        source_point: np.ndarray,
        observation_point: np.ndarray,
        frequency: Optional[float] = None,
    ) -> complex:
        """Evaluate G(r, r') for given source and observation points.

        Parameters
        ----------
        source_point : array_like shape (3,)
            Source point coordinates.
        observation_point : array_like shape (3,)
            Observation point coordinates.
        frequency : float, optional
            Operating frequency in Hz. Overrides *gf.frequency* if given.

        Returns
        -------
        complex
            Green's function value.

        Raises
        ------
        ValueError
            If source and observation points are identical (singularity).
        """
        src = np.asarray(source_point, dtype=np.float64)
        obs = np.asarray(observation_point, dtype=np.float64)
        r_mag = float(np.linalg.norm(obs - src))

        freq = frequency if frequency is not None else self.gf.frequency

        # --- Singularity handling -------------------------------------------
        if r_mag < 1e-12:
            return self.gf.principal_value()

        # --- Cache lookup ---------------------------------------------------
        cache_key = (round(r_mag, 10), round(freq, 10))
        if cache_key in self._cache:
            return self._cache[cache_key]

        # --- Evaluate and cache ---------------------------------------------
        if frequency is not None:
            self.gf.set_frequency(frequency)
        value = self.gf.evaluate(r_mag)

        # LRU eviction (simple FIFO)
        if len(self._cache) >= self._cache_size:
            # Remove oldest entry
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        self._cache[cache_key] = value

        return value

    def clear_cache(self) -> None:
        """Clear the evaluation cache."""
        self._cache.clear()

    @property
    def cache_size(self) -> int:
        """Number of cached entries."""
        return len(self._cache)


# ===================================================================
# Module-level example usage
# ===================================================================

if __name__ == "__main__":
    print("=== Green's Function ===\n")

    gf = GreensFunction(frequency=1e9)
    print(f"Reference frequency: {gf.frequency:.1e} Hz")
    print(f"Wavenumber k: {gf._k:.4f} rad/m\n")

    # Evaluate at various distances
    for r in [0.001, 0.01, 0.1, 1.0]:
        val = gf.evaluate(r)
        print(f"G({r} m) = {val:.6e} (mag={np.abs(val):.6e})")

    print(f"\nPrincipal value (self-term): {gf.principal_value():.6e}")
    print(f"Derivative at 0.01 m: {gf.derivative(0.01):.6e}\n")

    # Evaluator with caching
    evaluator = GreenEvaluator(gf, cache_size=100)
    src = np.array([0.0, 0.0, 0.0])
    obs = np.array([0.01, 0.01, 0.0])

    val1 = evaluator.evaluate(src, obs, frequency=1e9)
    print(f"Evaluator G({src} -> {obs}): {val1:.6e}")

    # Re-evaluate same points (should hit cache)
    val2 = evaluator.evaluate(src, obs, frequency=1e9)
    assert val1 == val2, "Cache miss!"
    print(f"Cache hit: {val2:.6e} (cache size={evaluator.cache_size})")
