"""Unit tests for the MoM solver engine and its sub-components.

This module provides comprehensive pytest-based unit tests covering:

- EFIE, MFIE, and CFIE formulation self-term singularity handling
- CFIE coupling factor verification (alpha * EFIE + (1-alpha) * MFIE)
- RWG basis function direction and edge length evaluation
- Triangle geometric properties (area, centroid, normal)
- BasisFunctionManager add/retrieve/list operations

All tests are self-contained using only numpy and pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

# Import the modules under test
from src.core.mom_solver.formulation import (
    EFIEFormulation,
    MFIEFormulation,
    CFIEFormulation,
    FormulationType,
    get_formulation,
)
from src.core.mom_solver.basis_functions import Triangle, RWGBasisFunction, BasisFunctionManager


# ===================================================================
# Test EFIE formulation self-term singularity handling
# ===================================================================

class TestEFIESelfElement:
    """Tests for EFIE self-term (diagonal) singularity handling."""

    def test_efie_formulation_self_element(self) -> None:
        """Verify EFIE self-term singularity handling returns complex value.

        When source_triangle_idx == test_triangle_idx, the Green's function
        integral diverges. The formulation must return a regularised complex
        value (principal-value approximation), not raise or return NaN/Inf.
        """
        efie = EFIEFormulation()
        frequency = 1e9  # 1 GHz

        result = efie.compute_element(0, 0, frequency)

        # Must be a complex number
        assert isinstance(result, (complex, np.complexfloating)), \
            f"Expected complex, got {type(result)}"

        # Must not be NaN or Inf
        assert np.isfinite(result), \
            f"Self-term returned non-finite value: {result}"

        # The singularity handling returns -j*k/(8*pi) which is purely imaginary
        k = 2 * np.pi * frequency / 299792458.0
        expected_imag = -k / (8 * np.pi)
        assert np.isclose(result.imag, expected_imag, rtol=1e-10), \
            f"Imaginary part {result.imag} != expected {expected_imag}"

    def test_efie_off_diagonal_returns_complex(self) -> None:
        """Verify EFIE off-diagonal elements also return complex values."""
        efie = EFIEFormulation()
        frequency = 1e9

        result = efie.compute_element(0, 5, frequency)
        assert isinstance(result, (complex, np.complexfloating))
        assert np.isfinite(result), f"Off-diagonal returned non-finite: {result}"


# ===================================================================
# Test MFIE formulation self-term with 0.5 factor
# ===================================================================

class TestMFIESelfElement:
    """Tests for MFIE self-term (diagonal) with the half-current factor."""

    def test_mfie_formulation_self_element(self) -> None:
        """Verify MFIE self-term includes 0.5 factor.

        The MFIE formulation adds a 0.5 real offset to the principal-value
        Green's function for the diagonal element, arising from the limiting
        process of approaching the surface (the half-current term).
        """
        mfie = MFIEFormulation()
        frequency = 1e9

        result = mfie.compute_element(0, 0, frequency)

        # Must be complex
        assert isinstance(result, (complex, np.complexfloating))
        assert np.isfinite(result), f"Self-term returned non-finite: {result}"

        # Real part should contain the 0.5 factor from MFIE self-term
        expected_real = 0.5
        assert np.isclose(result.real, expected_real, rtol=1e-10), \
            f"Real part {result.real} != expected {expected_real}"

        # Imaginary part should match EFIE principal value
        k = 2 * np.pi * frequency / 299792458.0
        expected_imag = -k / (8 * np.pi)
        assert np.isclose(result.imag, expected_imag, rtol=1e-10), \
            f"Imaginary part {result.imag} != expected {expected_imag}"

    def test_mfie_off_diagonal_returns_complex(self) -> None:
        """Verify MFIE off-diagonal elements return complex values."""
        mfie = MFIEFormulation()
        frequency = 1e9

        result = mfie.compute_element(0, 3, frequency)
        assert isinstance(result, (complex, np.complexfloating))
        assert np.isfinite(result), f"Off-diagonal returned non-finite: {result}"


# ===================================================================
# Test CFIE coupling factor
# ===================================================================

class TestCFIECoupling:
    """Tests for CFIE formulation as a weighted combination of EFIE and MFIE."""

    def test_cfie_coupling(self) -> None:
        """Verify CFIE = alpha * EFIE + (1-alpha) * MFIE.

        The Combined Field Integral Equation combines EFIE and MFIE with
        a coupling factor alpha (default 0.5). For any source/test pair,
        the CFIE element must equal alpha * EFIE_element + (1-alpha) * MFIE_element.
        """
        alpha = 0.5
        cfie = CFIEFormulation(coupling_factor=alpha)
        efie = EFIEFormulation()
        mfie = MFIEFormulation()
        frequency = 1e9

        # Test self-term (diagonal)
        efie_self = efie.compute_element(0, 0, frequency)
        mfie_self = mfie.compute_element(0, 0, frequency)
        cfie_self = cfie.compute_element(0, 0, frequency)

        expected_cfie_self = alpha * efie_self + (1 - alpha) * mfie_self
        assert np.isclose(cfie_self, expected_cfie_self, rtol=1e-10), \
            f"CFIE self-term {cfie_self} != expected {expected_cfie_self}"

        # Test off-diagonal pair
        efie_off = efie.compute_element(0, 5, frequency)
        mfie_off = mfie.compute_element(0, 5, frequency)
        cfie_off = cfie.compute_element(0, 5, frequency)

        expected_cfie_off = alpha * efie_off + (1 - alpha) * mfie_off
        assert np.isclose(cfie_off, expected_cfie_off, rtol=1e-10), \
            f"CFIE off-diagonal {cfie_off} != expected {expected_cfie_off}"

    def test_cfie_weighting_factor(self) -> None:
        """Verify CFIE weighting factor returns the coupling factor."""
        for alpha in [0.3, 0.5, 0.7]:
            cfie = CFIEFormulation(coupling_factor=alpha)
            assert np.isclose(cfie.get_weighting_factor(), alpha), \
                f"Weighting factor {cfie.get_weighting_factor()} != {alpha}"


# ===================================================================
# Test RWG basis function evaluation
# ===================================================================

class TestRWGBasisFunction:
    """Tests for RWG basis function direction and edge length."""

    def test_rwgbasis_function_evaluation(self) -> None:
        """Test RWG basis function direction and edge length.

        The RWG basis function must return a valid direction vector and
        edge length consistent with its stub implementation.
        """
        rwg = RWGBasisFunction(edge_idx=0, source_triangle_idx=1)

        # Direction should be a numpy array of shape (3,)
        direction = rwg.get_direction()
        assert isinstance(direction, np.ndarray), \
            f"Direction should be np.ndarray, got {type(direction)}"
        assert direction.shape == (3,), \
            f"Direction shape {direction.shape} != (3,)"

        # Direction should be unit length (stub returns [1,0,0])
        assert np.isclose(np.linalg.norm(direction), 1.0), \
            f"Direction norm {np.linalg.norm(direction)} != 1.0"

        # Edge length should be a positive float
        edge_length = rwg.get_edge_length()
        assert isinstance(edge_length, (int, float, np.floating)), \
            f"Edge length should be numeric, got {type(edge_length)}"
        assert edge_length > 0.0, \
            f"Edge length {edge_length} is not positive"

        # Evaluate at an arbitrary point should return a complex number
        point = np.array([0.05, 0.02, 0.0])
        value = rwg.evaluate(point)
        assert isinstance(value, (complex, np.complexfloating)), \
            f"Evaluate returned {type(value)}, expected complex"

    def test_rwgbasis_function_attributes(self) -> None:
        """Test RWG basis function stores edge and triangle indices."""
        rwg = RWGBasisFunction(edge_idx=5, source_triangle_idx=3, test_triangle_idx=7)

        assert rwg.edge_idx == 5
        assert rwg.source_triangle_idx == 3
        assert rwg.test_triangle_idx == 7


# ===================================================================
# Test Triangle geometric properties
# ===================================================================

class TestTriangleProperties:
    """Tests for Triangle area, centroid, and normal computation."""

    def test_triangle_properties(self) -> None:
        """Test Triangle area, centroid, normal with known vertices.

        Uses a right triangle with vertices (0,0,0), (1,0,0), (0,1,0) to
        verify:
        - Area = 0.5 * |e0 x e1| = 0.5
        - Centroid = (v0 + v1 + v2) / 3 = (1/3, 1/3, 0)
        - Normal is a unit vector perpendicular to the plane
        """
        v0 = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        v2 = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        tri = Triangle(v0, v1, v2)

        # Area should be 0.5 (right triangle with legs of length 1)
        assert np.isclose(tri.area, 0.5), \
            f"Area {tri.area} != expected 0.5"

        # Centroid = (v0 + v1 + v2) / 3
        expected_centroid = (v0 + v1 + v2) / 3.0
        assert np.allclose(tri.centroid, expected_centroid), \
            f"Centroid {tri.centroid} != expected {expected_centroid}"

        # Normal should be unit vector perpendicular to xy plane => [0, 0, -1] or [0,0,1]
        normal = tri.normal
        assert np.isclose(np.linalg.norm(normal), 1.0), \
            f"Normal norm {np.linalg.norm(normal)} != 1.0"

        # Normal should be perpendicular to edge vectors
        e0 = v1 - v0
        e1 = v2 - v0
        assert np.isclose(np.dot(normal, e0), 0.0, atol=1e-10), \
            "Normal not perpendicular to e0"
        assert np.isclose(np.dot(normal, e1), 0.0, atol=1e-10), \
            "Normal not perpendicular to e1"

    def test_triangle_equilateral(self) -> None:
        """Test area computation for an equilateral triangle."""
        side = 2.0
        v0 = np.array([0.0, 0.0, 0.0])
        v1 = np.array([side, 0.0, 0.0])
        h = side * np.sqrt(3) / 2.0
        v2 = np.array([side / 2.0, h, 0.0])

        tri = Triangle(v0, v1, v2)

        # Area of equilateral triangle: (sqrt(3)/4) * side^2
        expected_area = (np.sqrt(3) / 4.0) * side ** 2
        assert np.isclose(tri.area, expected_area, rtol=1e-10), \
            f"Equilateral area {tri.area} != {expected_area}"

    def test_triangle_non_zero_normal(self) -> None:
        """Test that normal is computed correctly for non-degenerate triangles."""
        v0 = np.array([1.0, 2.0, 3.0])
        v1 = np.array([4.0, 5.0, 6.0])
        v2 = np.array([7.0, 8.0, 9.0])

        tri = Triangle(v0, v1, v2)

        assert np.isclose(np.linalg.norm(tri.normal), 1.0), \
            "Normal is not a unit vector for non-degenerate triangle"


# ===================================================================
# Test BasisFunctionManager
# ===================================================================

class TestBasisFunctionManager:
    """Tests for the BasisFunctionManager add/retrieve/list operations."""

    def test_basis_function_manager(self) -> None:
        """Test adding and retrieving basis functions.

        Verifies that:
        - Adding a basis function increments the count
        - Retrieving by index returns the correct RWGBasisFunction
        - list_basis_functions() returns sorted indices
        - __len__ returns the correct count
        """
        mgr = BasisFunctionManager(num_triangles=10, num_edges=5)

        # Initially empty
        assert len(mgr) == 0, f"Expected 0 basis functions initially, got {len(mgr)}"

        # Add several basis functions
        for i in range(5):
            idx = mgr.add_basis_function(edge_idx=i, source_triangle=i % 10)
            assert idx == i, f"add_basis_function returned {idx}, expected {i}"

        # Now should have 5 basis functions
        assert len(mgr) == 5, f"Expected 5 basis functions, got {len(mgr)}"

        # Retrieve and verify
        bf = mgr.get_basis_function(0)
        assert bf is not None, "get_basis_function(0) returned None"
        assert bf.edge_idx == 0
        assert bf.source_triangle_idx == 0

        bf3 = mgr.get_basis_function(3)
        assert bf3 is not None
        assert bf3.edge_idx == 3
        assert bf3.source_triangle_idx == 3

        # Retrieving a non-existent index should return None
        assert mgr.get_basis_function(100) is None, \
            "get_basis_function(100) should return None"

        # list_basis_functions should return sorted indices
        indices = mgr.list_basis_functions()
        assert indices == [0, 1, 2, 3, 4], \
            f"list_basis_functions returned {indices}, expected [0,1,2,3,4]"

    def test_basis_function_manager_overwrite(self) -> None:
        """Test that adding with the same edge_idx overwrites the previous entry."""
        mgr = BasisFunctionManager(num_triangles=5, num_edges=5)

        mgr.add_basis_function(edge_idx=0, source_triangle=1)
        mgr.add_basis_function(edge_idx=0, source_triangle=2)

        bf = mgr.get_basis_function(0)
        assert bf is not None
        assert bf.source_triangle_idx == 2, \
            f"Expected overwritten source_triangle_idx=2, got {bf.source_triangle_idx}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
