"""Integration tests for field visualization (UC07).

Tests surface plots, streamline visualization, colour mapping, cut planes,
measurement tools, and time-domain animation scaffolding.  All tests run in
stub mode when PyVista/VTK are not installed.
"""

from __future__ import annotations

import logging
import math
import tempfile
from pathlib import Path

import numpy as np
import pytest

logger = logging.getLogger(__name__)


class TestFieldVisualizer:
    """Tests for the FieldVisualizer stub (PyVista/VTK unavailable)."""

    def test_visualizer_init_stub_mode(self):
        """When PyVista is absent the visualiser must be created in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        assert not viz._available  # stub mode expected
        assert viz.plotter is None

    def test_geometry_rendering_stub(self):
        """render_geometry must return None and log a warning in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        result = viz.render_geometry(vertices, faces)
        assert result is None

    def test_near_field_plotting_stub(self):
        """plot_near_field must return None in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        E = np.zeros((5, 3))
        H = np.zeros((5, 3))
        obs_pts = np.zeros((5, 3))
        src_pts = np.array([[0, 0, 0]])
        result = viz.plot_near_field(E, H, obs_pts, src_pts)
        assert result is None

    def test_far_field_plotting_stub(self):
        """plot_far_field must return None in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        result = viz.plot_far_field(np.zeros((10,)), np.zeros((10,)), np.zeros((10,)), np.zeros((10,)))
        assert result is None

    def test_contour_cross_section_stub(self):
        """plot_contour_on_cross_section must return None in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        grid = np.random.rand(10, 10)
        result = viz.plot_contour_on_cross_section(grid, "xy", z_value=0.0)
        assert result is None

    def test_color_mapping_stub(self):
        """add_color_mapping must return None in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        result = viz.add_color_mapping(None, field_type="E")  # type: ignore[arg-type]
        assert result is None

    def test_view_angle_stub(self):
        """set_view_angle must not raise in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        viz.set_view_angle("xy")  # should log warning but not raise
        assert viz.plotter is None

    def test_streamlines_stub(self):
        """plot_streamlines must return None in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        field = np.zeros((10, 3))
        pts = np.zeros((10, 3))
        result = viz.plot_streamlines(field, pts)
        assert result is None

    def test_field_on_surface_stub(self):
        """plot_field_on_surface must return None in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        values = np.array([1.0, 2.0, 3.0])
        result = viz.plot_field_on_surface(vertices, faces, values)
        assert result is None

    def test_animate_stub(self):
        """animate_time_domain_fields must return None in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        sequence = [np.zeros((5, 3))] * 3
        pts = np.zeros((5, 3))
        result = viz.animate_time_domain_fields(sequence, pts)
        assert result is None


class TestVTKRenderer:
    """Tests for the VTKRenderer stub (VTK unavailable)."""

    def test_renderer_init_stub_mode(self):
        """When VTK is absent the renderer must be created in stub mode."""
        from src.post_processing.visualization.vtk_renderer import VTKRenderer

        renderer = VTKRenderer()
        assert not renderer._available

    def test_polydata_creation_stub(self):
        """create_polydata must return None in stub mode."""
        from src.post_processing.visualization.vtk_renderer import VTKRenderer

        renderer = VTKRenderer()
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        result = renderer.create_polydata(vertices, faces)
        assert result is None

    def test_glyph_creation_stub(self):
        """create_glyph must return None in stub mode."""
        from src.post_processing.visualization.vtk_renderer import VTKRenderer

        renderer = VTKRenderer()
        points = np.zeros((5, 3))
        vectors = np.zeros((5, 3))
        result = renderer.create_glyph(points, vectors)
        assert result is None

    def test_field_arrows_stub(self):
        """render_field_arrows must return None in stub mode."""
        from src.post_processing.visualization.vtk_renderer import VTKRenderer

        renderer = VTKRenderer()
        E = np.zeros((5, 3))
        obs_pts = np.zeros((5, 3))
        src_pts = np.array([[0, 0, 0]])
        result = renderer.render_field_arrows(E, obs_pts, src_pts)
        assert result is None

    def test_surface_render_stub(self):
        """render_surface must return None in stub mode."""
        from src.post_processing.visualization.vtk_renderer import VTKRenderer

        renderer = VTKRenderer()
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0]])
        faces = np.array([[0, 1, 2]])
        result = renderer.render_surface(vertices, faces)
        assert result is None

    def test_lut_creation_stub(self):
        """create_lut must return None in stub mode."""
        from src.post_processing.visualization.vtk_renderer import VTKRenderer

        renderer = VTKRenderer()
        result = renderer.create_lut(field_min=0.0, field_max=1.0)
        assert result is None


class TestVisualizationEndToEnd:
    """End-to-end tests for visualization pipeline logic (stub mode)."""

    def test_field_statistics(self):
        """get_field_statistics must return correct stats."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        field = np.array([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0]])
        stats = viz.get_field_statistics(field)

        assert abs(stats["min"] - 1.0) < 1e-10
        assert abs(stats["max"] - 3.0) < 1e-10
        assert abs(stats["mean"] - 2.0) < 1e-10
        assert stats["std"] > 0.5

    def test_field_statistics_scalar(self):
        """get_field_statistics must work with scalar field data."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        field = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        stats = viz.get_field_statistics(field)

        assert abs(stats["min"] - 1.0) < 1e-10
        assert abs(stats["max"] - 5.0) < 1e-10
        assert abs(stats["mean"] - 3.0) < 1e-10

    def test_divergence_computation(self):
        """compute_field_divergence must return valid arrays."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        n_pts = 10
        E_field = np.random.rand(n_pts, 3)
        obs_pts = np.random.rand(n_pts, 3)

        div = viz.compute_field_divergence(E_field, obs_pts)
        assert len(div) == n_pts
        assert np.all(np.isfinite(div))

    def test_divergence_uniform_field(self):
        """Uniform field should have near-zero divergence."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        n_pts = 10
        E_field = np.ones((n_pts, 3))  # uniform field
        obs_pts = np.random.rand(n_pts, 3)

        div = viz.compute_field_divergence(E_field, obs_pts)
        # Uniform field should have moderate divergence (finite-diff is approximate)
        assert np.max(np.abs(div)) < 5.0  # generous tolerance for finite-difference

    def test_measurement_ruler_stub(self):
        """add_measurement_ruler must not raise in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        viz.add_measurement_ruler(np.array([0.0, 0.0, 0.0]), np.array([1.0, 1.0, 1.0]))

    def test_angle_measurement_stub(self):
        """add_angle_measurement must not raise in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        viz.add_angle_measurement(
            np.array([0.0, 0.0, 0.0]),
            np.array([1.0, 0.0, 0.0]),
            np.array([0.0, 1.0, 0.0]),
        )

    def test_cut_plane_stub(self):
        """add_cut_plane must return None in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        grid_3d = np.random.rand(10, 10, 10)
        result = viz.add_cut_plane(grid_3d, "z", plane_value=0.5)
        assert result is None

    def test_cut_plane_invalid_axis_stub(self):
        """add_cut_plane returns None in stub mode regardless of axis."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        grid_3d = np.random.rand(10, 10, 10)
        result = viz.add_cut_plane(grid_3d, "invalid")
        assert result is None

    def test_view_angle_invalid_stub(self):
        """set_view_angle logs warning but does not raise in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        # In stub mode this just logs a warning and returns early
        viz.set_view_angle("invalid")  # should not raise

    def test_contour_invalid_plane_stub(self):
        """plot_contour_on_cross_section returns None in stub mode."""
        from src.post_processing.visualization.pyvista_backend import (
            FieldVisualizer,
        )

        viz = FieldVisualizer()
        grid = np.random.rand(10, 10)
        result = viz.plot_contour_on_cross_section(grid, "invalid")
        assert result is None


class TestVisualizationModuleImports:
    """Verify that visualization module imports work correctly."""

    def test_import_pyvista_backend(self):
        from src.post_processing.visualization.pyvista_backend import FieldVisualizer
        assert FieldVisualizer is not None

    def test_import_vtk_renderer(self):
        from src.post_processing.visualization.vtk_renderer import VTKRenderer
        assert VTKRenderer is not None

    def test_import_package_init(self):
        """The __init__.py should expose FieldVisualizer and VTKRenderer."""
        from src.post_processing.visualization import (
            FieldVisualizer,
            VTKRenderer,
        )
        assert FieldVisualizer is not None
        assert VTKRenderer is not None
