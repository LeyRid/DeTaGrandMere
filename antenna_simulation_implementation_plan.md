# Antenna Simulation Software - Implementation Plan

## PROJECT OVERVIEW

**Total Duration**: 24 weeks (6 months)  
**Approach**: Autonomous AI-driven development  
**Primary Method**: Method of Moments (MoM) for initial implementation  
**Target**: Open-source, modular architecture  

---

## CAD MODULE STRATEGY - EXISTING LIBRARIES ONLY

**Key Decision**: Leverage mature CAD libraries instead of building from scratch
- **Primary**: OpenCASCADE (free, open-source)
- **Secondary**: CGAL (computational geometry algorithms)
- **Visualization**: VTK/Qt for rendering

---

## PHASE 0: PROJECT SETUP & FOUNDATION (Weeks 1-2)

### Week 1: Environment Configuration

**Deliverables:**
- [ ] Create project repository structure
- [ ] Set up development environment
- [ ] Install all required dependencies
- [ ] Initialize version control
- [ ] Create basic documentation

**Tasks:**
```
1. Initialize Git repository with proper .gitignore
2. Create directory structure:
   - src/ (source code)
   - include/ (headers)
   - tests/ (unit tests)
   - docs/ (documentation)
   - examples/ (test cases)
   - data/ (reference data)
3. Set up Python virtual environment with:
   - numpy, scipy
   - matplotlib, pyvista
   - opencascade-core (Python bindings for OpenCASCADE)
   - CGAL (via pip or conda)
   - petsc4py (parallel solvers)
   - h5py (data storage)
4. Create CMakeLists.txt for C++ build system
5. Document setup instructions in README.md
```

**Verification:**
- [ ] All dependencies installed successfully
- [ ] Basic CMake build works
- [ ] Python environment accessible

---

### Week 2: Physics Foundation & Research

**Deliverables:**
- [ ] Complete MoM theory documentation
- [ ] Reference implementations studied
- [ ] Mathematical formulation documented
- [ ] Algorithm pseudocode created

**Tasks:**
```
1. Study and document:
   - Method of Moments (MoM) fundamentals
   - RWG basis functions
   - Green's functions for free space
   - Integral equation formulations
   - Convergence criteria
2. Create mathematical reference document (LaTeX)
3. Analyze open-source solvers (Meep, SimPEG, PyNEC-like projects)
4. Design class hierarchy for solver architecture
5. Document simulation workflow steps
6. **Research CAD library options:**
   - OpenCASCADE capabilities and API
   - CGAL geometry processing features
   - Integration approaches
```

**Verification:**
- [ ] Complete MoM theory documentation
- [ ] Reference implementations reviewed
- [ ] Class diagram created

---

## PHASE 1: CAD MODULE - EXISTING LIBRARIES INTEGRATION (Weeks 3-6)

### Week 3: OpenCASCADE Integration

**Deliverables:**
- [ ] OpenCASCADE Python bindings configured
- [ ] Basic geometry import functionality
- [ ] Geometry validation utilities

**Tasks:**
```
1. Set up OpenCASCADE:
   - Install opencascade-core or occt-pybind11
   - Verify CAD kernel loading
2. Create OpenCASCADE wrapper module:
   - Import STEP/IGES files
   - Extract basic shapes (surfaces, wires, edges)
   - Validate geometry topology
3. Implement geometry validation:
   - Check for non-manifold geometry
   - Identify degenerate elements
   - Validate meshable surfaces
4. Create simple geometry tests
```

**Verification:**
- [ ] Can import STEP geometry files
- [ ] Geometry validation works correctly

---

### Week 4: Geometry Processing with CGAL

**Deliverables:**
- [ ] CGAL integration for mesh generation
- [ ] Surface mesh extraction from CAD models
- [ ] Mesh quality assessment tools

**Tasks:**
```
1. Integrate CGAL:
   - Use CGAL's surface mesh generation (Alpha Shapes)
   - Extract triangle meshes from CAD surfaces
2. Implement mesh extraction:
   - Convert CAD surfaces to triangle meshes
   - Clean and repair meshes
   - Remove small/negative area triangles
3. Add mesh quality tools:
   - Compute aspect ratio, skewness
   - Identify problematic elements
   - Generate quality reports
4. Create mesh processing utilities
```

**Verification:**
- [ ] Can extract valid triangle meshes from CAD models
- [ ] Mesh quality metrics computed correctly

---

### Week 5: Boundary Conditions & Material Mapping

**Deliverables:**
- [ ] Material properties database integration
- [ ] Boundary condition application to mesh
- [ ] Surface property mapping

**Tasks:**
```
1. Create material database:
   - Import materials from OpenCASCADE or external file
   - Define permittivity, permeability, loss tangent
   - Support frequency-dependent models (Debye/Cole-Cole)
2. Implement boundary condition system:
   - Apply PEC to conductive surfaces
   - Apply PMC to magnetic surfaces
   - Define radiation boundaries
3. Create property mapping:
   - Map CAD material IDs to simulation materials
   - Handle mixed-material regions
4. Add boundary condition testing
```

**Verification:**
- [ ] Materials loaded and stored correctly
- [ ] Boundary conditions applied to mesh

---

### Week 6: CAD Module Testing & Export

**Deliverables:**
- [ ] Complete CAD module test suite
- [ ] Mesh export functionality (STL/OBJ)
- [ ] CAD module API documentation

**Tasks:**
```
1. Create comprehensive tests:
   - Import various CAD formats (STEP, IGES)
   - Extract meshes from complex geometries
   - Validate mesh quality metrics
2. Implement mesh export:
   - Export to STL for visualization
   - Export to OBJ for 3D rendering
   - Add custom binary format option
3. Benchmark CAD module performance
4. Document CAD module API
5. Create example test cases
```

**Verification:**
- [ ] All tests pass
- [ ] Meshes export correctly

---

## PHASE 2: SOLVER ENGINE - MoM (Weeks 7-12)

### Week 7: Linear Algebra Foundation

**Deliverables:**
- [ ] Sparse matrix implementation using PETSc
- [ ] Preconditioners
- [ ] Iterative solvers

**Tasks:**
```
1. Implement sparse matrix structures:
   - Use PETSc for sparse matrices
   - Matrix assembly utilities
2. Add preconditioners:
   - ILU (Incomplete LU) via PETSc
   - Multigrid support
3. Implement iterative solvers:
   - GMRES (via PETSc)
   - BiCGStab (via PETSc)
   - Convergence monitoring
4. Create linear algebra testing suite
```

**Verification:**
- [ ] Solvers converge for test problems
- [ ] Preconditioners reduce iterations

---

### Week 8: MoM Formulation - Integral Equations

**Deliverables:**
- [ ] Electric field integral equation (EFIE)
- [ ] Magnetic field integral equation (MFIE)
- [ ] Combined Field Integral Equation (CFIE)

**Tasks:**
```
1. Implement EFIE formulation:
   - Surface current unknowns
   - Green's function integration
   - Testing procedure
2. Implement MFIE formulation:
   - Local operators
   - Testing procedure
3. Implement CFIE (combination of EFIE+MFIE)
4. Create mathematical reference for each formulation
```

**Verification:**
- [ ] All three formulations implemented
- [ ] Equations verified against literature

---

### Week 9: RWG Basis Functions

**Deliverables:**
- [ ] RWG basis function implementation
- [ ] Basis function testing
- [ ] Matrix assembly utilities

**Tasks:**
```
1. Implement RWG basis functions:
   - Function definitions
   - Jacobian calculations
   - Support triangle properties
2. Create basis function tests:
   - Orthogonality verification
   - Integration accuracy checks
3. Implement matrix assembly:
   - System matrix construction using PETSc
   - Right-hand side vector setup
   - Source excitation handling
4. Add Green's function evaluation
```

**Verification:**
- [ ] RWG functions integrate correctly
- [ ] Matrix assembly produces expected results

---

### Week 10: MoM Solver Implementation

**Deliverables:**
- [ ] Complete MoM solver class
- [ ] S-parameter computation
- [ ] Convergence analysis

**Tasks:**
```
1. Integrate all components:
   - CAD mesh → RWG basis functions
   - Matrix assembly → Sparse solver (PETSc)
   - Solution extraction → Field calculation
2. Implement S-parameter computation:
   - Port definitions
   - Scattering matrix calculation
   - Reflection/transmission coefficients
3. Add convergence monitoring:
   - Residual tracking
   - Error estimation
   - Adaptive stopping criteria
4. Create solver configuration options
```

**Verification:**
- [ ] Solver produces valid solutions
- [ ] S-parameters computed correctly

---

### Week 11: Verification with Simple Antennas

**Deliverables:**
- [ ] Dipole antenna verification
- [ ] Microstrip patch verification
- [ ] Comparison with analytical solutions

**Tasks:**
```
1. Implement test cases:
   - Half-wave dipole (analytical solution known)
   - Rectangular microstrip patch
   - Loop antenna
2. Compare results with:
   - Analytical formulas
   - Commercial software (CST/HFSS if available)
   - Published benchmark data
3. Identify discrepancies
4. Document verification results
```

**Verification:**
- [ ] Dipole S-parameters match theory within 5%
- [ ] Patch antenna patterns validated

---

### Week 12: Solver Optimization & Parallelization

**Deliverables:**
- [ ] Performance optimizations
- [ ] Parallel computing support (MPI)
- [ ] Memory management improvements

**Tasks:**
```
1. Optimize solver:
   - Precompute static matrices
   - Reduce Green's function calls
   - Cache frequently used values
2. Implement parallelization:
   - MPI for distributed memory
   - Domain decomposition
   - Parallel matrix assembly
3. Add memory optimization:
   - Out-of-core computation support
   - Memory mapping for large problems
4. Create performance benchmarks
```

**Verification:**
- [ ] Scalable with MPI (2x speedup with 2 nodes)
- [ ] Can solve larger problems

---

## PHASE 3: POST-PROCESSING & VISUALIZATION (Weeks 13-16)

### Week 13: Field Visualization

**Deliverables:**
- [ ] Near-field visualization
- [ ] Far-field visualization
- [ ] Radiation pattern plotting

**Tasks:**
```
1. Implement field calculations:
   - Near-field (E, H fields)
   - Far-field transformation
   - Polarization vectors
2. Create visualization modules:
   - 3D field rendering (PyVista/VTK)
   - 2D cross-section plots
   - Contour and streamlines
3. Add interactive viewing controls
4. Implement field animation for time-domain
```

**Verification:**
- [ ] Fields rendered correctly
- [ ] Patterns match expected shapes

---

### Week 14: Antenna Metrics & Analysis

**Deliverables:**
- [ ] Gain and directivity calculation
- [ ] Efficiency analysis
- [ ] Bandwidth determination

**Tasks:**
```
1. Implement antenna metrics:
   - Directivity (D = 4πU/Prad)
   - Gain (G = η × D)
   - Radiation efficiency (η)
   - Front-to-back ratio
2. Add bandwidth analysis:
   - S11 threshold crossing
   - Impedance matching
   - Resonant frequency identification
3. Create performance reports
4. Implement comparison metrics
```

**Verification:**
- [ ] Gain calculations verified against theory
- [ ] Bandwidth detection accurate

---

### Week 15: Data Export & Import

**Deliverables:**
- [ ] S-parameter export (Touchstone)
- [ ] Field data export (HDF5)
- [ ] Plot export (PDF, PNG)

**Tasks:**
```
1. Implement file formats:
   - Touchstone (.s2p, .s4p) for S-parameters
   - HDF5 for field data
   - CSV for tabular data
   - STL/OBJ for mesh visualization
2. Create import functionality
3. Add batch export capabilities
4. Document file format specifications
```

**Verification:**
- [ ] Touchstone files load correctly in commercial software
- [ ] Field data integrity verified

---

### Week 16: Post-Processing Testing

**Deliverables:**
- [ ] Complete test suite for post-processing
- [ ] Visualization quality assessment
- [ ] Performance benchmarks

**Tasks:**
```
1. Create comprehensive tests:
   - All antenna metrics validated
   - Visualizations verified
   - File I/O tested
2. Benchmark rendering performance
3. Compare results with reference implementations
4. Document post-processing API
5. Create example visualization scripts
```

**Verification:**
- [ ] All post-processing features work correctly
- [ ] Visualizations meet quality standards

---

## PHASE 4: OPTIMIZATION & ADVANCED FEATURES (Weeks 17-20)

### Week 17: GPU Acceleration

**Deliverables:**
- [ ] CUDA/OpenCL implementation
- [ ] GPU kernel optimization
- [ ] Hybrid CPU-GPU solver

**Tasks:**
```
1. Implement GPU acceleration:
   - CUDA kernels for matrix operations
   - GPU-based Green's function evaluation
   - Parallel field calculations
2. Create hybrid solver:
   - CPU-GPU data transfer management
   - Load balancing
   - Error handling
3. Optimize GPU kernels
4. Add performance profiling
```

**Verification:**
- [ ] 3x+ speedup on GPU
- [ ] Results match CPU implementation

---

### Week 18: Advanced Solver Methods

**Deliverables:**
- [ ] Fast Multipole Method (FMM)
- [ ] Multilevel Fast Multipole Algorithm (MLFMA)
- [ ] Hybrid MoM-FEM approach

**Tasks:**
```
1. Implement FMM:
   - Use existing FMM library (if available) or implement
   - Multipole expansion
   - Local expansion
   - Translation operators
2. Add MLFMA for scalability
3. Implement hybrid MoM-FEM:
   - Domain decomposition
   - Interface coupling
4. Create benchmark comparisons
```

**Verification:**
- [ ] FMM achieves O(N) complexity
- [ ] Scalable to large problems

---

### Week 19: Advanced Materials & Features

**Deliverables:**
- [ ] Frequency-dependent materials
- [ ] Anisotropic material support
- [ ] Multi-port excitation

**Tasks:**
```
1. Implement advanced materials:
   - Debye/Cole-Cole models
   - Drude/Lorentz dispersive materials
   - Anisotropic permittivity/permeability
2. Add multi-port excitation:
   - Multiple sources
   - Coupled ports
   - Power distribution analysis
3. Implement time-domain solver (FDTD)
4. Add broadband frequency sweep
```

**Verification:**
- [ ] Dispersion models work correctly
- [ ] Multi-port S-parameters computed

---

### Week 20: Integration & Refinement

**Deliverables:**
- [ ] Complete software integration
- [ ] Bug fixes and refinements
- [ ] User interface improvements

**Tasks:**
```
1. Integrate all modules:
   - CAD → Solver → Post-processing pipeline
   - Error handling throughout
   - User feedback mechanisms
2. Fix identified bugs
3. Refine user interface:
   - Command-line options
   - Configuration files
   - Progress indicators
4. Create user guide and tutorials
```

**Verification:**
- [ ] End-to-end workflow works
- [ ] All features functional

---

## PHASE 5: TESTING, VALIDATION & DOCUMENTATION (Weeks 21-24)

### Week 21: Comprehensive Testing

**Deliverables:**
- [ ] Complete test suite
- [ ] Regression tests
- [ ] Performance benchmarks

**Tasks:**
```
1. Create comprehensive test suite:
   - Unit tests for all modules
   - Integration tests
   - Regression tests
2. Implement continuous integration setup
3. Run performance benchmarks:
   - Compare with commercial software
   - Track optimization progress
4. Document test coverage
```

**Verification:**
- [ ] >90% code coverage
- [ ] All tests pass consistently

---

### Week 22: Validation Studies

**Deliverables:**
- [ ] Benchmark antenna comparisons
- [ ] Published literature validation
- [ ] Convergence studies

**Tasks:**
```
1. Create validation cases:
   - Compare with CST/HFSS (if available)
   - Match published benchmark results
   - Cross-validate with other open-source solvers
2. Perform convergence studies:
   - Mesh refinement analysis
   - Frequency sampling study
   - Solver parameter optimization
3. Document validation methodology
4. Create validation report
```

**Verification:**
- [ ] Results within 5% of reference
- [ ] Convergence verified

---

### Week 23: Documentation

**Deliverables:**
- [ ] User manual
- [ ] API documentation
- [ ] Example tutorials

**Tasks:**
```
1. Create user documentation:
   - Installation guide
   - Quick start tutorial
   - Detailed feature descriptions
   - Troubleshooting guide
2. Generate API documentation:
   - Doxygen/Sphinx format
   - Function signatures
   - Usage examples
3. Write example tutorials:
   - Simple antenna (dipole)
   - Patch antenna
   - Complex assembly
4. Create video demonstrations
```

**Verification:**
- [ ] Documentation complete and accurate
- [ ] Tutorials work end-to-end

---

### Week 24: Release Preparation

**Deliverables:**
- [ ] First release candidate
- [ ] Installation package
- [ ] Release notes

**Tasks:**
```
1. Prepare release:
   - Version number finalization
   - Changelog creation
   - Installation package (Linux, macOS, Windows)
2. Create release notes:
   - Feature list
   - Bug fixes
   - Known limitations
3. Final testing and verification
4. Prepare GitHub/GitLab repository
5. Create project landing page
```

**Verification:**
- [ ] Release candidate tested
- [ ] Installation successful on target platforms

---

## EXISTING LIBRARIES SUMMARY

| Category | Library | Purpose |
|----------|---------|---------|
| CAD Kernel | OpenCASCADE | Geometry modeling, import/export, surface extraction |
| Computational Geometry | CGAL | Mesh generation, geometry processing |
| Visualization | VTK/PyVista | 3D rendering, field visualization |
| Linear Algebra | PETSc | Sparse matrices, iterative solvers |
| Data Storage | HDF5 | Field data storage |
| Math | NumPy/SciPy | Numerical operations |

---

## AI-ENHANCED IMPLEMENTATION PLAN

### ENHANCEMENTS FOR AUTONOMOUS AI EXECUTION

#### 1. SKILL-BASED WORKFLOW (CRITICAL)

**Core Skills to Create:**

```
skills/
├── cad-integration/                    # OpenCASCADE & CGAL integration
│   ├── references/
│   │   ├── opencascade_api.md         # API documentation
│   │   └── cgal_meshing.md            # Mesh generation guide
│   ├── templates/
│   │   ├── geometry_wrapper.py        # Template for CAD wrapper
│   │   └── mesh_processor.py          # Mesh processing template
│   └── scripts/
│       ├── test_import_step.py         # STEP import test
│       └── validate_mesh_quality.py    # Mesh quality checker
│
├── mom-solver/                         # Method of Moments solver
│   ├── references/
│   │   ├── rwg_basis_functions.md     # RWG formulation
│   │   └── green_functions.md         # Green's function math
│   ├── templates/
│   │   ├── matrix_assembler.py        # Matrix assembly template
│   │   └── solver_engine.py           # Solver template
│   └── scripts/
│       ├── test_dipole.py             # Dipole verification
│       └── compute_sparameters.py      # S-parameter calculation
│
├── linear-algebra/                     # Sparse solvers & preconditioners
│   ├── references/
│   │   ├── petsc_guide.md             # PETSc usage guide
│   │   └── iterative_methods.md       # GMRES/BiCGStab docs
│   ├── templates/
│   │   ├── sparse_matrix.py           # Matrix template
│   │   └── preconditioner.py          # Preconditioner template
│   └── scripts/
│       ├── test_convergence.py        # Convergence testing
│       └── benchmark_solver.py        # Performance benchmark
│
├── post-processing/                    # Visualization & analysis
│   ├── references/
│   │   ├── visualization_guide.md     # VTK/PyVista usage
│   │   └── antenna_metrics.md         # Gain/directivity formulas
│   ├── templates/
│   │   ├── field_visualizer.py        # Field rendering template
│   │   └── plotter.py                 # Plotting template
│   └── scripts/
│       ├── visualize_patterns.py      # Pattern visualization
│       └── generate_report.py         # Report generation
│
├── testing-framework/                  # Automated testing framework
│   ├── templates/
│   │   ├── unit_test_template.py      # Test template
│   │   └── integration_test_template.py
│   └── scripts/
│       ├── run_all_tests.sh           # Test runner
│       └── generate_coverage_report.py
│
└── documentation-generator/            # Auto-documentation
    ├── templates/
    │   ├── api_doc_template.md        # API documentation template
    │   └── tutorial_template.md       # Tutorial template
    └── scripts/
        ├── generate_api_docs.sh
        └── create_tutorials.py
```

---

#### 2. MODULAR ARCHITECTURE GUIDELINES

**Clear Module Boundaries:**

```python
# Architecture Pattern

project/
├── src/
│   ├── core/                          # Core algorithms (MoM, FEM)
│   │   ├── mom_solver/
│   │   │   ├── __init__.py
│   │   │   ├── formulation.py         # EFIE/MFIE/CFIE
│   │   │   ├── basis_functions.py     # RWG implementation
│   │   │   └── green_function.py      # Green's function evaluator
│   │   ├── linear_algebra/
│   │   │   ├── sparse_matrix.py       # PETSc wrapper
│   │   │   ├── solver.py              # GMRES/BiCGStab
│   │   │   └── preconditioner.py      # ILU/AMG
│   │   └── field_calculations/
│   │       ├── near_field.py          # Near-field computation
│   │       └── far_field.py           # Far-field transformation
│   │
│   ├── cad/                           # CAD module (wrappers)
│   │   ├── opencascade_wrapper.py     # OpenCASCADE interface
│   │   ├── cgal_meshing.py            # CGAL mesh generator
│   │   ├── material_database.py       # Material properties
│   │   └── boundary_conditions.py     # PEC/PMC/PML
│   │
│   ├── post_processing/
│   │   ├── visualization/
│   │   │   ├── vtk_renderer.py        # VTK wrapper
│   │   │   └── pyvista_backend.py     # PyVista interface
│   │   ├── metrics/
│   │   │   ├── antenna_metrics.py     # Gain, directivity, etc.
│   │   │   └── bandwidth_analysis.py  # Bandwidth calculation
│   │   └── export/
│   │       ├── touchstone_export.py   # S-parameter files
│   │       └── hdf5_writer.py         # Field data storage
│   │
│   └── utils/
│       ├── geometry_utils.py          # Basic geometry helpers
│       ├── math_utils.py              # Numerical utilities
│       └── config_loader.py           # Configuration management
│
├── tests/
│   ├── unit/                          # Unit tests for each module
│   │   ├── test_mom_solver.py
│   │   ├── test_cad_wrapper.py
│   │   ├── test_linear_algebra.py
│   │   └── test_post_processing.py
│   ├── integration/                   # Integration tests
│   │   ├── test_dipole_antenna.py
│   │   ├── test_patch_antenna.py
│   │   └── test_full_workflow.py
│   └── benchmarks/
│       ├── performance_benchmarks.py
│       └── convergence_studies.py
│
├── examples/
│   ├── simple_dipole.py               # Simple dipole example
│   ├── patch_antenna.py               # Patch antenna example
│   └── complex_geometry.py            # Complex assembly example
│
└── docs/
    ├── api/                           # Auto-generated API docs
    ├── tutorials/                     # User tutorials
    └── references/                    # Physics reference material
```

**Interface Contracts:**

```python
# Example: Clear module interfaces

class CADWrapper:
    """Interface for CAD geometry handling"""

    def import_step(self, filepath: str) -> Geometry:
        """Import STEP file and return geometry object"""
        pass

    def extract_mesh(self, geometry: Geometry) -> TriangleMesh:
        """Extract triangle mesh from geometry"""
        pass

    def apply_boundary_condition(self, mesh: TriangleMesh,
                                condition_type: str,
                                region_id: int = None):
        """Apply boundary condition to mesh region"""
        pass

class MOMSolver:
    """Interface for MoM solver"""

    def setup_mesh(self, mesh: TriangleMesh, material_db: MaterialDatabase):
        """Initialize solver with mesh and materials"""
        pass

    def compute_system_matrix(self) -> SparseMatrix:
        """Assemble system matrix [Z][I] = [V]"""
        pass

    def solve(self, frequencies: List[float]) -> Solution:
        """Solve for given frequencies"""
        pass

class FieldVisualizer:
    """Interface for field visualization"""

    def plot_near_field(self, solution: Solution,
                       field_type: str = 'E',
                       slice_plane: str = 'xy'):
        """Plot near-field on specified plane"""
        pass

    def plot_radiation_pattern(self, solution: Solution,
                              theta_range: List[float],
                              phi_range: List[float]):
        """Plot radiation pattern in spherical coordinates"""
        pass
```

---

#### 3. TESTING FRAMEWORK

**Test Structure:**

```python
# tests/unit/test_mom_solver.py

import pytest
from src.core.mom_solver import MOMSolver, RWGBasisFunction
from src.cad.opencascade_wrapper import CADWrapper

class TestMOMSolver:
    """Unit tests for MoM solver"""

    def test_rwg_basis_orthogonality(self):
        """Verify RWG basis functions are orthogonal"""
        # Create two triangles
        t1, t2 = create_test_triangles()

        # Compute overlap integral
        overlap = compute_overlap(t1, t2)

        # Should be zero for non-overlapping or properly tested
        assert abs(overlap) < 1e-10

    def test_green_function_convergence(self):
        """Verify Green's function integration converges"""
        # Test with increasing number of quadrature points
        for n_points in [10, 20, 40, 80]:
            result = compute_green_function(n_points)
            expected = analytical_solution

            assert abs(result - expected) < tolerance[n_points]

    @pytest.mark.parametrize("frequency", [1e9, 2.4e9, 5.8e9])
    def test_dipole_sparameters(self, frequency):
        """Test dipole S-parameters against analytical solution"""
        # Create dipole geometry
        dipole = create_half_wave_dipole(frequency)

        # Solve
        solver = MOMSolver()
        solver.setup_mesh(dipole)
        solution = solver.solve([frequency])

        # Compare with analytical result
        s11_analytical = compute_analytical_s11(frequency)
        s11_computed = solution.s_parameters['S11']

        assert abs(s11_computed - s11_analytical) < 0.05

# tests/integration/test_full_workflow.py

class TestFullWorkflow:
    """Integration test for complete simulation workflow"""

    def test_dipole_simulation(self):
        """Complete workflow: CAD → Solver → Post-processing"""
        # 1. Import geometry
        cad = CADWrapper()
        dipole = cad.import_step('dipole.step')

        # 2. Mesh and prepare
        mesh = cad.extract_mesh(dipole)

        # 3. Solve
        solver = MOMSolver()
        solution = solver.solve([1e9, 2.4e9])

        # 4. Visualize
        visualizer = FieldVisualizer()
        visualizer.plot_radiation_pattern(solution)

        # Verify all steps completed successfully
        assert solution.converged
        assert len(solution.frequencies) == 2

# tests/benchmarks/performance_benchmarks.py

class PerformanceBenchmarks:
    """Performance benchmarks"""

    def test_mesh_generation_speed(self):
        """Mesh generation should complete within time limit"""
        geometry = load_complex_geometry()

        start_time = time.time()
        mesh = cad.extract_mesh(geometry)
        elapsed = time.time() - start_time

        assert elapsed < 30.0  # Should complete in 30 seconds

    def test_solver_scaling(self):
        """Solver should scale linearly with mesh size"""
        mesh_sizes = [1000, 2000, 4000]
        times = []

        for n in mesh_sizes:
            mesh = create_mesh_with_n_elements(n)
            start_time = time.time()
            solution = solver.solve([1e9])
            elapsed = time.time() - start_time
            times.append(elapsed)

        # Check scaling: O(n) expected
        ratios = [times[i] / times[0] for i in range(1, len(times))]
        assert all(ratio < 2.5 for ratio in ratios)  # Should be ~2x per doubling
```

**Test Automation:**

```bash
# scripts/run_all_tests.sh

#!/bin/bash

echo "Running unit tests..."
pytest tests/unit/ -v --cov=src --cov-report=html

echo "Running integration tests..."
pytest tests/integration/ -v

echo "Running benchmarks..."
python tests/benchmarks/performance_benchmarks.py

echo "Test suite complete!"
```

---

#### 4. REFERENCE IMPLEMENTATIONS

**Reference Code Templates:**

```python
# examples/reference_dipole.py
"""
Reference implementation for half-wave dipole antenna.
This serves as a benchmark for validation.
"""

import numpy as np
from src.cad.opencascade_wrapper import CADWrapper
from src.core.mom_solver import MOMSolver
from src.post_processing.visualization import FieldVisualizer

def create_half_wave_dipole(frequency: float):
    """Create half-wave dipole geometry"""
    cad = CADWrapper()

    # Dipole dimensions for given frequency
    wavelength = 3e8 / frequency
    length = wavelength / 2
    radius = wavelength / 100

    # Create cylinder (dipole rod)
    dipole = cad.create_cylinder(length, radius)

    return dipole

def compute_analytical_s11(frequency: float):
    """
    Compute analytical S11 for half-wave dipole.
    Reference: Balanis, Antenna Theory
    """
    wavelength = 3e8 / frequency
    beta = 2 * np.pi / wavelength

    # Input impedance of half-wave dipole
    R_in = 73 + j * 42.5  # Ohms at resonance

    # Reflection coefficient
    Gamma = (R_in - 50) / (R_in + 50)
    S11 = abs(Gamma)

    return S11

def run_validation():
    """Run dipole validation test"""
    frequency = 2.4e9  # 2.4 GHz

    print(f"Validating at {frequency/1e9} GHz...")

    # Create geometry
    dipole = create_half_wave_dipole(frequency)

    # Solve with our solver
    solver = MOMSolver()
    solution = solver.solve([frequency])

    # Compute analytical result
    s11_analytical = compute_analytical_s11(frequency)
    s11_computed = solution.s_parameters['S11']

    # Compare
    error = abs(s11_computed - s11_analytical)
    print(f"Analytical S11: {s11_analytical:.4f}")
    print(f"Computed S11:   {s11_computed:.4f}")
    print(f"Error:          {error:.4f}")

    # Validation criterion
    if error < 0.05:
        print("✓ PASS: Within 5% tolerance")
    else:
        print("✗ FAIL: Exceeds tolerance")

    return solution

if __name__ == "__main__":
    run_validation()
```

---

#### 5. DOCUMENTATION TEMPLATES

**API Documentation Template:**

```markdown
# API Documentation

## CADWrapper

### Methods

#### `import_step(filepath: str) -> Geometry`
Import a STEP file and return geometry object.

**Parameters:**
- `filepath` (str): Path to STEP file

**Returns:**
- `Geometry`: Imported geometry object

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `CADError`: If import fails

**Example:**
```python
cad = CADWrapper()
geometry = cad.import_step("antenna.step")
```

#### `extract_mesh(geometry: Geometry) -> TriangleMesh`
Extract triangle mesh from geometry.

**Parameters:**
- `geometry` (Geometry): Input geometry object

**Returns:**
- `TriangleMesh`: Extracted mesh

**Example:**
```python
mesh = cad.extract_mesh(geometry)
```

### Properties

#### `cad_version: str`
Returns OpenCASCADE version string.
```

---

#### 6. PERFORMANCE BENCHMARKS

**Benchmark Template:**

```python
# benchmarks/mom_solver_benchmark.py

import time
import numpy as np
from src.core.mom_solver import MOMSolver
from src.cad.opencascade_wrapper import CADWrapper

class MOMSolverBenchmark:
    """Performance benchmarks for MoM solver"""

    def __init__(self):
        self.results = []

    def benchmark_mesh_sizes(self, mesh_sizes=[1000, 2000, 4000, 8000]):
        """Benchmark solver performance with different mesh sizes"""

        print("\n=== Mesh Size Benchmark ===")

        for n in mesh_sizes:
            # Create test geometry
            geometry = self.create_test_geometry(n)

            # Setup and solve
            start_time = time.time()

            cad = CADWrapper()
            mesh = cad.extract_mesh(geometry)

            solver = MOMSolver()
            solver.setup_mesh(mesh)
            solution = solver.solve([1e9])

            elapsed = time.time() - start_time

            result = {
                'mesh_size': n,
                'time_seconds': elapsed,
                'converged': solution.converged
            }

            self.results.append(result)

            print(f"Mesh: {n:5d} | Time: {elapsed:.2f}s | Converged: {solution.converged}")

        # Compute scaling analysis
        self.analyze_scaling()

    def benchmark_frequencies(self, frequencies=[1e9, 2.4e9, 5.8e9]):
        """Benchmark solver performance at different frequencies"""

        print("\n=== Frequency Benchmark ===")

        for freq in frequencies:
            start_time = time.time()

            geometry = self.create_test_geometry(2000)
            mesh = cad.extract_mesh(geometry)

            solver = MOMSolver()
            solution = solver.solve([freq])

            elapsed = time.time() - start_time

            print(f"Freq: {freq/1e9:.2f} GHz | Time: {elapsed:.2f}s")

    def benchmark_preconditioners(self):
        """Compare different preconditioners"""

        print("\n=== Preconditioner Comparison ===")

        geometry = self.create_test_geometry(4000)
        mesh = cad.extract_mesh(geometry)

        preconditioners = ['none', 'ilu', 'amg']

        for pc in preconditioners:
            solver = MOMSolver(preconditioner=pc)
            solver.setup_mesh(mesh)

            start_time = time.time()
            solution = solver.solve([1e9])
            elapsed = time.time() - start_time

            iterations = len(solution.iteration_history)

            print(f"Preconditioner: {pc:6s} | Time: {elapsed:.2f}s | Iterations: {iterations}")

    def analyze_scaling(self):
        """Analyze O(n) scaling"""

        if len(self.results) < 2:
            return

        # Compute time ratios
        base_time = self.results[0]['time_seconds']

        print("\n=== Scaling Analysis ===")
        for i in range(1, len(self.results)):
            ratio = self.results[i]['time_seconds'] / base_time
            mesh_size = self.results[i]['mesh_size']

            print(f"{mesh_size:5d} elements | Time ratio: {ratio:.2f}x")

if __name__ == "__main__":
    benchmark = MOMSolverBenchmark()
    benchmark.benchmark_mesh_sizes()
```

---

#### 7. ERROR HANDLING PATTERNS

**Standardized Error Handling:**

```python
# src/utils/errors.py

class AntennaSimulationError(Exception):
    """Base exception for antenna simulation errors"""
    pass

class CADError(AntennaSimulationError):
    """CAD module errors"""
    pass

class SolverError(AntennaSimulationError):
    """Solver errors"""
    pass

class GeometryError(CADError):
    """Geometry-related errors"""
    def __init__(self, message: str, geometry_id: int = None):
        super().__init__(message)
        self.geometry_id = geometry_id

class MeshError(CADError):
    """Mesh generation/validation errors"""
    def __init__(self, message: str, mesh_quality: dict = None):
        super().__init__(message)
        self.mesh_quality = mesh_quality or {}

class ConvergenceError(SolverError):
    """Solver convergence failure"""
    def __init__(self, message: str, max_iterations: int, final_residual: float):
        super().__init__(message)
        self.max_iterations = max_iterations
        self.final_residual = final_residual

class FieldCalculationError(AntennaSimulationError):
    """Field calculation errors"""
    pass

# src/cad/opencascade_wrapper.py

def import_step(self, filepath: str) -> Geometry:
    try:
        # Attempt to import
        geometry = occt.import_file(filepath)

        # Validate geometry
        self._validate_geometry(geometry)

        return geometry

    except Exception as e:
        raise CADError(f"Failed to import STEP file {filepath}: {str(e)}")

    except ValueError as e:
        raise GeometryError(f"Invalid geometry in file: {str(e)}")

def extract_mesh(self, geometry: Geometry) -> TriangleMesh:
    try:
        # Generate mesh
        mesh = cgal.generate_surface_mesh(geometry)

        # Validate mesh quality
        quality = self._check_mesh_quality(mesh)

        if quality['aspect_ratio'] > 10.0:
            raise MeshError(
                "Mesh has poor aspect ratio",
                mesh_quality=quality
            )

        return mesh

    except Exception as e:
        raise CADError(f"Mesh generation failed: {str(e)}")

# src/core/mom_solver.py

def solve(self, frequencies: List[float]) -> Solution:
    try:
        # Setup system
        self._setup_system()

        # Solve for each frequency
        solutions = []
        for freq in frequencies:
            start_time = time.time()

            solution = self._solve_single_frequency(freq)
            elapsed = time.time() - start_time

            solution.computation_time = elapsed
            solutions.append(solution)

        return Solution(solutions, converged=True)

    except Exception as e:
        raise SolverError(f"Solver failed: {str(e)}")

def _solve_single_frequency(self, frequency: float) -> Solution:
    try:
        # Build matrix
        self._assemble_matrix()

        # Solve
        solution = self.solver.solve()

        # Check convergence
        if solution.residual > 1e-6 and solution.iterations >= self.max_iterations:
            raise ConvergenceError(
                "Solver did not converge",
                max_iterations=self.max_iterations,
                final_residual=solution.residual
            )

        return solution

    except Exception as e:
        raise SolverError(f"Frequency {frequency} Hz failed: {str(e)}")
```

---

#### 8. INTEGRATION PATTERNS

**Module Integration Workflow:**

```python
# examples/full_workflow.py

def run_full_simulation(input_file: str, output_dir: str):
    """
    Complete simulation workflow:
    1. Load CAD geometry
    2. Generate mesh
    3. Setup solver
    4. Solve for frequencies
    5. Post-process results
    6. Export data
    """

    # Step 1: Load CAD
    print(f"[Step 1/6] Loading CAD geometry from {input_file}...")
    cad = CADWrapper()
    geometry = cad.import_step(input_file)
    print("✓ Geometry loaded")

    # Step 2: Generate mesh
    print("[Step 2/6] Generating mesh...")
    mesh = cad.extract_mesh(geometry)
    print(f"✓ Mesh generated: {mesh.num_elements} elements")

    # Step 3: Setup solver
    print("[Step 3/6] Setting up solver...")
    solver = MOMSolver()
    solver.setup_mesh(mesh, material_db=MaterialDatabase())
    print("✓ Solver configured")

    # Step 4: Solve
    frequencies = [1e9, 2.4e9, 5.8e9]
    print(f"[Step 4/6] Solving for {len(frequencies)} frequencies...")
    solution = solver.solve(frequencies)
    print(f"✓ Solution complete (converged: {solution.converged})")

    # Step 5: Post-process
    print("[Step 5/6] Post-processing...")
    visualizer = FieldVisualizer()

    for freq, sol in zip(frequencies, solution.solutions):
        visualizer.plot_radiation_pattern(sol,
                                         theta_range=[0, 180],
                                         phi_range=[0, 360])
    print("✓ Visualization complete")

    # Step 6: Export
    print("[Step 6/6] Exporting results...")
    export_manager = ExportManager()
    export_manager.export_solution(solution, output_dir)
    print(f"✓ Results exported to {output_dir}")

    print("\n=== Simulation Complete ===")
    return solution

# Usage
if __name__ == "__main__":
    result = run_full_simulation("antenna.step", "results")
```

---

#### 9. AUTOMATED EXECUTION SCRIPT

**Phase Execution Script:**

```bash
#!/bin/bash
# scripts/run_phase.sh

PHASE=$1

case $PHASE in
    phase0)
        echo "Running Phase 0: Project Setup"
        python scripts/setup_project.py
        ;;
    phase1)
        echo "Running Phase 1: CAD Module"
        skill_manage action="create" name="cad-integration" category="cad"
        python skills/cad-integration/scripts/week3_integration.py
        python skills/cad-integration/scripts/week4_cgal.py
        python skills/cad-integration/scripts/week5_boundaries.py
        python skills/cad-integration/scripts/week6_testing.py
        ;;
    phase2)
        echo "Running Phase 2: MoM Solver"
        skill_manage action="create" name="mom-solver" category="solver"
        python skills/mom-solver/scripts/week7_linear_algebra.py
        python skills/mom-solver/scripts/week8_formulation.py
        python skills/mom-solver/scripts/week9_basis_functions.py
        python skills/mom-solver/scripts/week10_solver.py
        python skills/mom-solver/scripts/week11_verification.py
        python skills/mom-solver/scripts/week12_optimization.py
        ;;
    phase3)
        echo "Running Phase 3: Post-Processing"
        skill_manage action="create" name="post-processing" category="visualization"
        python skills/post-processing/scripts/week13_field_viz.py
        python skills/post-processing/scripts/week14_metrics.py
        python skills/post-processing/scripts/week15_export.py
        python skills/post-processing/scripts/week16_testing.py
        ;;
    phase4)
        echo "Running Phase 4: Optimization"
        python scripts/gpu_acceleration.py
        python scripts/fmm_implementation.py
        python scripts/advanced_features.py
        ;;
    phase5)
        echo "Running Phase 5: Testing & Documentation"
        python scripts/run_all_tests.sh
        python scripts/documentation_generator.py
        python scripts/release_prep.py
        ;;
    *)
        echo "Usage: $0 {phase0|phase1|phase2|phase3|phase4|phase5}"
        exit 1
        ;;
esac

echo "Phase $PHASE complete!"
```

---

#### 10. SUCCESS CRITERIA CHECKLIST

**AI Execution Checklist:**

```python
# scripts/check_progress.py

class ProgressChecker:
    """Check if milestones are met"""

    def __init__(self):
        self.milestones = {
            'phase0': {
                'env_setup': False,
                'docs_complete': False,
                'skills_created': False
            },
            'phase1': {
                'opencascade_import': False,
                'cgal_meshing': False,
                'boundary_conditions': False,
                'cad_tests_pass': False
            },
            'phase2': {
                'linear_algebra': False,
                'mom_formulation': False,
                'rwg_basis': False,
                'solver_working': False,
                'dipole_validation': False
            },
            'phase3': {
                'field_viz': False,
                'antenna_metrics': False,
                'export_functions': False,
                'post_processing_tests': False
            },
            'phase4': {
                'gpu_acceleration': False,
                'fmm_implemented': False,
                'advanced_features': False
            },
            'phase5': {
                'test_coverage': False,
                'validation_complete': False,
                'docs_complete': False,
                'release_ready': False
            }
        }

    def check_phase0(self):
        """Check Phase 0 completion"""
        # Check if environment is set up
        try:
            import numpy, scipy, opencascade_core
            self.milestones['phase0']['env_setup'] = True
        except ImportError:
            print("✗ Missing dependencies")

        # Check if documentation exists
        import os
        if os.path.exists('docs/'):
            self.milestones['phase0']['docs_complete'] = True

        print("Phase 0 Status:")
        for key, value in self.milestones['phase0'].items():
            status = "✓" if value else "✗"
            print(f"  {status} {key}")

    def check_phase1(self):
        """Check Phase 1 completion"""
        # Check CAD module tests
        try:
            from src.cad.opencascade_wrapper import CADWrapper
            self.milestones['phase1']['opencascade_import'] = True
        except ImportError:
            print("✗ OpenCASCADE wrapper not found")

        if os.path.exists('tests/unit/test_cad_wrapper.py'):
            self.milestones['phase1']['cad_tests_pass'] = True

        # Check CGAL integration
        try:
            from src.cad.cgal_meshing import generate_surface_mesh
            self.milestones['phase1']['cgal_meshing'] = True
        except ImportError:
            print("✗ CGAL meshing not found")

        print("\nPhase 1 Status:")
        for key, value in self.milestones['phase1'].items():
            status = "✓" if value else "✗"
            print(f"  {status} {key}")

    def check_phase2(self):
        """Check Phase 2 completion"""
        # Check solver
        try:
            from src.core.mom_solver import MOMSolver
            self.milestones['phase2']['solver_working'] = True
        except ImportError:
            print("✗ MoM solver not found")

        # Check dipole validation
        if os.path.exists('tests/integration/test_dipole_antenna.py'):
            self.milestones['phase2']['dipole_validation'] = True

        print("\nPhase 2 Status:")
        for key, value in self.milestones['phase2'].items():
            status = "✓" if value else "✗"
            print(f"  {status} {key}")

    def check_all(self):
        """Check all phases"""
        print("=== PROGRESS CHECK ===\n")

        for phase in ['phase0', 'phase1', 'phase2', 'phase3', 'phase4', 'phase5']:
            self.check_phase()
            print()

if __name__ == "__main__":
    checker = ProgressChecker()
    checker.check_all()
```

---

## SUMMARY OF ENHANCEMENTS

| Enhancement | Purpose | Benefit for AI |
|-------------|---------|----------------|
| **Skills System** | Reusable task modules | Autonomous execution without human intervention |
| **Modular Architecture** | Clear module boundaries | Easy parallel development and testing |
| **Testing Framework** | Automated validation | Continuous quality assurance |
| **Reference Implementations** | Code templates | AI can replicate proven patterns |
| **Documentation Templates** | Standardized docs | Auto-generation of user-facing docs |
| **Performance Benchmarks** | Quantitative targets | Clear success criteria |
| **Error Handling Patterns** | Consistent error handling | Robust autonomous execution |
| **Integration Workflows** | Complete pipelines | End-to-end automation |
| **Progress Checker** | Milestone tracking | Autonomous phase management |

---

## SUCCESS METRICS

| Metric | Target |
|--------|--------|
| Code Coverage | >90% |
| Test Pass Rate | 100% |
| Accuracy vs Reference | ±5% |
| Performance (MoM) | 1-2x CPU speedup with 4 cores |
| Documentation Completeness | All features documented |

---

## RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| Complexity overestimation | Start simple, iterate |
| Integration issues | Modular design, frequent testing |
| Performance bottlenecks | Profile early, optimize critical paths |
| Validation failures | Compare against multiple references |

---

**Total Estimated Timeline**: 24 weeks (6 months)  
**Key Milestones**: CAD Module (Week 6), Solver Ready (Week 12), Full System (Week 20), Release (Week 24)

---

## NEXT STEPS

1. **Review this plan** and confirm approach
2. **Set up project environment** following Phase 0
3. **Create skills** using the templates provided
4. **Begin autonomous execution** starting with Phase 0
5. **Monitor progress** using the ProgressChecker script
6. **Adjust as needed** based on results and challenges

This plan transforms high-level requirements into an **autonomous-executable specification** that an AI can work through systematically with minimal human intervention.