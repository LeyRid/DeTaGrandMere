"""Command-line interface parser for DeTaGrandMere antenna simulation software.

Provides a unified :func:`parse_arguments` function that builds an ``argparse``
parser with four subcommands::

    - **simulate**  -- run a full electromagnetic simulation
    - **import-cad**-- import a STEP CAD file and optionally validate it
    - **export**    -- export results to Touchstone or HDF5 format
    - **visualize** -- visualise field data from a given viewpoint

All default values are sourced from :data:`src.utils.config_loader.DEFAULTS`
to keep the CLI behaviour consistent with the configuration system.


Example usage ::

    from src.utils.cli_parser import parse_arguments

    # Parse command-line arguments (sys.argv by default)
    args = parse_arguments()

    if args.command == "simulate":
        print(f"Solver type: {args.solver_type}")
        print(f"Tolerance:   {args.tolerance}")

    elif args.command == "import-cad":
        print(f"STEP file:   {args.step_file}")
        print(f"Validate:    {args.validate}")
"""  # noqa: E501

from __future__ import annotations

import argparse
import sys
from typing import Optional


# Import defaults so CLI arguments stay in sync with the config system.
from src.utils.config_loader import DEFAULTS

# ---------------------------------------------------------------------------
# Subcommand builders
# ---------------------------------------------------------------------------


def _build_simulate_parser(subparsers: argparse._SubParsersAction) -> None:
    """Create the *simulate* subcommand parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        The parent ``add_subparsers`` object into which this subparser is
        registered.
    """
    parser = subparsers.add_parser(
        "simulate",
        help="Run a full electromagnetic simulation pipeline",
        description=(
            "Execute the complete DeTaGrandMere simulation workflow: "
            "import geometry, generate mesh, solve the MoM system, and "
            "compute S-parameters and field data."
        ),
    )

    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help=(
            "Path to a YAML or JSON configuration file. "
            f"Defaults to None (uses built-in defaults: {DEFAULTS})"
        ),
    )

    parser.add_argument(
        "--frequency",
        type=float,
        default=1e9,
        help="Operating frequency in Hz (default: 1000000000.0)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default=DEFAULTS["file_io"]["output_dir"],
        help=f"Directory for output files (default: {DEFAULTS['file_io']['output_dir']})",
    )

    solver_type_choices = ["EFIE", "MFIE", "CFIE"]
    parser.add_argument(
        "--solver-type",
        type=str,
        default=DEFAULTS["solver"]["solver_type"].upper(),
        choices=solver_type_choices,
        help=(
            f"Method of Moments solver type. Choices: {', '.join(solver_type_choices)} "
            f"(default: {DEFAULTS['solver']['solver_type'].upper()})"
        ),
    )

    parser.add_argument(
        "--tolerance",
        type=float,
        default=DEFAULTS["solver"]["tolerance"],
        help=f"Convergence tolerance (default: {DEFAULTS['solver']['tolerance']})",
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=DEFAULTS["solver"]["max_iterations"],
        help=f"Maximum solver iterations (default: {DEFAULTS['solver']['max_iterations']})",
    )

    parser.add_argument(
        "--mesh-file",
        type=str,
        default=None,
        help="Path to a pre-generated mesh file. If not provided, mesh is generated during the pipeline.",
    )

    parser.add_argument(
        "--port-info",
        type=str,
        default=None,
        help=(
            "JSON string or path to a file describing port configuration. "
            "E.g. '{\"ports\": [{\"id\": 1, \"name\": \"Port1\", \"impedance\": 50}]}'"
        ),
    )

    # Mesh parameters (can be overridden per-run)
    parser.add_argument(
        "--alpha-shape",
        type=float,
        default=DEFAULTS["mesh"]["alpha_shape"],
        help=f"Alpha shape parameter for meshing (default: {DEFAULTS['mesh']['alpha_shape']})",
    )

    parser.add_argument(
        "--min-quality",
        type=float,
        default=DEFAULTS["mesh"]["min_quality"],
        help=f"Minimum element quality threshold 0-1 (default: {DEFAULTS['mesh']['min_quality']})",
    )

    parser.add_argument(
        "--refinement-level",
        type=int,
        default=DEFAULTS["mesh"]["refinement_level"],
        help=f"Mesh refinement level (default: {DEFAULTS['mesh']['refinement_level']})",
    )


def _build_import_cad_parser(subparsers: argparse._SubParsersAction) -> None:
    """Create the *import-cad* subcommand parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        The parent ``add_subparsers`` object into which this subparser is
        registered.
    """
    parser = subparsers.add_parser(
        "import-cad",
        help="Import a STEP CAD file and optionally validate it",
        description=(
            "Read geometry from a STEP (STP) file, convert to internal "
            "representation, and optionally run geometric validation checks."
        ),
    )

    parser.add_argument(
        "--step-file",
        type=str,
        required=True,
        help="Path to the STEP (.step / .stp) CAD geometry file",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        default=False,
        help="Run geometric validation checks after import (e.g. manifold, watertight)",
    )


def _build_export_parser(subparsers: argparse._SubParsersAction) -> None:
    """Create the *export* subcommand parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        The parent ``add_subparsers`` object into which this subparser is
        registered.
    """
    export_format_choices = ["touchstone", "hdf5"]
    parser = subparsers.add_parser(
        "export",
        help="Export simulation results to Touchstone or HDF5 format",
        description=(
            "Write computed S-parameters, field data, or antenna metrics "
            "to an output file in the specified format."
        ),
    )

    parser.add_argument(
        "--input-file",
        type=str,
        required=True,
        help="Path to the simulation results file (e.g. HDF5 intermediate output)",
    )

    export_formats = export_format_choices
    parser.add_argument(
        "--format",
        type=str,
        default="touchstone",
        choices=export_formats,
        help=(
            f"Output format. Choices: {', '.join(export_formats)} "
            f"(default: touchstone)"
        ),
    )

    parser.add_argument(
        "--output-file",
        type=str,
        default=None,
        help="Destination file path for the exported results",
    )


def _build_visualize_parser(subparsers: argparse._SubParsersAction) -> None:
    """Create the *visualize* subcommand parser.

    Parameters
    ----------
    subparsers : argparse._SubParsersAction
        The parent ``add_subparsers`` object into which this subparser is
        registered.
    """
    parser = subparsers.add_parser(
        "visualize",
        help="Visualise simulation field data from a specified viewpoint",
        description=(
            "Render electromagnetic field quantities (E-field, H-field, "
            "current density) as 2D/3D plots or animations."
        ),
    )

    parser.add_argument(
        "--field-data",
        type=str,
        required=True,
        help="Path to the field data file (e.g. HDF5 or VTK)",
    )

    # view-angle can be azimuth/elevation/both; we accept a comma-separated string
    parser.add_argument(
        "--view-angle",
        type=str,
        default="0,0",
        help=(
            "Comma-separated azimuth,elevation angles in degrees "
            "(default: 0,0 for broadside)"
        ),
    )

    # Visualization backend from defaults
    parser.add_argument(
        "--backend",
        type=str,
        default=DEFAULTS["visualization"]["backend"],
        choices=["matplotlib", "plotly"],
        help=f"Plotting backend (default: {DEFAULTS['visualization']['backend']})",
    )

    parser.add_argument(
        "--color-map",
        type=str,
        default=DEFAULTS["visualization"]["color_map"],
        help=f"Colormap name (default: {DEFAULTS['visualization']['color_map']})",
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_arguments(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments and return a namespace.

    Builds a top-level ``ArgumentParser`` with four subcommands, each with
    its own argument definitions.  All default values are sourced from
    :data:`src.utils.config_loader.DEFAULTS` so the CLI stays in sync with
    the configuration system.

    Parameters
    ----------
    argv : list[str] | None
        List of command-line arguments to parse.  If ``None``,
        ``sys.argv[1:]`` is used (i.e. real command-line input).

    Returns
    -------
    argparse.Namespace
        An object whose attributes correspond to the parsed flags and
        subcommand name.  The subcommand name is always stored in the
        ``command`` attribute (e.g. ``"simulate"``, ``"import-cad"``).

    Example
    -------
    >>> args = parse_arguments(["simulate", "--solver-type", "EFIE"])
    >>> args.command
    'simulate'
    >>> args.solver_type
    'EFIE'
    """
    # Top-level parser
    top_parser = argparse.ArgumentParser(
        prog="de-tagrandmere",
        description="DeTaGrandMere: Planar Antenna CAD & Simulation Framework",
        epilog=(
            "Use <subcommand> --help for more information on that subcommand."
        ),
    )

    # Subparsers (action='store' keeps the command name accessible)
    subparsers = top_parser.add_subparsers(
        dest="command",
        title="subcommands",
        description="Available simulation workflow steps",
    )

    # Register each subcommand
    _build_simulate_parser(subparsers)
    _build_import_cad_parser(subparsers)
    _build_export_parser(subparsers)
    _build_visualize_parser(subparsers)

    # Parse and return
    args = top_parser.parse_args(argv)

    # Ensure every namespace has a 'command' attribute even if no subcommand
    # was given (argparse sets dest to None in that case)
    if not hasattr(args, "command"):
        args.command = None  # type: ignore[assignment]

    return args


# ---------------------------------------------------------------------------
# Module-level example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    # Quick demo: parse a simulated argv list
    sample_argv = [
        "simulate",
        "--solver-type", "CFIE",
        "--tolerance", "1e-08",
        "--max-iterations", "500",
        "--frequency", "2.4e9",
        "--output-dir", "./results",
    ]

    print("Parsing sample arguments:")
    for item in sample_argv:
        print(f"  {item}")
    print()

    args = parse_arguments(sample_argv)
    print(f"Parsed namespace (attrs):")
    for attr in sorted(vars(args)):
        val = getattr(args, attr)
        print(f"  {attr} = {val!r}")
