"""
Tests for S-Parameter Computation Module
=========================================

Unit tests for SParameterCalculator and MultiPortExcitation classes.
Tests cover single-frequency computation, frequency sweeps, reciprocity
validation, passivity checks, and multi-port excitation management.

Run with:
    pytest tests/unit/test_sparams.py -v


Module structure
----------------
- test_compute_S_parameters_single_frequency : Z-to-S conversion correctness
- test_validate_reciprocity                  : Symmetric vs asymmetric S-matrices
- test_validate_passivity                    : Passive (lossy) vs active (gain)
- test_compute_S_sweep                       : Frequency sweep result count
"""

from __future__ import annotations

import numpy as np
import pytest

from src.core.sparams_computation import (
    SParameterCalculator,
    MultiPortExcitation,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def calc_2port() -> SParameterCalculator:
    """A 2-port S-parameter calculator."""
    return SParameterCalculator(n_ports=2)


@pytest.fixture
def calc_3port() -> SParameterCalculator:
    """A 3-port S-parameter calculator."""
    return SParameterCalculator(n_ports=3)


@pytest.fixture
def exc_2port() -> MultiPortExcitation:
    """A 2-port multi-port excitation system."""
    return MultiPortExcitation(n_ports=2)


# ---------------------------------------------------------------------------
# test_compute_S_parameters_single_frequency
# ---------------------------------------------------------------------------


def test_compute_S_parameters_single_frequency(calc_2port) -> None:
    """
    Test single-frequency S-parameter computation with a known Z-matrix.

    Verifies that:
        1. The returned S-matrix has the correct dimensions (N x N).
        2. Diagonal elements are physically reasonable (|S_ii| <= 1 for passive).
        3. A perfectly matched load yields S = 0 matrix.
        4. An open/short circuit yields physically expected reflection coefficients.
    """
    # Case 1: Matched load -- Z = Z_ref * I should give S = 0
    Z_ref_val = 50.0
    Z_matched = np.eye(2) * Z_ref_val
    port_impedances = [Z_ref_val, Z_ref_val]
    S = calc_2port.compute_S_parameters(Z_matched, port_impedances, frequency_Hz=1e9)

    assert S.shape == (2, 2), "S-matrix should be 2x2"
    assert np.allclose(S, np.zeros((2, 2))), (
        f"Matched load should yield S=0. Got:\n{S}"
    )

    # Case 2: Open circuit at port 1, matched at port 2
    # Z = [[infinite, 0], [0, 50]] -> approximate with large value
    Z_open = np.array([[1e6, 0.0], [0.0, 50.0]], dtype=float)
    S_open = calc_2port.compute_S_parameters(Z_open, port_impedances, 1e9)

    assert S_open.shape == (2, 2), "S-matrix should be 2x2"
    # Port 1 open -> |S_11| ~ 1 (total reflection)
    assert np.isclose(np.abs(S_open[0, 0]), 1.0, atol=1e-3), (
        f"Open circuit port 1 should have |S_11| ~ 1. Got {np.abs(S_open[0, 0])}"
    )
    # Port 2 matched -> S_22 ~ 0
    assert np.isclose(np.abs(S_open[1, 1]), 0.0, atol=1e-3), (
        f"Matched port 2 should have |S_22| ~ 0. Got {np.abs(S_open[1, 1])}"
    )

    # Case 3: General passive network with lossy diagonal
    Z_lossy = np.array([[60.0, 15.0], [15.0, 60.0]], dtype=float)
    S_lossy = calc_2port.compute_S_parameters(Z_lossy, port_impedances, 1e9)

    assert S_lossy.shape == (2, 2), "S-matrix should be 2x2"
    # Diagonal elements should have magnitude <= 1 for passive system
    assert np.abs(S_lossy[0, 0]) <= 1.0 + 1e-6, (
        f"|S_11| = {np.abs(S_lossy[0, 0])} exceeds 1"
    )
    assert np.abs(S_lossy[1, 1]) <= 1.0 + 1e-6, (
        f"|S_22| = {np.abs(S_lossy[1, 1])} exceeds 1"
    )

    # Case 4: Verify that all S-parameter magnitudes are bounded for passive system
    calc_3port = SParameterCalculator(n_ports=3)
    Z_passive = np.array(
        [[55.0, 8.0, 5.0], [8.0, 55.0, 8.0], [5.0, 8.0, 55.0]], dtype=float
    )
    imp_3 = [50.0, 50.0, 50.0]
    S_3p = calc_3port.compute_S_parameters(Z_passive, imp_3, 1e9)

    assert S_3p.shape == (3, 3), "3-port S-matrix should be 3x3"
    for i in range(3):
        for j in range(3):
            assert np.abs(S_3p[i, j]) <= 1.0 + 1e-6, (
                f"|S_{i+1}{j+1}| = {np.abs(S_3p[i, j])} exceeds 1"
            )


# ---------------------------------------------------------------------------
# test_validate_reciprocity
# ---------------------------------------------------------------------------


def test_validate_reciprocity(calc_2port) -> None:
    """
    Test reciprocity check on symmetric (reciprocal) and asymmetric (non-
    reciprocal) S matrices.

    Verifies that:
        1. Symmetric S-matrices are correctly identified as reciprocal.
        2. Asymmetric S-matrices are correctly identified as non-reciprocal.
        3. Near-symmetric matrices with small numerical noise are still reciprocal.
    """
    # Case 1: Perfectly symmetric (reciprocal) matrix
    S_reciprocal = np.array([[0.1, 0.5], [0.5, 0.1]], dtype=float)
    assert calc_2port.validate_reciprocity(S_reciprocal) is True, (
        "Symmetric matrix should be reciprocal"
    )

    # Case 2: Asymmetric matrix (non-reciprocal, e.g., circulator)
    S_nonreciprocal = np.array([[0.0, 0.8], [0.0, 0.0]], dtype=float)
    assert calc_2port.validate_reciprocity(S_nonreciprocal) is False, (
        "Asymmetric matrix should not be reciprocal"
    )

    # Case 3: Near-symmetric with small numerical noise (should still pass)
    S_noisy = np.array(
        [[0.1, 0.5 + 1e-8], [0.5 + 2e-8, 0.1]], dtype=float
    )
    assert calc_2port.validate_reciprocity(S_noisy) is True, (
        "Near-symmetric matrix with small noise should be reciprocal"
    )

    # Case 4: Larger asymmetry (should fail)
    S_large_asym = np.array(
        [[0.1, 0.5], [0.5 + 1e-3, 0.1]], dtype=float
    )
    assert calc_2port.validate_reciprocity(S_large_asym) is False, (
        "Matrix with significant asymmetry should not be reciprocal"
    )

    # Case 5: 3-port symmetric matrix (e.g., lossless junction)
    S_3p_sym = np.array(
        [[0.0, 0.4, 0.4], [0.4, 0.0, 0.4], [0.4, 0.4, 0.0]], dtype=float
    )
    assert calc_2port.validate_reciprocity(S_3p_sym) is True, (
        "3-port symmetric matrix should be reciprocal"
    )


# ---------------------------------------------------------------------------
# test_validate_passivity
# ---------------------------------------------------------------------------


def test_validate_passivity(calc_2port) -> None:
    """
    Test passivity check on passive (lossy) and active (gain) systems.

    Verifies that:
        1. Lossy passive networks correctly identified as passive.
        2. Active (gain) networks correctly identified as non-passive.
        3. Lossless (unitary) S-matrices are correctly identified as passive.
    """
    # Case 1: Lossy passive network -- all singular values <= 1
    S_lossy = np.array([[0.3, 0.4], [0.4, 0.3]], dtype=float)
    assert calc_2port.validate_passivity(S_lossy) is True, (
        "Lossy passive network should be passive"
    )

    # Case 2: Active (gain) network -- singular value > 1
    S_active = np.array([[2.0, 0.0], [0.0, 2.0]], dtype=float)
    assert calc_2port.validate_passivity(S_active) is False, (
        "Active (gain) network should not be passive"
    )

    # Case 3: Lossless (unitary) S-matrix -- singular values = 1
    # Orthogonal matrix with eigenvalues +/-1 => singular values exactly 1
    S_lossless = np.array([[0.6, 0.8], [0.8, -0.6]], dtype=float)
    assert calc_2port.validate_passivity(S_lossless) is True, (
        "Lossless (unitary) network should be passive"
    )

    # Case 4: Identity matrix (perfect reflection, singular value = 1)
    S_identity = np.eye(2)
    assert calc_2port.validate_passivity(S_identity) is True, (
        "Identity S-matrix (|S|=1) should be passive"
    )

    # Case 5: Near-identity with tiny numerical noise
    S_nearly_identity = np.eye(2) + 1e-12
    assert calc_2port.validate_passivity(S_nearly_identity) is True, (
        "Near-identity matrix should still be passive"
    )

    # Case 6: Mixed -- one port active, one passive
    S_mixed = np.array([[0.5, 0.1], [0.1, 1.5]], dtype=float)
    sv = np.linalg.svd(S_mixed, compute_uv=False)
    is_passive = calc_2port.validate_passivity(S_mixed)
    # At least one singular value > 1 means non-passive
    if np.max(sv) > 1.0 + 1e-10:
        assert is_passive is False, (
            "Mixed active/passive system with max SV > 1 should not be passive"
        )


# ---------------------------------------------------------------------------
# test_compute_S_sweep
# ---------------------------------------------------------------------------


def test_compute_S_sweep(calc_2port) -> None:
    """
    Test frequency sweep produces correct number of results.

    Verifies that:
        1. The sweep returns the correct number of frequency points.
        2. Each S-parameter matrix in the sweep has correct dimensions.
        3. Frequencies are sorted in ascending order.
        4. A single-frequency sweep works correctly.
    """
    # Case 1: Multi-frequency sweep (5 frequencies)
    num_freqs = 5
    freqs = np.linspace(1e9, 2e9, num_freqs)
    Z_ref_val = 50.0

    # Build Z-matrices dictionary: each has the same Z (matched load)
    Z_matrices: dict[float, np.ndarray] = {}
    for f in freqs:
        Z_matrices[float(f)] = np.eye(2) * Z_ref_val

    port_impedances = [Z_ref_val, Z_ref_val]
    result = calc_2port.compute_S_sweep(Z_matrices, port_impedances)

    assert "frequencies" in result, "Result should contain 'frequencies' key"
    assert "S_params" in result, "Result should contain 'S_params' key"

    freqs_out = result["frequencies"]
    S_params = result["S_params"]

    # Verify number of frequencies
    assert len(freqs_out) == num_freqs, (
        f"Sweep should return {num_freqs} frequencies, got {len(freqs_out)}"
    )

    # Verify frequencies are sorted ascending
    assert np.all(np.diff(freqs_out) > 0), "Frequencies should be sorted ascending"

    # Verify each S-matrix has correct dimensions and is zero (matched load)
    for freq, S_mat in S_params.items():
        assert S_mat.shape == (2, 2), f"S-matrix at {freq} Hz should be 2x2"
        assert np.allclose(S_mat, np.zeros((2, 2))), (
            f"Matched load sweep at {freq} Hz should yield S=0"
        )

    # Case 2: Single-frequency sweep
    Z_single = {1e9: np.array([[60.0, 15.0], [15.0, 60.0]], dtype=float)}
    result_single = calc_2port.compute_S_sweep(Z_single, port_impedances)

    assert len(result_single["frequencies"]) == 1, (
        "Single-frequency sweep should return 1 frequency"
    )
    assert len(result_single["S_params"]) == 1, (
        "Single-frequency sweep should return 1 S-matrix"
    )

    # Case 3: Verify that computed S-values match single-frequency computation
    Z_mat = np.array([[60.0, 15.0], [15.0, 60.0]], dtype=float)
    S_single = calc_2port.compute_S_parameters(Z_mat, port_impedances, 1e9)
    S_sweep_val = list(result_single["S_params"].values())[0]

    assert np.allclose(S_single, S_sweep_val), (
        "Sweep result should match single-frequency computation"
    )
