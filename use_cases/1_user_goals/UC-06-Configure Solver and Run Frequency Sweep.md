# USE CASE UC-06-Configure Solver and Run Frequency Sweep

**Context of use:** RF Antenna Engineer configures the numerical solver settings (method, preconditioner, convergence criteria) and defines the frequency sweep parameters before executing the simulation. This determines how the impedance matrix is solved and over what frequency range results are computed. Proper solver configuration is essential for achieving convergence within reasonable computational time.

**Scope:** EM Simulation System — System scope, black box

**Level:** User-goal

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants the solver to converge reliably and produce accurate results across the entire frequency band of interest within acceptable wall-clock time.
- System Owner: Wants computational resources used efficiently — no wasted iterations on poor preconditioner choices or excessive tolerance settings.
- Auditor (off-stage): Needs convergence history, iteration counts, and residual values recorded for every solver execution.

**Precondition:** Geometry is imported, materials assigned, ports and boundaries defined, and mesh generated and validated. The engineer knows the frequency range of interest and any expected resonance locations.

**Minimal Guarantees:** All solver settings (method, preconditioner, tolerance, maximum iterations) are recorded before execution. Every solver run produces a convergence report with residual history, iteration count, and success/failure status. Failed runs preserve all intermediate data so they can be retried with adjusted settings.

**Success Guarantees:** The numerical solver converges to the specified tolerance within the maximum allowed iterations for every frequency point in the sweep. The resulting current distribution, S-parameters, and near-field solution are stored and available for post-processing. The engineer receives a clear convergence status report indicating whether results meet accuracy expectations.

**Trigger:** RF Antenna Engineer initiates solver configuration and frequency sweep execution.

## Main Success Scenario

1. RF Antenna Engineer: selects the numerical method (MoM, FEM, or FDTD) based on the antenna type and problem characteristics.
2. RF Antenna Engineer: specifies the frequency sweep range and sampling strategy (uniform or adaptive).
3. System: analyzes the mesh element count and recommends an appropriate preconditioner (none for <1000 elements, ILU for 1000-10000, AMG for >10000).
4. RF Antenna Engineer: accepts the recommended settings or manually configures solver parameters (Krylov method, tolerance, maximum iterations).
5. System: assembles the impedance matrix and applies the selected preconditioner.
6. System: solves the matrix equation at each frequency point in the sweep, monitoring convergence at each step.
7. System: stores converged solutions and generates a convergence report summarizing results across all frequency points.

## Extensions

1a. Selected numerical method is incompatible with the problem (e.g., MoM selected for a structure dominated by volumetric dielectrics):
   - System warns that MoM is optimized for surface-current problems on conductors and recommends FEM or hybrid MoM-FEM for dielectric-rich structures.
   - RF Antenna Engineer: changes to the recommended method or confirms the original choice with acknowledgment of limitations.
   - Execution resumes at step 2.

2a. Frequency sweep range is extremely wide (ratio > 10:1):
   - System warns that a single mesh may be inadequate across such a wide band and suggests running separate simulations for low and high frequency sub-bands with different mesh refinements.
   - RF Antenna Engineer: accepts the wide-band approach or splits into sub-band simulations.
   - If sub-bands: execution resumes at step 2 with adjusted range; each sub-band produces its own convergence report.

3a. Adaptive frequency sampling is selected:
   - System first performs a coarse sweep to identify resonance regions where S11 drops below threshold, then performs fine sweeps around each identified resonance.
   - RF Antenna Engineer: specifies the resonance detection threshold (e.g., |S11| < -10 dB).
   - Execution resumes at step 4 with adaptive sampling parameters set.

4a. Solver configuration includes settings that are too aggressive (tolerance > 1e-4, max iterations < 500):
   - System warns that these settings may not achieve accurate results and suggests conservative defaults (tolerance 1e-6 to 1e-9, max iterations 500-2000).
   - RF Antenna Engineer: accepts the warning and proceeds or adjusts to more conservative values.
   - If proceeding with aggressive settings: execution resumes at step 5 with a flag in metadata noting the non-standard configuration.

6a. Solver fails to converge at one or more frequency points:
   - System generates a per-frequency convergence diagnostic showing residual history, iteration count, and preconditioner effectiveness for each failed point.
   - System offers automatic retry strategies (switch preconditioner from ILU to AMG, relax tolerance, increase max iterations) applied sequentially until convergence is achieved or all strategies exhausted.
   - RF Antenna Engineer: reviews the diagnostic report and may manually intervene with custom solver adjustments.
   - Execution resumes at step 6 with adjusted settings for the failed frequency points only; converged frequencies retain their original results.

6b. Solver runs out of memory during matrix assembly or solution:
   - System halts computation, reports available vs. required memory, and suggests solutions (enable MPI domain decomposition, switch to out-of-core computation, reduce mesh density).
   - RF Antenna Engineer: enables parallel computing mode or adjusts problem size.
   - Execution resumes at step 5 with the new configuration.

## Technology and Data Variations List

- Step 1: MoM solves surface integral equations using RWG basis functions, optimal for conducting surfaces. FEM solves differential form of Maxwell's equations in volume elements, better for dielectric structures. FDTD is time-domain and naturally broadband but requires careful boundary conditions.
- Step 2: Frequency sweep strategies include uniform sampling (fixed points per band), adaptive sampling (coarse then fine around resonances), and interpolatory methods (sparse initial sweep with polynomial interpolation).
- Step 3: Preconditioner recommendations are based on mesh element count N: none for N < 1000, ILU (fill level 10) for N < 10000, AMG or multigrid for N > 10000.
- Step 6: Krylov methods include GMRES (generalized minimum residual), BiCGStab (biconjugate gradient stabilized), and direct solvers (LU decomposition for small problems).

## Related Information

- **Priority:** 1 (critical — solver convergence is the gatekeeper between setup and results)
- **Channels:** Desktop application with solver parameter editor, command-line interface with configuration file
- **Frequency:** Once per simulation run; settings may be saved as templates for reuse on similar antenna types.
- **Open Issues:** Should the system provide intelligent auto-tuning of solver parameters based on problem characteristics? How to handle frequency-dependent material dispersion during multi-frequency sweeps?
