"""Plot export utilities for generating publication-quality figures.

This module provides the :class:`PlotExporter` class for rendering simulation
results to standard image formats (PDF, PNG, SVG) using matplotlib and PyVista.

Supported plot types:
- Radiation pattern polar plots
- S-parameter magnitude/phase curves
- Field distribution surface plots
- Far-field radiation patterns in 3D
- Near-field magnitude contour maps
- Antenna metric bar charts

Example usage::

    from src.post_processing.export.plot_export import PlotExporter

    exporter = PlotExporter(output_dir="plots/")
    exporter.render_sparam_plot(
        frequencies=freqs,
        s11_mag=s11_mag,
        s11_phase=s11_phase,
        output_file="sparams.png"
    )
    exporter.render_radiation_pattern(
        theta=thetas,
        phi_phis=phis,
        pattern=pattern,
        output_file="radiation.png"
    )
"""

from __future__ import annotations

import os
import numpy as np
from typing import Optional, List, Tuple

try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None  # type: ignore
    Figure = None  # type: ignore

from src.utils.errors import VisualizationError


class PlotExporter:
    """Export simulation plots to PDF, PNG, and SVG formats.

    This class provides methods for rendering various antenna simulation
    results as publication-quality figures in multiple output formats.

    Parameters
    ----------
    output_dir : str, default="plots/"
        Directory where exported plot files will be saved.
    dpi : int, default=300
        Output resolution in dots per inch for raster formats (PNG).
    figure_size : tuple[float, float], default=(8.0, 6.0)
        Default figure dimensions in inches (width, height).
    """

    def __init__(
        self,
        output_dir: str = "plots/",
        dpi: int = 300,
        figure_size: Tuple[float, float] = (8.0, 6.0),
    ) -> None:
        """Initialise the plot exporter."""
        if not HAS_MATPLOTLIB:
            raise VisualizationError(
                "Matplotlib is required for plot export. Install with: pip install matplotlib"
            )

        self.output_dir = output_dir
        self.dpi = dpi
        self.figure_size = figure_size

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)

    def _save_figure(
        self,
        fig: Figure,
        filename: str,
        formats: Optional[List[str]] = None,
    ) -> List[str]:
        """Save a matplotlib figure to multiple output formats.

        Parameters
        ----------
        fig : matplotlib.figure.Figure
            The figure object to save.
        filename : str
            Base filename without extension.
        formats : list[str], optional
            Output formats: 'png', 'pdf', 'svg'. Defaults to all three.

        Returns
        -------
        list[str]
            Full paths of the saved files.

        Raises
        ------
        VisualizationError
            If saving fails or unsupported format is requested.
        """
        if formats is None:
            formats = ["png", "pdf", "svg"]

        supported_formats = {"png", "pdf", "svg"}
        for fmt in formats:
            if fmt not in supported_formats:
                raise VisualizationError(
                    f"Unsupported format: {fmt}",
                    context={"supported": list(supported_formats)},
                )

        saved_files = []
        base_path = os.path.join(self.output_dir, filename)

        for fmt in formats:
            try:
                filepath = f"{base_path}.{fmt}"
                fig.savefig(filepath, dpi=self.dpi if fmt == "png" else None, bbox_inches="tight")
                saved_files.append(filepath)
            except Exception as e:
                raise VisualizationError(
                    f"Failed to save {filename}.{fmt}",
                    context={"error": str(e)},
                )

        return saved_files

    # -------------------------------------------------------------------
    # S-parameter plots
#    ----------------------------------------------------------------

    def render_sparam_plot(
        self,
        frequencies: np.ndarray,
        s11_mag: np.ndarray,
        s11_phase: Optional[np.ndarray] = None,
        s21_mag: Optional[np.ndarray] = None,
        output_filename: str = "sparams",
    ) -> List[str]:
        """Render S-parameter magnitude and phase plot.

        Creates a dual-axis plot showing S-parameter magnitude (in dB) and
        optionally phase (in degrees) versus frequency.

        Parameters
        ----------
        frequencies : np.ndarray
            Frequency array in Hz with shape (N_freq,).
        s11_mag : np.ndarray
            |S11| magnitude values (linear scale) with shape (N_freq,).
        s11_phase : np.ndarray, optional
            S11 phase in degrees. If provided, plotted on secondary axis.
        s21_mag : np.ndarray, optional
            |S21| magnitude for comparison.
        output_filename : str, default="sparams"
            Base filename for saved plots.

        Returns
        -------
        list[str]
            Full paths of the saved PNG and PDF files.
        """
        freq_mhz = frequencies / 1e6
        s11_db = -20 * np.log10(np.maximum(s11_mag, 1e-15))

        fig, ax1 = plt.subplots(figsize=self.figure_size)

        # S11 magnitude (dB)
        ax1.plot(freq_mhz, s11_db, "b-", linewidth=2, label="|S11|")
        ax1.set_xlabel("Frequency (MHz)", fontsize=12)
        ax1.set_ylabel("|S11| (dB)", fontsize=12, color="blue")
        ax1.tick_params(axis="y", labelcolor="blue")
        ax1.grid(True, alpha=0.3)

        # Threshold line at -10 dB
        ax1.axhline(y=-10, color="r", linestyle="--", alpha=0.5, label="-10 dB threshold")

        # S21 if provided
        if s21_mag is not None:
            s21_db = -20 * np.log10(np.maximum(s21_mag, 1e-15))
            ax1.plot(freq_mhz, s21_db, "g-", linewidth=2, label="|S21|")

        # S11 phase on secondary axis
        if s11_phase is not None:
            ax2 = ax1.twinx()
            ax2.plot(freq_mhz, s11_phase, "m--", linewidth=1.5, label="∠S11")
            ax2.set_ylabel("Phase (deg)", fontsize=12, color="magenta")
            ax2.tick_params(axis="y", labelcolor="magenta")

        ax1.legend(loc="upper right", fontsize=10)
        fig.tight_layout()

        saved = self._save_figure(fig, output_filename)
        plt.close(fig)

        return saved

    def render_radiation_pattern(
        self,
        theta: np.ndarray,
        phi_phis: List[np.ndarray],
        patterns: List[np.ndarray],
        output_filename: str = "radiation_pattern",
        plot_type: str = "polar",
    ) -> List[str]:
        """Render far-field radiation pattern plot.

        Creates polar or linear plots of the antenna radiation pattern
        showing field magnitude versus angular position.

        Parameters
        ----------
        theta : np.ndarray
            Theta angles in degrees with shape (N_theta,).
        phi_phis : list[np.ndarray]
            List of phi angle arrays for each cut plane.
        patterns : list[np.ndarray]
            List of field magnitude patterns corresponding to each phi.
        output_filename : str, default="radiation_pattern"
            Base filename for saved plots.
        plot_type : str, default="polar"
            Plot style: 'polar' or 'linear'.

        Returns
        -------
        list[str]
            Full paths of the saved files.
        """
        if plot_type == "polar":
            fig = plt.figure(figsize=(8, 8))
            ax = fig.add_subplot(111, projection="polar")

            for phi, pattern in zip(phi_phis, patterns):
                # Convert to radians and ensure closed loop
                theta_rad = np.deg2rad(np.append(theta, theta[0]))
                pat = np.append(pattern, pattern[0])
                ax.plot(theta_rad, pat, linewidth=2)

            ax.set_theta_zero_location("N")
            ax.set_theta_direction("counterclockwise")
            ax.set_title("Radiation Pattern", fontsize=14)

        else:  # linear plot
            fig, ax = plt.subplots(figsize=self.figure_size)
            for phi, pattern in zip(phi_phis, patterns):
                ax.plot(theta, pattern, linewidth=2, label=f"phi={phi[0]:.1f} deg")
            ax.set_xlabel("Theta (deg)", fontsize=12)
            ax.set_ylabel("Field Magnitude", fontsize=12)
            ax.legend(fontsize=10)
            ax.grid(True, alpha=0.3)

        saved = self._save_figure(fig, output_filename)
        plt.close(fig)

        return saved

    def render_field_distribution(
        self,
        field_magnitude: np.ndarray,
        x_coords: np.ndarray,
        y_coords: np.ndarray,
        output_filename: str = "field_distribution",
        cmap: str = "viridis",
    ) -> List[str]:
        """Render near-field magnitude distribution as a contour plot.

        Creates a 2D color-mapped plot showing field magnitude across
        a cross-section plane.

        Parameters
        ----------
        field_magnitude : np.ndarray
            Field magnitude values with shape (N_y, N_x).
        x_coords : np.ndarray
            X coordinates with shape (N_x,).
        y_coords : np.ndarray
            Y coordinates with shape (N_y,).
        output_filename : str, default="field_distribution"
            Base filename for saved plots.
        cmap : str, default="viridis"
            Matplotlib colormap name.

        Returns
        -------
        list[str]
            Full paths of the saved files.
        """
        fig, ax = plt.subplots(figsize=self.figure_size)
        extent = [x_coords[0], x_coords[-1], y_coords[0], y_coords[-1]]

        im = ax.pcolormesh(
            x_coords,
            y_coords,
            field_magnitude,
            cmap=cmap,
            shading="auto",
        )
        plt.colorbar(im, ax=ax, label="|E| (V/m)")
        ax.set_xlabel("X (m)", fontsize=12)
        ax.set_ylabel("Y (m)", fontsize=12)
        ax.set_title("Near-Field Distribution", fontsize=14)

        saved = self._save_figure(fig, output_filename)
        plt.close(fig)

        return saved

    def render_antenna_metrics(
        self,
        metrics: dict,
        output_filename: str = "antenna_metrics",
    ) -> List[str]:
        """Render antenna metric comparison as a bar chart.

        Creates a horizontal bar chart showing key performance metrics
        including directivity, gain, bandwidth, and front-to-back ratio.

        Parameters
        ----------
        metrics : dict
            Dictionary with keys: 'directivity', 'gain', 'bandwidth',
            'fb_ratio'. Values are numeric (in dB or percent as appropriate).
        output_filename : str, default="antenna_metrics"
            Base filename for saved plots.

        Returns
        -------
        list[str]
            Full paths of the saved files.
        """
        labels = ["Directivity (dBi)", "Gain (dBi)", "Bandwidth (%)", "F/B Ratio (dB)"]
        values = [
            metrics.get("directivity", 0),
            metrics.get("gain", 0),
            metrics.get("bandwidth", 0),
            metrics.get("fb_ratio", 0),
        ]

        fig, ax = plt.subplots(figsize=self.figure_size)
        colors = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759"]
        bars = ax.barh(labels, values, color=colors, edgecolor="black", linewidth=0.5)

        # Add value labels
        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + 0.5,
                bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}",
                va="center",
                fontsize=11,
            )

        ax.set_xlabel("Value", fontsize=12)
        ax.set_title("Antenna Performance Metrics", fontsize=14)
        fig.tight_layout()

        saved = self._save_figure(fig, output_filename)
        plt.close(fig)

        return saved
