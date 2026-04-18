"""Unit tests for Green's function evaluation and caching.

This module provides comprehensive pytest-based unit tests covering:

- Direct Green's function evaluation G(r) = exp(-j*k*r) / (4*pi*r)
- Principal-value computation for the self-term (R=0 singularity)
- Radial derivative formula dG/dr = G * (-1/r - j*k)
- GreenEvaluator caching behavior (cache hit returns same value)

All tests are self-contained using only numpy and pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

# Import the modules under test
from src.core.mom_solver.green_function import GreensFunction, GreenEvaluator


# ===================================================================
# Test Green's function evaluation
# ===================================================================

class TestGreensFunctionEvaluation:
    """Tests for direct Green's function evaluation at known distances."""

    def test_greens_function_evaluation(self) -> None:
        """Verify G(r) = exp(-j*k*r) / (4*pi*r) at a known distance.

        For frequency f = 1e9 Hz, the wavenumber k = 2*pi*f/c.
        At r = 0.01 m, we can compute the expected Green's function value
        analytically and compare against the implementation.
        """
        frequency = 1e9
        gf = GreensFunction(frequency=frequency)

        # Known distance
        r_mag = 0.01  # metres

        result = gf.evaluate(r_mag)

        # Compute expected value manually
        k = 2 * np.pi * frequency / 299792458.0
        expected = np.exp(-1j * k * r_mag) / (4 * np.pi * r_mag)

        assert isinstance(result, (complex, np.complexfloating)), \
            f"Expected complex, got {type(result)}"
        assert np.isclose(result, expected, rtol=1e-10), \
            f"G({r_mag}) = {result}, expected {expected}"

    def test_greens_function_distance_dependence(self) -> None:
        """Verify Green's function magnitude decays as 1/r."""
        frequency = 1e9
        gf = GreensFunction(frequency=frequency)

        # Values at different distances should scale roughly as 1/r
        r_values = [0.001, 0.01, 0.1]
        magnitudes = []

        for r in r_values:
            val = gf.evaluate(r)
            magnitudes.append(np.abs(val))

        # Check that |G(0.001)| / |G(0.01)| ~ 10 (since 1/0.001 / 1/0.01 = 10)
        ratio_1 = magnitudes[0] / magnitudes[1]
        assert np.isclose(ratio_1, 10.0, atol=0.5), \
            f"Ratio |G(0.001)|/|G(0.01)| = {ratio_1}, expected ~10"

    def test_greens_function_singularity_raises(self) -> None:
        """Verify that evaluating at r <= 0 raises ValueError."""
        gf = GreensFunction(frequency=1e9)

        with pytest.raises(ValueError, match="singularity"):
            gf.evaluate(0.0)

        with pytest.raises(ValueError, match="singularity"):
            gf.evaluate(-0.01)


# ===================================================================
# Test principal value computation
# ===================================================================

class TestGreensFunctionPrincipalValue:
    """Tests for the principal-value Green's function at R=0."""

    def test_greens_function_principal_value(self) -> None:
        """Verify principal value is purely imaginary.

        The principal-value approximation for the self-term is:
            PV = -j * k / (8*pi)
        which is purely imaginary (zero real part).
        """
        frequency = 1e9
        gf = GreensFunction(frequency=frequency)

        pv = gf.principal_value()

        # Should be complex
        assert isinstance(pv, (complex, np.complexfloating)), \
            f"Expected complex, got {type(pv)}"

        # Real part should be zero (purely imaginary)
        assert np.isclose(pv.real, 0.0, atol=1e-15), \
            f"Principal value real part {pv.real} != 0"

        # Imaginary part should match -k/(8*pi)
        k = 2 * np.pi * frequency / 299792458.0
        expected_imag = -k / (8 * np.pi)
        assert np.isclose(pv.imag, expected_imag, rtol=1e-10), \
            f"Principal value imag {pv.imag} != expected {expected_imag}"

    def test_principal_value_frequency_dependence(self) -> None:
        """Verify principal value scales linearly with frequency."""
        gf = GreensFunction(frequency=1e9)
        pv_1ghz = gf.principal_value()

        gf.set_frequency(2e9)
        pv_2ghz = gf.principal_value()

        # PV is proportional to k which is proportional to f
        assert np.isclose(pv_2ghz.imag, 2 * pv_1ghz.imag, rtol=1e-10), \
            "Principal value should scale linearly with frequency"


# ===================================================================
# Test derivative computation
# ===================================================================

class TestGreensFunctionDerivative:
    """Tests for the radial derivative of the Green's function."""

    def test_greens_function_derivative(self) -> None:
        """Verify derivative formula dG/dr = G(r) * (-1/r - j*k).

        The analytical derivative of the free-space Green's function is:
            dG/dr = G(r) * (-1/r - j*k)
        where k = 2*pi*f/c.
        """
        frequency = 1e9
        gf = GreensFunction(frequency=frequency)

        r_mag = 0.01  # metres

        result = gf.derivative(r_mag)

        # Compute expected value
        g_val = gf.evaluate(r_mag)
        k = 2 * np.pi * frequency / 299792458.0
        expected = g_val * (-1.0 / r_mag - 1j * k)

        assert isinstance(result, (complex, np.complexfloating)), \
            f"Expected complex, got {type(result)}"
        assert np.isclose(result, expected, rtol=1e-10), \
            f"dG/dr({r_mag}) = {result}, expected {expected}"

    def test_derivative_singularity_raises(self) -> None:
        """Verify derivative raises ValueError at r <= 0."""
        gf = GreensFunction(frequency=1e9)

        with pytest.raises(ValueError, match="non-zero"):
            gf.derivative(0.0)

        with pytest.raises(ValueError, match="non-zero"):
            gf.derivative(-0.001)


# ===================================================================
# Test GreenEvaluator caching
# ===================================================================

class TestGreenEvaluatorCaching:
    """Tests for the GreenEvaluator caching mechanism."""

    def test_green_evaluator_caching(self) -> None:
        """Verify cache hit returns same value.

        When the GreenEvaluator is called with the same source/observation
        points and frequency twice, the second call should return the exact
        same cached value (not re-evaluate).
        """
        gf = GreensFunction(frequency=1e9)
        evaluator = GreenEvaluator(greens_function=gf, cache_size=100)

        src = np.array([0.0, 0.0, 0.0])
        obs = np.array([0.01, 0.01, 0.0])

        # First evaluation (cache miss)
        val1 = evaluator.evaluate(src, obs, frequency=1e9)

        # Second evaluation with same points and frequency (cache hit)
        val2 = evaluator.evaluate(src, obs, frequency=1e9)

        assert np.isclose(val1, val2), \
            f"Cache miss! val1={val1}, val2={val2}"

        # Cache should have one entry now
        assert evaluator.cache_size == 1, \
            f"Expected cache size 1, got {evaluator.cache_size}"

    def test_green_evaluator_different_frequencies(self) -> None:
        """Verify caching distinguishes different frequencies."""
        gf = GreensFunction(frequency=1e9)
        evaluator = GreenEvaluator(greens_function=gf, cache_size=100)

        src = np.array([0.0, 0.0, 0.0])
        obs = np.array([0.01, 0.01, 0.0])

        val_1ghz = evaluator.evaluate(src, obs, frequency=1e9)
        val_2ghz = evaluator.evaluate(src, obs, frequency=2e9)

        # Different frequencies should produce different values
        assert not np.isclose(val_1ghz, val_2ghz), \
            "Different frequencies should give different Green's function values"

        # Cache should have two entries
        assert evaluator.cache_size == 2, \
            f"Expected cache size 2, got {evaluator.cache_size}"

    def test_green_evaluator_clear_cache(self) -> None:
        """Verify clear_cache() empties the cache."""
        gf = GreensFunction(frequency=1e9)
        evaluator = GreenEvaluator(greens_function=gf, cache_size=100)

        src = np.array([0.0, 0.0, 0.0])
        obs = np.array([0.01, 0.01, 0.0])

        # Fill the cache
        evaluator.evaluate(src, obs, frequency=1e9)
        assert evaluator.cache_size == 1

        # Clear and verify
        evaluator.clear_cache()
        assert evaluator.cache_size == 0, \
            f"Cache not cleared! Size = {evaluator.cache_size}"

    def test_green_evaluator_same_no_frequency(self) -> None:
        """Verify caching works when frequency is taken from gf.frequency."""
        gf = GreensFunction(frequency=1e9)
        evaluator = GreenEvaluator(greens_function=gf, cache_size=100)

        src = np.array([0.0, 0.0, 0.0])
        obs = np.array([0.05, 0.05, 0.0])

        val1 = evaluator.evaluate(src, obs)
        val2 = evaluator.evaluate(src, obs)

        assert np.isclose(val1, val2), \
            f"Cache miss without explicit frequency: {val1} vs {val2}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
