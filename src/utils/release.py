"""Platform-specific installer generation utilities.

This module provides stub implementations for generating platform-specific
installers for DeTaGrandMere. It supports:

- Linux: .deb (Debian/Ubuntu) and .rpm (Fedora/RHEL) packages
- macOS: .dmg disk image with application bundle
- Windows: .msi installer with registry entries

Each stub creates the basic package structure; full packaging requires
platform-specific build tools.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional, List


class PlatformInstaller:
    """Generate platform-specific installation packages.

    This class provides methods for creating installers for different
    operating systems. Each method generates the necessary package
    structure and configuration files.

    Parameters
    ----------
    project_name : str, default="deTAGrandMere"
        Package name (lowercase, no spaces).
    version : str, default="0.1.0"
        Package version in semantic versioning format.
    maintainer : str, default="DeTaGrandMere Developers <dev@detagrandmere.org>"
        Package maintainer contact info.
    """

    def __init__(
        self,
        project_name: str = "deTAGrandMere",
        version: str = "0.1.0",
        maintainer: str = "DeTaGrandMere Developers <dev@detagrandmere.org>",
    ) -> None:
        """Initialise the platform installer generator."""
        self.project_name = project_name
        self.version = version
        self.maintainer = maintainer

    def create_deb_package(
        self,
        build_dir: str = "build/deb",
        python_executable: str = "/usr/bin/python3",
    ) -> str:
        """Create a Debian package (.deb) for Ubuntu/Debian.

        Parameters
        ----------
        build_dir : str, default="build/deb"
            Directory for building the package.
        python_executable : str, default="/usr/bin/python3"
            Path to the Python interpreter.

        Returns
        -------
        str
            Path to the generated .deb file.

        Raises
        ------
        RuntimeError
            If dpkg-deb is not available.
        """
        os.makedirs(build_dir, exist_ok=True)

        # Create debian control file
        control_content = f'''Package: {self.project_name}
Version: {self.version}
Section: science
Priority: optional
Architecture: all
Maintainer: {self.maintainer}
Description: Open-source planar antenna simulation software (MoM)
 A comprehensive Method of Moments electromagnetic simulation
 tool for planar antenna design and analysis.
'''

        control_path = os.path.join(build_dir, "DEBIAN", "control")
        os.makedirs(os.path.dirname(control_path), exist_ok=True)
        with open(control_path, "w") as f:
            f.write(control_content)

        # Create post-install script
        postinst_content = f'''#!/bin/bash
# Post-installation script for {self.project_name}
echo "Installation complete. Run simulations with:"
echo "  python run.py simulate --frequency 1e9"
'''

        postinst_path = os.path.join(build_dir, "DEBIAN", "postinst")
        with open(postinst_path, "w") as f:
            f.write(postinst_content)
        os.chmod(postinst_path, 0o755)

        # Create package
        deb_file = f"{build_dir}/{self.project_name}_{self.version}_all.deb"
        try:
            subprocess.run(
                ["dpkg-deb", "--build", build_dir, deb_file],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "dpkg-deb not found. Install with: sudo apt install dpkg"
            )

        return deb_file

    def create_rpm_package(
        self,
        build_dir: str = "build/rpm",
        python_executable: str = "/usr/bin/python3",
    ) -> str:
        """Create an RPM package for Fedora/RHEL.

        Parameters
        ----------
        build_dir : str, default="build/rpm"
            Directory for building the package.
        python_executable : str, default="/usr/bin/python3"
            Path to the Python interpreter.

        Returns
        -------
        str
            Path to the generated .rpm file.

        Raises
        ------
        RuntimeError
            If rpmbuild is not available.
        """
        os.makedirs(build_dir, exist_ok=True)

        # Create SPEC file
        spec_content = f'''%{{?fedora}} %bcond_without docs
Name: {self.project_name}
Version: {self.version}
Release: 1
Summary: Open-source planar antenna simulation software (MoM)
License: MIT
BuildArch: noarch

%description
A comprehensive Method of Moments electromagnetic simulation tool
for planar antenna design and analysis.

%install
python3 setup.py install --root %{buildroot}

%files
%{ _bindir }/*
'''

        spec_path = os.path.join(build_dir, f"{self.project_name}.spec")
        with open(spec_path, "w") as f:
            f.write(spec_content)

        # Build RPM
        rpm_file = f"{build_dir}/{self.project_name}-{self.version}.rpm"
        try:
            subprocess.run(
                ["rpmbuild", "-ba", "--define", f"_topdir {build_dir}", spec_path],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "rpmbuild not found. Install with: sudo dnf install rpm-build"
            )

        return rpm_file

    def create_dmg_package(
        self,
        build_dir: str = "build/dmg",
        app_name: str = "DeTaGrandMere.app",
    ) -> str:
        """Create a macOS disk image (.dmg).

        Parameters
        ----------
        build_dir : str, default="build/dmg"
            Directory for building the package.
        app_name : str, default="DeTaGrandMere.app"
        Name of the application bundle.

        Returns
        -------
        str
            Path to the generated .dmg file.

        Raises
        ------
        RuntimeError
            If hdiutil is not available.
        """
        os.makedirs(build_dir, exist_ok=True)

        # Create application directory structure
        app_dir = os.path.join(build_dir, app_name, "Contents", "MacOS")
        os.makedirs(app_dir, exist_ok=True)

        # Create launcher script
        launcher_content = f'''#!/bin/bash
cd "$(dirname "$0")"/../Resources
python3 run.py "$@"
'''

        launcher_path = os.path.join(app_dir, self.project_name)
        with open(launcher_path, "w") as f:
            f.write(launcher_content)
        os.chmod(launcher_path, 0o755)

        # Create Info.plist
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>{app_name}</string>
    <key>CFBundleVersion</key>
    <string>{self.version}</string>
    <key>CFBundleExecutable</key>
    <string>{self.project_name}</string>
</dict>
</plist>
'''

        plist_path = os.path.join(build_dir, app_name, "Contents", "Info.plist")
        with open(plist_path, "w") as f:
            f.write(plist_content)

        # Create dmg
        dmg_file = os.path.join(build_dir, f"{self.project_name}-{self.version}.dmg")
        try:
            subprocess.run(
                [
                    "hdiutil", "create",
                    "-fs", "HFS+",
                    "-volname", self.project_name,
                    "-srcfolder", os.path.join(build_dir, app_name),
                    dmg_file,
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "hdiutil not found. This command is macOS-specific."
            )

        return dmg_file

    def create_msi_package(
        self,
        build_dir: str = "build/msi",
        python_root: str = None,
    ) -> str:
        """Create a Windows installer (.msi).

        Parameters
        ----------
        build_dir : str, default="build/msi"
            Directory for building the package.
        python_root : str, optional
            Python installation root path. If None, uses system Python.

        Returns
        -------
        str
            Path to the generated .msi file.

        Raises
        ------
        RuntimeError
            If PyInstaller or py2msi is not available.
        """
        os.makedirs(build_dir, exist_ok=True)

        # Create basic MSI structure (simplified)
        msi_stub = f'''<?xml version="1.0" encoding="utf-8"?>
<Wix xmlns="http://schemas.microsoft.com/wix/2006/wi">
    <Product Name="{self.project_name}" Version="{self.version}"
             Manufacturer="{self.maintainer}" CodePage="1252">
        <Package InstallerVersion="301" Compressed="yes" />
        <Media Id="1" Cabinet="cab1.cab" Compression="high" />
        <Feature Id="MainFeature" Title="DeTaGrandMere" Level="1">
            <Component Directory="INSTALLDIR" Guid="*">
                <File Source="run.py" />
            </Component>
        </Feature>
    </Product>
</Wix>
'''

        wix_path = os.path.join(build_dir, f"{self.project_name}.wix")
        with open(wix_path, "w") as f:
            f.write(msi_stub)

        # Build MSI (requires WiX toolset)
        msi_file = os.path.join(build_dir, f"{self.project_name}-{self.version}.msi")
        try:
            subprocess.run(
                ["light", "-out", msi_file, wix_path],
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "WiX light.exe not found. Install WiX Toolset from https://wixtoolset.org/"
            )

        return msi_file


class CIConfigGenerator:
    """Generate CI/CD pipeline configurations.

    This class creates GitHub Actions workflow files for automated
    testing, building, and deployment of DeTaGrandMere.
    """

    @staticmethod
    def generate_github_actions_workflow(
        output_path: str = ".github/workflows/ci.yml",
    ) -> str:
        """Generate GitHub Actions CI/CD workflow file.

        Parameters
        ----------
        output_path : str, default=".github/workflows/ci.yml"
            Output path for the workflow file.

        Returns
        -------
        str
            Path to the generated workflow file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        content = '''name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.9', '3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-cov numpy scipy matplotlib pyvista h5py

      - name: Run unit tests
        run: |
          pytest tests/unit/ -v --tb=short

      - name: Run integration tests
        run: |
          pytest tests/integration/ -v --tb=short

      - name: Check code coverage
        run: |
          pytest --cov=src --cov-report=term-missing tests/

  build:
    runs-on: ubuntu-latest
    needs: test

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install build tools
        run: |
          pip install build twine

      - name: Build package
        run: |
          python -m build

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: dist
          path: dist/
'''

        with open(output_path, "w") as f:
            f.write(content)

        return output_path

    @staticmethod
    def generate_travis_ci(
        output_path: str = ".travis.yml",
    ) -> str:
        """Generate Travis CI configuration file.

        Parameters
        ----------
        output_path : str, default=".travis.yml"
            Output path for the Travis CI config.

        Returns
        -------
        str
            Path to the generated configuration file.
        """
        content = '''language: python
python:
  - "3.9"
  - "3.10"
  - "3.11"
  - "3.12"

install:
  - pip install pytest pytest-cov numpy scipy matplotlib pyvista h5py
  - pip install -e .

script:
  - pytest tests/ -v --tb=short

after_success:
  - pytest --cov=src --cov-report=term-missing tests/
'''

        with open(output_path, "w") as f:
            f.write(content)

        return output_path


class LandingPageGenerator:
    """Generate project landing page content.

    This class creates HTML and Markdown landing pages for the
    DeTaGrandMere project website, including overview, screenshots,
    quick start guide, and documentation links.
    """

    @staticmethod
    def generate_readme_landing(
        output_path: str = "README.md",
    ) -> str:
        """Generate an enhanced README landing page.

        Parameters
        ----------
        output_path : str, default="README.md"
            Output path for the README file.

        Returns
        -------
        str
            Path to the generated README file.
        """
        content = '''# DeTaGrandMere — Open-Source Planar Antenna Simulation Software

**Method of Moments (MoM) electromagnetic simulation for planar antenna design.**

[![PyPI version](https://img.shields.io/pypi/v/deTAGrandMere)](https://pypi.org/project/deTAGrandMere/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://github.com/deTAGrandMere/detagrandmere/actions/workflows/ci.yml/badge.svg)](https://github.com/deTAGrandMere/detagrandmere/actions/)

## Quick Start

```bash
# Install from PyPI (when available)
pip install deTAGrandMere

# Or install from source
git clone https://github.com/deTAGrandMere/detagrandmere.git
cd detagrandmere
./install.sh

# Run a simulation
python run.py simulate --frequency 1e9 --solver-type EFIE
```

## Features

- **CAD Import**: STEP file import with OpenCASCADE geometry kernel
- **Mesh Generation**: CGAL-based surface meshing with quality criteria
- **Material Models**: Dispersive (Debye/Lorentz/Drude) and anisotropic materials
- **Solver**: EFIE/MFIE/CFIE formulations with RWG basis functions
- **S-Parameters**: Multi-port S-parameter computation with reciprocity validation
- **Field Calculations**: Near-field and far-field transformations
- **Visualization**: PyVista/VTK-based 3D field visualization
- **Metrics**: Directivity, gain, bandwidth, F/B ratio computation
- **Export**: Touchstone (.sNp), HDF5, and plot formats (PDF/PNG/SVG)
- **Parallel**: MPI domain decomposition and GPU acceleration stubs
- **FMM/MLFMA**: Fast multipole method for large-scale problems

## Documentation

- [User Manual](docs/user_manual.md) — Installation, quick start, features
- [API Reference](docs/api_reference.md) — Module documentation with examples
- [Tutorials](docs/tutorials/) — Step-by-step simulation guides
- [File Formats](docs/file_formats/) — STEP, Touchstone, HDF5 specifications

## Examples

### Half-Wave Dipole Simulation

```python
from src.core.workflow import SimulationWorkflow

wf = SimulationWorkflow(frequency=1e9, solver_type="EFIE")
status = wf.run()
print(f"Directivity: {wf.metrics.directivity:.2f} dBi")
```

### Frequency Sweep

```python
import numpy as np
from src.core.workflow import SimulationWorkflow

freqs = np.linspace(0.5e9, 2e9, 100)
wf = SimulationWorkflow(frequencies=freqs, solver_type="CFIE")
results = wf.run_sweep()
```

## Installation

See [INSTALL.md](INSTALL.md) for detailed installation instructions.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:
- Submitting bug reports and feature requests
- Code review process
- Development workflow

## License

MIT License — see [LICENSE](LICENSE) for details.
'''

        with open(output_path, "w") as f:
            f.write(content)

        return output_path

    @staticmethod
    def generate_html_landing(
        output_path: str = "docs/index.html",
    ) -> str:
        """Generate an HTML landing page for the project website.

        Parameters
        ----------
        output_path : str, default="docs/index.html"
            Output path for the HTML file.

        Returns
        -------
        str
            Path to the generated HTML file.
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DeTaGrandMere — Planar Antenna Simulation Software</title>
    <style>
        body { font-family: system-ui, -apple-system, sans-serif; margin: 0; padding: 2em; }
        h1 { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.5em; }
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 1em; margin: 2em 0; }
        .feature-card { background: #f8f9fa; padding: 1.5em; border-radius: 8px; border-left: 4px solid #3498db; }
        .code-block { background: #2c3e50; color: #ecf0f1; padding: 1em; border-radius: 4px; overflow-x: auto; font-family: monospace; }
        a { color: #3498db; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>DeTaGrandMere</h1>
    <p>Open-source planar antenna simulation software using the Method of Moments (MoM).</p>

    <h2>Features</h2>
    <div class="feature-grid">
        <div class="feature-card">
            <h3>CAD Import</h3>
            <p>STEP file import with OpenCASCADE geometry kernel.</p>
        </div>
        <div class="feature-card">
            <h3>Mesh Generation</h3>
            <p>CGAL-based surface meshing with quality criteria.</p>
        </div>
        <div class="feature-card">
            <h3>MoM Solver</h3>
            <p>EFIE/MFIE/CFIE formulations with RWG basis functions.</p>
        </div>
        <div class="feature-card">
            <h3>S-Parameters</h3>
            <p>Multi-port S-parameter computation with reciprocity validation.</p>
        </div>
        <div class="feature-card">
            <h3>Field Visualization</h3>
            <p>PyVista/VTK-based 3D field visualization and radiation patterns.</p>
        </div>
        <div class="feature-card">
            <h3>Performance</h3>
            <p>MPI parallelization, GPU acceleration, and FMM/MLFMA support.</p>
        </div>
    </div>

    <h2>Quick Start</h2>
    <pre class="code-block">
pip install deTAGrandMere
python run.py simulate --frequency 1e9 --solver-type EFIE
    </pre>

    <h2>Documentation</h2>
    <ul>
        <li><a href="docs/user_manual.md">User Manual</a></li>
        <li><a href="docs/api_reference.md">API Reference</a></li>
        <li><a href="docs/tutorials/">Tutorials</a></li>
        <li><a href="docs/file_formats/">File Format Specifications</a></li>
    </ul>

    <h2>Get Involved</h2>
    <ul>
        <li><a href="CONTRIBUTING.md">Contributing Guide</a></li>
        <li><a href="https://github.com/deTAGrandMere/detagrandmere/issues">Issue Tracker</a></li>
        <li><a href="LICENSE">MIT License</a></li>
    </ul>
</body>
</html>
'''

        with open(output_path, "w") as f:
            f.write(content)

        return output_path
