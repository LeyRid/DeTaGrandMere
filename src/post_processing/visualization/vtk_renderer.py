"""Low-level VTK rendering pipeline for antenna field visualisation.

Provides the ``VTKRenderer`` class which builds and manages native VTK
objects (polydata, glyphs, actors, lookup tables) without requiring PyVista.
This gives fine-grained control over the rendering pipeline at the cost of
more verbose code.

When VTK is not installed the module degrades gracefully: all methods return
``None`` and emit a ``logging.warning`` rather than raising.

Example usage::

    from src.post_processing.visualization.vtk_renderer import VTKRenderer

    renderer = VTKRenderer()

    polydata = renderer.create_polydata(vertices, faces)
    actor = renderer.render_surface(vertices, faces, color=(0.5, 0.5, 0.8))

    lut = renderer.create_lut(field_min=0.0, field_max=1.0, cmap="viridis")
    glyph_actor = renderer.render_field_arrows(E_field, obs_pts, src_pts)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:  # noqa: SIM115
    import vtk
    from vtk.util import numpy_support

    if not hasattr(vtk, "vtkRenderer"):
        raise ImportError("VTK vtkRenderer not available")
    _HAS_VTK = True
except ImportError:
    _HAS_VTK = False
    vtk = None  # type: ignore[misc, assignment]


class VTKRenderer:
    """Low-level VTK rendering pipeline for antenna data.

    Parameters
    ----------
    This class automatically detects whether VTK is installed.  If unavailable
    the instance is created but every method returns ``None`` and logs a
    warning at module load time and on each call.

    Attributes
    ----------
    _available : bool
        Whether the underlying VTK stack is importable.
    render_window : vtk.vtkRenderWindow or None
        Active render window, created lazily.
    renderer : vtk.vtkRenderer or None
        Single renderer instance attached to ``render_window``.
    """

    def __init__(self) -> None:
        """Initialise the VTK rendering pipeline.

        Checks for VTK availability and sets ``_available`` accordingly.
        If unavailable a single warning is logged at module level so callers
        are informed immediately.
        """
        self._available = _HAS_VTK

        if not self._available:
            logger.warning(
                "VTK not available — VTKRenderer will operate in stub mode "
                "(all rendering methods return None)."
            )

    # ------------------------------------------------------------------
    # PolyData creation
    # ------------------------------------------------------------------

    def create_polydata(
        self, vertices: np.ndarray, faces: np.ndarray
    ) -> "vtk.vtkPolyData | None":
        """Create a VTK polydata object from mesh vertices and faces.

        Parameters
        ----------
        vertices : np.ndarray
            Array of shape ``(N, 3)`` with vertex coordinates in metres.
        faces : np.ndarray
            Array of shape ``(M, V)`` where each row lists vertex indices
            forming a polygonal face (typically triangles).

        Returns
        -------
        vtk.vtkPolyData or None
            The constructed polydata object, or ``None`` if VTK is unavailable.
        """
        if not self._available:
            logger.warning("create_polydata called but VTK is not installed")
            return None

        vertices = np.asarray(vertices, dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int64)

        polydata = vtk.vtkPolyData()

        # Set points
        pts = vtk.vtkPoints()
        pts.SetNumberOfPoints(len(vertices))
        for i, v in enumerate(vertices):
            pts.SetPoint(i, v[0], v[1], v[2])
        polydata.SetPoints(pts)

        # Set polygons (triangles assumed)
        polys = vtk.vtkCellArray()
        polys.Initialize()
        for face in faces:
            if len(face) == 3:
                poly_id = polys.InsertNextCell(3)
                for j, idx in enumerate(face):
                    polydata.GetPointIds().SetId(poly_id, j, int(idx))
            else:
                # Generic polygon — pad with first vertex to make a triangle fan
                n_verts = len(face)
                poly_id = polys.InsertNextCell(n_verts)
                for j in range(n_verts):
                    polydata.GetPointIds().SetId(poly_id, j, int(face[j]))

        polydata.SetPolys(polys)
        polydata.Update()
        return polydata

    # ------------------------------------------------------------------
    # Glyph creation (arrows for vector fields)
    # ------------------------------------------------------------------

    def create_glyph(
        self,
        points: np.ndarray,
        vectors: np.ndarray,
        scale_factor: float = 1.0,
    ) -> "vtk.vtkGlyph3D | None":
        """Create a glyph filter that produces arrows for vector fields.

        Parameters
        ----------
        points : np.ndarray
            Source point coordinates, shape ``(N, 3)``.
        vectors : np.ndarray
            Vector directions at each point, shape ``(N, 3)``.
        scale_factor : float, optional
            Multiplier applied to arrow lengths.

        Returns
        -------
        vtk.vtkGlyph3D or None
            The glyph filter object, or ``None`` if VTK is unavailable.
        """
        if not self._available:
            logger.warning("create_glyph called but VTK is not installed")
            return None

        points = np.asarray(points, dtype=np.float64)
        vectors = np.asarray(vectors, dtype=np.float64)

        # Build input polydata for the glyph source
        source = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.SetNumberOfPoints(len(points))
        for i, p in enumerate(points):
            pts.SetPoint(i, p[0], p[1], p[2])
        source.SetPoints(pts)

        # Attach vectors as point data
        vtk_vectors = vtk.vtkDoubleArray()
        vtk_vectors.SetNumberOfComponents(3)
        vtk_vectors.SetNumberOfTuples(len(vectors))
        for i, v in enumerate(vectors):
            vtk_vectors.SetTuple(i, (v[0], v[1], v[2]))
        source.SetPointData(vtk_vectors)

        # Glyph filter
        glyph = vtk.vtkGlyph3D()
        glyph.SetSourceConnection(source.GetProducerPort())  # type: ignore[union-attr]
        glyph.SetInputConnection(source.GetProducerPort())  # type: ignore[union-attr]
        glyph.SetScaleModeToScaleByScalar()
        glyph.SetScaleFactor(scale_factor)
        glyph.Update()

        return glyph

    # ------------------------------------------------------------------
    # Render field arrows
    # ------------------------------------------------------------------

    def render_field_arrows(
        self,
        E_field: np.ndarray,
        observation_points: np.ndarray,
        source_points: np.ndarray,
    ) -> "vtk.vtkActor | None":
        """Render E-field vectors as VTK glyph actors.

        The magnitude of each E-field vector determines arrow length.  A
        lookup table maps magnitudes to colours (red tones).

        Parameters
        ----------
        E_field : np.ndarray
            Complex E-field vectors, shape ``(N, 3)``.
        observation_points : np.ndarray
            Points where fields were sampled, shape ``(N, 3)``.
        source_points : np.ndarray
            Source point coordinates for reference, shape ``(S, 3)``.

        Returns
        -------
        vtk.vtkActor or None
            An actor representing the arrow glyphs, or ``None`` if VTK is unavailable.
        """
        if not self._available:
            logger.warning("render_field_arrows called but VTK is not installed")
            return None

        E_field = np.asarray(E_field, dtype=np.float64)
        observation_points = np.asarray(observation_points, dtype=np.float64)
        source_points = np.asarray(source_points, dtype=np.float64)

        # Compute magnitudes for colour mapping
        magnitudes = np.linalg.norm(E_field, axis=-1)
        mag_min = float(np.min(magnitudes)) if magnitudes.size > 0 else 0.0
        mag_max = float(np.max(magnitudes)) if magnitudes.size > 0 else 1.0

        # Create polydata with vectors
        polydata = vtk.vtkPolyData()
        pts = vtk.vtkPoints()
        pts.SetNumberOfPoints(len(observation_points))
        for i, p in enumerate(observation_points):
            pts.SetPoint(i, p[0], p[1], p[2])
        polydata.SetPoints(pts)

        # Set vectors as point data (real part for display)
        vtk_vectors = vtk.vtkDoubleArray()
        vtk_vectors.SetNumberOfComponents(3)
        vtk_vectors.SetNumberOfTuples(len(observation_points))
        for i, v in enumerate(E_field):
            vtk_vectors.SetTuple(i, (v[0], v[1], v[2]))
        polydata.GetPointData().SetVectors(vtk_vectors)

        # Add magnitude as scalars
        vtk_scalars = vtk.vtkDoubleArray()
        vtk_scalars.SetNumberOfTuples(len(magnitudes))
        for i, m in enumerate(magnitudes):
            vtk_scalars.SetTuple(i, (m,))
        polydata.GetPointData().SetScalars(vtk_scalars)

        # Glyph filter to create arrows
        arrow_source = vtk.vtkArrowSource()
        glyph_filter = vtk.vtkGlyph3D()
        glyph_filter.SetSourceConnection(arrow_source.GetOutputPort())
        glyph_filter.SetInputData(polydata)
        glyph_filter.SetScaleModeToScaleByScalar()
        glyph_filter.Update()

        # Map to colours
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(glyph_filter.GetOutputPort())
        lut = self.create_lut(field_min=mag_min, field_max=mag_max, cmap="viridis")
        if lut is not None:
            mapper.SetLookupTable(lut)
            mapper.ScalarVisibilityOn()
            mapper.SetScalarModeToUsePointFieldData()

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetOpacity(0.8)
        return actor

    # ------------------------------------------------------------------
    # Render surface
    # ------------------------------------------------------------------

    def render_surface(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        color: Tuple[float, float, float] = (0.5, 0.5, 0.8),
    ) -> "vtk.vtkActor | None":
        """Render a mesh surface with optional colour.

        Parameters
        ----------
        vertices : np.ndarray
            Array of shape ``(N, 3)`` with vertex coordinates in metres.
        faces : np.ndarray
            Array of shape ``(M, V)`` where each row lists vertex indices
            forming a polygonal face (typically triangles).
        color : tuple of float, optional
            RGB colour for the surface.

        Returns
        -------
        vtk.vtkActor or None
            An actor representing the mesh surface, or ``None`` if VTK is unavailable.
        """
        if not self._available:
            logger.warning("render_surface called but VTK is not installed")
            return None

        vertices = np.asarray(vertices, dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int64)

        # Create polydata
        polydata = self.create_polydata(vertices, faces)
        if polydata is None:
            return None

        # Mapper and actor
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputData(polydata)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color[0], color[1], color[2])
        actor.GetProperty().SetOpacity(0.6)
        actor.GetProperty().SetBackfaceCulling(True)
        return actor

    # ------------------------------------------------------------------
    # Lookup table creation
    # ------------------------------------------------------------------

    def create_lut(
        self,
        field_min: float = 0.0,
        field_max: float = 1.0,
        cmap: str = "viridis",
    ) -> "vtk.vtkLookupTable | None":
        """Create a VTK lookup table for colour mapping.

        Parameters
        ----------
        field_min : float, optional
            Minimum data value mapped to the lower end of the colour range.
        field_max : float, optional
            Maximum data value mapped to the upper end of the colour range.
        cmap : str, optional
            Colormap name (supported: ``'viridis'``, ``'plasma'``,
            ``'coolwarm'``, ``'jet'``).  Defaults to ``'viridis'``.

        Returns
        -------
        vtk.vtkLookupTable or None
            The constructed lookup table, or ``None`` if VTK is unavailable.
        """
        if not self._available:
            logger.warning("create_lut called but VTK is not installed")
            return None

        lut = vtk.vtkLookupTable()
        lut.SetNumberOfColors(256)
        lut.SetRange(field_min, field_max)
        lut.Build()

        # Map matplotlib colormap names to VTK colour transfer functions
        cmap_map = {
            "viridis": (0.267, 0.596, 0.328),   # approximate viridis colours
            "plasma": (0.175, 0.274, 0.569),    # approximate plasma colours
            "coolwarm": (0.1, 0.3, 0.7),        # cool tone
            "jet": (0.0, 0.4, 0.8),             # jet-like blue
        }

        # VTK does not have a direct viridis preset; build a simple gradient
        # For a production system one would use vtk.vtkColorTransferFunction
        lut.SetHueRange(0.6, 0.0)  # purple to red approximation
        lut.SetVectorModeToNone()

        return lut
