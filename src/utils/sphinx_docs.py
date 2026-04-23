"""Sphinx documentation configuration for DeTaGrandMere API reference.

This module provides the Sphinx configuration and documentation generation
pipeline for producing comprehensive API documentation from docstrings.

Usage::

    # Generate HTML docs
    python -m src.utils.sphinx_docs --output-dir docs/html

    # Generate PDF docs (requires LaTeX)
    python -m src.utils.sphinx_docs --output-format pdf --output-dir docs/pdf
"""

from __future__ import annotations

import os
import subprocess
import shutil
from typing import Optional, List


class SphinxDocGenerator:
    """Generate API documentation using Sphinx.

    This class automates the creation of HTML and PDF documentation from
    Python docstrings using the Sphinx documentation generator. It handles
    project configuration, extension setup, and build automation.

    Parameters
    ----------
    src_dir : str, default="src/"
        Source directory containing Python modules.
    output_dir : str, default="docs/"
        Output directory for generated documentation.
    project_name : str, default="DeTaGrandMere"
        Project name displayed in documentation headers.
    version : str, default="0.1.0"
        Project version for documentation metadata.
    """

    def __init__(
        self,
        src_dir: str = "src/",
        output_dir: str = "docs/",
        project_name: str = "DeTaGrandMere",
        version: str = "0.1.0",
    ) -> None:
        """Initialise the Sphinx documentation generator."""
        self.src_dir = src_dir
        self.output_dir = output_dir
        self.project_name = project_name
        self.version = version

    def generate_config(self) -> str:
        """Generate sphinx-quickstart configuration files.

        Creates conf.py and index.rst in the output directory with proper
        extensions for autodoc, autosummary, and Napoleon (NumPy-style).

        Returns
        -------
        str
            Path to the generated conf.py file.
        """
        os.makedirs(self.output_dir, exist_ok=True)

        # Generate conf.py
        conf_content = f'''# DeTaGrandMere documentation configuration
import sys
import os

sys.path.insert(0, os.path.abspath("{self.src_dir}"))

project = "{self.project_name}"
copyright = "2024, DeTaGrandMere Developers"
author = "DeTaGrandMere Developers"
version = "{self.version}"
release = "{self.version}"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.coverage",
    "sphinx.ext.mathjax",
    "sphinx_rtd_theme",
]

napoleon_google_docstring = True
napoleon_numpy_docstring = True

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]
master_doc = "index"
'''

        conf_path = os.path.join(self.output_dir, "conf.py")
        with open(conf_path, "w") as f:
            f.write(conf_content)

        # Generate index.rst
        index_content = f'''.. {self.project_name} documentation
.. toctree::
   :maxdepth: 2
   :caption: Contents:

   api_reference
   user_manual
   tutorials
   file_formats
   troubleshooting

API Reference
=============

.. autosummary::
   :toctree: generated

   src.cad.opencascade_wrapper.OpenCASCADEWrapper
   src.cad.cgal_meshing.CGALMeshGenerator
   src.core.mom_solver.solver_engine.MOMSolver
   src.core.field_calculations.near_field.NearFieldCalculator
   src.core.field_calculations.far_field.FarFieldTransformer
   src.post_processing.antenna_metrics.AntennaMetrics
   src.utils.data_io.TouchstoneExporter
   src.utils.data_io.HDF5Exporter
'''

        index_path = os.path.join(self.output_dir, "index.rst")
        with open(index_path, "w") as f:
            f.write(index_content)

        return conf_path

    def build_html(self) -> str:
        """Build HTML documentation.

        Returns
        -------
        str
            Path to the built index.html file.

        Raises
        ------
        RuntimeError
            If sphinx-build is not available or the build fails.
        """
        # Check for sphinx-build
        try:
            result = subprocess.run(
                ["sphinx-build", "--version"],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "sphinx-build not found. Install with: pip install sphinx sphinx-rtd-theme"
                )
        except FileNotFoundError:
            raise RuntimeError(
                "sphinx-build not found. Install with: pip install sphinx sphinx-rtd-theme"
            )

        # Run sphinx-build
        cmd = [
            "sphinx-build",
            "-b", "html",
            "-d", os.path.join(self.output_dir, "_doctrees"),
            self.output_dir,
            os.path.join(self.output_dir, "html"),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Sphinx build failed: {result.stderr}")

        return os.path.join(self.output_dir, "html", "index.html")

    def build_pdf(self) -> str:
        """Build PDF documentation (requires LaTeX).

        Returns
        -------
        str
            Path to the generated PDF file.

        Raises
        ------
        RuntimeError
            If latexmk or pdflatex is not available.
        """
        try:
            cmd = [
                "sphinx-build",
                "-b", "latex",
                "-d", os.path.join(self.output_dir, "_doctrees"),
                self.output_dir,
                os.path.join(self.output_dir, "latex"),
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)

            latex_dir = os.path.join(self.output_dir, "latex")
            subprocess.run(
                ["make", "-C", latex_dir],
                capture_output=True,
                text=True,
                check=True,
            )

            return os.path.join(latex_dir, f"{self.project_name.lower()}.pdf")

        except (FileNotFoundError, subprocess.CalledProcessError) as e:
            raise RuntimeError(
                f"PDF build failed: {str(e)}. Install LaTeX first."
            )


class FileFormatSpecGenerator:
    """Generate documentation for file format specifications.

    This class creates specification documents for the data formats
    supported by DeTaGrandMere, including STEP, Touchstone, and HDF5.
    """

    @staticmethod
    def generate_step_spec(output_path: str = "docs/file_formats/step.md") -> str:
        """Generate STEP file format specification documentation.

        Parameters
        ----------
        output_path : str, default="docs/file_formats/step.md"
            Output path for the specification document.

        Returns
        -------
        str
            Path to the generated specification file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        content = """# STEP File Format Specification

## Overview

DeTaGrandMere supports ISO 10303 (STEP) files for CAD geometry import.
The supported STEP version is AP214 (Constrained 2D Interchange).

## Supported Entities

- `PRODUCT`: Root product definition
- `GEORATIC_MODEL`: Geometric model container
- `VERTEX`, `EDGE`, `FACE`: Topological entities
- `AXIS2_PLACEMENT`, `AXIS2_DIRECTION`: Coordinate systems

## Import Requirements

1. Units must be specified in the file header
2. All geometry must be manifold (no self-intersections)
3. Closed solids are preferred for meshing

## Validation

The OpenCASCADE wrapper validates:
- Non-manifold edge detection
- Degenerate element identification
- Self-intersection checks
"""

        with open(output_path, "w") as f:
            f.write(content)

        return output_path

    @staticmethod
    def generate_touchstone_spec(output_path: str = "docs/file_formats/touchstone.md") -> str:
        """Generate Touchstone file format specification documentation.

        Parameters
        ----------
        output_path : str, default="docs/file_formats/touchstone.md"
            Output path for the specification document.

        Returns
        -------
        str
            Path to the generated specification file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        content = """# Touchstone File Format Specification

## Overview

DeTaGrandMere exports S-parameter data in Touchstone format (RFC 561).
Supports .s1p through .s4p files.

## Header Format

```
#! frequency DB S MA R 50
```

Fields:
- `frequency`: Frequency unit (GHZ, MHZ, KHZ, HZ)
- `parameter`: S (S-parameter), Y (admittance), Z (impedance)
- `format`: M (magnitude/phase), DB (decibel), RI (real/imaginary)
- `reference`: Reference impedance in ohms

## Data Format

Each row contains:
1. Frequency value
2-N: S-parameter values (complex or magnitude/phase depending on format)

## Example .s2p File

```
#! DeTaGrandMere v0.1.0
#! Frequency GHZ S MA R 50
# f(GHz)      S11_mag   S11_phase S21_mag S21_phase S12_mag S12_phase S22_mag S22_phase
1.000000      0.5234    -45.23     0.0012   89.12     ...
```

## Validation

The Touchstone importer validates:
- Header field count matches port count
- Data row length matches expected format
- No NaN or Inf values in data rows
"""

        with open(output_path, "w") as f:
            f.write(content)

        return output_path

    @staticmethod
    def generate_hdf5_spec(output_path: str = "docs/file_formats/hdf5.md") -> str:
        """Generate HDF5 file format specification documentation.

        Parameters
        ----------
        output_path : str, default="docs/file_formats/hdf5.md"
            Output path for the specification document.

        Returns
        -------
        str
            Path to the generated specification file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        content = """# HDF5 File Format Specification

## Overview

DeTaGrandMere uses HDF5 for field data storage with hierarchical organization.

## Directory Structure

```
fields.h5
├── metadata/          # Simulation metadata
│   ├── geometry_name  # String
│   ├── solver_type    # String (EFIE/MFIE/CFIE)
│   └── frequency_hz   # Float
├── frequencies/       # Frequency vector
│   └── values         # Dataset [N_freq] float64
├── field_data/        # Per-frequency field data
│   ├── f_0/           # First frequency point
│   │   ├── E_field    # Dataset [N_obs, 3] complex128
│   │   └── H_field    # Dataset [N_obs, 3] complex128
│   └── f_1/           # Second frequency point
│       ├── E_field
│       └── H_field
└── observation_points/
    └── coordinates    # Dataset [N_obs, 3] float64
```

## Compression

All datasets use gzip compression (level 3) by default.
Field data is stored as complex128 for full precision.

## Metadata

Common metadata fields:
- `geometry_name`: Name of the imported geometry file
- `solver_type`: "EFIE", "MFIE", or "CFIE"
- `frequency_hz`: Operating frequency in Hz
- `mesh_density`: Number of triangles in the mesh
"""

        with open(output_path, "w") as f:
            f.write(content)

        return output_path


class TutorialGenerator:
    """Generate tutorial examples for DeTaGrandMere.

    This class creates step-by-step tutorial scripts demonstrating
    common simulation workflows from geometry import to results export.
    """

    @staticmethod
    def generate_dipole_tutorial(output_path: str = "docs/tutorials/dipole.py") -> str:
        """Generate a half-wave dipole simulation tutorial.

        Parameters
        ----------
        output_path : str, default="docs/tutorials/dipole.py"
            Output path for the tutorial script.

        Returns
        -------
        str
            Path to the generated tutorial file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        content = '''"""Tutorial: Half-Wave Dipole Simulation

This tutorial demonstrates a complete simulation workflow for a
half-wave dipole antenna using DeTaGrandMere.

Steps:
1. Import CAD geometry (STEP file)
2. Generate surface mesh with CGAL
3. Define materials and boundary conditions
4. Set up port excitation
5. Run MoM solver (EFIE formulation)
6. Compute S-parameters and far-field patterns
7. Export results to Touchstone format

Requirements:
- DeTaGrandMere installed
- Python 3.9+
- numpy, scipy, matplotlib
"""

import sys
sys.path.insert(0, "/home/rid/Documents/Caad")

import numpy as np
from src.core.workflow import SimulationWorkflow

# Step 1: Create simulation workflow
workflow = SimulationWorkflow(
    frequency=1e9,           # 1 GHz operating frequency
    solver_type="EFIE",      # Electric Field Integral Equation
)

# Step 2: Run the simulation
status = workflow.run()

# Step 3: Check results
print(f"Simulation status: {status}")

# Step 4: Export S-parameters
from src.utils.data_io import TouchstoneExporter

exporter = TouchstoneExporter()
exporter.export_s_parameters(
    frequencies=workflow.frequencies,
    s_parameters=workflow.s_parameters,
    output_file="dipole_s2p.s2p"
)

print("Results exported to dipole_s2p.s2p")
'''

        with open(output_path, "w") as f:
            f.write(content)

        return output_path

    @staticmethod
    def generate_patch_tutorial(output_path: str = "docs/tutorials/patch.py") -> str:
        """Generate a microstrip patch antenna tutorial.

        Parameters
        ----------
        output_path : str, default="docs/tutorials/patch.py"
            Output path for the tutorial script.

        Returns
        -------
        str
            Path to the generated tutorial file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        content = '''"""Tutorial: Microstrip Patch Antenna Simulation

This tutorial demonstrates simulating a rectangular microstrip patch
antenna on a dielectric substrate using DeTaGrandMere.

Steps:
1. Define substrate material (epsilon_r=2.2, h=1.6mm)
2. Create patch geometry with dimensions for 2.4 GHz resonance
3. Mesh the patch and substrate surfaces
4. Apply PEC boundary conditions to patch and ground plane
5. Define wave port at feed point
6. Run frequency sweep around 2.4 GHz
7. Analyze S11 bandwidth and radiation pattern

Requirements:
- DeTaGrandMere installed
- Python 3.9+
"""

import sys
sys.path.insert(0, "/home/rid/Documents/Caad")

import numpy as np
from src.core.workflow import SimulationWorkflow
from src.cad.material_database import MaterialDatabase

# Step 1: Define substrate material
db = MaterialDatabase()
substrate = db.define_material(
    name="FR4",
    epsilon_r=2.2,
    loss_tangent=0.02,
    mu_r=1.0,
)

# Step 2: Create patch dimensions for 2.4 GHz
f_center = 2.4e9
c = 299792458.0

# Approximate patch dimensions
L = 0.49 * c / (np.sqrt(2.2) * f_center)  # Patch length
W = c / (2 * np.sqrt(2.2) * f_center)      # Patch width

print(f"Patch dimensions: {L:.3f}m x {W:.3f}m")

# Step 3: Create workflow with frequency sweep
workflow = SimulationWorkflow(
    frequencies=np.linspace(2.0e9, 3.0e9, 51),  # 2-3 GHz sweep
    solver_type="CFIE",                           # Combined Field IE
)

# Step 4: Run simulation
status = workflow.run()

print(f"Simulation complete: {status}")
'''

        with open(output_path, "w") as f:
            f.write(content)

        return output_path

    @staticmethod
    def generate_array_tutorial(output_path: str = "docs/tutorials/array.py") -> str:
        """Generate a 2x2 antenna array tutorial.

        Parameters
        ----------
        output_path : str, default="docs/tutorials/array.py"
            Output path for the tutorial script.

        Returns
        -------
        str
            Path to the generated tutorial file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        content = '''"""Tutorial: 2x2 Patch Antenna Array

This tutorial demonstrates simulating a 2x2 patch antenna array
with mutual coupling effects using DeTaGrandMere.

Steps:
1. Define single patch unit cell
2. Create 2x2 array with proper spacing
3. Define multiple ports (one per element)
4. Run multi-port simulation for full S-matrix
5. Analyze array factor and beam steering

Requirements:
- DeTaGrandMere installed
- Python 3.9+
"""

import sys
sys.path.insert(0, "/home/rid/Documents/Caad")

import numpy as np
from src.core.workflow import SimulationWorkflow

# Step 1: Define array parameters
n_elements = 4  # 2x2 array
spacing = 0.5e-3  # Element spacing in meters (lambda/2 at 2.4 GHz)

print(f"Array: {n_elements} elements, spacing={spacing:.3f}m")

# Step 2: Create multi-port workflow
workflow = SimulationWorkflow(
    frequency=2.4e9,
    solver_type="CFIE",
    n_ports=n_elements,  # Define ports for each element
)

# Step 3: Run multi-port simulation
status = workflow.run()

print(f"Multi-port simulation complete")
'''

        with open(output_path, "w") as f:
            f.write(content)

        return output_path
