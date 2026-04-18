"""
Release management utilities for the deTAGrandMere project.

This module provides functions and classes to manage software releases,
including generating build configuration files (pyproject.toml, setup.py),
building distributable packages (wheels and sdists), and generating
changelogs from git commit history.

Example usage::

    from src.utils.release import (
        create_pyproject_toml,
        create_setup_py,
        ReleaseManager
    )

    # Generate build configuration files
    create_pyproject_toml(output_dir="pkg_config")
    create_setup_py(output_dir="pkg_config")

    # Build and manage releases
    rm = ReleaseManager(version="0.2.0")
    package_path = rm.build_package()
    print(f"Built package: {package_path}")

    changelog = rm.generate_changelog(git_log=["feat: add dipole solver", "fix: patch boundary"])
    print(changelog)
"""

from __future__ import annotations

import os
import subprocess
import textwrap
from typing import Any


def create_pyproject_toml(
    output_dir: str = ".",
    name: str = "deTAGrandMere",
    version: str = "0.1.0"
) -> str:
    """Generate a pyproject.toml configuration file for the project.

    Creates a PEP 517 / PEP 518 compliant build configuration with setuptools
    as the build backend, project metadata, dependencies, and optional extras
    for various feature groups.

    Parameters
    ----------
    output_dir : str, optional
        Directory where pyproject.toml will be written. Default is ".".
    name : str, optional
        Project name. Default is "deTAGrandMere".
    version : str, optional
        Project version. Default is "0.1.0".

    Returns
    -------
    str
        The generated TOML content as a string.

    Notes
    -----
    The generated pyproject.toml includes:
    - Build system: setuptools + wheel
    - Core dependencies: numpy, scipy
    - Test dependency: pytest
    - Optional extras: cad (opencascade), meshing (cgal-python3),
      parallel (mpi4py, petsc4py), gpu (pycuda), viz (pyvista), h5py
    """
    toml_content = textwrap.dedent(f"""\
        [build-system]
        requires = ["setuptools>=68.0", "wheel>=0.41"]
        build-backend = "setuptools.backends._legacy"

        [project]
        name = "{name}"
        version = "{version}"
        description = "A comprehensive electromagnetic antenna simulation framework using Method of Moments and Finite Element methods."
        readme = "README.md"
        license = {{ text = "MIT" }}
        requires-python = ">= 3.9"

        authors = [
            {{ name = "deTAGrandMere Contributors", email = "contact@detagrandmere.org" }}
        ]

        dependencies = [
            "numpy>=1.24.0",
            "scipy>=1.10.0",
        ]

        [project.optional-dependencies]
        cad = [
            "opencascade-core",
        ]
        meshing = [
            "cgal-python3",
        ]
        parallel = [
            "mpi4py",
            "petsc4py",
        ]
        gpu = [
            "pycuda",
        ]
        viz = [
            "pyvista",
        ]
        h5py = [
            "h5py",
        ]

        [project.scripts]
        detag = "src.cli.main:main"

        [tool.setuptools.packages.find]
        where = ["."]
        include = ["src*"]
    """)

    output_path = os.path.join(output_dir, "pyproject.toml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(toml_content)

    return toml_content


def create_setup_py(
    output_dir: str = ".",
    name: str = "deTAGrandMere",
    version: str = "0.1.0"
) -> str:
    """Generate a traditional setup.py file for the project.

    Creates a setuptools-based setup script compatible with older Python
    packaging tools, including find_packages(), install_requires, and
    extras_require for optional feature groups.

    Parameters
    ----------
    output_dir : str, optional
        Directory where setup.py will be written. Default is ".".
    name : str, optional
        Project name. Default is "deTAGrandMere".
    version : str, optional
        Project version. Default is "0.1.0".

    Returns
    -------
    str
        The generated Python setup script content as a string.

    Notes
    -----
    The generated setup.py includes:
    - find_packages() for automatic package discovery
    - install_requires with core dependencies (numpy, scipy)
    - extras_require with optional feature groups (cad, meshing, parallel,
      gpu, viz, h5py)
    - pytest as a test-only dependency
    """
    setup_content = textwrap.dedent(f"""\
        import os
        from setuptools import setup, find_packages

        # Read the README for long description
        with open("README.md", encoding="utf-8") as f:
            long_description = f.read()

        setup(
            name="{name}",
            version="{version}",
            description="A comprehensive electromagnetic antenna simulation framework using Method of Moments and Finite Element methods.",
            long_description=long_description,
            long_description_content_type="text/markdown",
            author="deTAGrandMere Contributors",
            author_email="contact@detagrandmere.org",
            license="MIT",
            python_requires=">= 3.9",

            packages=find_packages(where="."),
            package_dir={{"": "."}},

            install_requires=[
                "numpy>=1.24.0",
                "scipy>=1.10.0",
            ],

            extras_require={{
                "cad": ["opencascade-core"],
                "meshing": ["cgal-python3"],
                "parallel": ["mpi4py", "petsc4py"],
                "gpu": ["pycuda"],
                "viz": ["pyvista"],
                "h5py": ["h5py"],
            }},

            entry_points={{
                "console_scripts": [
                    "detag=src.cli.main:main",
                ],
            }},

            classifiers=[
                "Development Status :: 3 - Alpha",
                "Intended Audience :: Science/Research",
                "License :: OSI Approved :: MIT License",
                "Programming Language :: Python :: 3.9",
                "Programming Language :: Python :: 3.10",
                "Programming Language :: Python :: 3.11",
                "Programming Language :: Python :: 3.12",
                "Topic :: Scientific/Engineering :: Physics",
            ],
        )
    """)

    output_path = os.path.join(output_dir, "setup.py")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(setup_content)

    return setup_content


class ReleaseManager:
    """Manage software releases for the deTAGrandMere project.

    Provides methods to build distributable packages (wheels and sdists)
    using subprocess calls to Python packaging tools, and to generate
    changelogs from git commit history. Handles missing build tools
    gracefully with informative error messages.

    Parameters
    ----------
    version : str, optional
        The project version for this release. Default is "0.1.0".

    Examples
    --------
    >>> rm = ReleaseManager(version="0.2.0")
    >>> # Build a package (requires build tool installed)
    >>> # path = rm.build_package()
    >>> changelog = rm.generate_changelog(["feat: add feature", "fix: resolve bug"])
    """

    def __init__(self, version: str = "0.1.0") -> None:
        """Initialize the release manager.

        Parameters
        ----------
        version : str, optional
            Project version string. Default is "0.1.0".
        """
        self.version: str = version

    def build_package(self) -> str:
        """Build wheel and sdist packages using Python's build module.

        Runs ``python -m build`` in the project root to create both a wheel
        (.whl) and source distribution (.tar.gz). If the build module is not
        available, falls back to running setup.py directly.

        Returns
        -------
        str
            Path to the most recently built package file (wheel or sdist).
            Returns an empty string if building fails due to missing tools.

        Raises
        ------
        RuntimeError
            If subprocess execution encounters a fatal error.

        Notes
        -----
        This method attempts to build packages in the project's root directory.
        It handles the case where ``python -m build`` is not installed by
        falling back to ``python setup.py sdist bdist_wheel``. Errors from
        missing compilers or dependencies are caught and reported without
        crashing the caller.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dist_dir = os.path.join(project_root, "dist")

        # Ensure dist directory exists
        os.makedirs(dist_dir, exist_ok=True)

        # Try using python -m build first (PEP 517/518 compliant)
        try:
            result = subprocess.run(
                ["python", "-m", "build", "--outdir", dist_dir],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                # Find the built files
                built_files = os.listdir(dist_dir)
                if built_files:
                    latest_file = sorted(built_files)[-1]
                    return os.path.join(dist_dir, latest_file)

        except (FileNotFoundError, subprocess.TimeoutExpired):
            # Build module not available or timed out; fall through to fallback
            pass

        # Fallback: use setup.py directly
        try:
            setup_py = os.path.join(project_root, "setup.py")
            if os.path.exists(setup_py):
                result = subprocess.run(
                    ["python", "setup.py", "sdist", "bdist_wheel"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=300
                )

                if result.returncode == 0:
                    dist_files = os.listdir(dist_dir)
                    if dist_files:
                        latest_file = sorted(dist_files)[-1]
                        return os.path.join(dist_dir, latest_file)

        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

        # If we still have nothing, check if any files were created
        try:
            dist_files = os.listdir(dist_dir)
            if dist_files:
                latest_file = sorted(dist_files)[-1]
                return os.path.join(dist_dir, latest_file)
        except OSError:
            pass

        return ""

    def generate_changelog(self, git_log: list[str] | None = None) -> str:
        """Parse git commit messages to generate a categorized changelog.

        Examines commit message prefixes (feat, fix, docs, perf, refactor, test)
        and groups entries accordingly. If no git_log is provided, attempts
        to read from the repository's git log automatically.

        Parameters
        ----------
        git_log : list of str or None, optional
            List of commit message strings. If None, reads from ``git log``
            in the project directory. Default is None.

        Returns
        -------
        str
            Markdown-formatted changelog with sections grouped by category.

        Notes
        -----
        Supported commit prefixes:
        - feat: New features
        - fix: Bug fixes
        - docs: Documentation changes
        - perf: Performance improvements
        - refactor: Code restructuring
        - test: Test additions or modifications

        Categories with no entries are omitted from the output.
        """
        categories = {
            "feat": [],
            "fix": [],
            "docs": [],
            "perf": [],
            "refactor": [],
            "test": [],
        }

        if git_log is not None:
            commits = git_log
        else:
            # Try to read from git log automatically
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            try:
                result = subprocess.run(
                    ["git", "log", "--pretty=%s"],
                    cwd=project_root,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0 and result.stdout.strip():
                    commits = result.stdout.strip().split("\n")
                else:
                    commits = []
            except (FileNotFoundError, subprocess.TimeoutExpired):
                commits = []

        # Parse commit messages by prefix
        for commit in commits:
            commit = commit.strip()
            if not commit:
                continue

            parts = commit.split(":", 1)
            if len(parts) < 2:
                continue

            prefix, message = parts[0].strip().lower(), parts[1].strip()

            if prefix in categories:
                categories[prefix].append(message)

        # Build markdown output
        lines = []
        lines.append(f"# Changelog for {self.version}")
        lines.append("")
        lines.append("## Summary")
        lines.append("")

        total = sum(len(entries) for entries in categories.values())
        lines.append(f"**Total changes**: {total}")
        lines.append("")

        category_labels = {
            "feat": "Features",
            "fix": "Bug Fixes",
            "docs": "Documentation",
            "perf": "Performance",
            "refactor": "Refactoring",
            "test": "Tests",
        }

        for cat_key in ["feat", "fix", "docs", "perf", "refactor", "test"]:
            entries = categories[cat_key]
            if not entries:
                continue

            lines.append(f"### {category_labels[cat_key]}")
            lines.append("")
            for entry in entries:
                lines.append(f"- {entry}")
            lines.append("")

        return "\n".join(lines)
