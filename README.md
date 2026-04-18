# DeTaGrandMere

**Open-Source Antenna Simulation Software using Method of Moments**

DeTaGrandMere is a high-performance electromagnetic simulation toolkit designed for antenna design and analysis. It leverages the Method of Moments (MoM) to solve Maxwell's equations on complex 3D geometries, providing accurate computation of S-parameters, radiation patterns, and near/far-field distributions. The codebase integrates modern open-source libraries for CAD handling, computational geometry, parallel linear algebra, and scientific visualization.

---

## Key Features

- **CAD Import** via OpenCASCADE — load STEP, IGES, and BREP files directly
- **CGAL Meshing** — robust surface and volume mesh generation
- **EFIE / MFIE / CFIE MoM Solver** — multiple integral equation formulations for numerical stability
- **RWG Basis Functions** — Rao-Wilton-Glisson edge elements for vector field discretization
- **PETSc Linear Algebra** — scalable sparse matrix operations and iterative solvers (GMRES, BiCGStab)
- **S-Parameter Computation** — full wave port excitation and scattering matrix evaluation
- **Near-Field / Far-Field Calculations** — equivalence principle-based radiation integration
- **PyVista Visualization** — interactive 3D rendering of currents, fields, and geometry
- **Touchstone / HDF5 Export** — industry-standard formats for post-simulation analysis
- **MPI Parallelization** — domain decomposition across distributed memory clusters
- **GPU Acceleration** — CUDA/OpenMP backend for matrix-vector products and field evaluation
- **Fast Multipole Method (FMM)** — O(N log N) complexity for large-scale problems

---

## Installation

### pip

```bash
pip install detagrandmere
```

### conda

```bash
conda install -c conda-forge detagrandmere
```

### From Source

```bash
git clone https://github.com/deTAGrandMere/detagrandmere.git
cd detagrandmere
pip install -r requirements.txt
python setup.py install
```

---

## Quick Start

```python
from detagrandmere import MoMSolver

solver = MoMSolver(geometry="antenna.step", frequency=2.4e9, formulation="CFIE")
solver.solve()
solver.export_touchstone("results/sparams.s2p")
```

---

## Module Overview

| Path                        | Purpose                                                        |
|-----------------------------|----------------------------------------------------------------|
| `src/cad`                   | CAD file I/O via OpenCASCADE; STEP/IGES/BREP import           |
| `src/core/mom_solver`       | EFIE/MFIE/CFIE formulation, RWG basis functions, matrix assembly |
| `src/core/linear_algebra`   | PETSc wrappers, FMM acceleration, GPU kernels                |
| `src/post_processing`       | S-parameter extraction, near/far-field transforms, export    |
| `src/utils`                 | Geometry helpers, meshing interface (CGAL), logging, config  |

---

## Architecture

```
┌─────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ STEP File   │────▶│ OpenCASCADE      │────▶│ CGAL Mesh         │
│ (.step)     │     │ CAD Import       │     │ Surface/Edge Mesh │
└─────────────┘     └──────────────────┘     └───────────────────┘
                                                       │
                                                       ▼
┌──────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ Touchstone   │◀────│ Post-Processing  │◀────│ MoM Solver        │
│ (.s2p) / HDF5│     │ Metrics Export   │     │ Matrix Assembly   │
└──────────────┘     └──────────────────┘     └───────────────────┘
                                                       ▲
                                       Fields ┌───────────────────┐
                                       ───────▶│ Currents & Potentials│
                                               └───────────────────┘

Data Flow Summary:
  STEP file → OpenCASCADE → CGAL Mesh → MoM Solver → Fields → Metrics → Touchstone/HDF5
```

---

## License

This project is licensed under the **MIT License**. See the `LICENSE` file for full details.

---

## Development

- Run tests with **pytest**: `pytest --cov=src tests/`
- Continuous integration runs automatically on every pull request via GitHub Actions
- Code style enforced by black and flake8 (pre-commit hooks recommended)
