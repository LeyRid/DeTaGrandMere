# EM Simulation System — Implementation Checklist (Active Journal)

## Project Overview

**Goal:** Build a complete open-source Electromagnetic (EM) Simulation System for RF Antenna Engineers using the Method of Moments (MoM). The system accepts antenna geometry, material properties, and simulation parameters as input, solves Maxwell's equations numerically, and produces validated results including S-parameters, radiation patterns, gain, directivity, and field distributions.

**Technology Stack:**
- Language: Python 3.11+ with C++ extensions via PETSc/PETSc4Py
- Geometry kernel: OpenCASCADE (STEP import), CGAL (meshing)
- Linear algebra: PETSc (sparse matrices, iterative solvers)
- Visualization: PyVista + VTK
- Parallelization: MPI + CUDA/OpenCL GPU acceleration
- Fast Multipole Method: MLFMA for large-scale problems
- Configuration: YAML/JSON + CLI arguments
- Testing: pytest with >90% coverage target

**Module Layout:**
```
src/
  cad/                    # Geometry import, materials, boundaries, ports
  core/
    mom_solver/           # MoM formulation (EFIE/MFIE/CFIE), RWG basis, Green's function
    linear_algebra/       # PETSc matrix assembly, solver selection, preconditioners
    field_calculations/   # Near-field and far-field computation
    fmm/                  # Fast Multipole Method acceleration
    gpu_acceleration/     # CUDA/OpenCL kernels
    workflow/             # End-to-end simulation orchestration
  post_processing/
    export/               # Touchstone, HDF5, CSV, image export
    visualization/        # PyVista/VTK rendering, pattern plots
  utils/                  # CLI parser, config loader, data I/O, convergence tools
```

---

## How to Use This Checklist

- Each use case has a `[ ]` checkbox list. Check off items as you implement them.
- Tasks are ordered by dependency — complete earlier items before later ones.
- Sub-items under `### Task Groups` represent individual coding tasks for an AI agent or developer.
- When a task is done, change `[ ]` to `[x]` and optionally note any issues encountered.

---

## UC-01: Run Electromagnetic Simulation (End-to-End Workflow) — [🔗](../use_cases/0_summary/UC-01-Run%20Electromagnetic%20Simulation.md)

**Goal:** Complete end-to-end simulation from geometry import to validated results. This orchestrates all other use cases.

### Task Group 1: Project Setup & Infrastructure
- [ ] Initialize project structure with src/, tests/, examples/, docs/
- [ ] Create pyproject.toml with dependencies (numpy, scipy, h5py, pyvista, vtk, pyyaml, click)
- [ ] Set up pytest configuration in pytest.ini with coverage thresholds
- [ ] Create CI pipeline (.github/workflows/ci.yml) for automated testing on PR
- [ ] Write __init__.py files with module docstrings at every package level

### Task Group 2: Configuration System
- [ ] Implement YAML config loader (src/utils/config_loader.py): parse simulation parameters, I/O paths, solver settings
- [ ] Implement CLI argument parser (src/utils/cli_parser.py) using click or argparse; support --config flag
- [ ] Add environment variable override mechanism for key settings (PETSC_DIR, OMP_NUM_THREADS)
- [ ] Write config schema validation with pydantic or jsonschema

### Task Group 3: Project & Data Management
- [ ] Implement project metadata store class: tracks geometry file, materials, ports, mesh params, solver config, timestamps
- [ ] Create output directory structure auto-generation (results/, logs/, metadata/)
- [ ] Implement JSON-based project state serialization/deserialization for session persistence

### Task Group 4: End-to-End Workflow Orchestrator
- [ ] Create SimulationWorkflow class (src/core/workflow.py) with run() method that chains: import_geometry -> define_ports -> generate_mesh -> solve -> compute_fields -> export_results
- [ ] Each step returns success/failure with diagnostic info; workflow halts on failure and logs context
- [ ] Implement parallel simulation execution for multi-frequency sweeps or parameter studies
- [ ] Add progress reporting (console progress bar with tqdm)

### Task Group 5: Logging & Reproducibility
- [ ] Implement structured logging with timestamps, module names, and severity levels
- [ ] Log all simulation parameters, mesh settings, solver configuration to a JSON log file
- [ ] Capture resource usage statistics (CPU time, memory peak, wall-clock time) per step

### Task Group 6: Integration Tests
- [ ] Write integration test: full workflow on a half-wave dipole geometry with known results
- [ ] Write integration test: workflow failure path (invalid geometry file) produces correct error message

---

## UC-02: Optimize Antenna Design Iteratively — [🔗](../use_cases/0_summary/UC-02-Optimize%20Antenna%20Design%20Iteratively.md)

**Goal:** Iterative design refinement loop with parameter tracking, result comparison, and convergence monitoring.

### Task Group 1: Design Parameter Management
- [ ] Create DesignParameter class: name, value, min, max, step, description, type (dimension/material/position)
- [ ] Implement DesignSpace class: collection of parameters with validation ranges and dependencies
- [ ] Add parameter sweep generator: cartesian product of parameter values for automated exploration

### Task Group 2: Iteration Engine
- [ ] Create OptimizationLoop class that manages iteration cycles: load baseline -> apply changes -> run simulation -> compare results -> decide next step
- [ ] Implement design versioning: each iteration gets a unique ID with full state snapshot (geometry params, config, results)
- [ ] Add rollback capability: restore any previous iteration's state

### Task Group 3: Comparison & Reporting
- [ ] Implement MetricsComparator: computes delta between iterations for S11, gain, bandwidth, beamwidth, F/B ratio
- [ ] Create DesignEvolutionReport class: generates summary tables and charts showing parameter changes vs. performance
- [ ] Add regression detection: flag when any metric degrades beyond a threshold; highlight trade-offs

### Task Group 4: Batch Processing
- [ ] Implement parallel execution for multiple design variants (MPI or multiprocessing)
- [ ] Create batch result aggregator that merges results from all parallel runs into a comparison table
- [ ] Add early stopping criteria: stop when no improvement over N iterations or target reached

### Task Group 5: Archive & Export
- [ ] Implement simulation archive: stores all iteration data in HDF5 with metadata
- [ ] Create export of design evolution report as CSV/JSON for external analysis
- [ ] Add HTML/PDF report generation with charts and parameter tables

---

## UC-03: Import Geometry and Define Materials — [🔗](../use_cases/1_user_goals/UC-03-Import%20Geometry%20and%20Define%20Materials.md)

**Goal:** Load antenna geometry from CAD files (STEP/STL/OBJ), validate integrity, and assign material properties.

### Task Group 1: STEP File Import (OpenCASCADE)
- [ ] Implement OpenCASCADE wrapper (src/cad/opencascade_wrapper.py): load STEP file using OCC.TopoDS, extract shapes, faces, edges, vertices
- [ ] Extract volume/solid topology information for region identification
- [ ] Handle multi-body STEP files: split into separate selectable bodies
- [ ] Add unit detection and conversion (mm, m, inch)

### Task Group 2: STL/OBJ File Import
- [ ] Implement STL parser: read binary and ASCII formats, extract triangle mesh (vertices, normals, faces)
- [ ] Implement OBJ parser: read vertices, face indices, optional texture coordinates
- [ ] Normalize coordinate systems between CAD formats

### Task Group 3: Geometry Validation
- [ ] Implement degenerate face detection: zero-area faces, coincident vertices, duplicate edges
- [ ] Implement non-manifold edge detection: edges shared by more than 2 faces
- [ ] Implement self-intersection detection: intersecting faces or volumes
- [ ] Implement gap detection: edges not properly connected to neighboring faces
- [ ] Create GeometryValidator class that returns a ValidationReport with errors, warnings, and severity levels

### Task Group 4: Automatic Repair (Best-Effort)
- [ ] Implement face repair: merge collinear edges, fill small gaps (< tolerance)
- [ ] Implement vertex snapping: merge vertices within distance threshold
- [ ] Add repair options: auto-repair all non-critical issues, or present list for manual review

### Task Group 5: Material Database
- [ ] Create Material class: name, permittivity (real/imag), permeability (real/imag), conductivity, loss tangent, frequency dispersion model
- [ ] Implement MaterialDatabase class with built-in entries: free space, copper, aluminum, FR4, Rogers, Teflon, silicon, gold
- [ ] Add material lookup by name with fuzzy matching
- [ ] Implement custom material creation: user-provided properties with validation

### Task Group 6: Material Assignment
- [ ] Create region-to-material mapping system: each geometric body/face gets a material assignment
- [ ] Validate material assignments: positive permittivity, non-negative conductivity, loss tangent in [0,1]
- [ ] Implement frequency-dependent material lookup for dispersive models (Debye, Lorentz, Drude)

### Task Group 7: 3D Viewer Integration
- [ ] Create GeometryViewer class that renders loaded geometry using PyVista with region labels and colors
- [ ] Add interactive selection: click on a face/body to identify it for material assignment
- [ ] Display validation errors visually (highlight red faces, warning yellow edges)

### Task Group 8: Tests
- [ ] Unit test: STEP import of simple geometry (box, cylinder) produces correct topology
- [ ] Unit test: STL import produces valid triangle mesh with correct vertex count
- [ ] Unit test: material validation rejects negative permittivity and conductivity > physical limit
- [ ] Integration test: full import pipeline on a dipole antenna STEP file

---

## UC-04: Define Ports and Boundary Conditions — [🔗](../use_cases/1_user_goals/UC-04-Define%20Ports%20and%20Boundary%20Conditions.md)

**Goal:** Configure electrical ports (excitation points) and simulation domain boundary conditions.

### Task Group 1: Port Definition
- [ ] Create Port class: type (lumped/waveguide), location (face/edge/volume), dimensions, excitation amplitude/phase, reference impedance
- [ ] Implement port placement UI/logic: select a face or edge on the geometry as feed point
- [ ] Calculate minimum recommended port size based on wavelength at lowest frequency (lambda/10)
- [ ] Validate port positioning: must be on a valid surface/edge of the geometry

### Task Group 2: Lumped Port Implementation
- [ ] Implement lumped port model: voltage source with series impedance across a gap in the conductor
- [ ] Handle multi-lumped-port configurations for differential or balanced feeds
- [ ] Validate lumped port dimensions against wavelength at operating frequency

### Task Group 3: Waveguide Port Implementation
- [ ] Implement waveguide port model: modal excitation on an opening surface
- [ ] Calculate waveguide modes (TE/TM) based on port geometry and frequency
- [ ] Handle aperture-coupled feeds and microstrip transitions as waveguide ports

### Task Group 4: Alternative Port Definition Methods
- [ ] Implement gap-based port detection: automatically find gaps in the geometry for lumped port placement
- [ ] Implement opening-based port detection: detect openings in conducting surfaces for waveguide ports
- [ ] Support proximity-fed and aperture-coupled structures with specialized port definitions

### Task Group 5: Boundary Condition System
- [ ] Create BoundaryCondition base class with subclasses: PEC, PMC, Radiation (absorbing), PML (Perfectly Matched Layer)
- [ ] Implement boundary condition assignment to simulation domain surfaces
- [ ] Validate boundary conditions: radiation/PML on outer surfaces of open-space problems; no conflicting boundaries
- [ ] Calculate recommended minimum distance from antenna to boundary (lambda/4 at lowest frequency)

### Task Group 6: PML Implementation
- [ ] Implement PML layer: coordinate stretching for absorbing boundary conditions
- [ ] Configure PML thickness and conductivity profile based on operating frequency
- [ ] Validate that PML is placed at sufficient distance from antenna structure

### Task Group 7: Validation & Error Reporting
- [ ] Create PortBoundaryValidator: checks all ports have valid placement, correct sizing, non-overlapping assignments
- [ ] Generate configuration report listing all ports and boundaries with their parameters
- [ ] Reject configurations that violate physical constraints with specific error messages

---

## UC-05: Generate and Validate Computational Mesh — [🔗](../use_cases/1_user_goals/UC-05-Generate%20and%20Validate%20Computational%20Mesh.md)

**Goal:** Create a quality computational mesh for the antenna geometry with wavelength-based element sizing.

### Task Group 1: Mesh Sizing Calculation
- [ ] Implement wavelength calculator: lambda = c / (f * sqrt(epsilon_r)) for given frequency and material
- [ ] Calculate global element size: lambda/20 in general regions at highest operating frequency
- [ ] Calculate local refinement zones: lambda/100 near feed points, lambda/50 at edges/corners

### Task Group 2: CGAL Mesh Generation
- [ ] Implement CGAL wrapper (src/cad/cgal_meshing.py): surface mesh generation using Delaunay triangulation
- [ ] Configure mesh quality criteria: aspect ratio < 3:1, skewness < 0.5, minimum angle > 20 degrees
- [ ] Apply local refinement rules to critical regions (feed points, edges, corners, material interfaces)

### Task Group 3: Mesh Quality Metrics
- [ ] Implement element quality calculator: computes aspect ratio, skewness, volume, Jacobian for each element
- [ ] Create MeshQualityReport class: summarizes statistics (min/max/mean aspect ratio, count of violations)
- [ ] Flag degenerate elements: zero-volume elements, negative volumes, collapsed faces

### Task Group 4: Mesh Visualization
- [ ] Add mesh display in 3D viewer with color-coding by element quality (green = good, red = violation)
- [ ] Interactive filtering: show only elements violating specific criteria
- [ ] Element count and size distribution histogram

### Task Group 5: Adaptive Mesh Control
- [ ] Implement manual refinement: user selects regions to refine with custom sizing parameters
- [ ] Create mesh parameter presets: coarse (quick debug), medium (standard), fine (production)
- [ ] Store mesh parameters in project metadata for reproducibility

### Task Group 6: Validation Gate
- [ ] Create MeshValidator that blocks solver execution if quality violations exceed threshold
- [ ] Generate remediation suggestions: which regions to refine, what sizing changes to apply
- [ ] Log all mesh generation parameters and quality metrics to project metadata

---

## UC-06: Configure Solver and Run Frequency Sweep — [🔗](../use_cases/1_user_goals/UC-06-Configure%20Solver%20and%20Run%20Frequency%20Sweep.md)

**Goal:** Set up the numerical solver (MoM formulation with PETSc) and execute frequency sweep computation.

### Task Group 1: MoM Formulation Engine
- [ ] Implement EFIE (Electric Field Integral Equation) formulation in src/core/mom_solver/formulation.py
- [ ] Implement MFIE (Magnetic Field Integral Equation) formulation as alternative
- [ ] Implement CFIE (Combined Field Integral Equation) to suppress interior resonance issues
- [ ] Document the mathematical formulation with docstrings referencing source equations

### Task Group 2: RWG Basis Functions
- [ ] Implement Rao-Wilton-Glisson (RWG) basis functions in src/core/mom_solver/basis_functions.py
- [ ] Create basis function indexing system mapping each mesh edge to its basis function pair
- [ ] Calculate basis function support area and normal vectors for each element

### Task Group 3: Green's Function Evaluation
- [ ] Implement free-space Green's function G(r,r') = exp(-jkR)/(4*pi*R) in src/core/mom_solver/green_function.py
- [ ] Add near-field approximation for source-receiver pairs within lambda/2 distance
- [ ] Implement singular integral treatment for self and adjacent triangle interactions
- [ ] Calculate spectral domain wavenumber k = omega * sqrt(mu_0 * epsilon_0)

### Task Group 4: Impedance Matrix Assembly
- [ ] Implement Galerkin testing: test RWG basis functions against each other to build Z matrix
- [ ] Create sparse matrix assembly using PETSc MATMPIAIJ format
- [ ] Parallel matrix assembly: each MPI process assembles its local portion of the impedance matrix
- [ ] Add matrix assembly timing and memory profiling

### Task Group 5: Solver Selection and Configuration
- [ ] Implement automatic preconditioner selection in src/core/linear_algebra/solver.py:
  - None for <1000 elements
  - ILU(fill=10) for 1000-10000 elements
  - AMG (Algebraic Multigrid) for >10000 elements
- [ ] Support solver method selection: GMRES, BiCGStab, direct LU (for small problems)
- [ ] Configure convergence tolerance (default 1e-6), maximum iterations (default 5000)

### Task Group 6: PETSc Integration
- [ ] Create PETScSession class that manages KSP (Krylov Subspace) solver context
- [ ] Implement Krylov solver iteration loop with residual monitoring at each step
- [ ] Add PETSc logging for solver performance (iterations to convergence, residual history)
- [ ] Handle PETSc error codes and translate to user-friendly messages

### Task Group 7: Frequency Sweep Engine
- [ ] Create FrequencySweep class: manages multiple frequency point computations
- [ ] Implement adaptive frequency sampling: denser sampling near expected resonances
- [ ] Add warm-start capability: use previous frequency solution as initial guess for adjacent frequencies
- [ ] Parallel frequency sweep: distribute independent frequency points across MPI processes

### Task Group 8: Solver Diagnostics
- [ ] Implement convergence monitoring: log residual norm vs. iteration count at each frequency point
- [ ] Create solver diagnostic report: total iterations, peak memory, wall-clock time per frequency
- [ ] Add failure recovery: if solver doesn't converge, suggest preconditioner change or tolerance relaxation

---

## UC-07: Analyze S-Parameters and Bandwidth Results — [🔗](../use_cases/1_user_goals/UC-07-Analyze%20S-Parameters%20and%20Bandwidth%20Results.md)

**Goal:** Post-process simulation results to extract S-parameters, resonance frequencies, bandwidth, and impedance matching information.

### Task Group 1: S-Parameter Computation
- [ ] Implement S-parameter calculation from port currents and voltages in src/core/sparams_computation.py
- [ ] Calculate S11 (reflection coefficient) for single-port systems
- [ ] Calculate full S-matrix for multi-port systems including mutual coupling coefficients
- [ ] Handle complex S-parameters (magnitude and phase) across the frequency sweep

### Task Group 2: Resonance Detection
- [ ] Implement resonance finder: scan S11 magnitude to find frequencies below -10 dB threshold
- [ ] Calculate precise resonance frequency using quadratic interpolation between data points
- [ ] Detect multiple resonances in wideband simulations; rank by depth of S11 minimum

### Task Group 3: Bandwidth Analysis
- [ ] Implement -3 dB bandwidth calculation: find f_lower and f_upper where |S11| = -3 dB
- [ ] Implement -10 dB bandwidth calculation for return loss specification
- [ ] Calculate fractional bandwidth: (f_upper - f_lower) / center_frequency * 100%
- [ ] Classify antenna type based on bandwidth: narrowband (<1%), moderate (1-10%), wideband (>10%)

### Task Group 4: Smith Chart Data
- [ ] Implement impedance calculation from S-parameters: Z = Z0 * (1+S)/(1-S)
- [ ] Generate Smith chart data points (reflection coefficient vs. frequency)
- [ ] Create Smith chart visualization using PyVista or matplotlib
- [ ] Mark key points: center (matched), short circuit, open circuit, inductive/capacitive regions

### Task Group 5: Performance Assessment
- [ ] Create SParameterAnalyzer class that produces a structured analysis report
- [ ] Compare results against design targets: S11 < -10 dB over specified bandwidth?
- [ ] Flag anomalies: multiple unexpected resonances, flat responses, impedance mismatches
- [ ] Export analysis data in CSV and JSON formats

---

## UC-08: Analyze Radiation Patterns and Far-Field Results — [🔗](../use_cases/1_user_goals/UC-08-Analyze%20Radiation%20Patterns%20and%20Far-Field%20Results.md)

**Goal:** Compute far-field radiation patterns from near-field solution and extract key antenna metrics.

### Task Group 1: Near-to-Far-Field Transformation
- [ ] Implement Green's function integration for far-field computation in src/core/field_calculations/far_field.py
- [ ] Calculate radiated electric field E(theta, phi) by integrating surface currents against e^(-jkR)/(4*pi*R)
- [ ] Compute magnetic field H from E using eta_0 = 377 ohms intrinsic impedance
- [ ] Apply 1/R distance decay and phase delay for each observation direction

### Task Group 2: Radiation Pattern Computation
- [ ] Create angular grid generator: uniform or adaptive theta/phi sampling (default 1 degree resolution)
- [ ] Compute radiation intensity U(theta, phi) = (r^2 / 2*eta_0) * |E|^2 at each observation point
- [ ] Calculate E-plane and H-plane pattern cuts from full spherical data
- [ ] Support custom angular cuts at arbitrary azimuth/elevation angles

### Task Group 3: Pattern Metrics Extraction
- [ ] Implement peak directivity calculation: D = 4*pi * U_max / P_rad
- [ ] Calculate gain accounting for efficiency losses (conduction + dielectric)
- [ ] Compute half-power beamwidth in E-plane and H-plane (angles where pattern drops 3 dB from peak)
- [ ] Calculate front-to-back ratio: max forward gain / max backward gain
- [ ] Determine side-lobe levels relative to main lobe peak

### Task Group 4: Polarization Analysis
- [ ] Decompose far-field into orthogonal polarization components (theta-polarized, phi-polarized)
- [ ] Calculate axial ratio for circular polarization assessment
- [ ] Identify dominant polarization and cross-polarization rejection ratio

### Task Group 5: Pattern Visualization
- [ ] Implement polar plot rendering for E-plane and H-plane cuts using PyVista/matplotlib
- [ ] Create 3D radiation sphere visualization with normalized intensity coloring
- [ ] Add pattern animation across multiple frequencies
- [ ] Support overlay of measured data for comparison

### Task Group 6: Metrics Report
- [ ] Create RadiationPatternAnalyzer class producing structured report with all extracted metrics
- [ ] Include pattern plots as embedded images in report
- [ ] Compare against design targets: does antenna meet directivity, beamwidth, and F/B ratio specs?

---

## UC-09: Verify Convergence and Mesh Quality — [🔗](../use_cases/1_user_goals/UC-09-Verify%20Convergence%20and%20Mesh%20Quality.md)

**Goal:** Perform convergence testing to ensure simulation results are independent of mesh density and solver settings.

### Task Group 1: Convergence Study Framework
- [ ] Create ConvergenceStudy class that manages iterative refinement cycles
- [ ] Implement baseline result capture: store key metrics (S11 at resonance, peak gain, resonant frequency)
- [ ] Define acceptance tolerance (default 1%) for metric stability between refinements

### Task Group 2: Mesh Density Refinement
- [ ] Implement mesh refinement factor application: multiply element count by 2x per iteration
- [ ] Apply consistent refinement across all regions to maintain proportional accuracy
- [ ] Track element count and quality metrics at each refinement level

### Task Group 3: Solver Parameter Tightening
- [ ] Implement solver tolerance refinement: tighten from 1e-4 to 1e-5 to 1e-6 to 1e-9
- [ ] Implement iteration count escalation for tight-tolerance runs
- [ ] Track convergence rate (iterations per frequency point) at each tolerance level

### Task Group 4: Metric Extraction and Comparison
- [ ] Create ConvergenceMonitor that extracts the same metrics from each refinement level
- [ ] Calculate relative change between successive levels: delta = |value_n - value_(n-1)| / value_(n-1)
- [ ] Detect convergence: all tracked metrics below tolerance threshold for N consecutive levels

### Task Group 5: Convergence Reporting
- [ ] Generate convergence plot data: metric value vs. element count (or solver iteration count)
- [ ] Create convergence report with tables showing values at each refinement level
- [ ] Flag metrics that have not converged within the allowed number of refinement levels
- [ ] Recommend next steps: further mesh refinement, solver adjustment, or accept current accuracy

---

## UC-10: Export Simulation Results for Post-Processing — [🔗](../use_cases/1_user_goals/UC-10-Export%20Simulation%20Results%20for%20Post-Processing.md)

**Goal:** Export simulation results in multiple formats for external analysis and documentation.

### Task Group 1: Export Format Support
- [ ] Implement Touchstone format export (src/post_processing/export/touchstone_export.py) for S-parameter data
- [ ] Implement HDF5 export for structured simulation data (fields, mesh, metadata)
- [ ] Implement CSV export for tabular results (S-parameters, metrics at each frequency point)
- [ ] Implement JSON export for metadata and analysis reports

### Task Group 2: Image Export
- [ ] Implement radiation pattern image export (PNG, SVG) from PyVista renderers
- [ ] Implement Smith chart image export
- [ ] Implement field distribution plot export (3D field plots as PNG/SVG)
- [ ] Add resolution options for print-quality exports

### Task Group 3: Metadata Embedding
- [ ] Create metadata schema: geometry file, mesh parameters, solver settings, port definitions, material assignments, timestamps
- [ ] Embed metadata in HDF5 files using named groups and attributes
- [ ] Include metadata as JSON sidecar file alongside CSV/Touchstone exports

### Task Group 4: Export Validation
- [ ] Validate exported files are readable by external tools (import Touchstone back into a test harness)
- [ ] Check data completeness: no missing frequency points, no NaN values in exported arrays
- [ ] Log export operation with file list, sizes, and formats for audit trail

---

## UC-11: Generate Computational Mesh with Adaptive Refinement (Subfunction) — [🔗](../use_cases/2_subfunctions/UC-11-Generate%20Computational%20Mesh%20with%20Adaptive%20Refinement.md)

**Goal:** Automated mesh generation with error-indicator-based adaptive refinement cycles.

### Task Group 1: Initial Mesh Generation
- [ ] Implement wavelength-based sizing from operating frequency in CGAL wrapper
- [ ] Generate surface mesh with Delaunay triangulation and quality constraints
- [ ] Apply local refinement rules: lambda/100 at feed points, lambda/50 at edges/corners, lambda/20 for dielectric interfaces

### Task Group 2: Mesh Quality Enforcement
- [ ] Implement element validation: aspect ratio < 3:1, skewness < 0.5, positive volume
- [ ] Add element count cap: configurable maximum to prevent unbounded growth
- [ ] Log all quality metrics per element for audit and debugging

### Task Group 3: Error Indicator Computation
- [ ] Implement current density variation error indicator: |J_high_freq - J_low_freq| / |J_low_freq|
- [ ] Implement field gradient magnitude indicator: ||grad E|| over each element
- [ ] Implement Green's function proximity indicator for sources near element boundaries

### Task Group 4: Adaptive Refinement Cycle
- [ ] Implement error-based refinement: split elements where error indicators exceed threshold
- [ ] Limit refinement depth to prevent excessive element count growth
- [ ] Validate mesh quality after each refinement step before proceeding to next cycle
- [ ] Stop adaptive cycles when all errors below threshold or max iterations reached

### Task Group 5: Test Harness
- [ ] Unit test: mesh generation on simple geometry produces correct element count and quality metrics
- [ ] Integration test: adaptive refinement on a dipole converges to stable S11 within tolerance

---

## UC-12: Solve Impedance Matrix Using Numerical Solver (Subfunction) — [🔗](../use_cases/2_subfunctions/UC-12-Solve%20Impedance%20Matrix%20Using%20Numerical%20Solver.md)

**Goal:** Assemble and solve the linear system [Z][I] = [V] for current distribution at each frequency point.

### Task Group 1: Preconditioner Selection
- [ ] Implement preconditioner selection logic based on element count (None/ILU/AMG as per UC-06)
- [ ] Configure ILU fill level and AMG parameters for optimal performance
- [ ] Log preconditioner choice and condition number improvement

### Task Group 2: Solver Initialization
- [ ] Initialize GMRES or BiCGStab solver with preconditioned system via PETSc KSP
- [ ] Set initial guess: zero vector for first frequency, interpolated previous solution for adjacent frequencies
- [ ] Configure tolerance, maximum iterations, and monitoring callbacks

### Task Group 3: Iteration Loop
- [ ] Implement Krylov iteration loop computing residual norms at each step
- [ ] Log convergence history: iteration number, residual norm, preconditioned residual
- [ ] Monitor for divergence: residual increasing instead of decreasing

### Task Group 4: Progress Tracking and Logging
- [ ] Create SolverProgressReporter that logs iteration progress to console and log file
- [ ] Estimate remaining time based on current iteration rate
- [ ] Support interruptible runs (SIGINT handling) with partial result saving

### Task Group 5: Failure Recovery
- [ ] Implement solver failure detection: non-convergence, NaN/Inf in solution, memory exhaustion
- [ ] Generate diagnostic report: residual history, preconditioner performance, element count
- [ ] Suggest remediation: change preconditioner, relax tolerance, increase max iterations
- [ ] Preserve intermediate solution data for retry strategies without re-assembly

### Task Group 6: Parallel Solver Execution
- [ ] Implement MPI-distributed matrix-vector products in the Krylov iteration
- [ ] Monitor per-process memory usage and load balance
- [ ] Add collective error handling across all MPI processes

---

## UC-13: Perform Near-Field to Far-Field Transformation (Subfunction) — [🔗](../use_cases/2_subfunctions/UC-13-Perform%20Near-Field%20to%20Far-Field%20Transformation.md)

**Goal:** Convert surface current distribution into far-field radiation patterns using Green's function propagation.

### Task Group 1: Green's Function Evaluation
- [ ] Implement G(r,r') = exp(-jkR)/(4*pi*R) for each source-observation point pair in src/core/field_calculations/far_field.py
- [ ] Vectorize computation using NumPy broadcasting for performance
- [ ] Handle near-field corrections for observation points within 3*D^2/lambda (Fresnel region)

### Task Group 2: Field Integration
- [ ] Integrate surface currents against Green's function to compute E(theta, phi) at each observation angle
- [ ] Compute H(theta, phi) from E using eta_0 = 377 ohms
- [ ] Apply proper coordinate transformations for spherical observation system

### Task Group 3: Radiation Intensity and Normalization
- [ ] Calculate radiation intensity U(theta, phi) = (r^2 / 2*eta_0) * |E|^2
- [ ] Normalize pattern to peak value (0 dB at maximum)
- [ ] Store absolute values alongside normalized for directivity calculation

### Task Group 4: Output Formatting
- [ ] Create far-field data structure with theta, phi grids and E/H field components (real/imag or magnitude/phase)
- [ ] Support both full spherical coverage and planar cuts
- [ ] Cache results to avoid recomputation when angular resolution changes

---

## UC-14: Validate Results Against Analytical Benchmarks (Subfunction) — [🔗](../use_cases/2_subfunctions/UC-14-Validate%20Results%20Against%20Analytical%20Benchmarks.md)

**Goal:** Compare simulation results against known analytical solutions for canonical antenna geometries.

### Task Group 1: Benchmark Library
- [ ] Create benchmark data catalog (src/core/benchmark_data.py) with analytical solutions for:
  - Half-wave dipole: theoretical gain ~2.15 dBi, input resistance ~73 ohms
  - Small loop antenna: theoretical directivity = 1.5, radiation resistance formula
  - Microstrip patch: approximate formulas for resonant frequency and gain
- [ ] Store benchmark data as JSON with geometry parameters, expected values, and validity ranges

### Task Group 2: Metric Extraction for Comparison
- [ ] Implement S11 comparison: extract |S11| at resonance from simulation vs. analytical value
- [ ] Implement gain comparison: compare simulated peak gain to theoretical directivity (accounting for efficiency)
- [ ] Implement beamwidth comparison: compare simulated HPBW to analytical approximation

### Task Group 3: Error Computation and Pass/Fail Logic
- [ ] Create BenchmarkValidator that computes relative error for each metric
- [ ] Define accuracy thresholds: S11 within 5%, gain within 1 dB, beamwidth within 1 degree
- [ ] Generate pass/fail verdict per metric with explicit error values

### Task Group 4: Validation Report
- [ ] Create validation report with benchmark case name, analytical values, simulated values, errors, and verdicts
- [ ] Export report as JSON for automated CI integration
- [ ] Flag cases where simulation exceeds tolerance for investigation

---

## UC-15: Manage Material Properties and Boundary Conditions (Subfunction) — [🔗](../use_cases/2_subfunctions/UC-15-Manage%20Material%20Properties%20and%20Boundary%20Conditions.md)

**Goal:** Centralized material library management and boundary condition consistency validation.

### Task Group 1: Material Database Management
- [ ] Implement CRUD operations for the material database: create, read, update, delete material entries
- [ ] Add search functionality: by name, by type (conductor/dielectric/substrate), by property range
- [ ] Support material import from external files (CSV, JSON)

### Task Group 2: Material Property Validation
- [ ] Validate physical plausibility: positive real permittivity, positive permeability, non-negative conductivity
- [ ] Validate loss tangent within [0, 1] for passive materials
- [ ] Check frequency dispersion models (Debye/Lorentz/Drude) for parameter consistency

### Task Group 3: Boundary Condition Consistency Checking
- [ ] Implement BC-region compatibility check: PEC on conductors, radiation/PML on outer surfaces
- [ ] Detect incompatible assignments: PMC on open-space problems, conflicting boundary types on same surface
- [ ] Validate that all geometry surfaces have appropriate boundary conditions assigned

### Task Group 4: Audit Trail
- [ ] Log all material and boundary changes with timestamps and engineer identity
- [ ] Maintain version history for material database entries
- [ ] Support rollback of material/boundary assignments to previous state

---

## Implementation Order (Recommended)

The following order minimizes rework by building dependencies first:

### Phase 1: Foundation (Core Infrastructure)
1. UC-03 Import Geometry and Define Materials (geometry + materials)
2. UC-04 Define Ports and Boundary Conditions (ports + boundaries)
3. UC-05 Generate and Validate Computational Mesh (meshing)

### Phase 2: Solver Core
4. UC-12 Solve Impedance Matrix Using Numerical Solver (solver engine)
5. UC-11 Generate Computational Mesh with Adaptive Refinement (refined meshing subfunction)

### Phase 3: Field Computation
6. UC-13 Perform Near-Field to Far-Field Transformation (far-field)
7. UC-07 Analyze S-Parameters and Bandwidth Results (S-params + bandwidth)
8. UC-08 Analyze Radiation Patterns and Far-Field Results (pattern analysis)

### Phase 4: Quality & Validation
9. UC-09 Verify Convergence and Mesh Quality (convergence testing)
10. UC-14 Validate Results Against Analytical Benchmarks (benchmark validation)

### Phase 5: Workflow & Export
11. UC-06 Configure Solver and Run Frequency Sweep (full sweep orchestration)
12. UC-10 Export Simulation Results for Post-Processing (export system)
13. UC-01 Run Electromagnetic Simulation (end-to-end orchestrator)

### Phase 6: Advanced Features
14. UC-02 Optimize Antenna Design Iteratively (optimization loop)
15. UC-15 Manage Material Properties and Boundary Conditions (material/boundary management)

---

## Verification Checklist (Final Quality Gate)

Before declaring the system complete, verify:

- [ ] All 15 use cases have corresponding implementation tasks checked off
- [ ] pytest suite passes with >90% code coverage
- [ ] CI pipeline runs on every PR and blocks merge on test failure
- [ ] Half-wave dipole benchmark produces S11 within 5% of -inf dB at resonance
- [ ] Dipole peak gain within 1 dB of theoretical 2.15 dBi
- [ ] Radiation pattern shows expected figure-8 shape in E-plane
- [ ] Convergence study shows <1% variation between fine and finest meshes
- [ ] Touchstone export produces valid .s2p file readable by external tools
- [ ] CLI interface works for all major use cases without configuration files
- [ ] Documentation includes API reference, user guide, and at least one tutorial
- [ ] README explains installation, usage, and contribution guidelines
