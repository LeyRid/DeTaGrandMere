# USE CASE UC-12-Solve Impedance Matrix Using Numerical Solver

**Context of use:** The solver component assembles and solves the impedance matrix equation [Z][I] = [V] derived from the chosen numerical method (MoM, FEM, or hybrid). For MoM, this represents the discretized Electric Field Integral Equation solved using RWG basis functions and Galerkin testing. This subfunction is invoked by UC-06 (Configure Solver and Run Frequency Sweep) for each frequency point in the sweep.

**Scope:** EM Simulation System — Subsystem scope, black box (solver component)

**Level:** Subfunction

**Primary Actor:** Solver Engine (automated)

**Stakeholders & Interests:**
- Solver Engine: Needs a well-conditioned impedance matrix and appropriate solver configuration to produce a convergent solution within the allowed iteration count.
- RF Antenna Engineer (off-stage): Wants accurate current distribution results with verified convergence, obtained in reasonable computational time.
- System Owner: Wants solver resource usage (CPU time, memory) tracked and optimized through intelligent preconditioner selection and parallel execution.

**Precondition:** A validated computational mesh exists. Port excitations and boundary conditions are defined. The impedance matrix has been assembled from the mesh geometry, material properties, and operating frequency. Solver parameters (method, preconditioner, tolerance, maximum iterations) have been specified.

**Minimal Guarantees:** Every solver execution logs the initial residual norm, convergence history at each iteration, final residual norm, iteration count, and success/failure status. If the solver fails to converge, all intermediate solution data is preserved so that retry strategies can be applied without re-assembly of the impedance matrix.

**Success Guarantees:** The linear system [Z][I] = [V] is solved to within the specified tolerance (typically 1e-6 to 1e-9). The resulting current vector I contains accurate surface current coefficients for all mesh elements. The solver reports a convergence metric confirming that the residual ||ZI - V|| / ||V|| is below the threshold. Computation completes within the maximum allowed wall-clock time.

**Trigger:** Solver receives an assembled impedance matrix, excitation vector, and solver configuration parameters for a specific frequency point.

## Main Success Scenario

1. Solver: selects the appropriate preconditioner based on mesh element count (none for <1000, ILU fill=10 for 1000-10000, AMG for >10000).
2. Solver: applies the preconditioner to the impedance matrix to improve its condition number.
3. Solver: initializes the iterative solver (GMRES or BiCGStab) with the preconditioned system and sets the initial guess (zero vector for first frequency, previous solution interpolated for adjacent frequencies).
4. Solver: iterates, computing residual norms at each step and checking convergence against the tolerance threshold.
5. Solver: monitors iteration progress and logs convergence history (residual vs. iteration count).
6. Solver: upon convergence or reaching maximum iterations, extracts the current vector solution.
7. Solver: verifies that the final residual meets the acceptance criterion and reports convergence status with diagnostic metrics.

## Extensions

1a. Preconditioner selection produces a matrix that is still ill-conditioned (condition number exceeds solver capability):
   - Solver switches to an alternative preconditioner (e.g., from ILU to AMG) or increases the ILU fill level automatically.
   - Execution resumes at step 2 with the new preconditioner.

2a. Initial guess from previous frequency interpolation is poor (causes slow convergence or divergence):
   - Solver discards the interpolated initial guess and restarts with a zero initial guess for this frequency point.
   - RF Antenna Engineer: may investigate whether the frequency step between consecutive points is too large.
   - Execution resumes at step 3 with zero initial guess.

4a. Iterative solver fails to converge within the maximum allowed iterations:
   - Solver attempts automatic retry strategies in sequence: (1) switch Krylov method from GMRES to BiCGStab, (2) increase maximum iterations by 50%, (3) relax tolerance one order of magnitude, (4) switch preconditioner type.
   - If all strategies fail, solver reports the failure with diagnostic information for each attempted strategy.
   - RF Antenna Engineer: reviews the diagnostic report and may manually adjust solver parameters or investigate mesh/geometry issues.
   - Execution ends at failure exit with full diagnostic data preserved.

4b. Solver detects oscillating residual (residual norm increases then decreases in a non-monotonic pattern):
   - Solver applies residual smoothing (restarts GMRES with a smaller restart parameter) to stabilize convergence.
   - RF Antenna Engineer: may investigate whether the impedance matrix assembly contains numerical errors.
   - Execution resumes at step 4 with restarted iterations.

6a. Solution is extracted but the final residual is marginally above tolerance (within 10x of threshold):
   - Solver offers to perform additional iterations with a stricter local tolerance or accepts the solution as engineering-acceptable.
   - RF Antenna Engineer: chooses to continue iterating or accept the marginal result.
   - If continuing: execution resumes at step 4 with additional iterations.

7a. Verification of final residual reveals that solver accuracy is insufficient for downstream analysis (e.g., far-field computation requires higher current accuracy than S-parameter computation):
   - Solver performs a final refinement pass with tighter tolerance specifically for frequencies where far-field results are requested.
   - Execution resumes at step 4 with the stricter tolerance applied.

## Technology and Data Variations List

- Step 1: Preconditioner types include None (no preconditioning, suitable only for very small problems), ILU (incomplete LU decomposition with configurable fill level), AMG (algebraic multigrid, best for large sparse systems), and block preconditioners (for MoM problems with structured element grouping).
- Step 3: Krylov methods include GMRES (generalized minimum residual, robust but memory-intensive due to orthogonalization), BiCGStab (biconjugate gradient stabilized, lighter memory footprint but less robust), and direct solvers (LU decomposition via sparse factorization for small problems where N < 5000).
- Step 3: Frequency interpolation initial guess uses linear or quadratic interpolation of the current vector from adjacent converged frequency points, reducing iteration count by 50-80% compared to zero initialization.

## Related Information

- **Priority:** 1 (critical subfunction — solver convergence is the gatekeeper for all downstream results)
- **Channels:** Invoked internally by UC-06; may be invoked directly via command-line interface for stand-alone matrix solving.
- **Frequency:** Once per frequency point per simulation run; typically 50-200 frequency points per sweep.
- **Related Use Cases:** Called by UC-06 (Configure Solver and Run Frequency Sweep); produces current vector consumed by UC-08 (Analyze Radiation Patterns and Far-Field Results) and UC-07 (Analyze S-Parameters and Bandwidth Results).
