"""RWG (Rao-Wilton-Glisson) basis functions for MoM triangular meshes.

The RWG basis function is defined on a pair of adjacent triangles sharing a common edge.
It provides a continuous tangential current distribution across the triangle boundary,
making it ideal for surface integral equation methods.

For triangle *T_a* (positive support) and triangle *T_b* (negative support) sharing edge E:

    psi_n(r) = { l_n / 2|T_a|   if r in T_a
               - l_n / 2|T_b|   if r in T_b
                0              otherwise }

where :math:`l_n` is the length of the shared edge and :math:`|T|` is the triangle area.

Example usage::

    from src.core.mom_solver.basis_functions import Triangle, RWGBasisFunction
    import numpy as np

    v0 = np.array([0.0, 0.0, 0.0])
    v1 = np.array([0.1, 0.0, 0.0])
    v2 = np.array([0.0, 0.1, 0.0])
    tri = Triangle(v0, v1, v2)
    print(f"Area: {tri.area:.6f}")

    rwg = RWGBasisFunction(edge_idx=0, source_triangle_idx=0)
    print(f"Direction: {rwg.get_direction()}")
"""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


# ===================================================================
# Triangle class
# ===================================================================

@dataclass
class Triangle:
    """Represents a single triangular mesh element.

    Parameters
    ----------
    v0 : array_like shape (3,)
        First vertex coordinates (x, y, z).
    v1 : array_like shape (3,)
        Second vertex coordinates (x, y, z).
    v2 : array_like shape (3,)
        Third vertex coordinates (x, y, z).
    """

    v0: np.ndarray = field(default_factory=lambda: np.zeros(3))
    v1: np.ndarray = field(default_factory=lambda: np.zeros(3))
    v2: np.ndarray = field(default_factory=lambda: np.zeros(3))
    area: float = 0.0
    centroid: np.ndarray = field(default_factory=lambda: np.zeros(3))
    normal: np.ndarray = field(default_factory=lambda: np.zeros(3))

    def __post_init__(self) -> None:
        """Compute derived properties from vertex coordinates."""
        v0, v1, v2 = (
            np.asarray(self.v0, dtype=np.float64),
            np.asarray(self.v1, dtype=np.float64),
            np.asarray(self.v2, dtype=np.float64),
        )

        # Centroid
        self.centroid = (v0 + v1 + v2) / 3.0

        # Edge vectors
        e0 = v1 - v0  # edge from v0 to v1
        e1 = v2 - v0  # edge from v0 to v2

        # Area = 0.5 * |e0 x e1|
        cross = np.cross(e0, e1)
        self.area = 0.5 * np.linalg.norm(cross)

        # Normal (unit vector)
        if self.area > 1e-15:
            self.normal = cross / np.linalg.norm(cross)
        else:
            self.normal = np.array([0.0, 0.0, 1.0])

    def edge_vectors(self) -> list[np.ndarray]:
        """Return the three edge vectors of the triangle.

        Returns
        -------
        list[np.ndarray]
            Edge vectors [v1-v0, v2-v1, v0-v2].
        """
        return [
            self.v1 - self.v0,
            self.v2 - self.v1,
            self.v0 - self.v2,
        ]

    def edge_lengths(self) -> np.ndarray:
        """Return the three edge lengths.

        Returns
        -------
        np.ndarray
            Array of shape (3,) with edge lengths [len(v0->v1), len(v1->v2), len(v2->v0)].
        """
        edges = self.edge_vectors()
        return np.array([np.linalg.norm(e) for e in edges])

    def longest_edge(self) -> np.ndarray:
        """Return the longest edge vector.

        Returns
        -------
        np.ndarray
            The longest edge vector (v_j - v_i).
        """
        lengths = self.edge_lengths()
        idx = np.argmax(lengths)
        return self.edge_vectors()[idx]

    def is_edge_shared_with(self, other_triangle_idx: int) -> bool:
        """Check if this triangle shares an edge with another (by index comparison).

        In a full mesh context this would check adjacency through the topology graph.
        For stub purposes we compare indices as a placeholder.

        Parameters
        ----------
        other_triangle_idx : int
            Index of the other triangle.

        Returns
        -------
        bool
            True if the triangles share an edge (stub: always False).
        """
        return False

    def __repr__(self) -> str:
        return f"Triangle(area={self.area:.6e}, centroid={self.centroid})"


# ===================================================================
# RWG Basis Function class
# ===================================================================

class RWGBasisFunction:
    """Rao-Wilton-Glisson (RWG) basis function on a triangular mesh.

    The RWG basis function is defined over two adjacent triangles sharing a common edge.
    It provides a piecewise-linear, continuous tangential current distribution.

    For triangle T_a (positive support) and triangle T_b (negative support):

        psi_n(r) = { l_n / (2|T_a|)  if r in T_a
                   - l_n / (2|T_b|)  if r in T_b
                    0                otherwise }

    where :math:`l_n` is the shared edge length and :math:`|T|` is the triangle area.

    Parameters
    ----------
    edge_idx : int
        Index of the shared edge within the mesh edge list.
    source_triangle_idx : int
        Index of the positive-support (source) triangle.
    test_triangle_idx : int, optional
        Index of the test (weighting) triangle. Defaults to *source_triangle_idx*.
    """

    def __init__(
        self,
        edge_idx: int,
        source_triangle_idx: int,
        test_triangle_idx: Optional[int] = None,
    ) -> None:
        self.edge_idx = edge_idx
        self.source_triangle_idx = source_triangle_idx
        self.test_triangle_idx = (
            source_triangle_idx if test_triangle_idx is None else test_triangle_idx
        )
        self.support_region: list[int] = [self.source_triangle_idx, self.test_triangle_idx]

    def evaluate(self, point: np.ndarray) -> complex:
        """Evaluate the RWG basis function at a given point.

        In the full implementation this would check whether *point* lies within
        either support triangle and return the appropriate amplitude.  This stub
        returns a placeholder value.

        Parameters
        ----------
        point : array_like shape (3,)
            Observation point in Cartesian coordinates.

        Returns
        -------
        complex
            Basis function amplitude at *point*.
        """
        # Stub: return unit amplitude; real implementation checks barycentric coords
        return 1.0 + 0j

    def get_direction(self) -> np.ndarray:
        """Return the direction vector along the shared edge.

        Returns
        -------
        np.ndarray
            Unit vector pointing from the negative-support triangle toward
            the positive-support triangle (along the shared edge).
        """
        return np.array([1.0, 0.0, 0.0])

    def get_edge_length(self) -> float:
        """Return the length of the shared edge.

        Returns
        -------
        float
            Edge length in metres (stub value).
        """
        return 1e-3  # placeholder

    def __repr__(self) -> str:
        return (
            f"RWGBasisFunction(edge={self.edge_idx}, "
            f"src={self.source_triangle_idx}, test={self.test_triangle_idx})"
        )


# ===================================================================
# Basis function manager
# ===================================================================

class BasisFunctionManager:
    """Manages a collection of RWG basis functions for a mesh.

    Parameters
    ----------
    num_triangles : int
        Number of triangles in the mesh.
    num_edges : int
        Number of internal (shared) edges.
    """

    def __init__(self, num_triangles: int = 0, num_edges: int = 0) -> None:
        self.num_triangles = num_triangles
        self.num_edges = num_edges
        self._basis_functions: dict[int, RWGBasisFunction] = {}

    def add_basis_function(self, edge_idx: int, source_triangle: int) -> int:
        """Register a new RWG basis function.

        Parameters
        ----------
        edge_idx : int
            Index of the shared edge.
        source_triangle : int
            Index of the positive-support triangle.

        Returns
        -------
        int
            The basis function index (same as *edge_idx*).
        """
        bf = RWGBasisFunction(edge_idx, source_triangle)
        self._basis_functions[edge_idx] = bf
        return edge_idx

    def get_basis_function(self, idx: int) -> Optional[RWGBasisFunction]:
        """Retrieve a basis function by index.

        Parameters
        ----------
        idx : int
            Basis function (edge) index.

        Returns
        -------
        RWGBasisFunction or None
            The basis function if found.
        """
        return self._basis_functions.get(idx)

    def list_basis_functions(self) -> list[int]:
        """Return all registered basis function indices.

        Returns
        -------
        list[int]
            Sorted list of edge indices.
        """
        return sorted(self._basis_functions.keys())

    def __len__(self) -> int:
        return len(self._basis_functions)


# ===================================================================
# Module-level example usage
# ===================================================================

if __name__ == "__main__":
    print("=== RWG Basis Functions ===\n")

    # Triangle creation
    v0 = np.array([0.0, 0.0, 0.0])
    v1 = np.array([0.1, 0.0, 0.0])
    v2 = np.array([0.0, 0.1, 0.0])
    tri = Triangle(v0, v1, v2)
    print(f"Triangle: {tri}")
    print(f"  Area:     {tri.area:.6e}")
    print(f"  Centroid: {tri.centroid}")
    print(f"  Normal:   {tri.normal}")
    print(f"  Edges:    {tri.edge_lengths()}")

    # RWG basis function
    rwg = RWGBasisFunction(edge_idx=0, source_triangle_idx=0)
    print(f"\nRWG Basis Function: {rwg}")
    print(f"  Direction: {rwg.get_direction()}")
    print(f"  Evaluate at [0.05, 0.02, 0]: {rwg.evaluate(np.array([0.05, 0.02, 0]))}")

    # Manager
    mgr = BasisFunctionManager(num_triangles=100, num_edges=150)
    for i in range(5):
        mgr.add_basis_function(i, i % 100)
    print(f"\nBasis Function Manager: {len(mgr)} functions")
    print(f"Registered indices: {mgr.list_basis_functions()}")
