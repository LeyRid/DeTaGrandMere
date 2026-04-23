#!/usr/bin/env python3
"""DeTaGrandMere — launch script.

Usage::

    python run.py simulate --frequency 1e9 --solver-type EFIE
    python run.py import-cad --step-file antenna.step --validate
    python run.py export --input-file results.h5 --format touchstone --output-file s2p.s2p
    python run.py visualize --field-data fields.h5 --view-angle xy

You can also pass a config file:

    python run.py simulate --config configs/antenna.yaml
"""

from __future__ import annotations

import sys

# Ensure the project root is on sys.path so ``src.*`` imports work.
sys.path.insert(0, "/home/rid/Documents/Caad")

from src.utils.cli_parser import parse_arguments
from src.core.workflow import SimulationWorkflow


def main(argv=None):
    """Parse CLI args and run the simulation workflow."""
    args = parse_arguments(argv)

    if not args.command:
        print("Available subcommands: simulate, import-cad, export, visualize")
        print("Use ``python run.py <subcommand> --help`` for details.")
        return 1

    # Build the workflow from parsed arguments (or a config file).
    workflow = SimulationWorkflow(cli_args=args)

    if args.command == "simulate":
        print("[DeTaGrandMere] Starting simulation ...")
        workflow.run()
        steps = workflow.status.get("steps", {})
        solve_info = steps.get("solve", {}).get("result", {})
        sparams_info = steps.get("sparams", {}).get("result", {})
        metrics_info = steps.get("metrics", {}).get("result", {})
        print("[DeTaGrandMere] Done.")
        print(f"  Solver      : {solve_info.get('solver_type', 'N/A')}")
        print(f"  Converged   : {solve_info.get('converged', False)}")
        print(f"  Solution norm: {solve_info.get('solution_norm', 0):.6e}")
        print(f"  S-params    : {sparams_info.get('port_count', 0)} port(s)")
        if metrics_info.get("gain_dbi") is not None:
            print(f"  Gain (dBi)  : {metrics_info['gain_dbi']:.4f}")

    elif args.command == "import-cad":
        print("[DeTaGrandMere] Importing CAD geometry ...")
        info = workflow.run_step("import")
        result = info.get("result", {}) if isinstance(info, dict) else {}
        if isinstance(result, dict):
            print(f"[DeTaGrandMere] Imported {result.get('num_shapes', 0)} shape(s).")
        else:
            print("[DeTaGrandMere] Done.")

    elif args.command == "export":
        print("[DeTaGrandMere] Exporting results ...")
        info = workflow.run_step("export")
        result = info.get("result", {}) if isinstance(info, dict) else {}
        if isinstance(result, dict):
            print(f"[DeTaGrandMere] Wrote to {result.get('output_dir')} ({result.get('format')}).")
        else:
            print("[DeTaGrandMere] Done.")

    elif args.command == "visualize":
        print("[DeTaGrandMere] Visualization stub — requires PyVista.")
        print("Install with: pip install pyvista numpy trimesh")

    return 0


if __name__ == "__main__":
    sys.exit(main())
