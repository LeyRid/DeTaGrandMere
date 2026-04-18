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

# Use Case 1: Import and Validate CAD Geometry

* [ ] Implement `src/cad/opencascade_wrapper.py` with OpenCASCADE wrapper class
* [ ] Implement `import_step_file()` method with error handling for malformed files
* [ ] Implement `extract_surfaces()`, `extract_edges()`, `extract_shapes()` methods
* [ ] Implement geometry validation: non-manifold detection, degenerate elements, self-intersection checks
* [ ] Create test fixtures with sample STEP files (simple + complex)
* [ ] Write tests in `tests/unit/test_opencascade_wrapper.py`

## CHARACTERISTIC INFORMATION

* Goal in Context: Load CAD geometry from STEP files and validate it for downstream meshing and simulation.
* Scope: OpenCASCADE integration, STEP parsing, geometry extraction and validation.
* Level: Main success scenario covers a single STEP file import; extensions handle multi-file, corrupted, or unsupported formats.
* Preconditions: OpenCASCADE Python bindings (opencascade-core or occt-pybind11) are installed and accessible.
* Success End Condition: Geometry is loaded, extracted into surfaces/edges/shapes with metadata, and passes all validation checks.
* Failed End Condition: Import fails with a descriptive `CADError` or `GeometryError`; invalid geometry is flagged for repair.
* Primary Actor: User or automated pipeline initiating a simulation.
* Trigger: User provides a STEP file path (or equivalent CAD format) to the software.

### MAIN SUCCESS SCENARIO

1. User invokes import with a STEP file path.
2. System loads OpenCASCADE and initializes the wrapper.
3. System parses the STEP file and stores geometry metadata (version, units, timestamps).
4. System extracts surfaces, edges, and shapes; stores topology information.
5. System validates geometry: checks non-manifold elements, degenerate faces/edges, self-intersections.
6. System generates a validation report marking valid vs. invalid regions.
7. Validated geometry is stored in the internal registry with unique IDs.

### EXTENSIONS

2a. STEP file is corrupted or unreadable : Report `CADError` with parse diagnostics; do not crash.
3a. File contains unsupported CAD format : Prompt user for conversion or reject with `CADError`.
5a. Geometry has non-manifold elements : Flag for repair; allow user to proceed with warnings or auto-repair.
5b. Degenerate faces/edges detected : Remove or flag them; report count and locations in validation output.

### SUB-VARIATIONS

5 : Non-manifold, zero-area, zero-length, self-intersection checks run in sequence.
6 : Validation report can be written to file or returned as an object.

### RELATED INFORMATION (optional)

* Priority: Critical — no simulation can proceed without valid geometry.
* Performance Target: Import a 10k-face STEP file in under 30 seconds on modern hardware.
* Frequency: High — every simulation workflow begins with geometry import.

---

# Use Case 2: Generate and Refine Surface Mesh

* [ ] Implement `src/cad/cgal_meshing.py` with CGAL wrapper class
* [ ] Implement `extract_triangle_mesh()` from CAD surfaces with alpha-shape size control
* [ ] Implement mesh cleaning: remove small/degenerate triangles, merge close vertices, fix non-manifold edges
* [ ] Implement mesh quality assessment: aspect ratio, skewness, quality index computation
* [ ] Implement refinement functions: refine near vertices, edge regions, corner regions, adaptive error-based refinement
* [ ] Write tests in `tests/unit/test_cgal_meshing.py` with benchmark comparisons

## CHARACTERISTIC INFORMATION

* Goal in Context: Convert validated CAD surfaces into a high-quality triangular mesh suitable for MoM basis function application.
* Scope: CGAL surface meshing, cleaning, quality assessment, and adaptive refinement.
* Level: Single geometry → single mesh; extensions handle multi-region meshes with different density targets.
* Preconditions: Geometry has passed validation (UC1); CGAL Python bindings (cgal-python3) are installed.
* Success End Condition: A manifold, closed triangular mesh is produced with quality metrics meeting configurable thresholds.
* Failed End Condition: Mesh generation fails; `MeshError` is raised with diagnostics on problematic regions.
* Primary Actor: Solver setup pipeline.
* Trigger: User or workflow initiates meshing after geometry import.

### MAIN SUCCESS SCENARIO

1. System receives validated CAD geometry from UC1.
2. CGAL wrapper extracts a triangle mesh using alpha-shape parameter for size control.
3. System stores vertex positions, face indices (connectivity), normals, and centroids.
4. Mesh cleaning removes degenerate triangles, merges close vertices, fixes non-manifold edges.
5. Quality metrics are computed: aspect ratio, skewness, quality index per triangle.
6. System identifies poor-quality regions and offers refinement options.
7. Adaptive refinement is applied if requested; quality metrics are recomputed.
8. Final mesh topology is validated (manifold, closed) and stored.

### EXTENSIONS

2a. Alpha-shade parameter not specified : Use default mesh density based on geometry bounding box.
4a. Mesh cleaning removes >20% of triangles : Warn user; suggest manual review or adjusted parameters.
7a. Refinement does not improve quality : Report failure and fall back to original mesh with warnings.

### SUB-VARIATIONS

5 : Quality metrics can be computed per-triangle or aggregated as histograms.
7 : Refinement can target specific regions (corners, edges, feed points) or apply uniformly.

### RELATED INFORMATION (optional)

* Priority: Critical — mesh quality directly affects solver accuracy and convergence.
* Performance Target: Mesh a 50k-face geometry in under 60 seconds.
* Frequency: High — every simulation requires a fresh mesh.

---

# Use Case 3: Define Materials, Boundary Conditions, and Ports

* [ ] Create `src/cad/material_database.py` with Material class (eps, mu, sigma, loss tangent, frequency-dependent models)
* [ ] Implement built-in library (copper, aluminum, FR4) and dispersive models (Debye/Cole-Cole/Drude/Lorentz)
* [ ] Create `src/cad/boundary_conditions.py` with PEC, PMC, RADIATION, PML types
* [ ] Implement material mapping to mesh regions by surface IDs or volume assignment
* [ ] Create `src/cad/port_definition.py` with lumped and waveguide port types
* [ ] Write tests in `tests/unit/test_boundary_conditions.py`

## CHARACTERISTIC INFORMATION

* Goal in Context: Assign physical materials, boundary conditions, and excitation ports to the mesh before solving.
* Scope: Material database, BC system, port definitions, material-to-mesh mapping.
* Level: Single simulation setup; extensions handle multi-material assemblies and frequency sweeps.
* Preconditions: Mesh exists (UC2); material properties are defined or loaded from a file.
* Success End Condition: All mesh regions have assigned materials, boundary conditions, and ports with validated consistency.
* Failed End Condition: Inconsistent material/BC assignments detected; `SolverError` raised with details.
* Primary Actor: Simulation designer or automated workflow.
* Trigger: User loads a configuration file specifying materials, BCs, and ports.

### MAIN SUCCESS SCENARIO

1. System loads material definitions from built-in library or external file (YAML/JSON).
2. Material properties are validated: real positive values, frequency-dependent consistency.
3. Boundary conditions are defined (PEC, PMC, RADIATION, PML) with configuration parameters.
4. Materials are mapped to mesh regions by surface ID or volume-based assignment.
5. Ports are created with type, location, size, impedance, and orientation.
6. System validates port placement relative to geometry (e.g., lambda/10 minimum size).
7. Material compatibility is checked across adjacent regions; warnings for mismatches.

### EXTENSIONS

1a. External material file uses unsupported format : Report `CADError` with format details.
4a. Mixed-material regions detected : Interpolate properties at element level; log interpolation method.
6a. Port size below lambda/10 : Warn user; allow override with explicit confirmation.

### SUB-VARIATIONS

2 : Frequency-dependent materials interpolate over the simulation frequency range.
4 : Material assignment can be by surface ID, volume region, or proximity-based heuristics.

### RELATED INFORMATION (optional)

* Priority: Critical — incorrect materials/BCs produce physically meaningless results.
* Performance Target: Map 10k mesh regions to materials in under 5 seconds.
* Frequency: High — every simulation requires material/BC/port setup.

---

# Use Case 4: Compute S-Parameters for Multi-Port Systems

* [ ] Implement port definitions in solver engine with single and multi-port support
* [ ] Implement S-parameter computation (S11, S21, etc.) with reflection/transmission coefficients
* [ ] Implement Touchstone export format (.s2p, .s4p) with frequency vector storage
* [ ] Validate S-parameter matrix properties (reciprocity, passivity for lossless)
* [ ] Write tests in `tests/integration/test_mom_solver.py`

## CHARACTERISTIC INFORMATION

* Goal in Context: Calculate scattering parameters characterizing how RF energy propagates through the antenna structure.
* Scope: Single and multi-port S-parameter computation, Touchstone export, matrix validation.
* Level: Full simulation run producing S-parameters across a frequency sweep; extensions handle adaptive sampling.
* Preconditions: MoM system matrix is assembled (UC5); ports are defined (UC3).
* Success End Condition: S-parameter matrix is computed for all port combinations across the frequency range.
* Failed End Condition: Solver fails to converge; `ConvergenceError` raised with residual history.
* Primary Actor: RF engineer analyzing antenna performance.
* Trigger: User requests S-parameter sweep after solver configuration.

### MAIN SUCCESS SCENARIO

1. System initializes port excitations for all defined ports.
2. For each frequency point in the sweep, system solves the linear system (UC5) with appropriate excitation.
3. Reflection coefficients are calculated from port 1 excitation; transmission coefficients from other ports.
4. S-parameter matrix is assembled across all frequencies and port combinations.
5. Matrix properties are validated: reciprocity check, passivity for lossless structures.
6. Results are stored in memory and optionally exported to Touchstone format.
7. User receives S-parameter data with frequency vector and metadata.

### EXTENSIONS

2a. Frequency sweep uses adaptive sampling : System refines frequency points where S-parameters change rapidly.
3a. Multi-port mutual coupling is significant : Compute full N-port matrix; warn about conditioning issues.
5a. Passivity violation detected : Flag potential numerical error; suggest mesh refinement or preconditioner change.

### SUB-VARIATIONS

2 : Excitation can be lumped port voltage source or waveguide mode excitation.
6 : Touchstone format supports 1-port through N-port; complex S-parameters stored in real/imaginary or dB/angle.

### RELATED INFORMATION (optional)

* Priority: Critical — S-parameters are the primary output for RF engineers.
* Performance Target: Compute S11 at 100 frequency points for a dipole in under 30 seconds (serial).
* Frequency: High — every simulation produces S-parameters.

---

# Use Case 5: Solve MoM System (EFIE/MFIE/CFIE + RWG Basis Functions)

* [ ] Create `src/core/mom_solver/formulation.py` with EFIE, MFIE, CFIE classes
* [ ] Create `src/core/mom_solver/basis_functions.py` with Triangle and RWGBasisFunction classes
* [ ] Create `src/core/mom_solver/green_function.py` with singularity handling and adaptive quadrature
* [ ] Create `src/core/mom_solver/solver_engine.py` with MOMSolver class (setup_mesh, compute_system_matrix, solve, extract_solution)
* [ ] Create `src/core/linear_algebra/preconditioner.py` and `solver.py` (GMRES, BiCGStab wrappers around PETSc)
* [ ] Implement parallel matrix assembly support via MPI
* [ ] Write tests across `tests/unit/test_mom_formulation.py`, `test_rwg_basis_functions.py`, `test_sparse_matrix.py`, `test_iterative_solvers.py`, `test_matrix_assembly.py`

## CHARACTERISTIC INFORMATION

* Goal in Context: Assemble and solve the Method of Moments linear system to find surface currents on the antenna structure.
* Scope: Integral equation formulations (EFIE/MFIE/CFIE), RWG basis functions, Green's function, PETSc solvers, parallel assembly.
* Level: Single-frequency solve; extensions handle frequency sweeps, adaptive stopping, and hybrid MoM-FEM.
* Preconditions: Mesh exists (UC2), materials/BCs/ports defined (UC3), solver configuration loaded.
* Success End Condition: Linear system is solved to within tolerance; surface current solution is extracted.
* Failed End Condition: Solver fails to converge after max iterations; `ConvergenceError` with residual history and recommendations.
* Primary Actor: Solver engine (automated).
* Trigger: User or workflow initiates simulation after full setup.

### MAIN SUCCESS SCENARIO

1. System sets up the mesh with RWG basis functions defined on each triangle edge.
2. Green's function is evaluated for each matrix element pair with singularity handling at R=0.
3. System assembles the MoM impedance matrix using EFIE (or MFIE/CFIE) formulation.
4. Right-hand side vector is constructed from port excitation(s).
5. PETSc iterative solver (GMRES or BiCGStab) with preconditioner (ILU/AMG) solves the linear system.
6. Convergence is monitored; residual history is tracked and reported.
7. Surface current solution is extracted from the solved vector.

### EXTENSIONS

2a. Green's function computation uses caching : Precomputed values reduce assembly time for frequency sweeps.
3a. CFIE formulation selected : EFIE and MFIE contributions are combined with configurable weighting.
5a. Solver does not converge at tolerance : Increase iteration count, change preconditioner, or switch solver; report diagnostics.
5b. MPI parallel assembly : Matrix is distributed across ranks; PETSc handles parallel solve automatically.

### SUB-VARIATIONS

3 : EFIE is preferred for thin structures; MFIE for electrically large conductors; CFIE combines both for stability.
6 : Convergence can be monitored by residual norm, energy norm, or user-defined criteria.

### RELATED INFORMATION (optional)

* Priority: Critical — this is the core computational engine.
* Performance Target: Solve a 10k-unknown system in under 60 seconds on a single core.
* Frequency: Very high — every simulation runs the solver.

---

# Use Case 6: Compute and Store Field Data (Near and Far Fields)

* [ ] Create `src/core/field_calculations/near_field.py` with E and H field calculation methods
* [ ] Create `src/core/field_calculations/far_field.py` with spherical coordinate transformation
* [ ] Implement field interpolation between mesh elements for observation points
* [ ] Support complex-valued field storage and frequency-dependent fields
* [ ] Write tests in integration suite verifying field calculations against analytical solutions

## CHARACTERISTIC INFORMATION

* Goal in Context: Calculate electromagnetic fields (E and H) in near and far regions from the solved surface currents.
* Scope: Near-field computation at observation points, far-field transformation to spherical coordinates.
* Level: Single-frequency field calculation; extensions handle frequency sweeps and volumetric field grids.
* Preconditions: Surface current solution exists from UC5.
* Success End Condition: E and H fields are computed at all requested observation points with correct polarization vectors.
* Failed End Condition: Singularity encountered at source location; `FieldCalculationError` raised.
* Primary Actor: Post-processing pipeline.
* Trigger: User requests field visualization or metric computation after solver completes.

### MAIN SUCCESS SCENARIO

1. System receives surface current solution from UC5.
2. Near-field E and H are calculated at user-specified observation points using current-to-field integrals.
3. Singularity at source locations is handled via principal value integration.
4. Far-field transformation converts near-field currents to spherical E_theta, E_phi components.
5. Polarization vectors are applied correctly for each observation angle (theta, phi).
6. Field values are stored in memory with frequency and geometry metadata.
7. Fields are available for visualization or metric computation.

### EXTENSIONS

2a. Observation points form a volumetric grid : System interpolates across the grid; stores 3D field arrays.
4a. Far-field uses angular sampling control : User specifies theta/phi resolution (default: 1-degree steps).
6a. Frequency-dependent fields : Fields are computed at all sweep frequencies and stored in an HDF5 structure.

### SUB-VARIATIONS

2 : Observation points can be individual points, lines, planes, or volumetric grids.
4 : Far-field transformation supports both spherical and Cartesian output coordinates.

### RELATED INFORMATION (optional)

* Priority: High — fields are required for visualization and antenna metrics.
* Performance Target: Compute far-field at 180x360 angular points in under 15 seconds.
* Frequency: Medium — depends on whether user requests field data.

---

# Use Case 7: Visualize Fields and Antenna Geometry

* [ ] Create `src/post_processing/visualization/vtk_renderer.py` with VTK-based rendering
* [ ] Create `src/post_processing/visualization/pyvista_backend.py` with interactive viewing controls
* [ ] Implement near-field surface plots, field line (streamline) visualization, contour plots on cross-sections
* [ ] Implement color mapping for field magnitude and animation support for time-domain fields
* [ ] Add cut plane functionality, multiple view angles, measurement tools
* [ ] Write tests in `tests/integration/test_field_visualization.py`

## CHARACTERISTIC INFORMATION

* Goal in Context: Provide interactive 3D visualization of electromagnetic fields and antenna geometry for analysis.
* Scope: VTK/PyVista rendering, field plots, cross-sections, color mapping, animations.
* Level: Interactive session; extensions handle batch export and automated quality assessment.
* Preconditions: Field data exists (UC6); geometry mesh is available (UC2).
* Success End Condition: Fields and geometry are rendered in an interactive 3D view with user-controllable parameters.
* Failed End Condition: Visualization backend fails to initialize; graceful fallback to text-based field summary.
* Primary Actor: RF engineer or designer analyzing simulation results.
* Trigger: User requests visualization after fields are computed.

### MAIN SUCCESS SCENARIO

1. System initializes PyVista/VTK rendering backend.
2. Geometry mesh is loaded into the scene with material coloring.
3. Near-field E and H vectors are plotted as arrows or surface plots on the geometry.
4. Far-field radiation pattern is rendered as a 3D polar plot.
5. Color mapping is applied to field magnitude with user-selectable colormap (jet, viridis, plasma).
6. User can interact: rotate view, apply cut planes, measure distances and angles.
7. Animation support allows time-domain field animation if applicable.

### EXTENSIONS

1a. No GPU available : Fall back to software rendering with reduced resolution.
3a. Large field dataset : System downsamples for display; full data remains available for export.
5a. Multiple field types displayed simultaneously : Overlay E-field magnitude with current density on geometry.

### SUB-VARIATIONS

4 : Far-field can be shown as a polar plot (2D slice) or 3D surface.
6 : Cut planes can be orthogonal to X, Y, or Z axes; user specifies plane position.

### RELATED INFORMATION (optional)

* Priority: High — visualization is the primary analysis interface.
* Performance Target: Render field plot in under 5 seconds for meshes up to 100k elements.
* Frequency: Medium — used during design iteration and result analysis.

---

# Use Case 8: Compute Antenna Metrics (Directivity, Gain, Bandwidth, F/B Ratio)

* [ ] Implement directivity calculation via radiation intensity integration in `src/post_processing/`
* [ ] Implement gain calculation multiplying directivity by radiation efficiency
* [ ] Implement bandwidth analysis: S11 threshold crossing, -3dB/-10dB bandwidth, resonant frequency detection
* [ ] Implement front-to-back ratio calculation based on antenna orientation
* [ ] Write tests in `tests/integration/test_antenna_metrics.py`

## CHARACTERISTIC INFORMATION

* Goal in Context: Extract key antenna performance metrics from simulated field data for comparison with specifications.
* Scope: Directivity, gain, bandwidth, front-to-back ratio calculations.
* Level: Post-simulation analysis; extensions handle frequency sweeps and multi-port metrics.
* Preconditions: Far-field data exists (UC6); S-parameters are computed (UC4).
* Success End Condition: All requested metrics are computed with documented methodology and uncertainty estimates.
* Failed End Condition: Insufficient angular sampling or missing far-field data; `FieldCalculationError` raised.
* Primary Actor: RF engineer reviewing antenna performance.
* Trigger: User requests metric report after simulation completes.

### MAIN SUCCESS SCENARIO

1. System integrates radiation intensity over the full sphere to compute directivity in dBi and linear scale.
2. Radiation efficiency is calculated from material losses; gain = directivity × efficiency.
3. S11 bandwidth is determined by finding frequency points where |S11| < threshold (default: -10 dB).
4. Resonant frequencies are identified as local minima in the S11 curve.
5. Front-to-back ratio is computed from far-field intensity in front vs. back directions.
6. Results are compiled into a structured report with methodology documentation.

### EXTENSIONS

2a. Material losses include dielectric and conductor components : Efficiency is decomposed and reported separately.
3a. Fractional bandwidth is requested : Computed as (f_high - f_low) / f_center × 100%.
5a. Arbitrary reference direction for F/B ratio : User specifies the front axis vector.

### SUB-VARIATIONS

1 : Directivity can be computed at a single frequency or across the sweep range.
3 : Bandwidth thresholds are configurable (-3dB, -6dB, -10dB); multiple thresholds produce multiple bandwidth values.

### RELATED INFORMATION (optional)

* Priority: High — metrics are the primary deliverable for antenna design validation.
* Performance Target: Compute all metrics for a 180x360 angular grid in under 5 seconds.
* Frequency: Medium — computed after each simulation run.

---

# Use Case 9: Export and Import Simulation Data

* [ ] Create `src/post_processing/export/touchstone_export.py` for .s2p/.s4p Touchstone format
* [ ] Implement HDF5 export for field data with hierarchical organization and compression
* [ ] Create `src/post_processing/export/plot_export.py` for PDF/PNG/SVG plot exports
* [ ] Implement Touchstone and HDF5 import with validation of imported data integrity
* [ ] Write tests in `tests/integration/test_data_io.py`

## CHARACTERISTIC INFORMATION

* Goal in Context: Persist simulation results to standard file formats for sharing, archival, and comparison with other tools.
* Scope: Touchstone S-parameter export, HDF5 field data export, plot export (PDF/PNG), data import from both formats.
* Level: File I/O operation; extensions handle batch export and partial imports.
* Preconditions: Simulation results exist in memory (S-parameters, fields, metrics).
* Success End Condition: Data is written to or read from disk in valid format with metadata intact.
* Failed End Condition: I/O error or file corruption detected; `SolverError` raised with diagnostics.
* Primary Actor: User or automated pipeline managing simulation data.
* Trigger: User requests export/import via CLI, config file, or API call.

### MAIN SUCCESS SCENARIO

1. System receives export request with format (Touchstone/HDF5/PDF) and output path.
2. For Touchstone: S-parameter matrix is formatted per RFC/S-Param specification; frequency vector stored.
3. For HDF5: Field data is organized hierarchically (near_field, far_field, geometry) with compression.
4. For plots: Matplotlib figures are rendered at user-specified resolution and layout.
5. File metadata (date, version, simulation parameters) is included in exported files.
6. System validates written file by performing a read-back and comparing data integrity.
7. User receives confirmation with file path and size.

### EXTENSIONS

2a. Multi-port Touchstone (>4 ports) : System writes .sNp format; warns about compatibility with older tools.
3a. Large field dataset : System uses HDF5 chunking and compression (gzip/lz4); reports compression ratio.
6a. Import from external file : System validates format compliance before loading; flags non-standard extensions.

### SUB-VARIATIONS

2 : Touchstone supports 1-port through N-port; formats: R (real), M (mag/phase), DB (decibel/angle).
3 : HDF5 datasets can be compressed with different algorithms (none, gzip, lzf, szip); user chooses trade-off.

### RELATED INFORMATION (optional)

* Priority: High — data portability is essential for open-source ecosystem integration.
* Performance Target: Export 10k frequency points of S-parameters in under 2 seconds.
* Frequency: Medium — used after each simulation or batch run.

---

# Use Case 10: Run End-to-End Simulation Workflow with CLI Interface

* [ ] Create complete simulation workflow script integrating CAD → Solver → Post-processing pipeline
* [ ] Implement command-line argument parser with interactive mode support
* [ ] Support configuration file-based workflow definition (YAML/JSON)
* [ ] Implement batch processing capabilities and progress reporting
* [ ] Write integration tests in `tests/integration/test_cad_pipeline.py` and `test_mom_solver.py`

## CHARACTERISTIC INFORMATION

* Goal in Context: Provide a streamlined, reproducible simulation workflow from geometry import to results export.
* Scope: Full pipeline orchestration, CLI interface, config file support, batch processing.
* Level: Multi-step workflow spanning all modules; extensions handle interactive mode and pipeline visualization.
* Preconditions: All module dependencies are installed; input files (geometry, config) are available.
* Success End Condition: Complete simulation produces results (S-parameters, fields, metrics, exports) without manual intervention.
* Failed End Condition: Pipeline fails at any stage; error is reported with stage context and recovery suggestions.
* Primary Actor: User running simulations via CLI or script.
* Trigger: User invokes the CLI command with input file paths and optional parameters.

### MAIN SUCCESS SCENARIO

1. User runs CLI command with geometry file path and optional config file.
2. System loads configuration: solver parameters, mesh settings, frequency sweep range, export options.
3. CAD module imports and validates geometry (UC1).
4. Meshing module generates and refines the surface mesh (UC2).
5. Materials, BCs, and ports are applied (UC3).
6. MoM solver assembles and solves the system matrix (UC5).
7. Field calculations produce near and far fields (UC6).
8. Antenna metrics are computed (UC8); results are exported (UC9).
9. User receives a summary report with all outputs and file paths.

### EXTENSIONS

2a. Config file is missing or invalid : System uses defaults; warns user of overridden parameters.
3a. Geometry validation fails : Pipeline aborts; user is prompted for corrected geometry or repair options.
4a. Meshing produces poor-quality elements : User can adjust mesh parameters and re-run without restarting pipeline.
6a. Solver does not converge : Pipeline logs convergence history; suggests preconditioner changes or mesh refinement.

### SUB-VARIATIONS

1 : CLI supports both interactive mode (prompting for missing params) and non-interactive batch mode.
2 : Config file can define multiple simulation scenarios in a single run for batch processing.

### RELATED INFORMATION (optional)

* Priority: Critical — this is the user-facing entry point for the entire application.
* Performance Target: Run a complete dipole antenna simulation from STEP to Touchstone export in under 5 minutes.
* Frequency: Very high — primary interaction mode for all users.

---

# Use Case 11: Execute Comprehensive Test Suite with Regression Testing

* [ ] Create comprehensive unit test suite covering all modules (see individual phase tests)
* [ ] Implement integration tests for full workflows and data I/O round-trips
* [ ] Create regression baseline tests for known analytical solutions (dipole, patch, loop antennas)
* [ ] Ensure >90% code coverage across all modules with pytest-cov
* [ ] Set up CI pipeline for automated testing on every commit

## CHARACTERISTIC INFORMATION

* Goal in Context: Maintain software quality by systematically testing all components and preventing regressions.
* Scope: Unit tests, integration tests, regression tests, coverage analysis, CI setup.
* Level: Entire codebase; each test targets specific functionality.
* Preconditions: Code is compiled/installed; test fixtures (sample files, analytical solutions) are in place.
* Success End Condition: All tests pass; coverage exceeds 90%; no regressions detected against baselines.
* Failed End Condition: Any test fails; failure is reported with stack trace and diagnostics.
* Primary Actor: Developer or CI system.
* Trigger: Code change, pre-release validation, or scheduled CI run.

### MAIN SUCCESS SCENARIO

1. System discovers all test files in the tests/ directory hierarchy.
2. Unit tests are executed first (fastest feedback); each module's tests run independently.
3. Integration tests execute against full workflows with sample geometries.
4. Regression tests compare results against stored baselines; deviations >5% trigger warnings.
5. Coverage report is generated showing per-file and aggregate percentages.
6. Results are compiled into a test summary with pass/fail counts, coverage %, and regression status.

### EXTENSIONS

2a. Specific test module requested : System runs only the specified tests using pytest markers.
4a. Regression deviation detected : System generates a diff report showing old vs. new results; flags for review.

### SUB-VARIATIONS

1 : Tests can be filtered by category (unit, integration, benchmark) and tags (slow, gpu-required).
5 : Coverage can be reported per-file, per-function, or as a single aggregate percentage.

### RELATED INFORMATION (optional)

* Priority: Critical — quality assurance for scientific computing software.
* Performance Target: Run full test suite in under 10 minutes on CI hardware.
* Frequency: Very high — every commit triggers tests; pre-release runs are exhaustive.

---

# Use Case 12: Generate Documentation and Tutorials

* [ ] Create comprehensive user manual with installation, quick start, feature descriptions, troubleshooting
* [ ] Generate API documentation using Sphinx or similar tool for all public modules
* [ ] Create tutorial examples: simple (dipole), intermediate (patch), advanced (complex assembly)
* [ ] Document file format specifications (STEP, Touchstone, HDF5) and configuration schema
* [ ] Add inline code comments and docstrings throughout the codebase

## CHARACTERISTIC INFORMATION

* Goal in Context: Enable users to install, use, and extend the software through clear documentation.
* Scope: User manual, API docs, tutorials, file format specs, configuration documentation.
* Level: Documentation project; each document targets a different audience (end-user, developer, integrator).
* Preconditions: Code is stable enough for documentation generation; examples are runnable.
* Success End Condition: All documented features have corresponding descriptions and working examples.
* Failed End Condition: Documentation generation fails (e.g., Sphinx error); incomplete docs are flagged.
* Primary Actor: Technical writer or developer producing documentation.
* Trigger: Pre-release milestone or major feature completion.

### MAIN SUCCESS SCENARIO

1. System extracts docstrings from all public modules and classes.
2. Sphinx generates API reference pages with class hierarchies, method signatures, and parameter types.
3. User manual is assembled with installation guide, quick start tutorial, feature descriptions, troubleshooting FAQ.
4. Tutorial scripts are created with step-by-step instructions and expected output validation.
5. File format specifications document structure, fields, and compatibility notes.
6. All documentation is built into HTML and PDF formats for distribution.

### EXTENSIONS

2a. API docs include code examples : Each method shows a usage snippet in the generated reference.
3a. User manual includes screenshots : Diagrams are generated from example simulations showing field plots.

### SUB-VARIATIONS

1 : Sphinx can generate both HTML (for web) and LaTeX/PDF (for print distribution).
4 : Tutorials are runnable as standalone scripts; they validate output against expected values automatically.

### RELATED INFORMATION (optional)

* Priority: High — documentation is essential for open-source adoption and maintainability.
* Performance Target: Build full docs in under 2 minutes.
* Frequency: Low to medium — updated per release or major feature addition.

---

# Use Case 13: Prepare Release Packages and Landing Page

* [ ] Create installation packages for Linux (deb, rpm), macOS (dmg), Windows (msi)
* [ ] Verify cross-platform compatibility and generate platform-specific installers
* [ ] Create comprehensive release notes with feature list, bug fixes, known limitations
* [ ] Set up GitHub/GitLab repository with CI/CD, issue templates, contribution guidelines
* [ ] Create project landing page with overview, screenshots, quick start, documentation links

## CHARACTERISTIC INFORMATION

* Goal in Context: Distribute the software to end users through official channels with professional packaging.
* Scope: Platform-specific installers, release notes, repository setup, landing page.
* Level: Release engineering; extensions handle automated distribution and version management.
* Preconditions: Software passes all tests (UC11); documentation is complete (UC12).
* Success End Condition: Packages install successfully on all target platforms; repository is publicly accessible.
* Failed End Condition: Package build fails on any platform; release is postponed until fixed.
* Primary Actor: Release engineer or project maintainer.
* Trigger: Milestone completion or scheduled release cycle.

### MAIN SUCCESS SCENARIO

1. System builds source distribution (sdist) and wheel packages using Python packaging tools.
2. Platform-specific installers are generated: .deb/.rpm for Linux, .dmg for macOS, .msi for Windows.
3. Each package is tested on a clean VM/container for that platform; installation and basic usage verified.
4. Release notes are compiled listing all features, fixes, known issues, and upgrade instructions.
5. Repository is configured with branches (main/develop), CI/CD pipeline, issue templates, contribution guidelines.
6. Landing page is published with project overview, installation instructions, screenshots, documentation links.

### EXTENSIONS

2a. Containerized distribution : System also generates Docker images for each platform variant.
4a. Semantic versioning bump : Version number is incremented following MAJOR.MINOR.PATCH rules; changelog updated.

### SUB-VARIATIONS

1 : Packages can include bundled dependencies or require system-level libraries (OpenCASCADE, CGAL, PETSc).
5 : CI/CD automatically publishes packages to PyPI and platform package repositories on tag creation.

### RELATED INFORMATION (optional)

* Priority: High — release engineering is the bridge between development and user adoption.
* Performance Target: Build and test all platform packages in under 30 minutes.
* Frequency: Low — per release cycle (every 6-12 months for major versions).

---

# Use Case 14: Support Advanced Materials (Dispersive and Anisotropic)

* [ ] Create `src/cad/materials/dispersive_materials.py` with Debye/Cole-Cole/Drude/Lorentz models
* [ ] Extend material database to support anisotropic permittivity/permeability tensors
* [ ] Update solver to handle frequency-dependent and anisotropic material properties
* [ ] Create test cases validating dispersive and anisotropic material simulations
* [ ] Document dispersion model usage, limitations, and parameter ranges

## CHARACTERISTIC INFORMATION

* Goal in Context: Model complex electromagnetic materials whose properties vary with frequency or direction.
* Scope: Dispersive models (Debye/Cole-Cole/Drude/Lorentz), anisotropic tensor materials, solver integration.
* Level: Material property extension; extensions handle multi-dispersion models and spatially-varying properties.
* Preconditions: Base material database is implemented (UC3); solver supports frequency sweeps.
* Success End Condition: Simulations with dispersive/anisotropic materials produce physically accurate results matching literature.
* Failed End Condition: Material parameters are invalid for the model; `CADError` raised with parameter diagnostics.
* Primary Actor: RF engineer modeling realistic antenna substrates or metamaterials.
* Trigger: User specifies frequency-dependent or anisotropic material in configuration.

### MAIN SUCCESS SCENARIO

1. System loads dispersive material parameters (resonance frequencies, strengths, damping coefficients).
2. Material properties are interpolated at each simulation frequency point using the selected dispersion model.
3. For anisotropic materials, permittivity/permeability tensors are constructed from user-specified components.
4. Solver uses the frequency-dependent tensor properties when assembling the MoM matrix.
5. Results account for material dispersion effects (loss tangent variation, phase velocity changes).

### EXTENSIONS

1a. Multiple dispersion models combined : System sums contributions from Debye, Lorentz, and Drude terms.
3a. Spatially-varying anisotropy : Material tensor varies by position in the geometry; interpolation is used.

### SUB-VARIATIONS

2 : Interpolation uses analytical formulas for dispersion models; no numerical integration required at runtime.
4 : Anisotropic solver adds off-diagonal terms to the impedance matrix.

### RELATED INFORMATION (optional)

* Priority: Medium — advanced materials are needed for specialized applications (substrates, metamaterials).
* Performance Target: Interpolate dispersive properties across 100 frequency points in under 5 seconds.
* Frequency: Low to medium — used for specific material types.

---

# Use Case 15: Scale Solver with MPI Parallelization and GPU Acceleration

* [ ] Implement MPI domain decomposition strategy for mesh distribution across ranks
* [ ] Add parallel matrix assembly support via PETSc's distributed matrices
* [ ] Create `src/core/gpu_acceleration/` directory with CUDA/OpenCL kernels for matrix operations
* [ ] Implement hybrid CPU-GPU solver architecture with data transfer management
* [ ] Write benchmarks comparing serial, MPI-parallel, and GPU-accelerated performance

## CHARACTERISTIC INFORMATION

* Goal in Context: Scale the MoM solver to large problems using parallel computing on clusters and GPUs.
* Scope: MPI domain decomposition, parallel assembly/solve, CUDA/OpenCL GPU kernels, hybrid CPU-GPU architecture.
* Level: Performance optimization; extensions handle multi-node scaling and adaptive load balancing.
* Preconditions: Serial solver is validated (UC5); MPI and CUDA/OpenCL runtimes are available.
* Success End Condition: Solver produces identical results to serial version with improved wall-clock time.
* Failed End Condition: Parallel/GPU execution fails; fallback to serial mode with warning.
* Primary Actor: High-performance computing user or automated scaling study.
* Trigger: User requests parallel run via CLI flag or configuration.

### MAIN SUCCESS SCENARIO

1. System initializes MPI communicator and determines the number of available ranks.
2. Mesh triangles are distributed across ranks using domain decomposition (spatial partitioning).
3. Each rank assembles its local matrix blocks; PETSc handles inter-rank communication for off-diagonal terms.
4. Parallel linear solver (PETSc KSP) solves the distributed system.
5. Results are collected from all ranks and combined into the global solution vector.
6. GPU-accelerated kernels are invoked for matrix-vector multiplication and Green's function evaluation.

### EXTENSIONS

2a. Adaptive load balancing : System redistributes mesh elements if rank workloads are uneven.
4a. Multi-node MPI run : System uses InfiniBand or Ethernet for inter-node communication; reports scaling efficiency.
6a. GPU fallback : If GPU is unavailable, system transparently uses CPU kernels without user intervention.

### SUB-VARIATIONS

3 : Domain decomposition can be spatial (geometric partitioning) or modal (basis function partitioning).
5 : Scaling speedup is reported as a function of rank count and problem size.

### RELATED INFORMATION (optional)

* Priority: Medium to High — scaling is essential for production-level antenna simulations.
* Performance Target: Achieve 80% parallel efficiency at 64 MPI ranks for a 1M-unknown problem.
* Frequency: Medium — used by HPC users and scaling studies.

---

# Use Case 16: Accelerate Matrix Assembly with Fast Multipole Method (FMM/MLFMA)

* [ ] Create `src/core/fmm/` directory with multipole and local expansion calculations
* [ ] Implement FMM kernel for matrix-vector multiplication reducing O(N²) to O(N log N) or O(N)
* [ ] Extend to multilevel FMM (MLFMA) with hierarchical clustering of triangles
* [ ] Benchmark MLFMA vs. direct MoM for large problems; validate accuracy
* [ ] Document FMM implementation details and parameter tuning

## CHARACTERISTIC INFORMATION

* Goal in Context: Reduce computational complexity of MoM matrix assembly and solve for electrically large structures.
* Scope: FMM kernel, MLFMA hierarchy, matrix-vector multiplication acceleration, accuracy validation.
* Level: Algorithmic optimization; extensions handle adaptive multipole order and hybrid FMM-MoM coupling.
* Preconditions: Serial solver is validated (UC5); problem size exceeds practical limits for O(N²) assembly.
* Success End Condition: MLFMA solution matches direct MoM within specified tolerance with significantly reduced computation time.
* Failed End Condition: FMM clustering fails or accuracy degrades; fallback to direct MoM with warning.
* Primary Actor: Solver engine (automated detection of large problems).
* Trigger: Problem size exceeds configurable threshold (e.g., >50k unknowns).

### MAIN SUCCESS SCENARIO

1. System detects large problem size and switches to MLFMA mode automatically (or via user flag).
2. Triangles are hierarchically clustered using a bounding box tree at multiple levels.
3. Multipole expansions are computed for each cluster; translations operators map between levels.
4. Matrix-vector multiplication uses FMM kernel: O(N log N) per iteration instead of O(N²).
5. MLFMA results are compared against direct MoM on a subset to validate accuracy.
6. Solution quality is reported with FMM error estimate and computational speedup factor.

### EXTENSIONS

1a. User forces direct MoM : System respects user override even for large problems; warns about performance impact.
3a. Adaptive multipole order : System adjusts P (order of expansion) based on cluster size and frequency.

### SUB-VARIATIONS

4 : FMM can be applied to impedance matrix-vector products or to the Green's function evaluation phase.
5 : Accuracy validation uses relative error norm ||x_MLFMA - x_direct|| / ||x_direct||.

### RELATED INFORMATION (optional)

* Priority: Medium — essential for solving real-world electrically large antenna problems.
* Performance Target: Solve a 1M-unknown problem in under 1 hour on a single node with MLFMA.
* Frequency: Low to medium — used when problem size warrants it.

---

# Use Case 17: Run Hybrid MoM-FEM Simulation for Complex Substrates

* [ ] Implement domain decomposition for hybrid MoM-FEM method
* [ ] Define interface coupling between MoM (open region) and FEM (dielectric volume) regions
* [ ] Implement material property handling at MoM-FEM interfaces
* [ ] Create test cases with dielectric substrates; validate against pure MoM and commercial solvers
* [ ] Benchmark hybrid solver performance vs. pure MoM

## CHARACTERISTIC INFORMATION

* Goal in Context: Simulate antennas on complex dielectric substrates by coupling surface integral method (MoM) with volume integral method (FEM).
* Scope: Domain decomposition, MoM-FEM interface coupling, dielectric material handling, validation.
* Level: Hybrid simulation; extensions handle multi-interface problems and adaptive FEM mesh refinement.
* Preconditions: MoM solver is validated (UC5); FEM library is available for volume discretization.
* Success End Condition: Hybrid solution matches commercial solver results within 5% tolerance for dielectric antenna problems.
* Failed End Condition: Interface coupling diverges; `SolverError` raised with conditioning diagnostics.
* Primary Actor: RF engineer simulating microstrip antennas or packaged devices.
* Trigger: User specifies a dielectric substrate geometry that requires volume discretization.

### MAIN SUCCESS SCENARIO

1. System decomposes the problem domain into MoM region (surfaces in free space) and FEM region (dielectric volumes).
2. Interface boundary is identified where MoM surfaces meet FEM volumes.
3. Continuity conditions (tangential E and H fields) are enforced at the interface via coupling matrix.
4. MoM and FEM subsystems are assembled separately; interface terms are added to couple them.
5. Combined linear system is solved using the parallel solver (UC15).
6. Results from both regions are combined into a unified field solution.

### EXTENSIONS

2a. Multiple dielectric volumes : System creates multiple FEM regions with separate interface boundaries.
4a. Adaptive FEM refinement : Mesh is refined in high-gradient regions near interfaces automatically.

### SUB-VARIATIONS

3 : Coupling can be weak (Nitscha-type) or strong (Lagrange multiplier); user chooses formulation.
5 : Hybrid solve may require iterative coupling between MoM and FEM subsystems.

### RELATED INFORMATION (optional)

* Priority: Medium — needed for realistic antenna-on-substrate simulations.
* Performance Target: Solve a hybrid MoM-FEM problem with 10k MoM unknowns and 5k FEM elements in under 5 minutes.
* Frequency: Low — specialized use case for substrate-integrated antennas.

---

# Use Case 18: Perform Convergence Studies and Validation Against Literature

* [ ] Implement mesh refinement studies: error vs. mesh density plots
* [ ] Implement frequency sampling studies: error vs. frequency step size
* [ ] Implement solver parameter optimization studies: tolerance, preconditioner type, iteration limits
* [ ] Select published benchmark problems from IEEE literature; replicate geometries and compare results
* [ ] Document convergence behavior and provide guidelines for mesh/frequency selection

## CHARACTERISTIC INFORMATION

* Goal in Context: Systematically validate numerical accuracy and provide users with best-practice recommendations.
* Scope: Mesh convergence, frequency sampling, solver parameter studies, published benchmark replication.
* Level: Validation project; each study targets a specific source of numerical error.
* Preconditions: Solver is validated on simple geometries (UC4); literature benchmark data is available.
* Success End Condition: Convergence rates match theoretical expectations; benchmark results agree within tolerance.
* Failed End Condition: Convergence is not observed or benchmark deviation exceeds acceptable threshold.
* Primary Actor: Validation engineer or automated CI job.
* Trigger: Pre-release validation milestone or research publication requirement.

### MAIN SUCCESS SCENARIO

1. System runs a series of simulations with systematically refined mesh densities (coarse to fine).
2. Error is computed against an analytical or highly-refined reference solution at each mesh level.
3. Convergence plot (error vs. DOF) is generated showing expected O(h^p) behavior.
4. Frequency sampling study varies frequency step size; error is tracked for resonant features.
5. Published benchmark problems (dipole, patch, slot antenna from IEEE Trans. Antennas Propag.) are replicated.
6. Results are compared against published data; discrepancies are documented and analyzed.

### EXTENSIONS

1a. Adaptive mesh refinement : System automatically refines regions with high error estimates.
5a. Multiple benchmark problems : System runs all selected benchmarks and aggregates results into a validation report.

### SUB-VARIATIONS

2 : Error can be measured in field magnitude, S-parameter, or far-field pattern norm.
5 : Benchmarks should include geometry CAD files and published numerical results for reproducibility.

### RELATED INFORMATION (optional)

* Priority: High — academic credibility depends on validated accuracy against established literature.
* Performance Target: Complete a full convergence study (5 mesh levels × 3 frequencies) in under 2 hours.
* Frequency: Low — typically performed at release milestones or when new features are added.

---

# Use Case 19: Manage Version History and Community Feedback

* [ ] Implement semantic versioning workflow (MAJOR.MINOR.PATCH) with changelog automation
* [ ] Monitor user feedback channels (GitHub issues, forums, email) for bug reports and feature requests
* [ ] Prioritize improvements based on impact assessment and community demand
* [ ] Maintain backward compatibility documentation and migration guides for breaking changes

## CHARACTERISTIC INFORMATION

* Goal in Context: Manage the long-term evolution of the project through structured versioning and community engagement.
* Scope: Version management, changelog automation, feedback triage, migration guides.
* Level: Project governance; extensions handle automated release pipelines and community contribution workflows.
* Preconditions: Software is released (UC13); user community is active.
* Success End Condition: Versions are clearly tracked; community feedback is systematically addressed.
* Failed End Condition: Feedback channels go unmonitored; version history becomes unclear or inconsistent.
* Primary Actor: Project maintainers and community managers.
* Trigger: Ongoing project lifecycle — continuous activity between releases.

### MAIN SUCCESS SCENARIO

1. System tracks all changes in a structured changelog (breaking features, new features, bug fixes).
2. Version number is incremented according to semantic versioning rules on release.
3. User feedback is collected from GitHub issues, forums, and direct communications.
4. Issues are triaged by severity and impact; feature requests are prioritized by community votes or maintainer assessment.
5. Migration guides are written for any breaking changes in the changelog.
6. Backward compatibility is maintained where possible; deprecation warnings are issued for removed features.

### EXTENSIONS

1a. Automated changelog generation : System parses commit messages and generates changelog entries automatically.
3a. Community contribution workflow : External contributors submit pull requests following contribution guidelines.

### SUB-VARIATIONS

2 : MAJOR bump for breaking API changes, MINOR for new features, PATCH for bug fixes.
5 : Migration guides include code examples showing old vs. new API usage.

### RELATED INFORMATION (optional)

* Priority: Medium — essential for sustainable open-source project health.
* Performance Target: Respond to critical issues within 48 hours; triage all issues within 1 week.
* Frequency: Continuous — ongoing activity throughout the project lifecycle.

---

# Use Case 20: Optimize Solver Performance and Memory Management

* [ ] Profile solver to identify bottlenecks in matrix assembly, Green's function evaluation, and solve phases
* [ ] Implement caching for static matrix elements that don't change with frequency
* [ ] Optimize memory access patterns and implement out-of-core computation for large problems
* [ ] Create memory monitoring and reporting tools; benchmark optimization improvements
* [ ] Document performance characteristics and tuning recommendations

## CHARACTERISTIC INFORMATION

* Goal in Context: Maximize computational efficiency to handle the largest possible antenna simulations within available resources.
* Scope: Profiling, caching strategies, memory optimization, out-of-core computation, performance documentation.
* Level: Performance engineering; extensions handle automatic parameter tuning and hardware-specific optimizations.
* Preconditions: Baseline solver is functional (UC5); profiling tools are available.
* Success End Target: 2-5x speedup over baseline for typical problem sizes; memory usage reduced by 30%+.
* Failed End Condition: Optimization introduces correctness bugs; performance regression detected.
* Primary Actor: Performance engineer or automated profiling job.
* Trigger: Identified performance bottleneck or pre-release optimization phase.

### MAIN SUCCESS SCENARIO

1. System profiles the solver to identify hotspots in matrix assembly, Green's function, and linear solve phases.
2. Static matrix elements (geometric terms independent of frequency) are cached and reused across frequency sweeps.
3. Memory access patterns are optimized: data is laid out for cache-friendly traversal (SoA vs AoS).
4. Out-of-core computation streams large matrices to disk when RAM is insufficient.
5. Memory monitoring tracks allocation/deallocation; leaks are reported and fixed.
6. Performance benchmarks compare pre/post optimization; speedup and memory reduction are quantified.

### EXTENSIONS

2a. Cache invalidation strategy : Cached elements are invalidated when geometry or frequency range changes.
4a. GPU out-of-core : Large problems are split across CPU and GPU with PCIe bandwidth as the bottleneck.

### SUB-VARIATIONS

3 : SoA (Structure of Arrays) layout improves vectorization; AoS may be better for object-oriented access patterns.
5 : Memory monitoring can integrate with system-level tools (valgrind, perf, NVIDIA Nsight).

### RELATED INFORMATION (optional)

* Priority: Medium to High — performance directly impacts practical usability for large problems.
* Performance Target: Achieve 2x speedup and 30% memory reduction within one optimization cycle.
* Frequency: Low to medium — performed during development sprints or pre-release phases.

---

# Use Case 21: Configure Simulation Parameters via Config File and CLI

* [ ] Implement YAML/JSON configuration schema validation for solver, mesh, BC, and I/O parameters
* [ ] Support environment variable overrides for CI/CD and containerized deployments
* [ ] Create default configuration templates for common antenna types (dipole, patch, loop)
* [ ] Document all configurable parameters with recommended values and constraints
* [ ] Implement CLI argument parser that merges with config file settings

## CHARACTERISTIC INFORMATION

* Goal in Context: Provide flexible, reproducible simulation configuration through files and command-line arguments.
* Scope: Config schema, environment variable overrides, default templates, CLI argument parsing, documentation.
* Level: Configuration management; extensions handle schema versioning and migration of old configs.
* Preconditions: All modules support configurable parameters (defined in their respective use cases).
* Success End Condition: Valid configuration is loaded with all parameters resolved; defaults applied for unspecified values.
* Failed End Condition: Config file fails validation; error reports missing or invalid fields with suggestions.
* Primary Actor: User or automated pipeline setting up a simulation.
* Trigger: User provides config file and/or CLI arguments before starting simulation.

### MAIN SUCCESS SCENARIO

1. System loads configuration from YAML/JSON file (if specified).
2. Schema validation checks all required fields, types, ranges, and cross-parameter consistency.
3. Environment variables override config file values where applicable (e.g., MPI rank count, output directory).
4. CLI arguments are parsed and merged; CLI takes precedence over config file and environment variables.
5. Default values are applied for any unspecified parameters based on the antenna type template.
6. Final configuration is logged and available to all modules in the pipeline.

### EXTENSIONS

1a. Config file not found : System uses built-in defaults; warns user of missing configuration.
2a. Schema version mismatch : System attempts auto-migration; if that fails, reports incompatibility with version info.

### SUB-VARIATIONS

3 : Environment variables use a naming convention (e.g., DETAGRANDMERE_SOLVER_TOLERANCE).
5 : Templates include dipole (default PEC, 1 port), patch (FR4 substrate, microstrip feed), loop (circular conductor).

### RELATED INFORMATION (optional)

* Priority: High — configuration is the bridge between user intent and solver behavior.
* Performance Target: Validate and load a config file in under 1 second.
* Frequency: Very high — every simulation run loads configuration.

---

# Use Case 22: Run Multi-Port Excitation and Mutual Coupling Analysis

* [ ] Extend port system to support N-port excitation with independent power distribution
* [ ] Implement mutual coupling matrix computation between all port pairs
* [ ] Compute full N×N S-parameter matrix for all port combinations across frequency sweep
* [ ] Create test cases with multi-port antennas (dipole arrays, patch antenna arrays)
* [ ] Validate multi-port results against analytical array factor models

## CHARACTERISTIC INFORMATION

* Goal in Context: Analyze antenna arrays and multi-port systems where ports interact through mutual coupling.
* Scope: Multi-port excitation, mutual coupling matrix, full N-port S-parameter computation, validation.
* Level: Full multi-port simulation; extensions handle adaptive port selection and coupled-mode analysis.
* Preconditions: Single-port solver is validated (UC4); port definitions support multiple ports (UC3).
* Success End Condition: Full N-port S-matrix is computed with accurate mutual coupling effects captured.
* Failed End Condition: Coupling matrix is ill-conditioned; `SolverError` raised with conditioning diagnostics.
* Primary Actor: RF engineer designing antenna arrays or multi-feed systems.
* Trigger: User defines multiple ports and requests array simulation.

### MAIN SUCCESS SCENARIO

1. System initializes all N ports with individual excitation amplitudes and phases.
2. For each frequency point, system solves the MoM system with port 1 excited (others terminated).
3. S-parameters are extracted for all N×N combinations (reflection at each port + transmission to all others).
4. Mutual coupling matrix is computed showing how energy couples between adjacent ports.
5. Array factor analysis compares simulated results with theoretical array factor predictions.
6. Results include full S-matrix, coupling coefficients, and array performance metrics.

### EXTENSIONS

2a. Adaptive excitation : System automatically sweeps phase shifts to find optimal beam direction.
4a. Coupling threshold filtering : Weakly coupled port pairs are flagged for potential decoupling techniques.

### SUB-VARIATIONS

3 : Full N-port matrix requires N separate solves per frequency point (or one solve with multiple excitations).
5 : Array factor comparison validates element spacing, phasing, and mutual coupling effects.

### RELATED INFORMATION (optional)

* Priority: Medium to High — essential for array antenna design and MIMO system analysis.
* Performance Target: Compute 4×4 S-matrix at 100 frequencies in under 5 minutes (serial).
* Frequency: Medium — used for array and multi-port antenna designs.

---

# Use Case 23: Implement Continuous Improvement and Quality Monitoring

* [ ] Monitor performance benchmarks over time; track regression trends
* [ ] Identify optimization opportunities through profiling on production workloads
* [ ] Maintain dependencies up to date with security vulnerability scanning
* [ ] Improve test coverage incrementally toward 100% target
* [ ] Enhance documentation and tutorials based on user questions and support tickets

## CHARACTERISTIC INFORMATION

* Goal in Context: Ensure long-term software quality, performance, and maintainability through continuous monitoring.
* Scope: Performance monitoring, dependency management, security scanning, test coverage improvement, documentation updates.
* Level: Continuous improvement program; extensions handle automated alerts and CI-gated releases.
* Preconditions: Software is released and in use (UC13); monitoring infrastructure is set up.
* Success End Condition: Performance trends are stable or improving; dependencies are current; coverage exceeds 95%.
* Failed End Condition: Undetected regressions reach production; security vulnerabilities remain unpatched.
* Primary Actor: Maintainer team and automated monitoring systems.
* Trigger: Continuous — ongoing activity between releases.

### MAIN SUCCESS SCENARIO

1. System runs scheduled benchmark suites and compares results against historical baselines.
2. Performance degradation alerts are triggered if metrics exceed defined thresholds (e.g., 10% slowdown).
3. Dependencies are scanned for security vulnerabilities using automated tools (pip-audit, Dependabot).
4. Test coverage is tracked; gaps are identified and filled with targeted tests.
5. User feedback from support tickets is analyzed to identify documentation gaps and improve tutorials.

### EXTENSIONS

1a. Automated regression alerts : System opens GitHub issues when benchmarks regress beyond thresholds.
3a. Dependency update automation : System automatically creates PRs for dependency updates; maintainers review.

### SUB-VARIATIONS

2 : Alerts can be configured per-metric (assembly time, solve time, memory usage) with different thresholds.
4 : Coverage gaps are identified by analyzing which code paths are not exercised by existing tests.

### RELATED INFORMATION (optional)

* Priority: Medium — essential for long-term project health and user trust.
* Performance Target: Run monitoring jobs weekly; respond to alerts within 1 week.
* Frequency: Continuous — ongoing throughout the project lifecycle.

---

## Coverage Verification Checklist

| Use Case | Implementation Steps | Test Steps | Status |
|----------|---------------------|------------|--------|
| UC1: Import CAD | 6 steps | 3 test items | ☐ |
| UC2: Mesh Generation | 8 steps | 4 test items | ☐ |
| UC3: Materials/BCs/Ports | 7 steps | 3 test items | ☐ |
| UC4: S-Parameters | 7 steps | 3 test items | ☐ |
| UC5: MoM Solver | 7 steps | 5 test files | ☐ |
| UC6: Field Calculations | 7 steps | 2 test items | ☐ |
| UC7: Visualization | 7 steps | 2 test items | ☐ |
| UC8: Antenna Metrics | 6 steps | 3 test items | ☐ |
| UC9: Data Export/Import | 7 steps | 2 test items | ☐ |
| UC10: End-to-End Workflow | 9 steps | 3 test items | ☐ |
| UC11: Test Suite & Regression | 6 steps | CI setup | ☐ |
| UC12: Documentation | 6 steps | Build verification | ☐ |
| UC13: Release Packaging | 6 steps | Cross-platform tests | ☐ |
| UC14: Advanced Materials | 5 steps | 3 test items | ☐ |
| UC15: MPI/GPU Scaling | 6 steps | Benchmark suite | ☐ |
| UC16: FMM/MLFMA | 6 steps | Accuracy validation | ☐ |
| UC17: Hybrid MoM-FEM | 6 steps | 2 test items | ☐ |
| UC18: Convergence Studies | 6 steps | Benchmark replication | ☐ |
| UC19: Version & Feedback | 6 steps | Triage workflow | ☐ |
| UC20: Performance Optimization | 6 steps | Pre/post benchmarks | ☐ |
| UC21: Configuration | 6 steps | Schema validation tests | ☐ |
| UC22: Multi-Port Analysis | 6 steps | Array factor validation | ☐ |
| UC23: Continuous Improvement | 5 steps | Monitoring dashboards | ☐ |

**Total use cases: 23 | Total implementation steps: ~140+ | Total test items: ~50+**

All 23 phases from the granular implementation plan are mapped to concrete use cases with actionable checklist items. Every task group (tasks 0.x through 23.x) has at least one corresponding use case, and all features from the cross-reference matrix are covered.
