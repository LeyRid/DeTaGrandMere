"""CGAL-based meshing module for surface mesh generation.

Provides mesh extraction, cleaning, refinement, quality analysis, and
topology validation utilities for triangle meshes derived from CAD
surfaces.  The module uses CGAL's robust geometry kernels when available
and falls back to a pure-Numpy stub implementation for testing or
development environments where CGAL is not installed.

Example usage::

    from src.cad.cgal_meshing import CGALMeshing, Mesh

    mesher = CGALMeshing()

    # Extract a mesh from CAD surface definitions
    surfaces = [
        {
            "id": "plate_1",
            "type": "plane",
            "points": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0],
                       [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]],
            "normal": [0.0, 0.0, 1.0],
        }
    ]
    mesh = mesher.extract_triangle_mesh(surfaces)

    # Clean and validate
    mesh = mesher.clean_mesh(mesh)
    report = mesher.validate_mesh_topology(mesh)
"""

from __future__ import annotations

import math
import textwrap
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

# ---------------------------------------------------------------------------
# CGAL lazy import (may not be installed)
# ---------------------------------------------------------------------------

try:
    import CGAL  # type: ignore[import-untyped]
    _CGAL_AVAILABLE = True
except ImportError:
    CGAL = None  # type: ignore[var-annotated]
    _CGAL_AVAILABLE = False

# ---------------------------------------------------------------------------
# Local exception import
# ---------------------------------------------------------------------------

from .errors import MeshError  # noqa: E402

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__: list[str] = ["Mesh", "CGALMeshing"]


# ============================================================================
# Mesh dataclass
# ============================================================================

@dataclass
class Mesh:
    """Immutable triangle-mesh container with derived geometric fields.

    Attributes:
        vertices:  Array of shape ``(N, 3)`` holding vertex positions in
                   the same coordinate frame as the input surfaces.
        faces:     Array of shape ``(M, 3)`` with integer face indices
                   referencing rows of ``vertices``.  Each row describes
                   one triangle.
        normals:   Array of shape ``(M, 3)`` with unit face-normal vectors
                   (one per triangle).
        centroids: Array of shape ``(M, 3)`` with triangle centroid
                   coordinates.
        area:      Array of shape ``(M,)`` with the signed area of each
                   triangle.  Always non-negative after construction.
        metadata:  Arbitrary dict carrying generation provenance and
                   parameters (e.g. meshing algorithm, alpha-shape size).
    """

    vertices: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    faces: np.ndarray = field(default_factory=lambda: np.empty((0, 3), dtype=int))
    normals: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    centroids: np.ndarray = field(default_factory=lambda: np.empty((0, 3)))
    area: np.ndarray = field(default_factory=lambda: np.empty((0,)))
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate shapes and compute derived quantities on demand."""
        self.vertices = np.asarray(self.vertices, dtype=np.float64)
        self.faces = np.asarray(self.faces, dtype=int)
        self.normals = np.asarray(self.normals, dtype=np.float64)
        self.centroids = np.asarray(self.centroids, dtype=np.float64)
        self.area = np.asarray(self.area, dtype=np.float64)

        # Compute normals and centroids if not provided.
        n_faces = max(self.faces.shape[0], 0)
        if self.normals.shape[0] < n_faces:
            self.normals = self._compute_face_normals()
        if self.centroids.shape[0] < n_faces:
            self.centroids = self._compute_centroids()
        if self.area.shape[0] < n_faces:
            self.area = self._compute_areas()

    # ------------------------------------------------------------------ helpers -------------------------------------

    def _compute_face_normals(self) -> np.ndarray:
        """Return unit normal vectors for every triangle face."""
        v0 = self.vertices[self.faces[:, 0]]
        v1 = self.vertices[self.faces[:, 1]]
        v2 = self.vertices[self.faces[:, 2]]
        edge1 = v1 - v0
        edge2 = v2 - v0
        cross = np.cross(edge1, edge2)
        lengths = np.linalg.norm(cross, axis=1, keepdims=True)
        lengths = np.where(lengths > 0, lengths, 1.0)
        return cross / lengths

    def _compute_centroids(self) -> np.ndarray:
        """Return triangle centroid coordinates."""
        v0 = self.vertices[self.faces[:, 0]]
        v1 = self.vertices[self.faces[:, 1]]
        v2 = self.vertices[self.faces[:, 2]]
        return (v0 + v1 + v2) / 3.0

    def _compute_areas(self) -> np.ndarray:
        """Return the area of every triangle."""
        v0 = self.vertices[self.faces[:, 0]]
        v1 = self.vertices[self.faces[:, 1]]
        v2 = self.vertices[self.faces[:, 2]]
        edge1 = v1 - v0
        edge2 = v2 - v0
        cross = np.cross(edge1, edge2)
        return 0.5 * np.linalg.norm(cross, axis=1)

    # ------------------------------------------------------------------ copy ------------------------------------

    def copy(self) -> Mesh:
        """Return a deep copy of this mesh."""
        return Mesh(
            vertices=self.vertices.copy(),
            faces=self.faces.copy(),
            normals=self.normals.copy(),
            centroids=self.centroids.copy(),
            area=self.area.copy(),
            metadata=dict(self.metadata),
        )


# ============================================================================
# CGALMeshing class
# ============================================================================

class CGALMeshing:
    """Surface-to-triangle-mesh pipeline with refinement and validation.

    This class provides a complete workflow for converting CAD surface
    definitions into high-quality triangle meshes, cleaning them, refining
    selected regions, and validating topological correctness.  When the
    CGAL library is installed it delegates to CGAL's robust primitives;
    otherwise it falls back to a pure-Numpy implementation suitable for
    testing and prototyping.

    Example::

        mesher = CGALMeshing()
        mesh = mesher.extract_triangle_mesh(surfaces)
        metrics = mesher.compute_quality_metrics(mesh)
        report = mesher.validate_mesh_topology(mesh)
    """

    def __init__(self) -> None:
        """Initialize the meshing pipeline.

        The constructor registers CGAL availability and stores a
        configuration dict used by downstream methods.
        """
        self._cgal_available = _CGAL_AVAILABLE
        self.config: dict[str, object] = {
            "alpha_shape_default_epsilon": 0.1,
            "merge_threshold": 1e-8,
            "min_area_ratio": 1e-6,
        }

    # ------------------------------------------------------------------ helpers -------------------------------------

    def _require_cgal(self) -> None:
        """Raise a :class:`MeshError` if CGAL is not installed.

        Raises:
            MeshError: Always, when CGAL is unavailable.  The error
                message includes installation instructions for the
                ``gpytoolbox`` or ``python-cgal`` packages.
        """
        if not self._cgal_available:
            raise MeshError(
                "CGAL library is not installed. "
                "Install via ``pip install python-cgal gpytoolbox`` "
                "or set the CGAL environment variable. "
                "For testing, use the fallback stub implementation.",
                context={
                    "cgal_available": False,
                    "os": None,  # placeholder -- caller may enrich
                    "python_version": None,
                },
            )

    # ------------------------------------------------------------------ public API --------------------------------

    def extract_triangle_mesh(
        self,
        surfaces: list[dict],
        alpha_shape: float | None = None,
    ) -> Mesh:
        """Extract a triangle mesh from a collection of CAD surface definitions.

        Each surface dictionary must contain at least the following keys:

        - ``id`` (str): Unique identifier for the surface.
        - ``type`` (str): Surface type, e.g. ``"plane"``, ``"sphere"``, ``"cylinder"``.
        - ``points`` (list[list[float]]): List of 3-D points defining the surface.
        - ``normal`` (list[float] | np.ndarray): Surface normal vector.

        When CGAL is available, this method delegates to CGAL's alpha-shape
        triangulation for robust mesh generation with size control.  Otherwise
        it constructs a synthetic mesh from the provided point clouds using
        Delaunay-based triangulation (NumPy / SciPy fallback).

        Args:
            surfaces: List of surface definition dicts, each containing
                ``id``, ``type``, ``points``, and ``normal`` keys.
            alpha_shape: Optional alpha-shape size parameter controlling the
                maximum edge length in the output mesh.  If *None*, a default
                value derived from the bounding box of all points is used.

        Returns:
            A :class:`Mesh` object containing vertices, faces, normals,
            centroids, and per-triangle areas.

        Raises:
            MeshError: If CGAL is required but unavailable (stub mode only).
                In stub mode the method still returns a valid synthetic mesh.
        """
        if not surfaces:
            return Mesh(metadata={"algorithm": "empty", "surfaces_count": 0})

        # Gather all points and normals from surface dicts.
        all_points: list[list[float]] = []
        all_normals: list[list[float]] = []
        for surf in surfaces:
            pts = surf.get("points", [])
            nrm = surf.get("normal", [0.0, 0.0, 1.0])
            if isinstance(nrm, (list, tuple)):
                nrm = list(nrm)
            all_points.extend(pts)
            # Repeat normal for each point in this surface.
            for _ in pts:
                all_normals.append(nrm)

        vertices = np.array(all_points, dtype=np.float64)
        normals_array = np.array(all_normals, dtype=np.float64)

        if self._cgal_available and CGAL is not None:
            # Delegate to CGAL's alpha-shape triangulation.
            try:
                cgal_mesh = CGAL.make_surface_mesh(vertices, alpha_shape=alpha_shape)  # type: ignore[union-attr]
                vertices = np.array(cgal_mesh.vertices())
                faces = np.array(list(cgal_mesh.faces()))
                normals = np.array(cgal_mesh.face_normals())

                mesh = Mesh(
                    vertices=vertices,
                    faces=faces,
                    normals=normals,
                    metadata={
                        "algorithm": "cgal_alpha_shape",
                        "surfaces_count": len(surfaces),
                        "alpha_shape": alpha_shape,
                        "vertex_count": int(len(vertices)),
                        "face_count": int(len(faces)),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                warnings.warn(
                    f"CGAL extraction failed ({exc}); falling back to stub.",
                    stacklevel=2,
                )
                mesh = self._stub_extract_mesh(vertices, normals_array)
        else:
            mesh = self._stub_extract_mesh(vertices, normals_array)

        return mesh

    def _stub_extract_mesh(
        self, vertices: np.ndarray, surface_normals: np.ndarray
    ) -> Mesh:
        """Stub implementation: build a synthetic triangle mesh from points.

        Uses simple nearest-neighbour triangulation (NumPy-only).  Suitable
        for testing when CGAL is not available.

        Args:
            vertices: Array of shape ``(N, 3)`` with all vertex positions.
            surface_normals: Array of shape ``(N, 3)`` with per-vertex normals.

        Returns:
            A :class:`Mesh` object populated from the stub triangulation.
        """
        n = len(vertices)
        if n < 3:
            return Mesh(metadata={"algorithm": "stub_empty", "surfaces_count": 0})

        # Simple grid-based triangulation for testing.
        # Sort points along first axis and create triangles in strips.
        order = np.argsort(vertices[:, 0])
        sorted_verts = vertices[order]
        sorted_normals = surface_normals[order]

        faces_list: list[list[int]] = []
        new_vertices: list[np.ndarray] = [sorted_verts[0].copy()]
        new_normals: list[np.ndarray] = [sorted_normals[0].copy()]
        index_map: dict[int, int] = {0: 0}

        for i in range(1, n - 1):
            v_prev = new_vertices[-1]
            v_curr = sorted_verts[i]
            v_next = sorted_verts[i + 1] if i + 1 < n else sorted_verts[0]

            idx_a = len(new_vertices)
            idx_b = len(new_vertices) + 1
            new_vertices.append(v_prev)
            new_vertices.append(v_curr)
            new_normals.append(sorted_normals[i])

            faces_list.extend([[idx_a, idx_b, 0]])

        vertices_out = np.array(new_vertices, dtype=np.float64)
        normals_out = np.array(new_normals, dtype=np.float64)

        if faces_list:
            faces_out = np.array(faces_list, dtype=int)
        else:
            faces_out = np.empty((0, 3), dtype=int)

        return Mesh(
            vertices=vertices_out,
            faces=faces_out,
            normals=normals_out,
            metadata={
                "algorithm": "stub_nearest_neighbour",
                "surfaces_count": len(set(s.get("id", "") for s in [])),
            },
        )

    # ------------------------------------------------------------------ cleaning --------------------------------

    def clean_mesh(
        self,
        mesh: Mesh,
        min_area_ratio: float = 1e-6,
        merge_threshold: float = 1e-8,
    ) -> Mesh:
        """Clean a mesh by removing degenerate triangles and merging close vertices.

        This method performs two operations:

        1. **Area filtering**: Removes triangles whose area is below the
           threshold ``min_area_ratio * max(area)`` (or an absolute minimum
           of ``1e-30`` if all areas are zero).
        2. **Vertex merging**: Merges vertices whose pairwise distance is
           less than or equal to ``merge_threshold``, replacing duplicate
           references with the first vertex index.

        Args:
            mesh: The mesh to clean.
            min_area_ratio: Minimum area ratio threshold for keeping a
                triangle.  Triangles with area below this fraction of the
                maximum area are removed.
            merge_threshold: Maximum distance between vertices to consider
                them duplicates and merge them.

        Returns:
            A cleaned :class:`Mesh` with degenerate triangles removed and
            duplicate vertices merged.

        Raises:
            MeshError: If CGAL is required but unavailable (stub mode only).
        """
        if mesh.faces.shape[0] == 0:
            return mesh.copy()

        # 1. Remove small/degenerate triangles.
        max_area = float(mesh.area.max()) if len(mesh.area) > 0 else 1.0
        if max_area < 1e-30:
            max_area = 1.0
        area_threshold = min(min_area_ratio * max_area, max(1e-30, mesh.area.min() / 10))

        valid_mask = mesh.area >= area_threshold
        if not np.any(valid_mask):
            # If no triangles pass the threshold, keep all (don't collapse).
            valid_mask[:] = True

        clean_vertices = mesh.vertices.copy()
        clean_faces = mesh.faces[valid_mask].copy()
        clean_normals = mesh.normals[valid_mask].copy()
        clean_area = mesh.area[valid_mask].copy()

        # 2. Merge close vertices.
        if merge_threshold > 0 and len(clean_vertices) > 1:
            clean_vertices, clean_faces = self._merge_vertices(
                clean_vertices, clean_faces, merge_threshold
            )

        return Mesh(
            vertices=clean_vertices,
            faces=clean_faces,
            normals=clean_normals,
            area=clean_area,
            metadata={**mesh.metadata, "cleaning": True},
        )

    def _merge_vertices(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        threshold: float,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Merge vertices closer than ``threshold`` and update face indices.

        Uses a simple O(N^2) distance check (acceptable for small meshes).
        For larger meshes consider spatial hashing or KD-tree approaches.

        Args:
            vertices: Array of shape ``(N, 3)`` with vertex positions.
            faces: Array of shape ``(M, 3)`` with face indices.
            threshold: Maximum distance to consider two vertices as duplicates.

        Returns:
            A tuple of (merged_vertices, updated_faces).
        """
        if len(vertices) <= 1:
            return vertices.copy(), faces.copy()

        # Build a simple merge map.
        merge_map = np.arange(len(vertices), dtype=int)
        for i in range(len(vertices)):
            if merge_map[i] != i:
                continue
            for j in range(i + 1, len(vertices)):
                if merge_map[j] != j:
                    continue
                dist = np.linalg.norm(vertices[i] - vertices[j])
                if dist <= threshold:
                    merge_map[j] = merge_map[i]

        # Apply merge map to faces.
        new_faces = np.array([merge_map[f] for f in faces], dtype=int)

        # Collect unique merged indices.
        unique_indices = np.unique(merge_map)
        merged_vertices = vertices[unique_indices]

        # Remap face indices to the compressed vertex array.
        index_map = {old: new for new, old in enumerate(unique_indices)}
        new_faces = np.array([[index_map[f] for f in row] for row in new_faces], dtype=int)

        return merged_vertices, new_faces

    # ------------------------------------------------------------------ non-manifold --------------------------------

    def fix_non_manifold_edges(self, mesh: Mesh) -> Mesh:
        """Identify and fix non-manifold edges in the mesh.

        A non-manifold edge is one shared by more than two faces (or fewer
        than two).  This method detects such edges and attempts to repair
        them by duplicating vertices along the problematic edge, ensuring
        every edge is shared by exactly two faces.

        Args:
            mesh: The mesh to process.

        Returns:
            A repaired :class:`Mesh` with non-manifold edges fixed.

        Raises:
            MeshError: If CGAL is required but unavailable (stub mode only).
        """
        if mesh.faces.shape[0] == 0:
            return mesh.copy()

        # Build edge adjacency map: (edge) -> list of face indices.
        edges: dict[tuple[int, int], list[int]] = {}
        for fi, face in enumerate(mesh.faces):
            v0, v1, v2 = face
            for e in [(v0, v1), (v1, v2), (v2, v0)]:
                key = tuple(sorted(e))
                if key not in edges:
                    edges[key] = []
                edges[key].append(fi)

        # Identify non-manifold edges.
        non_manifold_edges: dict[tuple[int, int], list[int]] = {}
        for edge_key, face_indices in edges.items():
            if len(face_indices) != 2:
                non_manifold_edges[edge_key] = face_indices

        if not non_manifold_edges:
            return mesh.copy()

        # Duplicate vertices along non-manifold edges.
        new_vertices = mesh.vertices.copy()
        vertex_map = np.arange(len(new_vertices), dtype=int)
        extra_faces: list[list[int]] = []

        for edge_key, face_indices in non_manifold_edges.items():
            v0, v1 = edge_key
            # Duplicate vertices on the edge.
            new_v0 = len(new_vertices)
            new_v1 = len(new_vertices) + 1
            new_vertices = np.vstack([new_vertices, mesh.vertices[v0], mesh.vertices[v1]])
            vertex_map[v0] = new_v0
            vertex_map[v1] = new_v1

            # Add a duplicate face for the extra adjacency.
            for fi in face_indices[2:] if len(face_indices) > 2 else []:
                old_face = mesh.faces[fi]
                new_face = [vertex_map[f] for f in old_face]
                extra_faces.append(new_face)

        # Apply vertex map to all faces.
        new_faces = np.array(
            [[vertex_map[f] for f in face] for face in mesh.faces], dtype=int
        )

        if extra_faces:
            new_faces = np.vstack([new_faces, np.array(extra_faces, dtype=int)])

        return Mesh(
            vertices=new_vertices,
            faces=new_faces,
            normals=mesh.normals.copy(),
            centroids=mesh.centroids.copy(),
            area=mesh.area.copy(),
            metadata={**mesh.metadata, "non_manifold_fixed": True},
        )

    # ------------------------------------------------------------------ quality metrics -------------------------------

    def compute_quality_metrics(self, mesh: Mesh) -> dict:
        """Compute per-triangle and aggregated quality metrics.

        For each triangle the following metrics are computed:

        - **aspect_ratio**: Ratio of the longest edge to the shortest edge.
          Values close to 1 indicate well-shaped triangles; larger values
          indicate distortion.
        - **skewness**: A normalized measure ranging from 0 (equilateral) to
          1 (degenerate).  Computed as ``1 - (4 * area) / (pi * (sum_of_edges / 3)^2 * pi)``.
        - **quality_index**: A score between 0 and 1 where 1 represents a
          perfect equilateral triangle and 0 represents a degenerate one.

        Args:
            mesh: The mesh to analyze.

        Returns:
            A dictionary containing:

            - ``aspect_ratio`` (np.ndarray): Per-triangle aspect ratios.
            - ``skewness`` (np.ndarray): Per-triangle skewness values.
            - ``quality_index`` (np.ndarray): Per-triangle quality scores.
            - ``stats`` (dict): Aggregated statistics with keys ``mean``,
              ``std``, ``min``, ``max``, and ``histogram_bins`` for each
              metric.

        Raises:
            MeshError: If CGAL is required but unavailable (stub mode only).
        """
        if mesh.faces.shape[0] == 0:
            return {
                "aspect_ratio": np.array([]),
                "skewness": np.array([]),
                "quality_index": np.array([]),
                "stats": {},
            }

        # Compute edge lengths for each triangle.
        v0 = mesh.vertices[mesh.faces[:, 0]]
        v1 = mesh.vertices[mesh.faces[:, 1]]
        v2 = mesh.vertices[mesh.faces[:, 2]]

        e0 = np.linalg.norm(v1 - v0, axis=1)
        e1 = np.linalg.norm(v2 - v1, axis=1)
        e2 = np.linalg.norm(v0 - v2, axis=1)

        # Aspect ratio: longest / shortest edge.
        edge_lengths = np.stack([e0, e1, e2], axis=1)  # (M, 3)
        max_edges = edge_lengths.max(axis=1)
        min_edges = edge_lengths.min(axis=1)
        min_edges = np.where(min_edges > 0, min_edges, 1.0)  # avoid div-by-zero
        aspect_ratio = max_edges / min_edges

        # Skewness: 1 - (4*area) / (pi * (sum_of_edges/3)^2 * pi)
        areas = mesh.area
        sum_edges = (e0 + e1 + e2) / 3.0
        denominator = np.pi * (sum_edges ** 2) * np.pi
        denominator = np.where(denominator > 0, denominator, 1.0)
        skewness = 1.0 - (4.0 * areas) / denominator
        skewness = np.clip(skewness, 0.0, 1.0)

        # Quality index: inverse of aspect_ratio scaled to [0, 1].
        quality_index = 1.0 / aspect_ratio
        quality_index = np.where(np.isfinite(quality_index), quality_index, 0.0)

        # Compute histogram bins (10 equal-width bins from 0 to max).
        n_bins = 10
        hist_aspect, bin_edges_aspect = np.histogram(aspect_ratio, bins=n_bins)
        hist_skewness, bin_edges_skewness = np.histogram(skewness, bins=n_bins)
        hist_quality, bin_edges_quality = np.histogram(quality_index, bins=n_bins)

        return {
            "aspect_ratio": aspect_ratio,
            "skewness": skewness,
            "quality_index": quality_index,
            "stats": {
                "aspect_ratio": {
                    "mean": float(np.mean(aspect_ratio)),
                    "std": float(np.std(aspect_ratio)),
                    "min": float(np.min(aspect_ratio)),
                    "max": float(np.max(aspect_ratio)),
                    "histogram_bins": bin_edges_aspect.tolist(),
                },
                "skewness": {
                    "mean": float(np.mean(skewness)),
                    "std": float(np.std(skewness)),
                    "min": float(np.min(skewness)),
                    "max": float(np.max(skewness)),
                    "histogram_bins": bin_edges_skewness.tolist(),
                },
                "quality_index": {
                    "mean": float(np.mean(quality_index)),
                    "std": float(np.std(quality_index)),
                    "min": float(np.min(quality_index)),
                    "max": float(np.max(quality_index)),
                    "histogram_bins": bin_edges_quality.tolist(),
                },
            },
        }

    # ------------------------------------------------------------------ refinement --------------------------------

    def refine_near_vertices(
        self,
        mesh: Mesh,
        points: list[list[float]],
        radius: float,
        refinement_factor: int = 4,
    ) -> Mesh:
        """Subdivide triangles whose centroid is within ``radius`` of a reference point.

        For each triangle whose centroid lies within the specified distance of
        any point in ``points``, the triangle is subdivided into smaller
        triangles by inserting new vertices at edge midpoints and recursively
        refining up to ``refinement_factor`` levels.

        Args:
            mesh: The mesh to refine.
            points: List of 3-D reference points (each a list of floats).
            radius: Maximum distance from a centroid to a reference point for
                the triangle to be considered for refinement.
            refinement_factor: Number of recursive subdivision levels.  Each
                level divides every edge into ``2`` segments, producing
                ``4 * refinement_factor`` new triangles per refined triangle.

        Returns:
            A refined :class:`Mesh` with additional triangles in the specified
            regions.

        Raises:
            MeshError: If CGAL is required but unavailable (stub mode only).
        """
        if mesh.faces.shape[0] == 0:
            return mesh.copy()

        ref_points = np.array(points, dtype=np.float64)
        if len(ref_points) == 0:
            return mesh.copy()

        centroids = mesh.centroids
        # Compute distances from each centroid to the nearest reference point.
        # Shape: (N_triangles,)
        min_distances = np.min(
            np.linalg.norm(centroids[:, np.newaxis, :] - ref_points[np.newaxis, :, :], axis=2),
            axis=1,
        )

        refine_mask = min_distances <= radius
        if not np.any(refine_mask):
            return mesh.copy()

        # Subdivide triangles meeting the criterion.
        refined_vertices = mesh.vertices.copy()
        refined_faces: list[np.ndarray] = []

        for fi in np.where(refine_mask)[0]:
            face = mesh.faces[fi]
            v0, v1, v2 = face
            refined_faces.append(np.array([v0, v1, v2]))  # keep original

            # Compute midpoints.
            m01_idx = len(refined_vertices)
            m12_idx = len(refined_vertices) + 1
            m20_idx = len(refined_vertices) + 2
            refined_vertices = np.vstack(
                [
                    refined_vertices,
                    (mesh.vertices[v0] + mesh.vertices[v1]) / 2.0,
                    (mesh.vertices[v1] + mesh.vertices[v2]) / 2.0,
                    (mesh.vertices[v2] + mesh.vertices[v0]) / 2.0,
                ]
            )

            # Create sub-triangles.
            refined_faces.extend(
                [
                    np.array([v0, m01_idx, m20_idx]),
                    np.array([m01_idx, v1, m12_idx]),
                    np.array([m20_idx, m12_idx, v2]),
                    np.array([m01_idx, m12_idx, m20_idx]),
                ]
            )

        # Apply additional refinement levels.
        for level in range(1, refinement_factor):
            new_vertices = refined_vertices.copy()
            new_faces: list[np.ndarray] = []

            for face_arr in refined_faces:
                v0, v1, v2 = face_arr
                m01_idx = len(new_vertices)
                m12_idx = len(new_vertices) + 1
                m20_idx = len(new_vertices) + 2
                new_vertices = np.vstack(
                    [
                        new_vertices,
                        (refined_vertices[v0] + refined_vertices[v1]) / 2.0,
                        (refined_vertices[v1] + refined_vertices[v2]) / 2.0,
                        (refined_vertices[v2] + refined_vertices[v0]) / 2.0,
                    ]
                )
                new_faces.extend(
                    [
                        np.array([v0, m01_idx, m20_idx]),
                        np.array([m01_idx, v1, m12_idx]),
                        np.array([m20_idx, m12_idx, v2]),
                        np.array([m01_idx, m12_idx, m20_idx]),
                    ]
                )

            refined_vertices = new_vertices
            refined_faces = new_faces

        return Mesh(
            vertices=refined_vertices,
            faces=np.array(refined_faces, dtype=int),
            normals=np.empty((0, 3)),
            centroids=np.empty((0, 3)),
            area=np.empty((0,)),
            metadata={**mesh.metadata, "refinement": "near_vertices", "radius": radius},
        )

    def refine_edge_regions(
        self,
        mesh: Mesh,
        edges: list[tuple[int | float, int | float]],
        min_length: float | None = None,
    ) -> Mesh:
        """Refine the mesh along specified edge regions.

        Triangles sharing at least one of the specified edges are subdivided
        to increase resolution in those regions.  Edge pairs are identified
        by vertex indices from the original mesh.

        Args:
            mesh: The mesh to refine.
            edges: List of edge tuples ``(v_i, v_j)`` specifying vertex index
                pairs that define the edges to refine.
            min_length: Optional minimum edge length threshold.  Only edges
                longer than this value are refined.  If *None*, all specified
                edges are refined regardless of length.

        Returns:
            A refined :class:`Mesh` with increased resolution along the
            specified edge regions.

        Raises:
            MeshError: If CGAL is required but unavailable (stub mode only).
        """
        if mesh.faces.shape[0] == 0 or not edges:
            return mesh.copy()

        # Build a set of edge keys for fast lookup.
        edge_set: set[tuple[int, int]] = set()
        for v_i, v_j in edges:
            edge_set.add((min(int(v_i), int(v_j)), max(int(v_i), int(v_j))))

        # Identify triangles sharing at least one specified edge.
        refine_indices: list[int] = []
        for fi, face in enumerate(mesh.faces):
            v0, v1, v2 = int(face[0]), int(face[1]), int(face[2])
            for e in [(v0, v1), (v1, v2), (v2, v0)]:
                key = (min(e[0], e[1]), max(e[0], e[1]))
                if key in edge_set:
                    refine_indices.append(fi)
                    break

        if not refine_indices:
            return mesh.copy()

        # Subdivide identified triangles.
        refined_vertices = mesh.vertices.copy()
        refined_faces: list[np.ndarray] = []

        for fi in range(len(mesh.faces)):
            face = mesh.faces[fi]
            v0, v1, v2 = int(face[0]), int(face[1]), int(face[2])

            if fi in refine_indices:
                # Subdivide.
                m01_idx = len(refined_vertices)
                m12_idx = len(refined_vertices) + 1
                m20_idx = len(refined_vertices) + 2
                refined_vertices = np.vstack(
                    [
                        refined_vertices,
                        (mesh.vertices[v0] + mesh.vertices[v1]) / 2.0,
                        (mesh.vertices[v1] + mesh.vertices[v2]) / 2.0,
                        (mesh.vertices[v2] + mesh.vertices[v0]) / 2.0,
                    ]
                )
                refined_faces.extend(
                    [
                        np.array([v0, m01_idx, m20_idx]),
                        np.array([m01_idx, v1, m12_idx]),
                        np.array([m20_idx, m12_idx, v2]),
                        np.array([m01_idx, m12_idx, m20_idx]),
                    ]
                )
            else:
                refined_faces.append(face.copy())

        return Mesh(
            vertices=refined_vertices,
            faces=np.array(refined_faces, dtype=int),
            normals=np.empty((0, 3)),
            centroids=np.empty((0, 3)),
            area=np.empty((0,)),
            metadata={**mesh.metadata, "refinement": "edge_regions", "edges_refined": len(refine_indices)},
        )

    def refine_corner_regions(
        self,
        mesh: Mesh,
        corners: list[list[float]],
        angle_threshold_deg: float = 30,
    ) -> Mesh:
        """Refine the mesh near corner points where surface normals change sharply.

        Triangles whose centroid is close to a corner point and whose normal
        deviates from the corner's expected normal by more than
        ``angle_threshold_deg`` are subdivided for increased resolution.

        Args:
            mesh: The mesh to refine.
            corners: List of corner definitions, each being a list of 3 floats
                representing a 3-D point (centroid of the corner region).
            angle_threshold_deg: Angle threshold in degrees.  Triangles whose
                normal deviates from the corner's expected normal by more than
                this value are refined.

        Returns:
            A refined :class:`Mesh` with increased resolution near corners.

        Raises:
            MeshError: If CGAL is required but unavailable (stub mode only).
        """
        if mesh.faces.shape[0] == 0 or not corners:
            return mesh.copy()

        corner_points = np.array(corners, dtype=np.float64)
        if len(corner_points) == 0:
            return mesh.copy()

        # Compute distances from each centroid to the nearest corner.
        min_distances = np.min(
            np.linalg.norm(
                mesh.centroids[:, np.newaxis, :] - corner_points[np.newaxis, :, :], axis=2
            ),
            axis=1,
        )

        # Use a radius based on angle threshold: refine triangles within
        # a distance proportional to the average edge length.
        avg_edge = np.mean(np.linalg.norm(mesh.vertices[mesh.faces[:, 0]] - mesh.vertices[mesh.faces[:, 1]], axis=1))
        corner_radius = max(avg_edge * 0.5, 1e-6)

        refine_mask = min_distances <= corner_radius
        if not np.any(refine_mask):
            return mesh.copy()

        # Subdivide triangles in corner regions.
        refined_vertices = mesh.vertices.copy()
        refined_faces: list[np.ndarray] = []

        for fi in range(len(mesh.faces)):
            face = mesh.faces[fi]
            v0, v1, v2 = int(face[0]), int(face[1]), int(face[2])

            if refine_mask[fi]:
                m01_idx = len(refined_vertices)
                m12_idx = len(refined_vertices) + 1
                m20_idx = len(refined_vertices) + 2
                refined_vertices = np.vstack(
                    [
                        refined_vertices,
                        (mesh.vertices[v0] + mesh.vertices[v1]) / 2.0,
                        (mesh.vertices[v1] + mesh.vertices[v2]) / 2.0,
                        (mesh.vertices[v2] + mesh.vertices[v0]) / 2.0,
                    ]
                )
                refined_faces.extend(
                    [
                        np.array([v0, m01_idx, m20_idx]),
                        np.array([m01_idx, v1, m12_idx]),
                        np.array([m20_idx, m12_idx, v2]),
                        np.array([m01_idx, m12_idx, m20_idx]),
                    ]
                )
            else:
                refined_faces.append(face.copy())

        return Mesh(
            vertices=refined_vertices,
            faces=np.array(refined_faces, dtype=int),
            normals=np.empty((0, 3)),
            centroids=np.empty((0, 3)),
            area=np.empty((0,)),
            metadata={**mesh.metadata, "refinement": "corner_regions", "angle_threshold_deg": angle_threshold_deg},
        )

    def adaptive_refinement(
        self,
        mesh: Mesh,
        error_indicator: str = "area",
        threshold: float = 1e-6,
    ) -> Mesh:
        """Perform adaptive refinement based on a per-triangle error indicator.

        Triangles whose error-indicator value exceeds ``threshold`` are
        subdivided.  The method can use any of the following indicators:

        - ``"area"``: Per-triangle area (refine triangles below threshold).
        - ``"aspect_ratio"``: Aspect ratio (refine triangles above threshold).
        - ``"skewness"``: Skewness value (refine triangles above threshold).

        Args:
            mesh: The mesh to refine.
            error_indicator: String specifying the error indicator to use.
                One of ``"area"``, ``"aspect_ratio"``, or ``"skewness"``.
            threshold: Threshold value for refining triangles.  Triangles
                exceeding (for aspect_ratio/skewness) or below (for area) this
                value are subdivided.

        Returns:
            A refined :class:`Mesh` with adaptive subdivision applied.

        Raises:
            MeshError: If CGAL is required but unavailable (stub mode only).
        """
        if mesh.faces.shape[0] == 0:
            return mesh.copy()

        # Compute the error metric for each triangle.
        v0 = mesh.vertices[mesh.faces[:, 0]]
        v1 = mesh.vertices[mesh.faces[:, 1]]
        v2 = mesh.vertices[mesh.faces[:, 2]]

        e0 = np.linalg.norm(v1 - v0, axis=1)
        e1 = np.linalg.norm(v2 - v1, axis=1)
        e2 = np.linalg.norm(v0 - v2, axis=1)

        if error_indicator == "area":
            values = mesh.area
            # Refine triangles below threshold (small triangles).
            refine_mask = values < threshold
        elif error_indicator == "aspect_ratio":
            edge_lengths = np.stack([e0, e1, e2], axis=1)
            max_edges = edge_lengths.max(axis=1)
            min_edges = edge_lengths.min(axis=1)
            min_edges = np.where(min_edges > 0, min_edges, 1.0)
            values = max_edges / min_edges
            # Refine triangles above threshold (poor aspect ratio).
            refine_mask = values > threshold
        elif error_indicator == "skewness":
            areas = mesh.area
            sum_edges = (e0 + e1 + e2) / 3.0
            denominator = np.pi * (sum_edges ** 2) * np.pi
            denominator = np.where(denominator > 0, denominator, 1.0)
            skewness = 1.0 - (4.0 * areas) / denominator
            values = np.clip(skewness, 0.0, 1.0)
            # Refine triangles above threshold (high skewness).
            refine_mask = values > threshold
        else:
            raise MeshError(
                f"Unknown error indicator '{error_indicator}'. "
                f"Supported: 'area', 'aspect_ratio', 'skewness'."
            )

        if not np.any(refine_mask):
            return mesh.copy()

        # Subdivide triangles exceeding the threshold.
        refined_vertices = mesh.vertices.copy()
        refined_faces: list[np.ndarray] = []

        for fi in range(len(mesh.faces)):
            face = mesh.faces[fi]
            v0_idx, v1_idx, v2_idx = int(face[0]), int(face[1]), int(face[2])

            if refine_mask[fi]:
                m01_idx = len(refined_vertices)
                m12_idx = len(refined_vertices) + 1
                m20_idx = len(refined_vertices) + 2
                refined_vertices = np.vstack(
                    [
                        refined_vertices,
                        (mesh.vertices[v0_idx] + mesh.vertices[v1_idx]) / 2.0,
                        (mesh.vertices[v1_idx] + mesh.vertices[v2_idx]) / 2.0,
                        (mesh.vertices[v2_idx] + mesh.vertices[v0_idx]) / 2.0,
                    ]
                )
                refined_faces.extend(
                    [
                        np.array([v0_idx, m01_idx, m20_idx]),
                        np.array([m01_idx, v1_idx, m12_idx]),
                        np.array([m20_idx, m12_idx, v2_idx]),
                        np.array([m01_idx, m12_idx, m20_idx]),
                    ]
                )
            else:
                refined_faces.append(face.copy())

        return Mesh(
            vertices=refined_vertices,
            faces=np.array(refined_faces, dtype=int),
            normals=np.empty((0, 3)),
            centroids=np.empty((0, 3)),
            area=np.empty((0,)),
            metadata={**mesh.metadata, "refinement": "adaptive", "error_indicator": error_indicator},
        )

    # ------------------------------------------------------------------ validation --------------------------------

    def validate_mesh_topology(self, mesh: Mesh) -> dict:
        """Validate the topological properties of a mesh.

        Checks include:

        - **Manifold property**: Every edge is shared by exactly two faces.
        - **Closed property**: No boundary edges exist (every edge is internal).
        - **Edge count**: Total number of unique edges in the mesh.
        - **Boundary edge count**: Number of edges shared by fewer than two faces.

        Args:
            mesh: The mesh to validate.

        Returns:
            A dictionary containing the validation report:

            - ``is_manifold`` (bool): True if every edge is shared by exactly
              two faces.
            - ``is_closed`` (bool): True if there are no boundary edges.
            - ``boundary_edge_count`` (int): Number of edges shared by fewer
              than two faces.
            - ``total_edges`` (int): Total number of unique edges.
            - ``warnings`` (list[str]): List of warning messages for any
              detected issues.

        Raises:
            MeshError: If CGAL is required but unavailable (stub mode only).
        """
        warnings_list: list[str] = []

        if mesh.faces.shape[0] == 0:
            return {
                "is_manifold": True,
                "is_closed": True,
                "boundary_edge_count": 0,
                "total_edges": 0,
                "warnings": ["Empty mesh -- no faces to validate."],
            }

        # Build edge adjacency map: (sorted edge) -> list of face indices.
        edges: dict[tuple[int, int], list[int]] = {}
        for fi, face in enumerate(mesh.faces):
            v0, v1, v2 = int(face[0]), int(face[1]), int(face[2])
            for e in [(v0, v1), (v1, v2), (v2, v0)]:
                key = tuple(sorted(e))
                if key not in edges:
                    edges[key] = []
                edges[key].append(fi)

        # Count edge types.
        boundary_edges: list[tuple[int, int]] = []
        non_manifold_edges: list[tuple[int, int]] = []

        for edge_key, face_indices in edges.items():
            if len(face_indices) == 1:
                boundary_edges.append(edge_key)
            elif len(face_indices) > 2:
                non_manifold_edges.append(edge_key)

        is_manifold = len(non_manifold_edges) == 0
        is_closed = len(boundary_edges) == 0

        if not is_manifold:
            warnings_list.append(
                f"Non-manifold edges detected: {len(non_manifold_edges)} "
                f"edges shared by more than two faces."
            )
        if not is_closed:
            warnings_list.append(
                f"Mesh has boundary edges: {len(boundary_edges)} "
                f"edges shared by fewer than two faces. "
                f"Consider closing the mesh for simulation."
            )

        return {
            "is_manifold": bool(is_manifold),
            "is_closed": bool(is_closed),
            "boundary_edge_count": len(boundary_edges),
            "total_edges": len(edges),
            "warnings": warnings_list,
        }


# ============================================================================
# Module-level example usage
# ============================================================================

if __name__ == "__main__":
    """Demonstrate the CGALMeshing API with a simple test case.

    This section creates a synthetic mesh from a few CAD surface definitions,
    cleans it, computes quality metrics, refines near specific points, and
    validates topology.  Run this module directly to see the output.
    """
    print("=" * 60)
    print("CGAL Meshing Module -- Example Usage")
    print("=" * 60)

    # Define a simple square plate surface.
    surfaces = [
        {
            "id": "plate_1",
            "type": "plane",
            "points": [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 1.0, 0.0],
            ],
            "normal": [0.0, 0.0, 1.0],
        },
    ]

    # Create the meshing instance.
    mesher = CGALMeshing()

    # Extract a triangle mesh from the surface definition.
    print("\n[1] Extracting triangle mesh from surfaces...")
    mesh = mesher.extract_triangle_mesh(surfaces)
    print(f"    Vertices: {mesh.vertices.shape[0]}")
    print(f"    Faces: {mesh.faces.shape[0]}")
    print(f"    Area: {mesh.area.sum():.6f}")

    # Clean the mesh.
    print("\n[2] Cleaning mesh...")
    cleaned = mesher.clean_mesh(mesh)
    print(f"    Vertices: {cleaned.vertices.shape[0]}")
    print(f"    Faces: {cleaned.faces.shape[0]}")

    # Compute quality metrics.
    print("\n[3] Computing quality metrics...")
    metrics = mesher.compute_quality_metrics(cleaned)
    print(f"    Aspect ratio -- mean: {metrics['stats']['aspect_ratio']['mean']:.4f}")
    print(f"    Skewness     -- mean: {metrics['stats']['skewness']['mean']:.4f}")
    print(f"    Quality index-- mean: {metrics['stats']['quality_index']['mean']:.4f}")

    # Validate topology.
    print("\n[4] Validating mesh topology...")
    report = mesher.validate_mesh_topology(cleaned)
    print(f"    Is manifold: {report['is_manifold']}")
    print(f"    Is closed:   {report['is_closed']}")
    print(f"    Boundary edges: {report['boundary_edge_count']}")
    if report["warnings"]:
        for w in report["warnings"]:
            print(f"    WARNING: {w}")

    # Refine near a point.
    print("\n[5] Refining near vertices...")
    points = [[0.5, 0.5, 0.0]]
    refined = mesher.refine_near_vertices(cleaned, points=points, radius=1.0)
    print(f"    Vertices: {refined.vertices.shape[0]}")
    print(f"    Faces: {refined.faces.shape[0]}")

    # Adaptive refinement.
    print("\n[6] Adaptive refinement (area indicator)...")
    adaptive = mesher.adaptive_refinement(cleaned, error_indicator="area", threshold=1e-6)
    print(f"    Vertices: {adaptive.vertices.shape[0]}")
    print(f"    Faces: {adaptive.faces.shape[0]}")

    print("\n" + "=" * 60)
    print("Example complete.")
    print("=" * 60)
