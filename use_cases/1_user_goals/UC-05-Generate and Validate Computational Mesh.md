# USE CASE UC-05-Generate and Validate Computational Mesh

**Context of use:** RF Antenna Engineer generates a computational mesh for the antenna geometry and validates its quality before solver execution. The mesh is the critical link between the physical geometry and the numerical solution — poor mesh quality directly causes inaccurate or divergent results. This use case covers both initial mesh generation and adaptive refinement based on solution feedback.

**Scope:** EM Simulation System — System scope, black box

**Level:** User-goal

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants a mesh that accurately captures field variations (especially near feed points, edges, and material interfaces) without excessive element count that would waste computational resources.
- System Owner: Wants mesh generation to respect memory and time constraints while maintaining acceptable accuracy.
- Auditor (off-stage): Needs mesh quality metrics recorded for each simulation run to support reproducibility claims.

**Precondition:** Geometry has been imported and validated. Material properties are assigned. Ports and boundary conditions are defined. The operating frequency is known so that wavelength-dependent mesh sizing can be calculated.

**Minimal Guarantees:** Every element in the generated mesh is logged with its size, aspect ratio, and skewness metrics. Mesh quality violations (degenerate elements, excessive aspect ratio) are reported before solver execution. All mesh parameters used for generation are recorded in project metadata.

**Success Guarantees:** The computational mesh covers all geometry surfaces and volumes with element sizes that satisfy wavelength-based requirements (lambda/20 in general regions, lambda/100 near feed points and singularities). Mesh quality metrics meet acceptance criteria (aspect ratio < 3:1 for most elements, skewness < 0.5). No degenerate elements exist. The engineer can proceed to solver execution with confidence in mesh adequacy.

**Trigger:** RF Antenna Engineer initiates mesh generation for the configured antenna simulation.

## Main Success Scenario

1. RF Antenna Engineer: specifies global and local mesh sizing parameters based on operating frequency and geometry features.
2. System: calculates wavelength at the operating frequency and derives element size requirements (lambda/20 general, lambda/100 critical regions).
3. System: generates the initial mesh using the specified quality criteria and refinement targets.
4. System: computes mesh quality metrics for all elements — element size, aspect ratio, skewness, and volume.
5. RF Antenna Engineer: reviews mesh quality report identifying any elements that violate acceptance criteria.
6. System: displays flagged elements in the 3D viewer with their specific quality violations highlighted.
7. RF Antenna Engineer: adjusts mesh parameters for flagged regions (manual refinement) or enables adaptive meshing to automatically refine high-error areas.
8. System: re-generates or refines the mesh and re-evaluates quality metrics until all elements meet acceptance criteria.

## Extensions

1a. Engineer does not specify local refinement targets:
   - System applies default refinement rules (lambda/50 near edges and corners, lambda/100 at feed points).
   - Execution resumes at step 2 with defaults noted in metadata.

2a. Operating frequency is a range rather than a single value:
   - System uses the longest wavelength (lowest frequency) for mesh sizing to ensure adequacy across the entire band.
   - RF Antenna Engineer: may override by specifying a separate fine-mesh frequency for resonance regions.
   - Execution resumes at step 3.

3a. Mesh generation fails due to geometry complexity (too many small features, extreme aspect ratios in CAD):
   - System reports the specific geometric feature causing failure and suggests simplification options.
   - RF Antenna Engineer: simplifies the geometry externally or reduces refinement intensity.
   - Execution resumes at step 3 with corrected inputs.

4a. Mesh quality report shows elements exceeding acceptance criteria (aspect ratio > 3:1, skewness > 0.5):
   - System offers automatic remeshing with adjusted quality parameters or manual element-level correction.
   - RF Antenna Engineer: chooses automatic remeshing with stricter criteria or accepts some violations for non-critical regions.
   - If automatic: execution resumes at step 3 with new parameters.

5a. Adaptive meshing is enabled but the solution has not yet been computed (no error indicators available):
   - System performs an initial coarse solve to generate error indicators, then refines based on field gradients and current variations.
   - RF Antenna Engineer: approves the adaptive refinement strategy and its target error threshold.
   - Execution resumes at step 3 with the refined mesh.

6a. Mesh element count exceeds available memory or specified maximum:
   - System reports the element count versus the limit and suggests coarsening low-error regions.
   - RF Antenna Engineer: authorizes selective coarsening of elements in uniform field regions.
   - Execution resumes at step 7 with coarsened mesh.

## Technology and Data Variations List

- Step 3: Mesh generation may use CGAL for Delaunay triangulation and quality-controlled surface meshes, or an internal mesher with RWG-compatible triangle basis functions.
- Step 4: Quality metrics include element size relative to wavelength, aspect ratio (max edge / min edge), skewness (deviation from ideal equilateral triangle), and volume positivity.
- Step 7: Adaptive refinement strategies include error-indicator-based refinement (current density variation, field gradient magnitude, Green's function proximity) and geometry-based refinement (fixed-size rules for feed points, edges, corners).

## Related Information

- **Priority:** 1 (critical — mesh quality directly determines solution accuracy; under-refined meshes cause >5% S-parameter error and oscillatory radiation patterns)
- **Channels:** Desktop application with interactive mesh visualization, command-line interface with configuration file
- **Frequency:** Once per simulation setup, plus additional refinement cycles during adaptive or iterative workflows.
- **Open Issues:** Should the system support h-refinement (element subdivision), p-refinement (basis function order increase), or hp-adaptive strategies? How to handle multi-scale geometries with features spanning orders of magnitude in size?
