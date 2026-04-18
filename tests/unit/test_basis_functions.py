"""Unit tests for RWG basis functions and triangle geometry.

This module provides comprehensive pytest-based unit tests covering:

- Triangle area computation using the cross-product formula
- Triangle centroid as the average of vertices
- Triangle normal as a unit vector perpendicular to edges
- RWGBasisFunction direction, edge length, and evaluate methods

All tests are self-contained using only numpy and pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

# Import the modules under test
from src.core.mom_solver.basis_functions import Triangle, RWGBasisFunction


# ===================================================================
# Test Triangle area computation
# ===================================================================

class TestTriangleArea:
    """Tests for Triangle area computation."""

    def test_triangle_area_computation(self) -> None:
        """Verify area = 0.5 * |e0 x e1| for a known triangle.

        Uses vertices (0,0,0), (1,0,0), (0,1,0) which form a right triangle
        with area = 0.5 * |(1,0,0) x (0,1,0)| = 0.5 * |[0,0,1]| = 0.5.
        """
        v0 = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        v2 = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        tri = Triangle(v0, v1, v2)

        # Compute expected area manually: 0.5 * |e0 x e1|
        e0 = v1 - v0
        e1 = v2 - v0
        cross = np.cross(e0, e1)
        expected_area = 0.5 * np.linalg.norm(cross)

        assert isinstance(tri.area, float), \
            f"Area should be float, got {type(tri.area)}"
        assert tri.area > 0.0, \
            f"Area {tri.area} is not positive for non-degenerate triangle"
        assert np.isclose(tri.area, expected_area, rtol=1e-10), \
            f"Triangle area {tri.area} != expected {expected_area}"

    def test_triangle_area_right_triangle(self) -> None:
        """Verify area of a right triangle with legs a and b is (a*b)/2."""
        # Right triangle with legs 3 and 4, area = 6
        v0 = np.array([0.0, 0.0, 0.0])
        v1 = np.array([3.0, 0.0, 0.0])
        v2 = np.array([0.0, 4.0, 0.0])

        tri = Triangle(v0, v1, v2)

        expected_area = (3.0 * 4.0) / 2.0  # = 6.0
        assert np.isclose(tri.area, expected_area, rtol=1e-10), \
            f"Right triangle area {tri.area} != expected {expected_area}"

    def test_triangle_area_scalings(self) -> None:
        """Verify area scales quadratically with uniform scaling."""
        v0 = np.array([0.0, 0.0, 0.0])
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])

        tri_small = Triangle(v0, v1, v2)

        # Scale by factor of 2: area should quadruple
        v0_s = np.array([0.0, 0.0, 0.0])
        v1_s = np.array([2.0, 0.0, 0.0])
        v2_s = np.array([0.0, 2.0, 0.0])

        tri_large = Triangle(v0_s, v1_s, v2_s)

        assert np.isclose(tri_large.area, 4 * tri_small.area, rtol=1e-10), \
            f"Scaled area {tri_large.area} != 4 * small_area {4 * tri_small.area}"


# ===================================================================
# Test Triangle centroid
# ===================================================================

class TestTriangleCentroid:
    """Tests for Triangle centroid computation."""

    def test_triangle_centroid(self) -> None:
        """Verify centroid = (v0 + v1 + v2) / 3.

        The centroid of a triangle is the arithmetic mean of its three vertices.
        This test uses arbitrary vertex coordinates to verify the formula.
        """
        v0 = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        v1 = np.array([4.0, 5.0, 6.0], dtype=np.float64)
        v2 = np.array([7.0, 8.0, 9.0], dtype=np.float64)

        tri = Triangle(v0, v1, v2)

        expected_centroid = (v0 + v1 + v2) / 3.0

        assert isinstance(tri.centroid, np.ndarray), \
            f"Centroid should be np.ndarray, got {type(tri.centroid)}"
        assert tri.centroid.shape == (3,), \
            f"Centroid shape {tri.centroid.shape} != (3,)"

        assert np.allclose(tri.centroid, expected_centroid), \
            f"Centroid {tri.centroid} != expected {expected_centroid}"

    def test_triangle_centroid_origin(self) -> None:
        """Verify centroid when one vertex is at origin."""
        v0 = np.array([0.0, 0.0, 0.0])
        v1 = np.array([3.0, 0.0, 0.0])
        v2 = np.array([0.0, 3.0, 0.0])

        tri = Triangle(v0, v1, v2)

        expected_centroid = (v0 + v1 + v2) / 3.0  # [1, 1, 0]
        assert np.allclose(tri.centroid, expected_centroid), \
            f"Centroid {tri.centroid} != expected {expected_centroid}"


# ===================================================================
# Test Triangle normal
# ===================================================================

class TestTriangleNormal:
    """Tests for Triangle normal vector computation."""

    def test_triangle_normal(self) -> None:
        """Verify normal is a unit vector perpendicular to edges.

        For the triangle with vertices (0,0,0), (1,0,0), (0,1,0):
        - Edge vectors are e0 = (1,0,0) and e1 = (0,1,0)
        - Normal should be parallel to (0,0,1) or (0,0,-1)
        - Normal must have unit length
        """
        v0 = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        v1 = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        v2 = np.array([0.0, 1.0, 0.0], dtype=np.float64)

        tri = Triangle(v0, v1, v2)

        # Normal must be a unit vector
        assert isinstance(tri.normal, np.ndarray), \
            f"Normal should be np.ndarray, got {type(tri.normal)}"
        normal_norm = np.linalg.norm(tri.normal)
        assert np.isclose(normal_norm, 1.0, atol=1e-10), \
            f"Normal norm {normal_norm} != 1.0"

        # Normal must be perpendicular to edge vectors
        e0 = v1 - v0
        e1 = v2 - v0

        dot_0 = np.dot(tri.normal, e0)
        dot_1 = np.dot(tri.normal, e1)

        assert np.isclose(dot_0, 0.0, atol=1e-10), \
            f"Normal not perpendicular to e0: dot = {dot_0}"
        assert np.isclose(dot_1, 0.0, atol=1e-10), \
            f"Normal not perpendicular to e1: dot = {dot_1}"

    def test_triangle_normal_z_rotation(self) -> None:
        """Verify normal rotates correctly when vertices are rotated around z-axis."""
        # Triangle in xy plane, normal should point along +z or -z
        v0 = np.array([0.0, 0.0, 0.0])
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])

        tri_1 = Triangle(v0, v1, v2)

        # Same triangle rotated 90 degrees around z-axis
        v0_r = np.array([0.0, 0.0, 0.0])
        v1_r = np.array([0.0, 1.0, 0.0])
        v2_r = np.array([-1.0, 0.0, 0.0])

        tri_2 = Triangle(v0_r, v1_r, v2_r)

        # Both normals should be perpendicular to their respective planes (xy plane)
        assert np.isclose(abs(tri_1.normal[2]), 1.0, atol=1e-10), \
            "Normal of xy-plane triangle not aligned with z-axis"
        assert np.isclose(abs(tri_2.normal[2]), 1.0, atol=1e-10), \
            "Rotated triangle normal not aligned with z-axis"


# ===================================================================
# Test RWGBasisFunction properties
# ===================================================================

class TestRWGBasisFunctionProperties:
    """Tests for RWGBasisFunction direction, edge length, and evaluate."""

    def test_rwgbasis_function_properties(self) -> None:
        """Test RWGBasisFunction direction, edge length, and evaluate.

        Verifies that the RWG basis function stub returns valid values for:
        - get_direction(): a unit vector along the x-axis
        - get_edge_length(): a positive float
        - evaluate(point): a complex number
        """
        rwg = RWGBasisFunction(edge_idx=0, source_triangle_idx=1)

        # Test direction
        direction = rwg.get_direction()
        assert isinstance(direction, np.ndarray), \
            f"Direction should be np.ndarray, got {type(direction)}"
        assert direction.shape == (3,), \
            f"Direction shape {direction.shape} != (3,)"

        # Direction should have unit length (stub returns [1, 0, 0])
        assert np.isclose(np.linalg.norm(direction), 1.0, atol=1e-10), \
            f"Direction norm {np.linalg.norm(direction)} != 1.0"

        # Test edge length
        edge_length = rwg.get_edge_length()
        assert isinstance(edge_length, (int, float, np.floating)), \
            f"Edge length should be numeric, got {type(edge_length)}"
        assert edge_length > 0.0, \
            f"Edge length {edge_length} is not positive"

        # Test evaluate at arbitrary point
        test_point = np.array([0.05, 0.02, 0.0], dtype=np.float64)
        value = rwg.evaluate(test_point)

        assert isinstance(value, (complex, np.complexfloating)), \
            f"Evaluate returned {type(value)}, expected complex"
        assert np.isfinite(value), \
            f"Evaluate at {test_point} returned non-finite: {value}"

    def test_rwgbasis_function_different_indices(self) -> None:
        """Test RWGBasisFunction with different edge and triangle indices."""
        rwg = RWGBasisFunction(edge_idx=10, source_triangle_idx=5, test_triangle_idx=7)

        assert rwg.edge_idx == 10
        assert rwg.source_triangle_idx == 5
        assert rwg.test_triangle_idx == 7
        assert 5 in rwg.support_region
        assert 7 in rwg.support_region

    def test_rwgbasis_function_default_test_index(self) -> None:
        """Test that test_triangle_idx defaults to source_triangle_idx."""
        rwg = RWGBasisFunction(edge_idx=0, source_triangle_idx=3)

        assert rwg.test_triangle_idx == 3, \
            f"test_triangle_idx should default to {rwg.source_triangle_idx}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
