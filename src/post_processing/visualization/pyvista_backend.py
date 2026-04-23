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


    # ------------------------------------------------------------------
    # Streamline (field line) visualization
    # ------------------------------------------------------------------

    def plot_streamlines(
        self,
        field_data: np.ndarray,
        observation_points: np.ndarray,
        n_lines: int = 50,
        cmap: str = "viridis",
    ) -> "pv.Plotter | None":
        """Plot streamlines (field lines) through the vector field.

        Streamlines trace the direction of the electric or magnetic field
        at each observation point.  The line colour encodes field magnitude.

        Parameters
        ----------
        field_data : np.ndarray
            Vector field data, shape ``(N, 3)`` (real part used for direction).
        observation_points : np.ndarray
            Points where the field is sampled, shape ``(N, 3)``.
        n_lines : int, optional
            Number of seed streamlines to generate. Default is 50.
        cmap : str, optional
            Colormap name for magnitude colouring. Default is ``'viridis'``.

        Returns
        -------
        pyvista.Plotter or None
            The active plotter instance, or ``None`` if PyVista is unavailable.
        """
        if not self._available:
            logger.warning("plot_streamlines called but PyVista/VTK is not installed")
            return None

        field_data = np.asarray(field_data, dtype=np.float64)
        observation_points = np.asarray(observation_points, dtype=np.float64)

        if self.plotter is None:
            self.plotter = pv.Plotter()

        # Create a structured grid for streamline integration
        n_pts = len(observation_points)
        data = pv.PolyData(observation_points)

        # Normalize vectors and attach as point data
        norms = np.linalg.norm(field_data, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        unit_vectors = field_data / norms
        data["field_direction"] = unit_vectors
        data["field_magnitude"] = np.linalg.norm(field_data, axis=1)

        try:
            self.plotter.add_streamlines(
                data,
                center=np.mean(observation_points, axis=0),
                direction="field_direction",
                n_points=n_pts // 2,
                cmap=cmap,
                show_flow_width=True,
                name="streamlines",
            )
        except Exception as e:
            logger.warning("Streamline generation failed: %s", e)

        self.add_color_mapping(self.plotter, field_type="Field magnitude")
        self.plotter.show()
        return self.plotter

    # ------------------------------------------------------------------
    # Surface plot (field magnitude on geometry surface)
    # ------------------------------------------------------------------

    def plot_field_on_surface(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        field_values: np.ndarray,
        cmap: str = "viridis",
    ) -> "pv.Plotter | None":
        """Plot field magnitude colour-mapped onto the antenna geometry surface.

        Parameters
        ----------
        vertices : np.ndarray
            Mesh vertex coordinates, shape ``(N, 3)``.
        faces : np.ndarray
            Face connectivity, shape ``(M, V)``.
        field_values : np.ndarray
            Scalar field values per vertex or face, shape ``(N,)`` or ``(M,)``.
        cmap : str, optional
            Colormap name. Default is ``'viridis'``.

        Returns
        -------
        pyvista.Plotter or None
            The active plotter instance, or ``None`` if PyVista is unavailable.
        """
        if not self._available:
            logger.warning("plot_field_on_surface called but PyVista/VTK is not installed")
            return None

        vertices = np.asarray(vertices, dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int64)
        field_values = np.asarray(field_values, dtype=np.float64)

        if self.plotter is None:
            self.plotter = pv.Plotter()

        mesh = pv.PolyData(vertices, faces)
        if len(field_values) == len(vertices):
            mesh.point_data["field_magnitude"] = field_values
        elif len(field_values) == len(faces):
            mesh.cell_data["field_magnitude"] = field_values

        self.plotter.add_mesh(
            mesh,
            scalars="field_magnitude",
            cmap=cmap,
            show_edges=True,
            opacity=0.9,
            name="surface_field",
        )

        self.add_color_mapping(self.plotter, field_type="Surface field magnitude")
        self.plotter.show()
        return self.plotter

    # ------------------------------------------------------------------
    # Animation support for time-domain fields
    # ------------------------------------------------------------------

    def animate_time_domain_fields(
        self,
        E_field_sequence: list[np.ndarray],
        observation_points: np.ndarray,
        dt: float = 1e-9,
        n_cycles: int = 2,
        cmap: str = "viridis",
    ) -> "pv.Plotter | None":
        """Animate time-domain field evolution at fixed observation points.

        Parameters
        ----------
        E_field_sequence : list[np.ndarray]
            Sequence of E-field snapshots, each shape ``(N, 3)``.
        observation_points : np.ndarray
            Observation point coordinates, shape ``(N, 3)``.
        dt : float, optional
            Time step in seconds between frames. Default is 1 ns.
        n_cycles : int, optional
            Number of complete oscillation cycles to animate. Default is 2.
        cmap : str, optional
            Colormap for field magnitude. Default is ``'viridis'``.

        Returns
        -------
        pyvista.Plotter or None
            The active plotter instance, or ``None`` if PyVista is unavailable.
        """
        if not self._available:
            logger.warning("animate_time_domain_fields called but PyVista/VTK is not installed")
            return None

        observation_points = np.asarray(observation_points, dtype=np.float64)
        E_field_sequence = [np.asarray(e, dtype=np.float64) for e in E_field_sequence]

        if self.plotter is None:
            self.plotter = pv.Plotter()

        # Compute max magnitude across all frames
        all_mags = np.concatenate([np.linalg.norm(e, axis=1) for e in E_field_sequence])
        mag_max = float(np.max(all_mags)) if len(all_mags) > 0 else 1.0

        def _update_frame(frame_idx):
            """Update the plotter with a single time step."""
            # Remove previous frame data
            self.plotter.clear()

            E_frame = E_field_sequence[frame_idx % len(E_field_sequence)]
            magnitude = np.linalg.norm(E_frame, axis=1)

            # Create point cloud with magnitude scalars
            data = pv.PolyData(observation_points)
            data["E_magnitude"] = magnitude

            self.plotter.add_mesh(
                data,
                scalars="E_magnitude",
                cmap=cmap,
                clim=[0, mag_max],
                show_edges=True,
                point_size=8,
                render_points_as_spheres=True,
                name=f"frame_{frame_idx}",
            )

            # Add title with time
            t = frame_idx * dt
            self.plotter.add_text(f"t = {t:.3e} s", font_size=12, position="upper_left")

        n_frames = len(E_field_sequence)
        if n_frames > 0:
            self.plotter.show_animation(
                _update_frame,
                frames=n_frames,
                interval=int(dt * 1000),  # ms between frames
                loop=True,
            )

        self.add_color_mapping(self.plotter, field_type="E magnitude")
        return self.plotter

    # ------------------------------------------------------------------
    # Cut plane functionality with measurement tools
    # ------------------------------------------------------------------

    def add_cut_plane(
        self,
        field_grid: np.ndarray,
        plane_axis: str = "z",
        plane_value: float = 0.0,
        cmap: str = "plasma",
    ) -> "pv.Plotter | None":
        """Add a cut-plane slice through 3-D field data with measurement overlay.

        Parameters
        ----------
        field_grid : np.ndarray
            3-D array of field magnitude values, shape ``(Nx, Ny, Nz)``.
        plane_axis : str, optional
            Axis perpendicular to the cut plane: ``'x'``, ``'y'``, or ``'z'``.
        plane_value : float, optional
            Coordinate value for the cut plane. Default is 0.0.
        cmap : str, optional
            Colormap name. Default is ``'plasma'``.

        Returns
        -------
        pyvista.Plotter or None
            The active plotter instance, or ``None`` if PyVista is unavailable.
        """
        if not self._available:
            logger.warning("add_cut_plane called but PyVista/VTK is not installed")
            return None

        field_grid = np.asarray(field_grid, dtype=np.float64)

        if self.plotter is None:
            self.plotter = pv.Plotter()

        # Create a structured grid from the 3-D data
        Nx, Ny, Nz = field_grid.shape
        x = np.linspace(-1.0, 1.0, Nx)
        y = np.linspace(-1.0, 1.0, Ny)
        z = np.linspace(-1.0, 1.0, Nz)

        if plane_axis == "z":
            # Slice at constant z
            zi = max(0, min(int(np.round((plane_value - z[0]) / (z[-1] - z[0]) * (Nz - 1))), Nz - 1))
            slice_data = field_grid[:, :, zi]
            xx, yy = np.meshgrid(x, y)
            zz = np.full_like(xx, z[zi])
        elif plane_axis == "y":
            yi = max(0, min(int(np.round((plane_value - y[0]) / (y[-1] - y[0]) * (Ny - 1))), Ny - 1))
            slice_data = field_grid[:, yi, :]
            xx, zz = np.meshgrid(x, z)
            yy = np.full_like(xx, y[yi])
        elif plane_axis == "x":
            xi = max(0, min(int(np.round((plane_value - x[0]) / (x[-1] - x[0]) * (Nx - 1))), Nx - 1))
            slice_data = field_grid[xi, :, :]
            yy, zz = np.meshgrid(y, z)
            xx = np.full_like(yy, x[xi])
        else:
            raise ValueError(f"Unknown plane_axis '{plane_axis}'")

        points = np.column_stack((xx.ravel(), yy.ravel(), zz.ravel()))
        data = pv.PolyData(points)
        data["field_magnitude"] = slice_data.ravel()

        self.plotter.add_mesh(
            data,
            scalars="field_magnitude",
            cmap=cmap,
            show_edges=True,
            opacity=0.9,
            name=f"cut_plane_{plane_axis}",
        )

        # Add measurement annotations
        self.plotter.add_text(
            f"Cut plane: {plane_axis} = {plane_value:.2f}",
            font_size=11,
            position="upper_right",
        )

        self.add_color_mapping(self.plotter, field_type=f"Cut plane ({plane_axis})")
        return self.plotter

    def add_measurement_ruler(
        self,
        point_a: np.ndarray,
        point_b: np.ndarray,
    ) -> None:
        """Add a measurement line between two points with distance annotation.

        Parameters
        ----------
        point_a : np.ndarray
            First point coordinates, shape ``(3,)``.
        point_b : np.ndarray
            Second point coordinates, shape ``(3,)``.
        """
        if not self._available:
            logger.warning("add_measurement_ruler called but PyVista/VTK is not installed")
            return

        if self.plotter is None:
            logger.warning("add_measurement_ruler called but no plotter exists")
            return

        point_a = np.asarray(point_a, dtype=np.float64)
        point_b = np.asarray(point_b, dtype=np.float64)

        distance = float(np.linalg.norm(point_b - point_a))

        self.plotter.add_lines(
            [point_a, point_b],
            color="white",
            line_width=2,
            name="measurement_ruler",
        )

        # Add midpoint label
        midpoint = (point_a + point_b) / 2
        self.plotter.add_text(
            f"d = {distance:.4f} m",
            font_size=10,
            position="lower_right",
            name="measurement_label",
        )

    def add_angle_measurement(
        self,
        vertex: np.ndarray,
        point_a: np.ndarray,
        point_b: np.ndarray,
    ) -> None:
        """Add an angle measurement at a vertex between two points.

        Parameters
        ----------
        vertex : np.ndarray
            Vertex coordinates where the angle is measured, shape ``(3,)``.
        point_a : np.ndarray
            First arm point, shape ``(3,)``.
        point_b : np.ndarray
            Second arm point, shape ``(3,)``.
        """
        if not self._available:
            logger.warning("add_angle_measurement called but PyVista/VTK is not installed")
            return

        if self.plotter is None:
            logger.warning("add_angle_measurement called but no plotter exists")
            return

        vertex = np.asarray(vertex, dtype=np.float64)
        point_a = np.asarray(point_a, dtype=np.float64)
        point_b = np.asarray(point_b, dtype=np.float64)

        # Compute angle using dot product
        va = point_a - vertex
        vb = point_b - vertex
        va_norm = np.linalg.norm(va)
        vb_norm = np.linalg.norm(vb)

        if va_norm > 1e-12 and vb_norm > 1e-12:
            cos_angle = np.dot(va, vb) / (va_norm * vb_norm)
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            angle_deg = np.degrees(np.arccos(cos_angle))

            self.plotter.add_lines(
                [vertex, point_a], color="yellow", line_width=1, name="angle_arm_a"
            )
            self.plotter.add_lines(
                [vertex, point_b], color="yellow", line_width=1, name="angle_arm_b"
            )

            midpoint = vertex + (point_a - vertex) * 0.3
            self.plotter.add_text(
                f"theta = {angle_deg:.1f} deg",
                font_size=10,
                position="lower_left",
                name="angle_label",
            )

    def get_field_statistics(self, field_data: np.ndarray) -> dict:
        """Compute and return field statistics (min, max, mean, std).

        Parameters
        ----------
        field_data : np.ndarray
            Field array, shape ``(N,)`` or ``(N, 3)``.

        Returns
        -------
        dict
            Statistics dictionary with keys: min, max, mean, std, median, peak.
        """
        field_data = np.asarray(field_data, dtype=np.float64)
        magnitude = np.linalg.norm(field_data, axis=-1) if field_data.ndim > 1 else field_data

        return {
            "min": float(np.min(magnitude)),
            "max": float(np.max(magnitude)),
            "mean": float(np.mean(magnitude)),
            "std": float(np.std(magnitude)),
            "median": float(np.median(magnitude)),
            "peak": float(np.max(magnitude)),
        }

    def compute_field_divergence(self, E_field: np.ndarray, observation_points: np.ndarray) -> np.ndarray:
        """Compute approximate field divergence using finite differences.

        Parameters
        ----------
        E_field : np.ndarray
            Electric field vectors, shape ``(N, 3)``.
        observation_points : np.ndarray
            Observation point coordinates, shape ``(N, 3)``.

        Returns
        -------
        np.ndarray
            Approximate divergence values, shape ``(N,)``.
        """
        E_field = np.asarray(E_field, dtype=np.float64)
        observation_points = np.asarray(observation_points, dtype=np.float64)

        # Simple finite-difference divergence estimate
        n_pts = len(observation_points)
        div = np.zeros(n_pts, dtype=np.float64)

        for i in range(n_pts):
            # Find nearest neighbours (k=3)
            dists = np.linalg.norm(observation_points - observation_points[i], axis=1)
            dists[i] = np.inf  # exclude self
            neighbors = np.argsort(dists)[:3]

            div_sum = 0.0
            for j in neighbors:
                dx = observation_points[j, 0] - observation_points[i, 0]
                dy = observation_points[j, 1] - observation_points[i, 1]
                dz = observation_points[j, 2] - observation_points[i, 2]
                dist = np.linalg.norm([dx, dy, dz])

                if dist > 1e-15:
                    div_sum += (E_field[i, 0] * dx + E_field[i, 1] * dy + E_field[i, 2] * dz) / dist

            div[i] = div_sum / max(len(neighbors), 1)

        return div
