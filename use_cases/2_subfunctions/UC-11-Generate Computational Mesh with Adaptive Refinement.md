# USE CASE UC-11-Generate Computational Mesh with Adaptive Refinement

**Context of use:** The mesh generator component generates a computational mesh for the antenna geometry and performs adaptive refinement cycles based on error indicators computed from an initial solution. This is a subfunction invoked by UC-05 (Generate and Validate Computational Mesh) when manual mesh control is insufficient or when adaptive refinement is required for accuracy.

**Scope:** EM Simulation System — Subsystem scope, black box (mesh generator component)

**Level:** Subfunction

**Primary Actor:** Solver Engine (automated)

**Stakeholders & Interests:**
- Solver Engine: Needs a mesh with element sizes appropriate for the operating wavelength and quality metrics within acceptable bounds to produce accurate numerical solutions.
- RF Antenna Engineer (off-stage): Wants the mesh to automatically refine critical regions (feed points, edges, corners) without requiring manual intervention for every simulation.
- System Owner: Wants mesh generation to respect computational resource limits — element count should not grow unbounded during adaptive cycles.

**Precondition:** Geometry has been loaded with material properties assigned. The operating frequency is known so that wavelength-dependent sizing can be calculated. An initial coarse solution may or may not exist (for error-indicator-based refinement).

**Minimal Guarantees:** Every mesh element meets minimum quality criteria (aspect ratio < 3:1, skewness < 0.5, positive volume). No degenerate elements exist. The total element count is tracked and capped at a configurable maximum. All mesh generation parameters and quality metrics are logged.

**Success Guarantees:** The computational mesh covers the entire geometry with element sizes satisfying wavelength requirements (lambda/20 in general regions, lambda/100 at feed points and singularities). Adaptive refinement has been applied to all regions where error indicators exceed the target threshold. The resulting mesh enables the solver to achieve convergence within the specified tolerance.

**Trigger:** Mesh generator receives a geometry configuration with specified quality targets and an optional initial solution for error estimation.

## Main Success Scenario

1. Mesh Generator: calculates wavelength-based element size requirements from the operating frequency and geometry scale.
2. Mesh Generator: generates an initial surface mesh using Delaunay triangulation with quality criteria (aspect ratio, skewness bounds).
3. Mesh Generator: applies local refinement rules to critical regions — feed points (lambda/100), edges and corners (lambda/50), dielectric interfaces (lambda/20).
4. Mesh Generator: validates the mesh quality metrics across all elements and flags violations.
5. Mesh Generator: if an initial solution exists, computes error indicators for each element based on current density variation, field gradient magnitude, and Green's function proximity to sources.
6. Mesh Generator: refines elements where error indicators exceed the target threshold, coarsens elements in low-error regions.
7. Mesh Generator: re-validates mesh quality after refinement and checks that the total element count is within limits.
8. Mesh Generator: outputs the final mesh with all quality metrics and refinement history for downstream use by the solver.

## Extensions

1a. Wavelength cannot be determined (no frequency specified):
   - Mesh Generator rejects the configuration and requests the operating frequency or wavelength as input.
   - Execution ends at failure exit.

2a. Initial mesh generation fails due to geometric complexity (extreme aspect ratios in CAD, tiny features relative to overall size):
   - Mesh Generator reports the specific geometric feature causing failure and suggests geometry simplification options.
   - RF Antenna Engineer: simplifies the geometry or adjusts minimum feature size tolerance.
   - Execution resumes at step 2 with corrected inputs.

3a. Mesh quality validation detects violations that cannot be resolved by local refinement (e.g., globally poor element shapes):
   - Mesh Generator triggers a full remeshing pass with adjusted global quality parameters rather than incremental refinement.
   - RF Antenna Engineer: may adjust the global quality targets if the automatic adjustment is insufficient.
   - Execution resumes at step 2 with new global criteria.

5a. No initial solution exists for error indicator computation:
   - Mesh Generator skips the adaptive refinement cycle (steps 5-6) and proceeds directly to output with the geometry-based refined mesh from step 3.
   - RF Antenna Engineer: may later invoke an adaptive refinement pass after obtaining an initial solution.
   - Execution resumes at step 8.

6a. Error indicator computation produces inconsistent results (some elements flagged for refinement while neighbors are not, creating disconnected refinement regions):
   - Mesh Generator applies a smoothing pass to error indicators requiring that refinement regions be spatially contiguous.
   - RF Antenna Engineer: may adjust the minimum refinement region size if the smoothing is too aggressive.
   - Execution resumes at step 6 with smoothed indicators.

7a. Element count exceeds the maximum allowed after refinement:
   - Mesh Generator identifies the lowest-priority elements for coarsening (those in regions with the lowest error indicators and farthest from singularities) and coarsens them until the limit is satisfied.
   - RF Antenna Engineer: may increase the element count limit if accuracy requirements demand it.
   - Execution resumes at step 7 with the coarsened mesh.

## Technology and Data Variations List

- Step 2: Mesh generation may use CGAL for Delaunay surface triangulation with quality-controlled element shapes, or an internal mesher producing RWG-compatible triangle basis functions specifically optimized for Method of Moments.
- Step 5: Error indicator methods include current density variation (standard deviation of current across element boundaries), field gradient magnitude (norm of E and H field gradients), and Green's function proximity (inverse distance to source/feed points).

## Related Information

- **Priority:** 1 (critical subfunction — mesh quality directly determines solver accuracy)
- **Channels:** Invoked internally by UC-05; may also be invoked directly via command-line interface for batch mesh generation.
- **Frequency:** Once per simulation setup, plus additional adaptive cycles during refinement iterations.
- **Related Use Cases:** Called by UC-05 (Generate and Validate Computational Mesh); produces output consumed by UC-06 (Configure Solver and Run Frequency Sweep).
