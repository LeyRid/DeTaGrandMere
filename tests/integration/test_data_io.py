"""Integration tests for data I/O (UC09).

Tests Touchstone export/import, HDF5 export/import, plot export, and
data integrity validation across all supported formats.
"""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def sample_sparams():
    """Generate sample S-parameter data for testing."""
    n_freq = 10
    n_ports = 2
    frequencies = np.linspace(1e9, 2e9, n_freq)  # 1-2 GHz

    # Create a realistic S-parameter matrix (diagonal dominant)
    s_params = np.zeros((n_freq, n_ports, n_ports), dtype=complex)
    for i in range(n_freq):
        freq_norm = i / (n_freq - 1)  # 0 to 1
        s_params[i, 0, 0] = -20 + 10 * freq_norm + 0j  # S11 from -20 dB to -10 dB
        s_params[i, 0, 1] = 0.1 * (1 - freq_norm) * np.exp(1j * 0.5)
        s_params[i, 1, 0] = s_params[i, 0, 1]
        s_params[i, 1, 1] = -15 + 5 * freq_norm + 0j

    return frequencies, s_params


@pytest.fixture
def sample_field_data():
    """Generate sample field data for testing."""
    n_pts = 20
    # Near-field: E and H components (6 total)
    near_field = np.random.rand(n_pts, 6) - 0.5
    far_field = np.random.rand(100) + 0j  # Complex far-field

    frequencies = np.linspace(1e9, 1.5e9, 5)  # 1-1.5 GHz
    return near_field, far_field, frequencies


# ---------------------------------------------------------------------------
# Touchstone export/import tests
# ---------------------------------------------------------------------------


class TestTouchstoneExport:
    """Tests for Touchstone file format export."""

    def test_s1p_export(self, temp_dir):
        """Test single-port Touchstone export (.s1p)."""
        from src.post_processing.export.touchstone_export import TouchstoneExporter

        freqs = np.array([1e9, 1.5e9, 2e9])
        s_params = np.zeros((3, 1, 1), dtype=complex)
        s_params[0, 0, 0] = -10 + 0j
        s_params[1, 0, 0] = -15 + 0.5j
        s_params[2, 0, 0] = -20 - 0.3j

        exporter = TouchstoneExporter(n_ports=1)
        output_path = os.path.join(temp_dir, "test.s1p")
        result = exporter.write_sparams(freqs, s_params, output_path)

        assert os.path.exists(result)
        assert result.endswith(".s1p")

        # Verify file content
        with open(result) as f:
            lines = f.readlines()
        assert any("Touchstone" in line for line in lines)
        assert len(lines) > 3  # header + data lines

    def test_s2p_export(self, temp_dir):
        """Test two-port Touchstone export (.s2p)."""
        from src.post_processing.export.touchstone_export import TouchstoneExporter

        freqs = np.array([1e9, 2e9])
        s_params = np.zeros((2, 2, 2), dtype=complex)
        s_params[0, 0, 0] = -10 + 0j
        s_params[0, 0, 1] = 0.5 + 0.1j
        s_params[0, 1, 0] = 0.5 - 0.1j
        s_params[0, 1, 1] = -12 + 0j

        exporter = TouchstoneExporter(n_ports=2)
        output_path = os.path.join(temp_dir, "test.s2p")
        result = exporter.write_sparams(freqs, s_params, output_path)

        assert os.path.exists(result)
        assert result.endswith(".s2p")

    def test_s4p_export(self, temp_dir):
        """Test four-port Touchstone export (.s4p)."""
        from src.post_processing.export.touchstone_export import TouchstoneExporter

        freqs = np.array([1e9])
        s_params = np.zeros((1, 4, 4), dtype=complex)
        for p in range(4):
            for q in range(4):
                s_params[0, p, q] = (p + q) * 0.1j

        exporter = TouchstoneExporter(n_ports=4)
        output_path = os.path.join(temp_dir, "test.s4p")
        result = exporter.write_sparams(freqs, s_params, output_path)

        assert os.path.exists(result)
        assert result.endswith(".s4p")

    def test_realistic_sparams_export(self, temp_dir, sample_sparams):
        """Test export with realistic multi-frequency S-parameter data."""
        from src.post_processing.export.touchstone_export import (
            TouchstoneExporter,
            TouchstoneImporter,
        )

        freqs, s_params = sample_sparams
        exporter = TouchstoneExporter(n_ports=2)
        output_path = os.path.join(temp_dir, "realistic.s2p")
        result = exporter.write_sparams(freqs, s_params, output_path)

        assert os.path.exists(result)

        # Verify data integrity by reading back
        importer = TouchstoneImporter()
        imported = importer.read_sparams(result)

        assert len(imported["frequencies_hz"]) == len(freqs)
        assert imported["n_ports"] == 2


class TestTouchstoneImport:
    """Tests for Touchstone file format import."""

    def test_import_s1p(self, temp_dir):
        """Test importing a single-port Touchstone file."""
        from src.post_processing.export.touchstone_export import (
            TouchstoneExporter,
            TouchstoneImporter,
        )

        # Create and export
        freqs = np.array([1e9, 1.5e9])
        s_params = np.zeros((2, 1, 1), dtype=complex)
        s_params[0, 0, 0] = -10 + 0j
        s_params[1, 0, 0] = -15 + 0.5j

        exporter = TouchstoneExporter(n_ports=1)
        output_path = os.path.join(temp_dir, "import_test.s1p")
        exporter.write_sparams(freqs, s_params, output_path)

        # Import and validate
        importer = TouchstoneImporter()
        data = importer.read_sparams(output_path)

        assert len(data["frequencies_hz"]) == 2
        assert abs(data["frequencies_hz"][0] - 1e9) < 1e6
        assert data["n_ports"] == 1

    def test_import_s2p(self, temp_dir):
        """Test importing a two-port Touchstone file."""
        from src.post_processing.export.touchstone_export import (
            TouchstoneExporter,
            TouchstoneImporter,
        )

        freqs = np.array([1e9])
        s_params = np.zeros((1, 2, 2), dtype=complex)
        s_params[0, 0, 0] = -10 + 0j
        s_params[0, 0, 1] = 0.5 + 0.1j
        s_params[0, 1, 0] = 0.5 - 0.1j
        s_params[0, 1, 1] = -12 + 0j

        exporter = TouchstoneExporter(n_ports=2)
        output_path = os.path.join(temp_dir, "import_test.s2p")
        exporter.write_sparams(freqs, s_params, output_path)

        importer = TouchstoneImporter()
        data = importer.read_sparams(output_path)

        assert len(data["frequencies_hz"]) == 1
        assert data["n_ports"] == 2
        np.testing.assert_allclose(data["s_params"], s_params, rtol=1e-6)

    def test_import_validation_pass(self, temp_dir):
        """Test that valid Touchstone files pass validation."""
        from src.post_processing.export.touchstone_export import (
            TouchstoneExporter,
            TouchstoneImporter,
        )

        freqs = np.array([1e9, 2e9])
        s_params = np.zeros((2, 2, 2), dtype=complex)
        s_params[0] = np.eye(2) * 0.1 + 0j
        s_params[1] = np.eye(2) * 0.05 + 0j

        exporter = TouchstoneExporter(n_ports=2)
        output_path = os.path.join(temp_dir, "valid.s2p")
        exporter.write_sparams(freqs, s_params, output_path)

        importer = TouchstoneImporter(validate=True)
        data = importer.read_sparams(output_path)  # Should not raise

    def test_import_validation_fail(self, temp_dir):
        """Test that corrupted files are caught by validation."""
        from src.post_processing.export.touchstone_export import (
            TouchstoneExporter,
            TouchstoneImporter,
        )

        # Create a valid file but manually corrupt it after export
        freqs = np.array([1e9])
        s_params = np.zeros((1, 2, 2), dtype=complex)
        s_params[0, 0, 0] = -10 + 0j
        s_params[0, 0, 1] = 0.5 + 0.1j
        s_params[0, 1, 0] = 0.5 - 0.1j
        s_params[0, 1, 1] = -12 + 0j

        exporter = TouchstoneExporter(n_ports=2)
        output_path = os.path.join(temp_dir, "corrupt.s2p")
        exporter.write_sparams(freqs, s_params, output_path)

        # Manually corrupt the file by inserting non-numeric data
        with open(output_path, "a") as f:
            f.write("INVALID_DATA\n")

        importer = TouchstoneImporter(validate=True)
        with pytest.raises(ValueError):
            importer.read_sparams(output_path)

    def test_import_nonexistent_file(self):
        """Test that missing files raise FileNotFoundError."""
        from src.post_processing.export.touchstone_export import TouchstoneImporter

        importer = TouchstoneImporter()
        with pytest.raises(FileNotFoundError):
            importer.read_sparams("/nonexistent/path/file.s2p")


class TestTouchstoneRoundTrip:
    """End-to-end round-trip tests for Touchstone format."""

    def test_s1p_roundtrip(self, temp_dir):
        """Test complete export/import cycle for .s1p files."""
        from src.post_processing.export.touchstone_export import (
            TouchstoneExporter,
            TouchstoneImporter,
        )

        freqs = np.array([500e6, 1e9, 1.5e9])
        s_params = np.zeros((3, 1, 1), dtype=complex)
        s_params[0, 0, 0] = -5 + 0j
        s_params[1, 0, 0] = -20 + 1j
        s_params[2, 0, 0] = -30 - 0.5j

        exporter = TouchstoneExporter(n_ports=1)
        output_path = os.path.join(temp_dir, "roundtrip.s1p")
        exporter.write_sparams(freqs, s_params, output_path)

        importer = TouchstoneImporter()
        data = importer.read_sparams(output_path)

        np.testing.assert_allclose(data["frequencies_hz"], freqs, rtol=1e-6)
        np.testing.assert_allclose(data["s_params"], s_params, rtol=1e-4)

    def test_s2p_roundtrip(self, temp_dir):
        """Test complete export/import cycle for .s2p files."""
        from src.post_processing.export.touchstone_export import (
            TouchstoneExporter,
            TouchstoneImporter,
        )

        freqs = np.array([1e9, 2e9])
        s_params = np.zeros((2, 2, 2), dtype=complex)
        s_params[0, 0, 0] = -10 + 0j
        s_params[0, 0, 1] = 0.3 + 0.2j
        s_params[0, 1, 0] = 0.3 - 0.2j
        s_params[0, 1, 1] = -12 + 0j
        s_params[1, 0, 0] = -15 + 0j
        s_params[1, 0, 1] = 0.2 + 0.1j
        s_params[1, 1, 0] = 0.2 - 0.1j
        s_params[1, 1, 1] = -18 + 0j

        exporter = TouchstoneExporter(n_ports=2)
        output_path = os.path.join(temp_dir, "roundtrip.s2p")
        exporter.write_sparams(freqs, s_params, output_path)

        importer = TouchstoneImporter()
        data = importer.read_sparams(output_path)

        np.testing.assert_allclose(data["frequencies_hz"], freqs, rtol=1e-6)
        np.testing.assert_allclose(data["s_params"], s_params, rtol=1e-4)


# ---------------------------------------------------------------------------
# HDF5 export/import tests
# ---------------------------------------------------------------------------


class TestHDF5Export:
    """Tests for HDF5 file format export."""

    def test_export_fields(self, temp_dir, sample_field_data):
        """Test exporting field data to HDF5."""
        from src.utils.data_io import HDF5Exporter

        near_field, far_field, frequencies = sample_field_data
        exporter = HDF5Exporter(compression=True)
        output_path = os.path.join(temp_dir, "fields.h5")
        result = exporter.export_fields(
            near_field=near_field,
            far_field=far_field,
            frequencies=frequencies,
            output_file=output_path,
        )

        assert os.path.exists(result)
        assert result.endswith(".h5")

    def test_export_sparams(self, temp_dir, sample_sparams):
        """Test exporting S-parameters to HDF5."""
        from src.utils.data_io import HDF5Exporter

        freqs, s_params = sample_sparams
        exporter = HDF5Exporter(compression=True)
        output_path = os.path.join(temp_dir, "sparams.h5")
        result = exporter.export_sparams(freqs, s_params, output_path)

        assert os.path.exists(result)
        assert result.endswith(".h5")

    def test_export_with_metadata(self, temp_dir):
        """Test exporting with custom metadata."""
        from src.utils.data_io import HDF5Exporter

        freqs = np.array([1e9])
        s_params = np.zeros((1, 2, 2), dtype=complex)
        s_params[0] = np.eye(2) * 0.1 + 0j

        exporter = HDF5Exporter(compression=False)
        output_path = os.path.join(temp_dir, "with_meta.h5")
        result = exporter.export_sparams(
            freqs, s_params, output_path,
            metadata={"simulation_type": "FEM", "mesh_order": "2nd"}
        )

        assert os.path.exists(result)


class TestHDF5Import:
    """Tests for HDF5 file format import."""

    def test_import_hdf5(self, temp_dir):
        """Test importing an HDF5 file with field data."""
        from src.utils.data_io import HDF5Exporter, HDF5Importer

        # Create and export
        near_field = np.random.rand(10, 6) - 0.5
        far_field = np.random.rand(50) + 0j
        frequencies = np.array([1e9, 1.5e9])

        exporter = HDF5Exporter(compression=False)
        output_path = os.path.join(temp_dir, "test.h5")
        exporter.export_fields(near_field, far_field, frequencies, output_path)

        # Import and validate
        importer = HDF5Importer()
        data = importer.import_hdf5(output_path)

        assert "metadata" in data
        assert "frequencies" in data
        np.testing.assert_allclose(data["frequencies"], frequencies, rtol=1e-6)

    def test_import_partial(self, temp_dir):
        """Test importing only specific datasets from HDF5."""
        from src.utils.data_io import HDF5Exporter, HDF5Importer

        near_field = np.random.rand(10, 6) - 0.5
        far_field = np.random.rand(50) + 0j
        frequencies = np.array([1e9])

        exporter = HDF5Exporter(compression=False)
        output_path = os.path.join(temp_dir, "partial.h5")
        exporter.export_fields(near_field, far_field, frequencies, output_path)

        importer = HDF5Importer()
        data = importer.import_partial(
            output_path,
            ["frequencies", "far_field/E_theta"]
        )

        assert "frequencies" in data
        assert "far_field/E_theta" in data
        assert len(data["frequencies"]) == 1


class TestHDF5RoundTrip:
    """End-to-end round-trip tests for HDF5 format."""

    def test_fields_roundtrip(self, temp_dir):
        """Test complete export/import cycle for field data."""
        from src.utils.data_io import HDF5Exporter, HDF5Importer

        near_field = np.array([[1.0, 0.5, 0.3, 0.2, 0.1, 0.05]] * 5)
        far_field = np.array([0.8 + 0.2j] * 20)
        frequencies = np.array([1e9, 1.5e9, 2e9])

        exporter = HDF5Exporter(compression=False)
        output_path = os.path.join(temp_dir, "rt_fields.h5")
        exporter.export_fields(near_field, far_field, frequencies, output_path)

        importer = HDF5Importer()
        data = importer.import_hdf5(output_path)

        np.testing.assert_allclose(data["frequencies"], frequencies, rtol=1e-6)
        np.testing.assert_allclose(data["near_field/E_field"], near_field[:, :3], atol=1e-6)

    def test_sparams_roundtrip(self, temp_dir):
        """Test complete export/import cycle for S-parameters."""
        from src.utils.data_io import HDF5Exporter, HDF5Importer

        freqs = np.array([1e9, 2e9])
        s_params = np.zeros((2, 2, 2), dtype=complex)
        s_params[0, 0, 0] = -10 + 0j
        s_params[0, 0, 1] = 0.5 + 0.1j
        s_params[0, 1, 0] = 0.5 - 0.1j
        s_params[0, 1, 1] = -12 + 0j

        exporter = HDF5Exporter(compression=False)
        output_path = os.path.join(temp_dir, "rt_sparams.h5")
        exporter.export_sparams(freqs, s_params, output_path)

        importer = HDF5Importer()
        data = importer.import_hdf5(output_path)

        np.testing.assert_allclose(data["frequencies"], freqs, rtol=1e-6)
        np.testing.assert_allclose(data["s_parameters"], s_params, rtol=1e-4)


# ---------------------------------------------------------------------------
# Plot export tests
# ---------------------------------------------------------------------------


class TestPlotExport:
    """Tests for plot export module."""

    def test_sparam_plot_export(self):
        """Test exporting S-parameter plots."""
        from src.post_processing.export.plot_export import PlotExporter

        freqs = np.linspace(1e9, 2e9, 10)
        s11_mag = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
        s11_phase = np.linspace(0, 180, 10)

        exporter = PlotExporter(output_dir="/tmp/test_plots")
        saved_files = exporter.render_sparam_plot(
            frequencies=freqs,
            s11_mag=s11_mag,
            s11_phase=s11_phase,
            output_filename="test_sparams",
        )

        assert len(saved_files) >= 3  # png, pdf, svg
        for f in saved_files:
            assert os.path.exists(f)

    def test_radiation_pattern_export(self):
        """Test exporting radiation pattern plots."""
        from src.post_processing.export.plot_export import PlotExporter

        theta = np.linspace(0, 180, 36)
        patterns = [np.random.rand(36), np.random.rand(36)]
        phis = [np.array([0]), np.array([90])]

        exporter = PlotExporter(output_dir="/tmp/test_plots")
        saved_files = exporter.render_radiation_pattern(
            theta=theta,
            phi_phis=phis,
            patterns=patterns,
            output_filename="test_rad",
        )

        assert len(saved_files) >= 3
        for f in saved_files:
            assert os.path.exists(f)

    def test_field_distribution_export(self):
        """Test exporting field distribution plots."""
        from src.post_processing.export.plot_export import PlotExporter

        field_mag = np.random.rand(20, 20)
        x_coords = np.linspace(-1, 1, 20)
        y_coords = np.linspace(-1, 1, 20)

        exporter = PlotExporter(output_dir="/tmp/test_plots")
        saved_files = exporter.render_field_distribution(
            field_magnitude=field_mag,
            x_coords=x_coords,
            y_coords=y_coords,
            output_filename="test_field",
        )

        assert len(saved_files) >= 3
        for f in saved_files:
            assert os.path.exists(f)

    def test_antenna_metrics_export(self):
        """Test exporting antenna metrics plots."""
        from src.post_processing.export.plot_export import PlotExporter

        metrics = {
            "directivity": 8.5,
            "gain": 7.2,
            "bandwidth": 15.3,
            "fb_ratio": 20.1,
        }

        exporter = PlotExporter(output_dir="/tmp/test_plots")
        saved_files = exporter.render_antenna_metrics(
            metrics=metrics,
            output_filename="test_metrics",
        )

        assert len(saved_files) >= 3
        for f in saved_files:
            assert os.path.exists(f)


# ---------------------------------------------------------------------------
# Error handling tests
# ---------------------------------------------------------------------------


class TestDataIOErrorHandling:
    """Tests for error handling in data I/O operations."""

    def test_touchstone_nonexistent_file(self):
        """Test FileNotFoundError for missing Touchstone file."""
        from src.post_processing.export.touchstone_export import TouchstoneImporter

        importer = TouchstoneImporter()
        with pytest.raises(FileNotFoundError):
            importer.read_sparams("/nonexistent/file.s2p")

    def test_hdf5_nonexistent_file(self):
        """Test FileNotFoundError for missing HDF5 file."""
        from src.utils.data_io import HDF5Importer

        importer = HDF5Importer()
        with pytest.raises(FileNotFoundError):
            importer.import_hdf5("/nonexistent/file.h5")

    def test_plot_export_no_matplotlib(self):
        """Test that PlotExporter raises ImportError without matplotlib."""
        # This test verifies the module structure; actual import error only
        # occurs when matplotlib is not installed (which it is in CI)
        from src.post_processing.export.plot_export import HAS_MATPLOTLIB

        if HAS_MATPLOTLIB:
            # If matplotlib is available, verify normal operation
            from src.post_processing.export.plot_export import PlotExporter
            exporter = PlotExporter(output_dir="/tmp/test_plots")
            assert exporter is not None
        else:
            # If matplotlib is not available, verify error is raised
            with pytest.raises(ImportError):
                from src.post_processing.export.plot_export import PlotExporter
                PlotExporter(output_dir="/tmp/test_plots")
