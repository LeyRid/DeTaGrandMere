# USE CASE UC-03-Import Geometry and Define Materials

**Context of use:** RF Antenna Engineer imports an antenna geometry file into the EM Simulation System and assigns correct material properties to all regions before running any simulation. This is the essential first step for every simulation workflow.

**Scope:** EM Simulation System — System scope, black box

**Level:** User-goal

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants geometry imported correctly with accurate material properties so that simulation results reflect the intended physical design.
- System Owner: Wants invalid or corrupted geometry files detected early to avoid wasted computational resources on downstream steps.
- Auditor (off-stage): Needs a record of which geometry file and material assignments were used for each simulation run.

**Precondition:** Antenna geometry file exists in a supported format (STEP, STL, or OBJ). The engineer has the material property specifications for all components of the antenna design.

**Minimal Guarantees:** Every imported geometry file is logged with its source path, import timestamp, and validation status. All material assignments are recorded so they can be audited or restored later.

**Success Guarantees:** Geometry is fully loaded into the simulation environment with all faces, edges, and volumes correctly identified. Every region has appropriate material properties assigned (conductivity, permittivity, permeability, loss tangent). The system reports geometry validation status confirming no degenerate elements exist.

**Trigger:** RF Antenna Engineer selects a geometry file to load into the simulation system.

## Main Success Scenario

1. RF Antenna Engineer: opens the geometry import dialog and selects an antenna geometry file.
2. System: reads the file and parses its geometric data (vertices, faces, edges, volumes).
3. System: validates geometric integrity — checks for degenerate faces, non-manifold edges, and self-intersections.
4. RF Antenna Engineer: reviews geometry validation results and confirms the structure is loadable.
5. System: displays the loaded geometry in a 3D viewer with region identification labels.
6. RF Antenna Engineer: assigns material properties to each geometric region based on the design specification.
7. System: verifies that all regions have material assignments and that assigned properties are physically valid (positive permittivity, appropriate conductivity ranges).
8. System: records the complete geometry-material mapping in the project metadata store.

## Extensions

3a. Geometry file format is not supported:
   - System rejects the file and displays a list of supported formats with their characteristics and fidelity levels.
   - RF Antenna Engineer: converts the file to a supported format using an external tool or selects a different file.
   - Execution resumes at step 1.

3b. Geometry validation detects errors (degenerate faces, gaps, overlapping surfaces):
   - System highlights each error in the 3D viewer and provides a textual description of the issue.
   - RF Antenna Engineer: chooses to attempt automatic repair, manually correct the geometry externally, or proceed with warnings for non-critical issues.
   - If proceeding with warnings: execution resumes at step 4 with flagged regions noted in metadata.

5a. Geometry contains multiple disconnected bodies that need separate treatment:
   - System identifies each disconnected body and presents them as separate selectable regions.
   - RF Antenna Engineer: confirms the identification or merges/splits bodies as needed.
   - Execution resumes at step 6.

6a. Material database lookup fails for a specified material name:
   - System offers to create a custom material entry with manually entered properties.
   - RF Antenna Engineer: provides permittivity, permeability, conductivity, and loss tangent values.
   - Execution resumes at step 6 with the new custom material assigned.

7a. Assigned material properties are physically invalid (negative permittivity, conductivity exceeding physical limits):
   - System rejects the assignment and displays acceptable ranges for each property type.
   - RF Antenna Engineer: corrects the material property values.
   - Execution resumes at step 6.

## Technology and Data Variations List

- Step 1: Supported input formats include STEP (full B-rep with topological data), STL (surface triangulation only), and OBJ (polygon mesh with optional texture coordinates).
- Step 2: File parsing may use OpenCASCADE kernel for STEP files or a lightweight parser for STL/OBJ.
- Step 6: Material properties may come from a built-in database, a user-defined material library file, or manual entry.

## Related Information

- **Priority:** 1 (highest — no simulation can proceed without valid geometry and materials)
- **Channels:** Desktop application with 3D viewer, command-line interface with file path argument
- **Frequency:** Every new simulation; the same geometry may be reused across many simulation runs.
- **Open Issues:** Should the system auto-detect material types from geometry metadata? How to handle frequency-dependent material properties (dispersion)?
