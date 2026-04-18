# DeTaGrandMere — Open-Source Antenna Simulation Software (Method of Moments)

## Architectural Guidelines
- Python-first with C++ via PETSc/PETSc4Py for numerics; CGAL and OpenCASCADE as C++ backends with Python bindings
- Strict modular separation: `src/cad/`, `src/core/mom_solver/`, `src/core/linear_algebra/`, `src/post_processing/`, `src/utils/`
- Configuration-driven: YAML/JSON config files + environment variable overrides
- Testing pyramid: unit → integration → regression benchmarks at every phase
- Semantic versioning (MAJOR.MINOR.PATCH); CI with >90% coverage target

## Scope Definition
- In-scope: CAD import (STEP), CGAL surface meshing, material database, boundary conditions, MoM solver (EFIE/MFIE/CFIE + RWG basis functions), PETSc linear algebra, S-parameter computation, near/far-field calculations, visualization (PyVista/VTK), antenna metrics, Touchstone/HDF5 export, MPI parallelization, GPU acceleration (CUDA/OpenCL), Fast Multipole Method, dispersive/anisotropic materials
- Out-of-scope: Full-wave FEM solver (hybrid MoM-FEM is in-scope but limited to coupling interface), proprietary CAD kernels, real-time simulation

## Cross-Reference Matrix
| Feature | Use Case(s) |
|---------|-------------|
| STEP file import | UC1, UC5 |
| OpenCASCADE geometry | UC1, UC2, UC3 |
| CGAL mesh generation | UC2 |
| Mesh cleaning & quality | UC2 |
| Material database | UC3, UC18 |
| Boundary conditions (PEC/PMC/RADIATION/PML) | UC3, UC5 |
| Port definitions | UC4, UC5 |
| EFIE/MFIE/CFIE formulations | UC5 |
| RWG basis functions | UC5, UC6 |
| PETSc sparse matrix & solvers | UC5, UC7 |
| Green's function evaluation | UC5, UC6 |
| S-parameter computation | UC8 |
| Near-field calculation | UC9 |
| Far-field transformation | UC10 |
| Field visualization (PyVista/VTK) | UC10 |
| Directivity / Gain / Bandwidth / F/B ratio | UC11 |
| Touchstone / HDF5 export | UC12 |
| Data import (Touchstone, HDF5) | UC13 |
| MPI parallelization | UC5, UC7 |
| GPU acceleration (CUDA/OpenCL) | UC7, UC8 |
| Fast Multipole Method (FMM/MLFMA) | UC8 |
| Hybrid MoM-FEM | UC5 |
| Dispersive materials (Debye/Lorentz/Drude) | UC18 |
| Anisotropic materials | UC18 |
| Multi-port excitation | UC4, UC5 |
| End-to-end workflow | UC19 |
| CLI / config file interface | UC19 |
| Comprehensive test suite | UC20 |
| Documentation (API, user manual, tutorials) | UC21 |
| Release preparation & packaging | UC22 |

---

[→ Import and Validate CAD Geometry](./USE_CASES/UC01.md)
[→ Generate and Refine Surface Mesh](./USE_CASES/UC02.md)
[→ Define Materials, Boundary Conditions, and Ports](./USE_CASES/UC03.md)
[→ Compute S-Parameters for Multi-Port Systems](./USE_CASES/UC04.md)
[→ Solve MoM System (EFIE/MFIE/CFIE + RWG Basis Functions)](./USE_CASES/UC05.md)
[→ Compute and Store Field Data (Near and Far Fields)](./USE_CASES/UC06.md)
[→ Visualize Fields and Antenna Geometry](./USE_CASES/UC07.md)
[→ Compute Antenna Metrics (Directivity, Gain, Bandwidth, F/B Ratio)](./USE_CASES/UC08.md)
[→ Export and Import Simulation Data](./USE_CASES/UC09.md)
[→ Run End-to-End Simulation Workflow with CLI Interface](./USE_CASES/UC10.md)
[→ Execute Comprehensive Test Suite with Regression Testing](./USE_CASES/UC11.md)
[→ Generate Documentation and Tutorials](./USE_CASES/UC12.md)
[→ Prepare Release Packages and Landing Page](./USE_CASES/UC13.md)
[→ Support Advanced Materials (Dispersive and Anisotropic)](./USE_CASES/UC14.md)
[→ Scale Solver with MPI Parallelization and GPU Acceleration](./USE_CASES/UC15.md)
[→ Accelerate Matrix Assembly with Fast Multipole Method (FMM/MLFMA)](./USE_CASES/UC16.md)
[→ Run Hybrid MoM-FEM Simulation for Complex Substrates](./USE_CASES/UC17.md)
[→ Perform Convergence Studies and Validation Against Literature](./USE_CASES/UC18.md)
[→ Manage Version History and Community Feedback](./USE_CASES/UC19.md)
[→ Optimize Solver Performance and Memory Management](./USE_CASES/UC20.md)
[→ Configure Simulation Parameters via Config File and CLI](./USE_CASES/UC21.md)
[→ Run Multi-Port Excitation and Mutual Coupling Analysis](./USE_CASES/UC22.md)
[→ Implement Continuous Improvement and Quality Monitoring](./USE_CASES/UC23.md)
