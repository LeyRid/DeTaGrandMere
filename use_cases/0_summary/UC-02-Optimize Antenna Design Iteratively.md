# USE CASE UC-02-Optimize Antenna Design Iteratively

**Context of use:** RF Antenna Engineer iteratively refines an antenna design based on simulation feedback, adjusting geometry parameters, material properties, and mesh settings across multiple simulation cycles until performance targets are met. This use case encompasses the full optimization loop spanning many individual simulation runs.

**Scope:** EM Simulation System — Enterprise scope (spanning multiple simulation sessions over days or weeks)

**Level:** Summary

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants to converge on an optimal antenna design with minimal manual trial-and-error, preserving intermediate results for comparison.
- System Owner: Wants efficient resource utilization across many simulation iterations without data loss between sessions.
- Auditor (off-stage): Needs complete record of all design changes and corresponding performance metrics for traceability.
- Simulation Archive (supporting actor): Maintains version history of designs and their associated results for comparative analysis.

**Precondition:** At least one baseline antenna simulation has been completed with validated results. The engineer has defined performance targets (e.g., S11 < -10 dB over specified bandwidth, minimum gain threshold, acceptable radiation pattern shape).

**Minimal Guarantees:** Every design iteration and its associated simulation results are stored with full parameter history so that any previous design state can be restored. All computational resources consumed by optimization runs are logged for cost tracking.

**Success Guarantees:** Engineer reaches a design that satisfies all defined performance targets or determines that no feasible solution exists within the current design space. Complete comparison data across all iterations is available, showing how each parameter change affected each metric.

**Trigger:** RF Antenna Engineer initiates an iterative optimization session from an existing antenna design with baseline simulation results.

## Main Success Scenario

1. RF Antenna Engineer: selects a baseline design and its associated simulation results for optimization.
2. System: presents current performance metrics against defined targets, highlighting areas of concern.
3. RF Antenna Engineer: identifies parameters to modify (dimensions, materials, feed position, etc.).
4. System: generates the modified geometry and prepares an updated simulation configuration.
5. RF Antenna Engineer: confirms changes and initiates the next simulation run.
6. System: executes the simulation using the optimized workflow (UC-01).
7. System: computes new performance metrics and compares them to previous iteration results.
8. RF Antenna Engineer: reviews comparison data and decides whether to continue optimizing or accept current design.
9. System: archives all iteration data, creates a design evolution report showing parameter changes versus performance improvements.

## Extensions

2a. No baseline simulation exists for the selected design:
   - System prompts engineer to run an initial simulation first.
   - Execution transfers to UC-01-Run Electromagnetic Simulation.
   - Upon completion, execution resumes at step 3 with freshly generated metrics.

3a. Engineer wants to optimize multiple parameters simultaneously:
   - System offers parameter sweep or automated optimization tool (if available).
   - RF Antenna Engineer: chooses manual adjustment per iteration or enables automated search.
   - If automated: system generates a sequence of design variants and runs them in parallel where possible.

4a. Modified geometry fails validation:
   - System rejects the geometry change with specific error details.
   - RF Antenna Engineer: corrects the parameter values and retries.
   - Execution resumes at step 4.

5a. Simulation fails or does not converge for the modified design:
   - System reports failure diagnostics and preserves previous iteration results intact.
   - RF Antenna Engineer: adjusts simulation settings, modifies geometry less aggressively, or abandons this parameter change.
   - Execution resumes at step 5 with corrected inputs.

7a. Performance metrics indicate degradation from previous iteration:
   - System flags the regression and highlights which specific metrics worsened.
   - RF Antenna Engineer: decides to revert parameters, try a different adjustment direction, or explore whether the degradation is acceptable for gains in other areas.
   - Execution resumes at step 8 with full comparison data displayed.

8a. Engineer determines that performance targets are met:
   - System generates a final design report with all relevant metrics, simulation settings, and geometry files ready for export.
   - Execution ends at success exit.

8b. Engineer determines that further optimization is needed but no clear direction exists:
   - System suggests exploring alternative design topologies or material configurations.
   - RF Antenna Engineer: chooses to explore new design space (new baseline) or continue with current parameters using different adjustment strategies.
   - Execution resumes at step 2 or transfers to UC-01 for a fresh simulation.

## Technology and Data Variations List

- Step 6: Simulation may use single-frequency point analysis for quick feedback or full frequency sweep for thorough evaluation.
- Step 7: Performance metrics may include S-parameters, gain, directivity, radiation efficiency, front-to-back ratio, and mutual coupling (for array antennas).
- Step 9: Design evolution report may be exported as PDF, HTML, or structured data file (JSON/CSV) for inclusion in documentation.

## Related Information

- **Priority:** 2 (high — core engineering workflow but depends on UC-01 being functional)
- **Channels:** Desktop application with interactive design parameter editor
- **Frequency:** Continuous throughout the design phase; may span weeks of iterative refinement.
- **Open Issues:** Should the system support machine-learning-based surrogate models for faster optimization? How to handle constraints from manufacturing capabilities (minimum feature size, material availability)?
