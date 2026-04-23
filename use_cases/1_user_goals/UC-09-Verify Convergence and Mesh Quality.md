# USE CASE UC-09-Verify Convergence and Mesh Quality

**Context of use:** RF Antenna Engineer performs convergence testing to verify that simulation results are independent of mesh density and solver settings. This quality assurance step confirms that the computed results have reached numerical accuracy and are not artifacts of insufficient discretization or premature solver termination. Running simulations without convergence verification is a common pitfall that produces unreliable results.

**Scope:** EM Simulation System — System scope, black box

**Level:** User-goal

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants mathematical assurance that the simulation results are numerically converged and not dependent on arbitrary mesh or solver choices.
- System Owner: Wants verification data stored so that result reliability can be demonstrated to reviewers, clients, or regulatory bodies.
- Auditor (off-stage): Needs a complete convergence history showing how results changed with increasing refinement, establishing that a stable solution was reached.

**Precondition:** At least one simulation has been completed with converged solver results. The engineer has identified the key output metrics to verify (e.g., S11 at resonance frequency, peak gain, resonant frequency).

**Minimal Guarantees:** Every convergence test run is logged with its mesh parameters, solver settings, and resulting metric values. The system preserves all intermediate solutions so that convergence plots can be generated retroactively. Results of each test are timestamped and attributed to the engineer who initiated them.

**Success Guarantees:** The engineer has verified that key metrics change by less than 1% (or a user-defined tolerance) between successively refined mesh or solver configurations. A convergence report documents the trend of each metric as refinement increases, showing asymptotic approach to a stable value. The engineer can confidently proceed with design decisions based on results whose numerical accuracy has been established.

**Trigger:** RF Antenna Engineer initiates a convergence verification study after completing an initial simulation.

## Main Success Scenario

1. RF Antenna Engineer: selects the key metrics to verify (e.g., S11 at resonance, peak gain, resonant frequency) and defines the acceptance tolerance (default 1%).
2. System: records the baseline simulation results for all selected metrics from the initial mesh and solver configuration.
3. RF Antenna Engineer: specifies the refinement strategy — mesh density increase (e.g., 2x element count) or solver parameter tightening (e.g., tolerance from 1e-4 to 1e-6).
4. System: generates a refined simulation configuration with increased discretization or tighter convergence criteria.
5. System: runs the simulation with the refined configuration on the same geometry, ports, and boundary conditions.
6. System: extracts the same key metrics from the new solution and compares them to the baseline values.
7. RF Antenna Engineer: reviews the convergence report showing metric changes across all refinement levels tested.
8. System: determines whether all metrics have converged within the specified tolerance or identifies which metrics still need further refinement.

## Extensions

1a. Engineer does not specify which metrics to verify:
   - System defaults to verifying S11 at the lowest resonance frequency, peak gain at center frequency, and resonant frequency shift.
   - Execution resumes at step 2 with default metrics.

2a. Baseline simulation has not yet been completed or its results are unavailable:
   - System prompts the engineer to run an initial simulation first.
   - Execution transfers to UC-06 (Configure Solver and Run Frequency Sweep) or UC-01 (Run Electromagnetic Simulation).
   - Upon completion, execution resumes at step 2 with the newly generated baseline results.

3a. Mesh refinement strategy is selected:
   - System increases element count by the specified factor, ensuring that critical regions (feed points, edges, corners) receive proportional refinement to maintain lambda/100 sizing.
   - RF Antenna Engineer: confirms the refinement factor or specifies per-region refinement targets.
   - Execution resumes at step 4 with the refined mesh configuration.

4a. Solver parameter tightening is selected:
   - System reduces tolerance (e.g., from 1e-4 to 1e-6), increases maximum iterations, and optionally switches to a more robust Krylov method or preconditioner.
   - RF Antenna Engineer: selects which parameters to tighten and by what factor.
   - Execution resumes at step 4 with the tightened solver configuration.

5a. Refined simulation fails to converge or takes excessively long (more than 10x baseline time):
   - System reports the failure mode (no convergence, iteration limit reached, memory overflow) and preserves the partial solution for analysis.
   - RF Antenna Engineer: adjusts the refinement increment (smaller step), changes preconditioner strategy, or abandons this particular metric's convergence path.
   - Execution resumes at step 4 with adjusted parameters or skips to step 7 with available data.

6a. Some metrics have not converged within tolerance after the current refinement level:
   - System identifies which specific metrics are still changing beyond tolerance and recommends additional refinement targeted at those metrics.
   - RF Antenna Engineer: authorizes further refinement iterations or accepts that certain metrics require even higher resolution than is practical.
   - Execution resumes at step 3 for the non-converged metrics.

7a. Convergence testing reveals that results are oscillating rather than converging monotonically:
   - System flags the oscillatory behavior and suggests that the refinement may be introducing numerical noise (e.g., from mesh topology changes between refinement levels).
   - RF Antenna Engineer: switches to a consistent mesh refinement approach (same topology, only subdivision) or increases the refinement step size.
   - Execution resumes at step 3 with corrected refinement strategy.

## Technology and Data Variations List

- Step 3: Mesh refinement strategies include uniform global refinement (all elements subdivided), targeted local refinement (only high-error regions subdivided per adaptive meshing criteria from UC-05), and p-refinement (increasing basis function polynomial order rather than element count).
- Step 6: Metric comparison uses relative error |metric_new - metric_old| / |metric_old|. For frequency-based metrics like resonant frequency, absolute error in Hz or MHz may be more meaningful.

## Related Information

- **Priority:** 2 (high — convergence verification is essential for result credibility but is a QA step performed periodically rather than on every simulation)
- **Channels:** Desktop application with interactive convergence plot viewer showing metric evolution across refinement levels, command-line interface producing convergence report files
- **Frequency:** After initial simulation runs on new antenna types or significantly modified designs; may be skipped for incremental design changes where prior convergence has been established.
- **Open Issues:** Should the system provide automated convergence acceleration (extrapolation to zero-mesh-size limit)? How to handle cases where different metrics converge at different rates, requiring conflicting refinement strategies?
