# USE CASE UC-01-Run Electromagnetic Simulation

**Context of use:** RF Antenna Engineer loads antenna geometry, configures simulation parameters, runs the numerical solver, and obtains validated electromagnetic results including S-parameters, radiation patterns, and field distributions. This use case covers the complete end-to-end workflow from geometry import to final result analysis.

**Scope:** EM Simulation System — System scope, black box

**Level:** Summary

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants reliable simulation results that accurately predict real-world antenna behavior within acceptable computational time.
- Auditor (off-stage): Needs complete audit trail of all simulation parameters and settings for reproducibility and compliance.
- System Owner: Wants the system to preserve all project data and avoid computational waste from failed runs.
- Solver Engine (supporting actor): Expects well-formed input geometry, properly defined ports, and valid material properties to produce a convergent solution.

**Precondition:** Antenna geometry file exists in a supported format (STEP, STL, or OBJ). The engineer has access to the EM Simulation System.

**Minimal Guarantees:** Complete logging of all simulation parameters, mesh settings, solver configuration, and output files so that any run can be reproduced exactly. Every simulation attempt — successful or failed — is recorded with timestamp, error details if applicable, and resource usage statistics.

**Success Guarantees:** Simulation completes with converged solution. All requested results (S-parameters across frequency band, far-field radiation patterns at specified frequencies, near-field distribution plots) are computed, stored in a structured output directory, and available for the engineer to review and export.

**Trigger:** RF Antenna Engineer initiates a new simulation from an antenna geometry file.

## Main Success Scenario

1. RF Antenna Engineer: imports antenna geometry file into the system.
2. System: validates geometry integrity and assigns default material properties based on file metadata.
3. RF Antenna Engineer: defines port locations, types, and excitation parameters.
4. RF Antenna Engineer: sets simulation frequency range, method selection (MoM/FEM), and solver options.
5. System: generates computational mesh with quality metrics verification.
6. System: runs the numerical solver on the defined problem configuration.
7. System: computes far-field radiation patterns from near-field solution data.
8. RF Antenna Engineer: reviews convergence report and result quality indicators.
9. System: stores all results, logs, and metadata in the project output directory.

## Extensions

2a. Geometry validation fails (degenerate faces, non-manifold edges):
   - System reports specific geometry errors to engineer with suggested repairs.
   - RF Antenna Engineer: chooses to repair geometry externally or cancel the simulation.

3a. Port definition conflicts with geometry (port overlaps radiating element, port size too small for wavelength):
   - System warns engineer about the conflict and suggests corrections based on wavelength at lowest frequency.
   - RF Antenna Engineer: adjusts port placement, type, or size.
   - Execution resumes at step 3.

4a. Solver method incompatible with geometry (e.g., MoM selected for volumetric dielectric structure):
   - System recommends FEM or hybrid MoM-FEM and explains why.
   - RF Antenna Engineer: selects recommended method or confirms alternative choice.
   - Execution resumes at step 4.

5a. Mesh quality verification fails (degenerate elements, excessive aspect ratio, insufficient refinement near feed):
   - System reports mesh quality metrics with flagged regions.
   - RF Antenna Engineer: adjusts mesh parameters and re-triggers mesh generation.
   - Execution resumes at step 5.

6a. Solver does not converge within maximum iterations:
   - System generates convergence diagnostic report showing residual history, iteration count, and preconditioner performance.
   - System offers recommended solver adjustments (preconditioner change, tolerance relaxation, iteration increase).
   - RF Antenna Engineer: applies suggested changes or manually adjusts settings and re-runs solver.
   - Execution resumes at step 6.

6b. Solver runs out of memory during computation:
   - System halts computation and reports available vs. required memory.
   - System suggests parallel computing options (MPI domain decomposition, out-of-core computation).
   - RF Antenna Engineer: enables parallel mode or reduces problem size.
   - Execution resumes at step 6.

7a. Far-field transformation fails due to insufficient near-field data:
   - System reports the deficiency and suggests increasing boundary distance from antenna.
   - RF Antenna Engineer: adjusts simulation domain size and re-runs.
   - Execution resumes at step 6.

## Technology and Data Variations List

- Step 2: Geometry import may use STEP, STL, or OBJ format; each has different level of geometric fidelity preserved.
- Step 3: Port type may be lumped (voltage source with series impedance) or waveguide (modal expansion); selection depends on structure size relative to wavelength.
- Step 4: Numerical method may be MoM (surface currents), FEM (volume elements), FDTD (time-domain), or hybrid approaches.
- Step 6: Solver may use direct methods (LU decomposition for small problems) or iterative methods (GMRES with ILU/AMG preconditioning for large problems).

## Related Information

- **Priority:** 1 (highest — this is the core system workflow)
- **Channels:** Desktop application, command-line interface
- **Frequency:** Daily to weekly for active design engineers; less frequent for research and analysis roles.
- **Open Issues:** How to handle multi-physics coupling (thermal, mechanical)? Should the system support automated geometry optimization loops?
