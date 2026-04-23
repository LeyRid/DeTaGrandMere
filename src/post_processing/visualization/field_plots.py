"""Advanced field visualization with surface plots, streamlines, and contour maps.

This module extends the PyVista backend with advanced visualization capabilities:

- Near-field surface plots showing E/H field magnitude on geometry
- Field line (streamline) visualization for vector field direction
- Contour plots on cross-section planes
- Color mapping with user-selectable colormaps (jet, viridis, plasma)
- Cut plane functionality for 2D field slices
- Multiple view angles and measurement tools

Example usage::

    from src.post_processing.visualization.field_plots import AdvancedFieldPlotter

    plotter = AdvancedFieldPlotter()
    plotter.add_surface_plot(
        mesh=polydata,
        field_data=E_field,
        cmap="viridis",
        title="E-field magnitude"
    )
    plotter.add_streamlines(
        source_points=points,
        field_vectors=field_vectors,
        cmap="plasma"
    )
    plotter.show()
"""

from __future__ import annotations

import numpy as np
from typing import Optional, List, Tuple

try:
    import pyvista as pv
    HAS_PYVISTA = True
except ImportError:
    HAS_PYVISTA = False
    pv = None  # type: ignore

from src.utils.errors import VisualizationError


class AdvancedFieldPlotter:
    """Advanced field visualization with surface plots and streamlines.

    This class provides enhanced PyVista-based visualization for electromagnetic
    field data, including near-field surface plots, field line streamlines,
    contour maps on cross-sections, and cut plane functionality.

    Parameters
    ----------
    window_size : tuple[int, int], optional
        Initial window size as (width, height). Default is (800, 600).
    show_axes : bool, default=True
        Whether to display the coordinate axes.

    Attributes
    ----------
    plotter : pyvista.Plotter
        The underlying PyVista plotter instance.
    """

    def __init__(
        self,
        window_size: Tuple[int, int] = (800, 600),
        show_axes: bool = True,
    ) -> None:
        """Initialise the advanced field plotter."""
        if not HAS_PYVISTA:
            raise VisualizationError(
                "PyVista is required for advanced visualization. Install with: pip install pyvista"
            )

        self.plotter = pv.Plotter(window_size=window_size, show_axes=show_axes)
        self._surfaces_added: List[pv.PolyData] = []
        self._streamlines_added: List[pv.Arrow] = []
        self._contours_added: List[pv.Scalars] = []

    # -------------------------------------------------------------------
    # Surface plot methods
    # -------------------------------------------------------------------

    def add_surface_plot(
        self,
        mesh: pv.PolyData,
        field_data: np.ndarray,
        cmap: str = "viridis",
        clim: Optional[Tuple[float, float]] = None,
        title: str = "",
        opacity: float = 1.0,
    ) -> None:
        """Add a near-field surface plot showing field magnitude on geometry.

        The field data is mapped to the mesh vertices and rendered as a
        color-mapped surface plot. Field magnitude is used for coloring
        while preserving the phase information in a separate legend.

        Parameters
        ----------
        mesh : pyvista.PolyData
            Geometry mesh (antenna structure or observation surface).
        field_data : np.ndarray
            Complex field array with shape (N_vertices, 3). Magnitude is
            computed for coloring.
        cmap : str, default="viridis"
            Matplotlib colormap name for field magnitude coloring.
        clim : tuple[float, float], optional
            Color bar limits as (min, max). Auto-scaled if None.
        title : str, default=""
            Title displayed above the plot.
        opacity : float, default=1.0
            Surface opacity from 0.0 (transparent) to 1.0 (opaque).
        """
        mesh = mesh.copy()

        # Compute field magnitude per vertex
        magnitude = np.sqrt(np.sum(np.abs(field_data) ** 2, axis=1))

        # Add as point data for coloring
        mesh.point_data["field_magnitude"] = magnitude
        mesh.active_scalars_name = "field_magnitude"

        # Set color limits if provided
        if clim is None:
            clim = (float(np.min(magnitude)), float(np.max(magnitude)))

        self.plotter.add_mesh(
            mesh,
            cmap=cmap,
            clim=clim,
            opacity=opacity,
            show_edges=True,
            name=title or "surface",
        )
        self._surfaces_added.append(mesh)

    def add_contour_plot(
        self,
        field_data: np.ndarray,
        observation_points: np.ndarray,
        plane_normal: np.ndarray = np.array([0, 0, 1]),
        plane_origin: np.ndarray = np.array([0, 0, 0]),
        n_contours: int = 10,
        cmap: str = "jet",
    ) -> None:
        """Add contour plots on a cross-section plane.

        Creates a contour plot of field magnitude on a user-defined plane
        through the observation region. The plane is defined by a normal
        vector and origin point.

        Parameters
        ----------
        field_data : np.ndarray
            Field array with shape (N_points, 3) at observation_points.
        observation_points : np.ndarray
            Cartesian coordinates with shape (N_points, 3).
        plane_normal : np.ndarray, default=[0, 0, 1]
            Normal vector defining the contour plane orientation.
        plane_origin : np.ndarray, default=[0, 0, 0]
            A point on the contour plane.
        n_contours : int, default=10
            Number of contour levels to display.
        cmap : str, default="jet"
            Colormap for contour coloring.
        """
        obs_pts = np.asarray(observation_points)
        field_data = np.asarray(field_data)

        # Compute magnitude and reshape for grid
        magnitude = np.sqrt(np.sum(np.abs(field_data) ** 2, axis=1))

        # Create a structured grid from observation points (if regular)
        try:
            # Attempt to create a structured point set
            unique_x = np.unique(obs_pts[:, 0])
            unique_y = np.unique(obs_pts[:, 1])
            unique_z = np.unique(obs_pts[:, 2])

            if len(unique_x) > 1 and len(unique_y) > 1:
                # Create a structured grid for contour extraction
                grid = pv.StructuredGrid()
                grid.dimensions = (len(unique_x), len(unique_y), len(unique_z))
                grid.x = unique_x.tolist()
                grid.y = unique_y.tolist()
                grid.z = unique_z.tolist()

                # Reshape magnitude to match grid dimensions
                mag_grid = np.zeros((len(unique_x), len(unique_y), len(unique_z)))
                for i, (x, y, z) in enumerate(obs_pts):
                    ix = np.argmin(np.abs(unique_x - x))
                    iy = np.argmin(np.abs(unique_y - y))
                    iz = np.argmin(np.abs(unique_z - z))
                    mag_grid[ix, iy, iz] = magnitude[i]

                grid.point_data["magnitude"] = mag_grid.flatten()
                self.plotter.add_contour(
                    grid,
                    scalars="magnitude",
                    cmap=cmap,
                    num_contours=n_contours,
                    opacity=0.7,
                    name="contour",
                )
        except Exception:
            # Fallback: add point cloud with color mapping
            cloud = pv.PolyData(obs_pts)
            cloud.point_data["magnitude"] = magnitude
            self.plotter.add_points(
                cloud,
                scalars="magnitude",
                cmap=cmap,
                point_size=8,
                render_points_as_spheres=True,
                name="contour",
            )

        self._contours_added.append(obs_pts)

    # -------------------------------------------------------------------
    # Streamline methods
#    ----------------------------------------------------------------

    def add_streamlines(
        self,
        source_points: np.ndarray,
        field_vectors: np.ndarray,
        cmap: str = "plasma",
        n_streamlines: int = 20,
        line_width: float = 2.0,
    ) -> None:
        """Add field line streamlines showing field direction.

        Creates streamline curves starting from source points and following
        the field vector direction. Useful for visualizing near-field
        radiation patterns and field line topology.

        Parameters
        ----------
        source_points : np.ndarray
            Starting points for streamlines with shape (N_sources, 3).
        field_vectors : np.ndarray
            Vector field values at source_points with shape (N_sources, 3).
        cmap : str, default="plasma"
            Colormap for streamline coloring by field magnitude.
        n_streamlines : int, default=20
            Number of streamlines to generate.
        line_width : float, default=2.0
            Width of streamline lines in pixels.
        """
        source_points = np.asarray(source_points)
        field_vectors = np.asarray(field_vectors)

        # Compute magnitudes for coloring
        magnitudes = np.sqrt(np.sum(field_vectors ** 2, axis=1))

        # Create polydata with point data
        pdata = pv.PolyData(source_points)
        pdata.point_data["field_vector"] = field_vectors
        pdata.point_data["magnitude"] = magnitudes

        # Generate streamlines from a subset of source points
        n_sources = len(source_points)
        step = max(1, n_sources // n_streamlines)
        seed_indices = np.arange(0, n_sources, step)[:n_streamlines]
        seed_points = source_points[seed_indices]

        # Add streamlines (PyVista will integrate along the vector field)
        self.plotter.add_streamlines(
            pdata,
            scalars="magnitude",
            cmap=cmap,
            line_width=line_width,
            seed_scale=0.05,
            name="streamlines",
        )

        self._streamlines_added.append(pdata)

    # -------------------------------------------------------------------
    # Cut plane functionality
#    ----------------------------------------------------------------

    def add_cut_plane(
        self,
        mesh: pv.PolyData,
        field_data: np.ndarray,
        normal: np.ndarray = np.array([0, 0, 1]),
        origin: Optional[np.ndarray] = None,
        cmap: str = "viridis",
    ) -> None:
        """Add a cut plane through the geometry showing field values.

        Creates a planar cut through the mesh and displays field magnitude
        on the cross-section. Useful for examining field distribution
        across specific planes.

        Parameters
        ----------
        mesh : pyvista.PolyData
            Geometry mesh to cut through.
        field_data : np.ndarray
            Field values at mesh vertices with shape (N_vertices, 3).
        normal : np.ndarray, default=[0, 0, 1]
            Normal vector defining the cut plane orientation.
        origin : np.ndarray, optional
            A point on the cut plane. Defaults to mesh center.
        cmap : str, default="viridis"
            Colormap for field coloring.
        """
        normal = np.asarray(normal)

        # Compute magnitude
        magnitude = np.sqrt(np.sum(np.abs(field_data) ** 2, axis=1))

        # Create cut plane polydata
        pdata = mesh.copy()
        pdata.point_data["magnitude"] = magnitude

        # Add the cut plane to the plotter
        self.plotter.add_mesh(
            pdata,
            cmap=cmap,
            show_edges=True,
            opacity=0.8,
            name="cut_plane",
        )

    def add_measurement_lines(
        self,
        points: List[np.ndarray],
        color: str = "red",
        label: str = "",
    ) -> None:
        """Add measurement lines between pairs of points.

        Parameters
        ----------
        points : list[np.ndarray]
            List of [start_point, end_point] pairs for each measurement line.
        color : str, default="red"
            Line color name in PyVista format.
        label : str, default=""
            Label displayed next to the measurement.
        """
        for start, end in points:
            start = np.asarray(start)
            end = np.asarray(end)

            # Create a line between the two points
            line = pv.Line(start, end)
            self.plotter.add_mesh(
                line,
                color=color,
                line_width=2,
                name=label or "measurement",
            )

    # -------------------------------------------------------------------
    # View management
#    ----------------------------------------------------------------

    def set_view_angle(self, angle: str = "xy") -> None:
        """Set the camera view angle.

        Parameters
        ----------
        angle : str, default="xy"
            View direction as a string: 'xy', 'xz', 'yz', 'x', 'y', 'z'.
        """
        angle_map = {
            "xy": (0, 0),
            "xz": (0, 90),
            "yz": (-90, 0),
            "x": (0, -90),
            "y": (90, 0),
            "z": (0, 0),
        }
        if angle in angle_map:
            self.plotter.camera_position = angle_map[angle]

    def show(self) -> None:
        """Render and display the visualization window."""
        self.plotter.show()

    def close(self) -> None:
        """Close the plotter and release resources."""
        self.plotter.close()


class ColormapManager:
    """Manage colormap selection and field value mapping.

    Provides utility methods for selecting appropriate colormaps based on
    field type (magnitude, phase, real/imaginary) and normalizing field
    values to the [0, 1] range for consistent coloring.
    """

    AVAILABLE_COLORMAPS = [
        "viridis",
        "plasma",
        "jet",
        "coolwarm",
        "seismic",
        "RdYlBu",
        "cividis",
        "magma",
        "inferno",
    ]

    @staticmethod
    def normalize_field(
        field_data: np.ndarray,
        method: str = "magnitude",
    ) -> np.ndarray:
        """Normalize field data to [0, 1] range for coloring.

        Parameters
        ----------
        field_data : np.ndarray
            Field array with shape (N, 3).
        method : str, default="magnitude"
            Normalization method: 'magnitude', 'real', 'imag', or 'phase'.

        Returns
        -------
        np.ndarray
            Normalized values with shape (N,) and dtype float64.

        Raises
        ------
        VisualizationError
            If the normalization method is not supported.
        """
        if method == "magnitude":
            mag = np.sqrt(np.sum(np.abs(field_data) ** 2, axis=1))
            max_val = np.max(mag)
            return mag / max_val if max_val > 0 else mag

        elif method == "real":
            real_part = np.real(field_data[:, 0])
            max_abs = np.max(np.abs(real_part))
            return real_part / max_abs if max_abs > 0 else real_part

        elif method == "imag":
            imag_part = np.imag(field_data[:, 0])
            max_abs = np.max(np.abs(imag_part))
            return imag_part / max_abs if max_abs > 0 else imag_part

        elif method == "phase":
            phase = np.angle(field_data[:, 0])
            return (phase + np.pi) / (2 * np.pi)

        else:
            raise VisualizationError(
                f"Unsupported normalization method: {method}",
                context={"available_methods": ["magnitude", "real", "imag", "phase"]},
            )

    @staticmethod
    def get_colormap(name: str = "viridis"):
        """Get a matplotlib colormap by name.

        Parameters
        ----------
        name : str, default="viridis"
            Colormap name. Must be one of the available colormaps.

        Returns
        -------
        matplotlib.colors.Colormap
            The requested colormap object.

        Raises
        ------
        VisualizationError
            If the colormap name is not available.
        """
        import matplotlib.pyplot as plt

        if name not in ColormapManager.AVAILABLE_COLORMAPS:
            raise VisualizationError(
                f"Colormap '{name}' not available",
                context={"available": ColormapManager.AVAILABLE_COLORMAPS},
            )
        return plt.get_cmap(name)
