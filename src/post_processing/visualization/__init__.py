"""DeTaGrandMere — Open-Source Antenna Simulation Software (Method of Moments).

This package provides visualization backends for antenna field data:

* ``FieldVisualizer``  — High-level PyVista-based 3-D visualiser.
* ``VTKRenderer``      — Low-level native VTK rendering pipeline.

Both classes handle missing dependencies gracefully, returning ``None`` and
logging warnings rather than raising when PyVista/VTK are unavailable.

Example usage::

    from src.post_processing.visualization import FieldVisualizer, VTKRenderer

    viz = FieldVisualizer()
    renderer = VTKRenderer()
"""

from src.post_processing.visualization.pyvista_backend import FieldVisualizer
from src.post_processing.visualization.vtk_renderer import VTKRenderer

__all__ = ["FieldVisualizer", "VTKRenderer"]
