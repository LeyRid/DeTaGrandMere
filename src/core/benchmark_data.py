"""Regression test baselines for known analytical solutions.

This module provides reference data for validating simulation results
against known analytical solutions for canonical antenna geometries:

- Half-wave dipole (analytical impedance and radiation pattern)
- Microstrip patch antenna (closed-form resonance frequency)
- Loop antenna (small-loop approximation)

These baselines are used by the convergence study framework to verify
numerical accuracy.
"""

from __future__ import annotations

import numpy as np


class DipoleBaseline:
    """Analytical reference data for a half-wave dipole antenna.

    Parameters for the reference dipole:
    - Length: lambda/2 at 1 GHz (0.15 m in free space)
    - Radius: 1 mm
    - Feed gap: 1 mm centered

    Reference values from Balakin, "Analytical Antenna Theory", and
    NEC simulation results for validation.
    """

    @staticmethod
    def get_input_impedance() -> dict:
        """Return analytical input impedance at 1 GHz.

        Returns
        -------
        dict
            Impedance reference data with keys:
            - 'resistance': real part in ohms (approx 73 ohms)
            - 'reactance': imaginary part in ohms (small, ~+42 ohms)
        """
        return {
            "frequency_hz": 1e9,
            "length_m": 0.149895,  # lambda/2 at 1 GHz
            "radius_m": 0.001,
            "resistance_ohm": 73.1,
            "reactance_ohm": 42.5,
            "impedance_ohm": 73.1 + 42.5j,
        }

    @staticmethod
    def get_radiation_pattern() -> dict:
        """Return analytical far-field pattern for half-wave dipole.

        The E-field pattern is proportional to cos(pi/2 * sin(theta)) / cos(theta).

        Returns
        -------
        dict
            Pattern reference data with keys:
            - 'theta_deg': array of theta angles
            - 'pattern_linear': normalized field magnitude
            - 'pattern_dbi': directivity in dBi
        """
        thetas = np.linspace(0, 180, 181)
        thetas_rad = np.deg2rad(thetas)

        # Half-wave dipole pattern: cos(pi/2 * cos(theta)) / sin(theta)
        pattern = np.cos(np.pi / 2 * np.cos(thetas_rad))
        sin_theta = np.sin(thetas_rad)
        # Handle theta=0 and theta=pi singularities
        mask = np.abs(sin_theta) > 1e-10
        pattern[~mask] = 0.0
        pattern[mask] /= sin_theta[mask]

        # Normalize to max value
        pattern = np.abs(pattern)
        pattern /= np.max(np.abs(pattern))

        return {
            "theta_deg": thetas,
            "pattern_linear": pattern,
            "max_directivity_dbi": 2.15,  # Theoretical max for HWD
        }


class PatchBaseline:
    """Analytical reference data for a rectangular microstrip patch.

    Reference dimensions for a substrate with epsilon_r=2.2, h=1.6mm:
    - Length L ~ lambda_g/2 at 2.4 GHz
    - Width W chosen for optimal radiation efficiency
    """

    @staticmethod
    def get_resonant_frequency() -> dict:
        """Return analytical resonant frequency calculation.

        Returns
        -------
        dict
            Resonance reference data with keys:
            - 'epsilon_r': relative permittivity of substrate
            - 'height_m': substrate thickness in meters
            - 'length_m': patch length in meters
            - 'width_m': patch width in meters
            - 'f_resonant_ghz': calculated resonant frequency
        """
        epsilon_r = 2.2
        h = 1.6e-3  # mm to m
        c = 299792458.0

        # Approximate patch length for TM010 mode
        L = 0.49 * c / (np.sqrt(epsilon_r) * 2.4e9)
        W = c / (2.4e9 * np.sqrt(epsilon_r))  # Optimal width

        return {
            "epsilon_r": epsilon_r,
            "height_m": h,
            "length_m": L,
            "width_m": W,
            "f_resonant_ghz": 2.4,
            "mode": "TM010",
        }

    @staticmethod
    def get_s11_threshold() -> dict:
        """Return expected S11 bandwidth for patch antenna.

        Returns
        -------
        dict
            Bandwidth reference data with keys:
            - 's11_threshold_db': return loss threshold in dB
            - 'fractional_bandwidth_pct': typical fractional BW
        """
        return {
            "s11_threshold_db": -10,
            "fractional_bandwidth_pct": 5.0,  # Typical for thin substrate
            "q_factor": 15.0,  # Quality factor estimate
        }


class LoopBaseline:
    """Analytical reference data for a small loop antenna.

    Reference loop: circular, radius a = lambda/10, wire radius << a.
    """

    @staticmethod
    def get_input_impedance() -> dict:
        """Return analytical input impedance for small loop.

        Returns
        -------
        dict
            Impedance reference data with keys:
            - 'resistance_ohm': radiation resistance (very small, ~0.1 ohm)
            - 'reactance_ohm': inductive reactance (positive)
        """
        return {
            "type": "small_loop",
            "resistance_ohm": 0.0796,  # Approx for lambda/10 loop
            "reactance_ohm": 5.0,  # Inductive at 1 GHz
        }

    @staticmethod
    def get_radiation_pattern() -> dict:
        """Return analytical far-field pattern for small loop.

        Pattern is proportional to sin(theta) (doughnut shape).

        Returns
        -------
        dict
            Pattern reference data with keys:
            - 'theta_deg': array of theta angles
            - 'pattern_linear': normalized field magnitude
            - 'max_directivity_dbi': theoretical max directivity
        """
        thetas = np.linspace(0, 180, 181)
        thetas_rad = np.deg2rad(thetas)

        # Small loop pattern: sin(theta)
        pattern = np.sin(thetas_rad)

        return {
            "theta_deg": thetas,
            "pattern_linear": np.abs(pattern),
            "max_directivity_dbi": 1.76,  # Theoretical max for small loop
        }


class BenchmarkRegistry:
    """Registry of benchmark problems for regression testing."""

    _benchmarks = {
        "dipole_hwd": DipoleBaseline,
        "patch_rect": PatchBaseline,
        "loop_small": LoopBaseline,
    }

    @classmethod
    def get_benchmark(cls, name: str):
        """Get a benchmark class by name.

        Parameters
        ----------
        name : str
            Benchmark name from the registry.

        Returns
        -------
        type
            The benchmark class.

        Raises
        ------
        ValueError
            If the benchmark name is not registered.
        """
        if name not in cls._benchmarks:
            raise ValueError(
                f"Unknown benchmark: {name}. Available: {list(cls._benchmarks.keys())}"
            )
        return cls._benchmarks[name]

    @classmethod
    def list_benchmarks(cls) -> list:
        """List all available benchmark names."""
        return list(cls._benchmarks.keys())
