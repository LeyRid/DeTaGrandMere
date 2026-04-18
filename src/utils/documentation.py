"""
Documentation generation utilities for the deTAGrandMere project.

This module provides tools to automatically generate API documentation,
user manuals, and step-by-step tutorials for antenna simulation workflows.
It leverages Python's introspection capabilities to extract docstrings and
generates structured Markdown output suitable for Sphinx or MkDocs.

Example usage::

    from src.utils.documentation import DocGenerator, TutorialGenerator

    # Generate API docs for a module
    gen = DocGenerator(project_name="DeTaGrandMere", version="0.1.0")
    api_docs = gen.generate_api_docs("src.core.mom_solver")
    print(api_docs[:200])

    # Create user manual
    gen.generate_user_manual(output_dir="docs")

    # Generate tutorials
    tutorial_gen = TutorialGenerator()
    dipole_md = tutorial_gen.generate_dipole_tutorial()
    print(dipole_md[:300])
"""

from __future__ import annotations

import inspect
import os
import textwrap
from typing import Any


class DocGenerator:
    """Generate comprehensive documentation for the deTAGrandMere project.

    This class handles the creation of API documentation from module docstrings,
    user manuals with installation and usage instructions, and step-by-step
    tutorials for common antenna simulation workflows.

    Parameters
    ----------
    project_name : str, optional
        Name of the project to document. Default is "DeTaGrandMere".
    version : str, optional
        Version string for the documentation header. Default is "0.1.0".

    Examples
    --------
    >>> gen = DocGenerator("MyProject", "1.2.3")
    >>> docs = gen.generate_api_docs("src.core.mom_solver")
    >>> print(docs)  # doctest: +SKIP
    """

    def __init__(self, project_name: str = "DeTaGrandMere", version: str = "0.1.0") -> None:
        """Initialize the documentation generator.

        Parameters
        ----------
        project_name : str, optional
            Project name for documentation headers.
        version : str, optional
            Version string for the documentation title.
        """
        self.project_name: str = project_name
        self.version: str = version

    def generate_api_docs(self, module_path: str) -> str:
        """Generate API documentation from Python docstrings for a given module.

        Imports the specified module by path and extracts all classes, functions,
        and methods along with their docstrings. Produces a Markdown-formatted
        string suitable for inclusion in project documentation.

        Parameters
        ----------
        module_path : str
            Dot-separated module path (e.g., "src.core.mom_solver").

        Returns
        -------
        str
            Markdown-formatted API documentation string containing class and
            method signatures with descriptions.

        Raises
        ------
        ImportError
            If the module cannot be imported.
        ValueError
            If the module path is empty or invalid.
        """
        if not module_path:
            raise ValueError("module_path must be a non-empty string")

        lines: list[str] = []
        lines.append(f"# API Documentation - {self.project_name} v{self.version}")
        lines.append("")
        lines.append(f"Generated for module: ``{module_path}``")
        lines.append("")
        lines.append("---")
        lines.append("")

        try:
            import importlib
            module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(
                f"Could not import module '{module_path}': {e}"
            ) from e

        # Module docstring
        mod_doc = inspect.getdoc(module)
        if mod_doc:
            lines.append(f"## Module: ``{module_path}``")
            lines.append("")
            lines.append(mod_doc)
            lines.append("")

        # Iterate over module-level objects
        members = {
            name: obj for name, obj in inspect.getmembers(module)
            if not name.startswith("_")
        }

        classes = {}
        functions = {}
        submodules = {}

        for name, obj in members.items():
            if inspect.ismodule(obj):
                full_name = f"{module_path}.{name}"
                submodules[name] = full_name
            elif inspect.isclass(obj):
                classes[name] = obj
            elif callable(obj):
                functions[name] = obj

        # Document submodules
        if submodules:
            lines.append("## Submodules")
            lines.append("")
            for name, path in sorted(submodules.items()):
                lines.append(f"- ``{path}``")
            lines.append("")

        # Document classes
        if classes:
            lines.append("## Classes")
            lines.append("")
            for class_name in sorted(classes.keys()):
                cls = classes[class_name]
                lines.append(f"### ``{class_name}``")
                lines.append("")
                cls_doc = inspect.getdoc(cls)
                if cls_doc:
                    lines.append(cls_doc)
                    lines.append("")

                # Methods
                methods = self._extract_methods(cls)
                if methods:
                    lines.append("**Methods**")
                    lines.append("")
                    for method_name, sig_str, method_doc in methods:
                        lines.append(f"#### ``{method_name}``")
                        lines.append("")
                        lines.append(f"``python")
                        lines.append(f"{sig_str}")
                        lines.append("``")
                        lines.append("")
                        if method_doc:
                            lines.append(method_doc)
                            lines.append("")

                # Attributes (public ones only)
                attrs = self._extract_attributes(cls)
                if attrs:
                    lines.append("**Attributes**")
                    lines.append("")
                    for attr_name, attr_val in attrs:
                        lines.append(f"- ``{attr_name}``: {attr_val}")
                    lines.append("")

        # Document standalone functions
        if functions:
            lines.append("## Functions")
            lines.append("")
            for func_name in sorted(functions.keys()):
                func = functions[func_name]
                sig_str = self._format_signature(func)
                lines.append(f"### ``{func_name}``")
                lines.append("")
                lines.append(f"``python")
                lines.append(f"{sig_str}")
                lines.append("``")
                lines.append("")
                func_doc = inspect.getdoc(func)
                if func_doc:
                    lines.append(func_doc)
                    lines.append("")

        return "\n".join(lines)

    def _extract_methods(self, cls: type) -> list[tuple[str, str, str | None]]:
        """Extract public methods from a class with signatures and docstrings.

        Parameters
        ----------
        cls : type
            A Python class object.

        Returns
        -------
        list of (name, signature_string, docstring) tuples
        """
        methods = []
        for name in dir(cls):
            if name.startswith("_"):
                continue
            obj = getattr(cls, name)
            if callable(obj) and inspect.isfunction(obj):
                sig_str = self._format_signature(obj)
                doc = inspect.getdoc(obj)
                methods.append((name, sig_str, doc))
        return methods

    def _extract_attributes(self, cls: type) -> list[tuple[str, str]]:
        """Extract public instance attributes from a class.

        Parameters
        ----------
        cls : type
            A Python class object.

        Returns
        -------
        list of (name, description_string) tuples
        """
        attrs = []
        try:
            instance = cls.__new__(cls)
            for name in dir(instance):
                if name.startswith("_"):
                    continue
                obj = getattr(instance, name)
                if not callable(obj):
                    desc = type(obj).__name__
                    attrs.append((name, desc))
        except (TypeError, AttributeError):
            pass  # Cannot instantiate; skip attribute extraction
        return attrs

    def _format_signature(self, func: Any) -> str:
        """Format a function or method signature as a Python code string.

        Parameters
        ----------
        func : callable
            A Python function or method object.

        Returns
        -------
        str
            Formatted signature string with type hints.
        """
        try:
            sig = inspect.signature(func)
            params_str = ", ".join(
                f"{name}{param}" for name, param in sig.parameters.items()
            )
            return f"def {func.__name__}({params_str})"
        except (ValueError, TypeError):
            return f"def {func.__name__}(...)"

    def generate_user_manual(self, output_dir: str = "docs") -> None:
        """Create a comprehensive user manual and write it to the docs directory.

        Generates a Markdown-formatted user manual covering installation steps,
        quick start guide, module overview, configuration options, and usage
        examples for the deTAGrandMere project.

        Parameters
        ----------
        output_dir : str, optional
            Directory path where the manual will be written. Default is "docs".

        Notes
        -----
        The generated manual includes sections on:
        - Installation via pip and from source
        - Quick start with a minimal simulation example
        - Overview of core modules (geometry, solver, post-processing)
        - Configuration file format and options
        - Advanced usage examples
        """
        os.makedirs(output_dir, exist_ok=True)

        manual = textwrap.dedent("""\
            # User Manual for {project_name} v{version}

            ## Table of Contents

            1. [Installation](#installation)
               - [From PyPI](#from-pypi)
               - [From Source](#from-source)
            2. [Quick Start](#quick-start)
            3. [Module Overview](#module-overview)
            4. [Configuration](#configuration)
            5. [Examples](#examples)
            6. [API Reference](#api-reference)

            ---

            ## Installation

            ### From PyPI

            Install the latest stable release::

                pip install deTAGrandMere

            ### From Source

            Clone the repository and install in development mode::

                git clone https://github.com/example/deTAGrandMere.git
                cd deTAGrandMere
                pip install -e .

            ## Quick Start

            Run a basic dipole antenna simulation::

                from src.core import geometry, mom_solver
                from src.post_processing import s_parameters

                # Define a half-wave dipole
                dipole = geometry.Dipole(wavelength=1.0, center=[0, 0, 0])

                # Solve using Method of Moments
                solver = mom_solver.MOMSolver(dipole)
                results = solver.solve()

                # Export S-parameters
                s_parameters.export_sparam(results, "output.s2p")

            ## Module Overview

            ### Core Modules

            - ``src.core.geometry``: Antenna geometry definitions (dipole, patch, loop, arrays).
            - ``src.core.mom_solver``: Method of Moments electromagnetic solver.
            - ``src.core.fem_solver``: Finite Element Method solver for complex geometries.
            - ``src.core.materials``: Material property database and interpolation.

            ### Post-Processing

            - ``src.post_processing.s_parameters``: S-parameter computation and export.
            - ``src.post_processing.radiation_patterns``: Far-field pattern generation.
            - ``src.post_processing.impedance``: Input impedance and VSWR calculation.

            ### Utilities

            - ``src.utils.documentation``: Documentation and tutorial generation.
            - ``src.utils.release``: Build and release management.
            - ``src.utils.version_history``: Semantic versioning and changelog management.

            ## Configuration

            deTAGrandMere uses a YAML configuration file (``config.yaml``)::

                solver:
                  type: mom
                  tolerance: 1e-6
                  max_iterations: 500

                mesh:
                  element_order: 2
                  refinement_levels: 3

                output:
                  format: sparam
                  directory: ./results

            ## Examples

            ### Microstrip Patch Antenna

            Create a patch antenna on FR4 substrate and simulate::

                from src.core import geometry, materials
                from src.core import mom_solver

                # Define FR4 material
                fr4 = materials.Material(name="FR4", epsilon_r=4.4, loss_tangent=0.02)

                # Create patch geometry
                patch = geometry.Patch(
                    substrate=fr4,
                    width=10.0,
                    length=10.0,
                    feed_offset=[2.5, 0]
                )

                solver = mom_solver.MOMSolver(patch)
                results = solver.solve()

            ### N-Element Array

            Simulate a uniform linear array with mutual coupling::

                from src.core import geometry, array_engine

                array = array_engine.LinearArray(
                    element_count=8,
                    spacing=0.5,  # wavelength units
                    element_type="dipole"
                )

                results = array.simulate(coupling=True)

            ## API Reference

            For complete API documentation, run the doc generator::

                from src.utils.documentation import DocGenerator
                gen = DocGenerator()
                docs = gen.generate_api_docs("src.core.mom_solver")
                print(docs)
        """).format(project_name=self.project_name, version=self.version)

        output_path = os.path.join(output_dir, "manual.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(manual)

        return None

    def create_tutorial(self, tutorial_name: str = "dipole_simulation") -> None:
        """Create a step-by-step tutorial for common antenna types.

        Generates a Markdown-formatted tutorial covering geometry creation,
        meshing, solver setup, and post-processing for selected antenna types
        (dipole, patch, loop). Saves the tutorial to the tutorials subdirectory.

        Parameters
        ----------
        tutorial_name : str, optional
            Name of the tutorial file (without extension). Default is
            "dipole_simulation". The file will be saved as
            ``{output_dir}/tutorials/{tutorial_name}.md``.

        Notes
        -----
        Each tutorial includes:
        - Prerequisites and setup instructions
        - Complete runnable code examples
        - Explanation of key concepts
        - Expected output and interpretation
        """
        tutorials_dir = os.path.join("docs", "tutorials")
        os.makedirs(tutorials_dir, exist_ok=True)

        tutorial = textwrap.dedent("""\
            # Tutorial: {tutorial_name}

            ## Overview

            This tutorial demonstrates a complete simulation workflow for the
            selected antenna type using deTAGrandMere. You will learn how to
            define geometry, configure the solver, run simulations, and
            export results.

            ## Prerequisites

            - Python 3.9 or later
            - deTAGrandMere installed (see User Manual)
            - NumPy and SciPy

            ## Step-by-Step Guide

            ### Step 1: Import Libraries

            ````python
            import numpy as np
            from src.core import geometry, materials
            from src.core.mom_solver import MOMSolver
            from src.post_processing import s_parameters
            ````

            ### Step 2: Define Materials

            ````python
            air = materials.Material(name="Air", epsilon_r=1.0)
            copper = materials.Material(name="Copper", epsilon_r=1.0, conductivity=5.8e7)
            fr4 = materials.Material(name="FR4", epsilon_r=4.4, loss_tangent=0.02)
            ````

            ### Step 3: Create Antenna Geometry

            ````python
            antenna = geometry.Dipole(
                wavelength=1.0,
                center=[0, 0, 0],
                orientation="z",
                conductor=copper
            )
            ````

            ### Step 4: Configure and Run Solver

            ````python
            solver_config = {
                "tolerance": 1e-6,
                "max_iterations": 500,
                "frequency_range": [1e9, 3e9],
                "num_frequencies": 101
            }

            solver = MOMSolver(antenna, config=solver_config)
            results = solver.solve()
            ````

            ### Step 5: Post-Processing and Export

            ````python
            # Compute S-parameters
            s_params = s_parameters.compute_sparam(results)

            # Export to Touchstone format
            s_parameters.export_touchstone(s_params, "results/dipole.s2p")

            # Plot radiation pattern (requires pyvista)
            try:
                from src.post_processing import radiation_patterns
                radiation_patterns.plot_far_field(results)
            except ImportError:
                print("PyVista not installed; skipping visualization.")
            ````

            ## Expected Output

            After running the tutorial, you should see:

            - ``results/dipole.s2p``: Touchstone S-parameter file
            - Console output showing convergence status and computed frequencies
            - (Optional) A 3D radiation pattern plot

            ## Next Steps

            - Explore the patch antenna tutorial for substrate-based designs.
            - Check the array tutorial for multi-element simulations.
            - Read the configuration reference for advanced solver options.
        """).format(tutorial_name=tutorial_name)

        output_path = os.path.join(tutorials_dir, f"{tutorial_name}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(tutorial)


class TutorialGenerator:
    """Generate specialized antenna simulation tutorials.

    Provides pre-built tutorial content for common antenna types including
    half-wave dipoles, microstrip patches, and N-element arrays. Each tutorial
    includes complete runnable code from geometry creation through S-parameter
    export.

    Examples
    --------
    >>> tg = TutorialGenerator()
    >>> dipole_md = tg.generate_dipole_tutorial()
    >>> assert "half-wave" in dipole_md.lower()
    >>> patch_md = tg.generate_patch_tutorial()
    >>> assert "FR4" in patch_md
    """

    def __init__(self) -> None:
        """Initialize the tutorial generator."""
        pass

    def generate_dipole_tutorial(self) -> str:
        """Generate a tutorial for half-wave dipole simulation.

        Creates a complete step-by-step guide covering geometry creation,
        solver configuration, and S-parameter export for a half-wave dipole
        antenna.

        Returns
        -------
        str
            Markdown-formatted tutorial string with code examples and
            explanations.

        Notes
        -----
        The tutorial covers:
        - Half-wave dipole theory basics
        - Geometry parameterization
        - MoM solver setup
        - Frequency sweep configuration
        - S-parameter export in Touchstone format
        """
        return textwrap.dedent("""\
            # Tutorial: Half-Wave Dipole Simulation

            ## Introduction

            The half-wave dipole is the simplest and most fundamental antenna
            type. This tutorial walks through a complete simulation workflow
            from geometry definition to S-parameter export.

            ## Theory

            A half-wave dipole has a total length of approximately lambda/2,
            where lambda is the free-space wavelength at the operating frequency.
            The input impedance is approximately 73 + j42 ohms at resonance.

            ## Complete Example

            ### Step 1: Setup and Imports

            ````python
            import numpy as np
            from src.core.geometry import Dipole
            from src.core.materials import Material, copper
            from src.core.mom_solver import MOMSolver
            from src.post_processing.s_parameters import export_touchstone
            ````

            ### Step 2: Define Parameters

            ````python
            frequency = 1.0e9  # 1 GHz
            c = 3.0e8          # speed of light in m/s
            wavelength = c / frequency

            # Half-wave dipole length
            dipole_length = wavelength / 2.0

            print(f"Operating frequency: {frequency / 1e9} GHz")
            print(f"Wavelength: {wavelength * 100:.1f} cm")
            print(f"Dipole length: {dipole_length * 100:.1f} cm")
            ````

            ### Step 3: Create Geometry

            ````python
            # Define conductor material
            copper_mat = Material(name="Copper", conductivity=5.8e7)

            # Create half-wave dipole centered at origin
            antenna = Dipole(
                length=dipole_length,
                radius=0.001,       # wire radius in meters
                center=[0, 0, 0],
                orientation="z",
                conductor=copper_mat
            )

            print(f"Created dipole: {antenna}")
            ````

            ### Step 4: Configure Solver

            ````python
            # Define frequency sweep range
            num_freqs = 101
            freq_min = 0.5e9   # 500 MHz
            freq_max = 2.0e9   # 2 GHz

            solver_config = {
                "solver_type": "mom",
                "tolerance": 1e-6,
                "max_iterations": 500,
                "frequency_range": [freq_min, freq_max],
                "num_frequencies": num_freqs,
                "basis_order": 2
            }

            solver = MOMSolver(antenna, config=solver_config)
            print("Solver initialized successfully")
            ````

            ### Step 5: Run Simulation

            ````python
            # Execute the simulation
            results = solver.solve()

            print(f"Simulation complete.")
            print(f"Number of frequency points: {len(results.frequencies)}")
            print(f"Frequency range: {results.frequencies[0]/1e6:.1f} - "
                  f"{results.frequencies[-1]/1e6:.1f} MHz")
            ````

            ### Step 6: Analyze Results

            ````python
            # Extract S11 (reflection coefficient)
            s11_magnitude = np.abs(results.s_parameters[:, 0, 0])
            s11_db = 20 * np.log10(np.maximum(s11_magnitude, 1e-10))

            # Find frequency of best match
            min_idx = np.argmin(s11_magnitude)
            resonant_freq = results.frequencies[min_idx] / 1e9
            s11_best = s11_db[min_idx]

            print(f"Best match frequency: {resonant_freq:.3f} GHz")
            print(f"S11 at resonance: {s11_best:.2f} dB")
            ````

            ### Step 7: Export S-Parameters

            ````python
            # Export to Touchstone format (Touchstone 1.0)
            output_path = "results/half_wave_dipole.s2p"
            export_touchstone(
                s_parameters=results.s_parameters,
                frequencies=results.frequencies,
                filepath=output_path
            )

            print(f"S-parameters exported to: {output_path}")
            ````

            ## Expected Output

            ::

                Operating frequency: 1.0 GHz
                Wavelength: 30.0 cm
                Dipole length: 15.0 cm
                Created dipole: Dipole(length=0.15m)
                Solver initialized successfully
                Simulation complete.
                Number of frequency points: 101
                Frequency range: 500.0 - 2000.0 MHz
                Best match frequency: 0.985 GHz
                S11 at resonance: -30.12 dB
                S-parameters exported to: results/half_wave_dipole.s2p

            ## Exercises

            1. Vary the dipole length and observe the effect on resonant frequency.
            2. Change the wire radius and study its impact on bandwidth.
            3. Add a feed gap parameter and model a coaxial feed.
        """)

    def generate_patch_tutorial(self) -> str:
        """Generate a tutorial for microstrip patch antenna on FR4 substrate.

        Creates a complete guide for designing and simulating a rectangular
        microstrip patch antenna on a FR4 dielectric substrate, including
        substrate modeling, feed configuration, and impedance matching.

        Returns
        -------
        str
            Markdown-formatted tutorial string with code examples and
            explanations.

        Notes
        -----
        The tutorial covers:
        - FR4 substrate properties (epsilon_r=4.4, loss_tangent=0.02)
        - Patch dimension calculation using transmission line model
        - Coaxial feed placement
        - Surface current visualization
        """
        return textwrap.dedent("""\
            # Tutorial: Microstrip Patch Antenna on FR4

            ## Introduction

            Microstrip patch antennas are widely used in mobile communications,
            GPS receivers, and WiFi systems due to their low profile, lightweight
            design, and ease of fabrication on PCB substrates. This tutorial
            demonstrates a complete simulation using FR4 substrate.

            ## Substrate Properties

            FR-4 is a common PCB material with the following properties:

            - Relative permittivity (epsilon_r): 4.4
            - Loss tangent: 0.02
            - Typical thickness: 1.6 mm

            ## Complete Example

            ### Step 1: Setup and Imports

            ````python
            import numpy as np
            from src.core.geometry import PatchAntenna
            from src.core.materials import Material
            from src.core.mom_solver import MOMSolver
            from src.post_processing.s_parameters import export_touchstone
            ````

            ### Step 2: Define FR4 Substrate

            ````python
            # FR4 substrate parameters
            substrate = Material(
                name="FR4",
                epsilon_r=4.4,
                loss_tangent=0.02,
                thickness=1.6e-3  # 1.6 mm in meters
            )

            copper = Material(name="Copper", conductivity=5.8e7)

            print(f"Substrate: {substrate.name}")
            print(f"Epsilon_r: {substrate.epsilon_r}")
            print(f"Thickness: {substrate.thickness * 1000:.1f} mm")
            ````

            ### Step 3: Calculate Patch Dimensions

            ````python
            frequency = 2.4e9  # WiFi band - 2.4 GHz
            c = 3.0e8
            wavelength_free = c / frequency
            wavelength_sub = wavelength_free / np.sqrt(substrate.epsilon_r)

            # Approximate patch dimensions (transmission line model)
            # Width for better radiation efficiency
            patch_width = 1.5 * wavelength_sub

            # Length considering fringing fields
            delta_L = 0.38 * substrate.thickness  # fringing field extension
            patch_length = 0.9 * wavelength_sub + 2 * delta_L

            print(f"Operating frequency: {frequency / 1e9} GHz")
            print(f"Patch width: {patch_width * 1000:.2f} mm")
            print(f"Patch length: {patch_length * 1000:.2f} mm")
            ````

            ### Step 4: Create Patch Geometry

            ````python
            # Define feed position (offset from center along length)
            feed_offset = [0.0, patch_width / 4]  # 1/4 width offset for 50-ohm match

            antenna = PatchAntenna(
                substrate=substrate,
                patch_width=patch_width,
                patch_length=patch_length,
                feed_offset=feed_offset,
                ground_plane=True,
                conductor=copper
            )

            print(f"Created patch antenna: {antenna}")
            ````

            ### Step 5: Configure and Run Solver

            ````python
            solver_config = {
                "solver_type": "mom",
                "tolerance": 1e-6,
                "max_iterations": 500,
                "frequency_range": [2.0e9, 3.0e9],
                "num_frequencies": 101,
                "surface_currents": True
            }

            solver = MOMSolver(antenna, config=solver_config)
            results = solver.solve()

            print(f"Simulation complete: {len(results.frequencies)} frequency points")
            ````

            ### Step 6: Analyze and Export

            ````python
            # Find resonant frequency (minimum S11)
            s11_mag = np.abs(results.s_parameters[:, 0, 0])
            min_idx = np.argmin(s11_mag)
            res_freq = results.frequencies[min_idx] / 1e9

            print(f"Resonant frequency: {res_freq:.3f} GHz")
            print(f"S11 at resonance: {20*np.log10(np.maximum(s11_mag, 1e-10))[min_idx]:.2f} dB")

            # Export results
            export_touchstone(
                s_parameters=results.s_parameters,
                frequencies=results.frequencies,
                filepath="results/patch_antenna.s2p"
            )
            ````

            ## Exercises

            1. Vary substrate thickness and observe bandwidth changes.
            2. Change feed position to study impedance matching effects.
            3. Add a slot cut in the patch and measure the frequency shift.
        """)

    def generate_array_tutorial(self) -> str:
        """Generate a tutorial for N-element array antenna with mutual coupling.

        Creates a comprehensive guide for simulating linear and planar antenna
        arrays, including mutual coupling analysis, beam steering, and array
        factor computation. Demonstrates how element interactions affect overall
        array performance.

        Returns
        -------
        str
            Markdown-formatted tutorial string with code examples and
            explanations.

        Notes
        -----
        The tutorial covers:
        - Uniform linear array (ULA) theory
        - Mutual coupling between adjacent elements
        - Beam steering via phase excitation
        - Array factor vs element pattern combination
        """
        return textwrap.dedent("""\
            # Tutorial: N-Element Array with Mutual Coupling

            ## Introduction

            Antenna arrays provide beam steering capability, increased gain, and
            improved directivity. This tutorial demonstrates a complete simulation
            of an N-element array including mutual coupling effects between
            adjacent elements.

            ## Array Theory Basics

            For a uniform linear array (ULA) with N elements spaced by d:

            - Array Factor: AF = sum_{n=0}^{N-1} I_n * exp(j*n*k*d*sin(theta))
            - Mutual coupling modifies the effective excitation coefficients
            - Element spacing < lambda/2 avoids grating lobes

            ## Complete Example

            ### Step 1: Setup and Imports

            ````python
            import numpy as np
            from src.core.geometry import LinearArray, Dipole
            from src.core.materials import Material, copper
            from src.core.array_engine import ArraySimulator
            from src.post_processing.s_parameters import export_touchstone
            ````

            ### Step 2: Define Array Parameters

            ````python
            N = 8                 # number of elements
            frequency = 1.0e9     # 1 GHz
            c = 3.0e8
            wavelength = c / frequency

            # Element spacing (half-wavelength)
            d = wavelength / 2.0

            print(f"Array: {N} elements, spacing = {d * 100:.1f} cm")
            print(f"Wavelength: {wavelength * 100:.1f} cm")
            ````

            ### Step 3: Create Individual Element and Array

            ````python
            # Define a single dipole element
            element = Dipole(
                length=wavelength / 2.0,
                radius=0.001,
                orientation="z"
            )

            # Create N-element linear array
            array = LinearArray(
                element_count=N,
                spacing=d,
                element_type="dipole",
                orientation="z",
                feed_phase=[0.0] * N  # uniform excitation
            )

            print(f"Created {N}-element linear array")
            print(f"Array length: {N * d:.2f} m")
            ````

            ### Step 4: Run Array Simulation with Coupling

            ````python
            simulator = ArraySimulator(array)

            # Full-wave simulation including mutual coupling
            results_coupled = simulator.simulate(
                coupling=True,
                frequency_range=[0.5e9, 2.0e9],
                num_frequencies=101
            )

            print(f"Coupled simulation complete")
            print(f"Number of ports: {len(results_coupled.s_parameters)}")
            ````

            ### Step 5: Compare Coupled vs Decoupled Results

            ````python
            # Run without mutual coupling for comparison
            results_decoupled = simulator.simulate(
                coupling=False,
                frequency_range=[0.5e9, 2.0e9],
                num_frequencies=101
            )

            # Analyze S-parameter differences
            s11_coupled = np.abs(results_coupled.s_parameters[0, 0])
            s11_decoupled = np.abs(results_decoupled.s_parameters[0, 0])

            coupling_effect = np.abs(s11_coupled - s11_decoupled)
            max_effect = np.max(coupling_effect) * 100

            print(f"Max S-parameter deviation due to coupling: {max_effect:.2f}%")
            ````

            ### Step 6: Beam Steering Analysis

            ````python
            # Apply a linear phase progression for beam steering
            scan_angle_deg = 30.0
            scan_angle_rad = np.radians(scan_angle_deg)
            k = 2 * np.pi / wavelength

            # Required phase shift between elements
            delta_phi = -k * d * np.sin(scan_angle_rad)
            feed_phases = np.array([i * delta_phi for i in range(N)])

            array.set_feed_phases(feed_phases.tolist())

            results_steered = simulator.simulate(
                coupling=True,
                frequency_range=[frequency, frequency],
                num_frequencies=1
            )

            print(f"Beam steered to {scan_angle_deg} degrees")
            ````

            ### Step 7: Export Results

            ````python
            # Export S-parameters for the coupled case
            export_touchstone(
                s_parameters=results_coupled.s_parameters,
                frequencies=results_coupled.frequencies,
                filepath="results/array_coupled.s2p"
            )

            # Export decoupled comparison
            export_touchstone(
                s_parameters=results_decoupled.s_parameters,
                frequencies=results_decoupled.frequencies,
                filepath="results/array_decoupled.s2p"
            )

            print("Results exported successfully")
            ````

            ## Key Observations

            - Mutual coupling shifts resonant frequencies and changes input impedance
            - Element spacing affects both beam width and grating lobe positions
            - Phase excitation enables electronic beam steering without mechanical movement
            - Coupling effects become significant at spacings < lambda/2

            ## Exercises

            1. Vary N from 4 to 16 and observe gain improvement.
            2. Change spacing from lambda/4 to lambda and study grating lobes.
            3. Implement a Taylor or Chebyshev amplitude taper to reduce sidelobes.
        """)
