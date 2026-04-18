"""PyVista-based visualization backend for antenna field data.

Provides the ``FieldVisualizer`` class, which wraps PyVista/VTK rendering
capabilities to visualise antenna geometry, near-field E/H vectors, far-field
radiation patterns, and cross-sectional field contours.

When PyVista or VTK are not installed the module degrades gracefully: all
methods return ``None`` and emit a ``logging.warning`` rather than raising.

Example usage::

    from src.post_processing.visualization.pyvista_backend import FieldVisualizer

    viz = FieldVisualizer()

    # Render antenna mesh
    plotter = viz.render_geometry(vertices, faces)

    # Plot near-field vectors
    if plotter is not None:
        plotter = viz.plot_near_field(E_field, H_field, obs_pts, src_pts)

    # Plot far-field pattern
    plotter = viz.plot_far_field(E_theta, E_phi, theta, phi)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import numpy as np

logger = logging.getLogger(__name__)

try:  # noqa: SIM115
    import pyvista as pv

    if not hasattr(pv, "Plotter"):
        raise ImportError("PyVista Plotter not available")
    _HAS_PYVISTA = True
except ImportError:
    _HAS_PYVISTA = False
    pv = None  # type: ignore[misc, assignment]


class FieldVisualizer:
    """Interactive 3-D visualiser for antenna electromagnetic fields.

    Parameters
    ----------
    This class automatically detects whether PyVista and VTK are installed.
    If they are unavailable the instance is created but every rendering method
    returns ``None`` and logs a warning at module load time and on each call.

    Attributes
    ----------
    _available : bool
        Whether the underlying PyVista/VTK stack is importable.
    plotter : pyvista.Plotter or None
        The active PyVista plotter instance, created lazily by the first
        rendering method that needs one.
    """

    def __init__(self) -> None:
        """Initialise the visualiser backend.

        Checks for PyVista availability and sets ``_available`` accordingly.
        If unavailable a single warning is logged at module level so callers
        are informed immediately.
        """
        self._available = _HAS_PYVISTA
        self.plotter: Optional["pv.Plotter"] = None

        if not self._available:
            logger.warning(
                "PyVista/VTK not available — FieldVisualizer will operate in "
                "stub mode (all rendering methods return None)."
            )

    # ------------------------------------------------------------------
    # Geometry rendering
    # ------------------------------------------------------------------

    def render_geometry(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        material_colors: Optional[dict] = None,
    ) -> "pv.Plotter | None":
        """Render an antenna geometry mesh.

        Parameters
        ----------
        vertices : np.ndarray
            Array of shape ``(N, 3)`` with vertex coordinates in metres.
        faces : np.ndarray
            Array of shape ``(M, V)`` where each row lists vertex indices
            forming a polygonal face (typically triangles, so ``V == 3``).
        material_colors : dict, optional
            Mapping from material name to an RGB or RGBA tuple / list.

        Returns
        -------
        pyvista.Plotter or None
            The active plotter instance, or ``None`` if PyVista is unavailable.
        """
        if not self._available:
            logger.warning("render_geometry called but PyVista/VTK is not installed")
            return None

        vertices = np.asarray(vertices, dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int64)

        # Build pyvista PolyData
        mesh = pv.PolyData(vertices, faces)

        # Create or reuse the plotter
        if self.plotter is None:
            self.plotter = pv.Plotter()

        self.plotter.add_mesh(
            mesh,
            color="lightgray",
            show_edges=True,
            opacity=0.6,
            name="geometry",
        )

        # Apply material colours if provided
        if material_colors:
            for mat_name, rgb in material_colors.items():
                mask = np.array([f"material_{mat_name}" for _ in range(len(faces))])
                # In practice one would tag cells; stub implementation.
                logger.debug("Applying colour %s for material %s", rgb, mat_name)

        self.plotter.show()
        return self.plotter

    # ------------------------------------------------------------------
    # Near-field plotting
    # ------------------------------------------------------------------

    def plot_near_field(
        self,
        E_field: np.ndarray,
        H_field: np.ndarray,
        observation_points: np.ndarray,
        source_points: np.ndarray,
    ) -> "pv.Plotter | None":
        """Plot near-field E and H vectors as arrows on the geometry surface.

        Vectors are colour-mapped by their magnitude (norm across the last
        axis).  E-field arrows use red tones; H-field arrows use blue tones.

        Parameters
        ----------
        E_field : np.ndarray
            Complex E-field vectors at observation points, shape ``(N, 3)``.
        H_field : np.ndarray
            Complex H-field vectors at observation points, shape ``(N, 3)``.
        observation_points : np.ndarray
            Points where fields were sampled, shape ``(N, 3)``.
        source_points : np.ndarray
            Source point coordinates for reference, shape ``(S, 3)``.

        Returns
        -------
        pyvista.Plotter or None
            The active plotter instance, or ``None`` if PyVista is unavailable.
        """
        if not self._available:
            logger.warning("plot_near_field called but PyVista/VTK is not installed")
            return None

        E_field = np.asarray(E_field, dtype=np.float64)
        H_field = np.asarray(H_field, dtype=np.float64)
        observation_points = np.asarray(observation_points, dtype=np.float64)
        source_points = np.asarray(source_points, dtype=np.float64)

        if self.plotter is None:
            self.plotter = pv.Plotter()

        # E-field arrows
        e_magnitude = np.linalg.norm(E_field, axis=-1)
        e_scale = 1e-9 * np.maximum(e_magnitude.max(), 1.0)  # normalise
        if e_magnitude.size > 0:
            self.plotter.add_arrows(
                observation_points,
                E_field,
                scale_factor=e_scale,
                color="red",
                name="E_field_arrows",
                opacity=0.7,
            )

        # H-field arrows
        h_magnitude = np.linalg.norm(H_field, axis=-1)
        h_scale = 1e-9 * np.maximum(h_magnitude.max(), 1.0)
        if h_magnitude.size > 0:
            self.plotter.add_arrows(
                observation_points,
                H_field,
                scale_factor=h_scale,
                color="blue",
                name="H_field_arrows",
                opacity=0.7,
            )

        # Source points as spheres
        if source_points.size > 0:
            self.plotter.add_points(
                source_points,
                color="green",
                point_size=10,
                render_points_spheres=True,
                name="sources",
            )

        self.add_color_mapping(self.plotter, field_type="Near-field E/H")
        self.plotter.show()
        return self.plotter

    # ------------------------------------------------------------------
    # Far-field plotting
    # ------------------------------------------------------------------

    def plot_far_field(
        self,
        E_theta: np.ndarray,
        E_phi: np.ndarray,
        theta: np.ndarray,
        phi: np.ndarray,
    ) -> "pv.Plotter | None":
        """Plot far-field radiation pattern as a 3-D polar plot (dBi scale).

        Parameters
        ----------
        E_theta : np.ndarray
            Theta-component of the electric field, linear scale.
        E_phi : np.ndarray
            Phi-component of the electric field, linear scale.
        theta : np.ndarray
            Theta angles in radians, shape ``(N,)``.
        phi : np.ndarray
            Phi angles in radians, shape ``(N,)``.

        Returns
        -------
        pyvista.Plotter or None
            The active plotter instance, or ``None`` if PyVista is unavailable.
        """
        if not self._available:
            logger.warning("plot_far_field called but PyVista/VTK is not installed")
            return None

        E_theta = np.asarray(E_theta, dtype=np.float64)
        E_phi = np.asarray(E_phi, dtype=np.float64)
        theta = np.asarray(theta, dtype=np.float64)
        phi = np.asarray(phi, dtype=np.float64)

        # Combine polarisation components and convert to dBi
        e_total = np.sqrt(np.abs(E_theta) ** 2 + np.abs(E_phi) ** 2)
        e_total[e_total == 0] = np.nan  # avoid log(0)
        gain_dbi = 10.0 * np.log10(e_total ** 2)

        if self.plotter is None:
            self.plotter = pv.Plotter()

        # Build spherical coordinates for the radiation surface
        N = len(theta)
        x = gain_dbi * np.sin(theta) * np.cos(phi)
        y = gain_dbi * np.sin(theta) * np.sin(phi)
        z = gain_dbi * np.cos(theta)

        # Create a simple triangle mesh for the pattern
        points = np.column_stack((x, y, z))
        pattern = pv.PolyData(points)
        pattern["gain_dBi"] = gain_dbi

        self.plotter.add_mesh(
            pattern,
            cmap="viridis",
            clim=[float(gain_dbi.min()), float(gain_dbi.max())],
            show_edges=True,
            opacity=0.8,
            name="far_field_pattern",
        )

        self.add_color_mapping(self.plotter, field_type="Far-field (dBi)")
        self.plotter.show()
        return self.plotter

    # ------------------------------------------------------------------
    # Cross-section contour
    # ------------------------------------------------------------------

    def plot_contour_on_cross_section(
        self,
        field_data: np.ndarray,
        cross_section_plane: str = "xy",
        z_value: float = 0.0,
    ) -> "pv.Plotter | None":
        """Plot field magnitude contour on a cross-sectional plane.

        Parameters
        ----------
        field_data : np.ndarray
            2-D array of field values on the chosen plane.
        cross_section_plane : str, optional
            Plane to slice along: ``'xy'``, ``'xz'``, or ``'yz'``.
        z_value : float, optional
            Coordinate value for the fixed axis (in metres).

        Returns
        -------
        pyvista.Plotter or None
            The active plotter instance, or ``None`` if PyVista is unavailable.
        """
        if not self._available:
            logger.warning(
                "plot_contour_on_cross_section called but PyVista/VTK is not installed"
            )
            return None

        field_data = np.asarray(field_data, dtype=np.float64)

        if self.plotter is None:
            self.plotter = pv.Plotter()

        # Create a structured grid from the 2-D data
        ny, nx = field_data.shape
        x = np.linspace(-1.0, 1.0, nx)
        y = np.linspace(-1.0, 1.0, ny)
        xx, yy = np.meshgrid(x, y)

        if cross_section_plane == "xy":
            zz = np.full_like(xx, z_value)
            points = np.column_stack((xx.ravel(), yy.ravel(), zz.ravel()))
        elif cross_section_plane == "xz":
            zz = np.column_stack((xx.ravel(), np.zeros_like(xx.ravel()), yy.ravel()))
            points = np.column_stack(
                (xx.ravel(), np.full(xx.size, z_value), yy.ravel())
            )
        elif cross_section_plane == "yz":
            points = np.column_stack(
                (np.full(yy.size, z_value), yy.ravel(), xx.ravel())
            )
        else:
            raise ValueError(f"Unknown cross_section_plane '{cross_section_plane}'")

        field_flat = field_data.ravel()
        data = pv.PolyData(points)
        data["field_magnitude"] = np.abs(field_flat)

        self.plotter.add_mesh(
            data,
            scalars="field_magnitude",
            cmap="viridis",
            show_edges=True,
            opacity=0.8,
            name="cross_section_contour",
        )

        self.add_color_mapping(self.plotter, field_type=f"Cross-section ({cross_section_plane})")
        self.plotter.show()
        return self.plotter

    # ------------------------------------------------------------------
    # Colour mapping helper
    # ------------------------------------------------------------------

    def add_color_mapping(
        self,
        plotter: "pv.Plotter",
        field_type: str = "E",
        cmap: str = "viridis",
    ) -> None:
        """Add a colour-bar legend to the given plotter.

        Parameters
        ----------
        plotter : pyvista.Plotter
            The active PyVista plotter instance.
        field_type : str, optional
            Descriptor shown on the colour bar (e.g. ``'E'``, ``'H'``).
        cmap : str, optional
            Matplotlib colormap name used for the colour bar.
        """
        if not self._available:
            logger.warning("add_color_mapping called but PyVista/VTK is not installed")
            return None  # type: ignore[return-value]

        plotter.add_scalar_bar(
            field_type,
            cmap=cmap,
            title_fontsize=12,
            label_fontsize=10,
        )

    # ------------------------------------------------------------------
    # View angle helper
    # ------------------------------------------------------------------

    def set_view_angle(self, angle: str = "xy") -> None:
        """Set the camera view angle of the active plotter.

        Parameters
        ----------
        angle : str, optional
            Preset view direction: ``'xy'``, ``'xz'``, ``'yz'``, or ``'iso'``.
        """
        if not self._available:
            logger.warning("set_view_angle called but PyVista/VTK is not installed")
            return

        if self.plotter is None:
            logger.warning("set_view_angle called but no plotter has been created yet")
            return

        view_map = {
            "xy": [0, 1, 0],
            "xz": [1, 0, 0],
            "yz": [0, 0, 1],
            "iso": None,  # default isometric
        }

        if angle not in view_map:
            raise ValueError(
                f"Unknown view angle '{angle}'; choose from {list(view_map.keys())}"
            )

        camera_position = view_map[angle]
        if camera_position is not None:
            self.plotter.camera_position = camera_position
