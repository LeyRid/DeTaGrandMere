# USE CASE UC-15-Manage Material Properties and Boundary Conditions

**Context of use:** The material and boundary component manages the library of electromagnetic material properties (permittivity, permeability, conductivity, loss tangent) and validates that boundary condition assignments are physically consistent with the geometry and simulation method. This subfunction supports UC-03 (Import Geometry and Define Materials) and UC-04 (Define Ports and Boundary Conditions) by providing centralized material management and automatic consistency checking.

**Scope:** EM Simulation System — Subsystem scope, black box (material/boundary component)

**Level:** Subfunction

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants a reliable material database with accurate electromagnetic properties and automatic validation of boundary condition assignments to prevent physically impossible configurations.
- System Owner: Wants material data integrity maintained — no corrupted or inconsistent entries that could produce silently wrong simulation results.
- Auditor (off-stage): Needs a complete record of all material assignments and boundary condition changes for reproducibility and traceability.

**Precondition:** The material database exists with at least basic material entries (free space, common conductors, standard dielectrics). Boundary condition types are defined in the system configuration.

**Minimal Guarantees:** Every material property entry is validated for physical plausibility before being accepted into the active database. Every boundary condition assignment is checked for consistency with the assigned region's geometry and material type. All changes to materials or boundaries are logged with timestamps and the engineer who made them.

**Success Guarantees:** All assigned materials have physically valid electromagnetic properties (positive permittivity, positive permeability, non-negative conductivity, loss tangent within [0, 1]). All boundary conditions are compatible with their assigned regions (PEC on conductors, radiation/PML on outer surfaces, no PMC on open-space problems). The engineer receives immediate feedback when an assignment is physically invalid.

**Trigger:** RF Antenna Engineer requests material assignment to a geometry region or boundary condition assignment to a simulation domain surface.

## Main Success Scenario

1. RF Antenna Engineer: selects a material from the database or creates a new custom material entry with electromagnetic properties.
2. System: validates that all material properties are physically plausible (positive real part of permittivity, positive permeability, non-negative conductivity, loss tangent in valid range).
3. RF Antenna Engineer: assigns the validated material to one or more geometry regions.
4. System: checks that the assigned material is appropriate for the region's geometry type (e.g., conductive material on metal surfaces, dielectric on substrate regions).
5. RF Antenna Engineer: selects a boundary condition type (PEC, PMC, radiation, PML) and assigns it to simulation domain surface(s).
6. System: validates that the boundary condition is physically appropriate for the region's location (e.g., radiation or PML on outer boundaries, not PEC on open-space surfaces).
7. System: records all material and boundary assignments in the project metadata store with timestamps and validation status.

## Extensions

1a. Material database lookup fails for a requested material name:
   - System searches for partial name matches and suggests the closest existing entries.
   - RF Antenna Engineer: selects a close match or creates a new custom material.
   - If creating new: execution resumes at step 1 with the custom material entry form.

2a. Material properties are physically invalid (negative permittivity, conductivity exceeding physical limits for solids):
   - System rejects the assignment and displays acceptable ranges for each property type with physical context (e.g., "conductivity of copper is approximately 5.8e7 S/m").
   - RF Antenna Engineer: corrects the material property values.
   - Execution resumes at step 1 with corrected values.

4a. Material assignment conflicts with existing geometry metadata (e.g., a region labeled as 'copper' in CAD is assigned a dielectric material):
   - System flags the conflict and asks whether to override the CAD metadata or follow it.
   - RF Antenna Engineer: chooses to override (intentional modification) or accept the CAD label.
   - If overriding: execution resumes at step 3 with the override noted in metadata.

5a. Boundary condition assignment is physically inappropriate for the region location (e.g., PEC on outer radiation boundary):
   - System warns that the selected boundary condition will produce unphysical results and recommends the appropriate type for the region's position relative to the antenna.
   - RF Antenna Engineer: selects the recommended boundary condition or confirms the original choice with acknowledgment of expected artifacts.
   - If confirmed: execution resumes at step 6 with a warning flag in metadata.

6a. PML boundary is assigned without specifying thickness:
   - System uses the default PML thickness (1 wavelength at the lowest operating frequency) and reports this to the engineer.
   - RF Antenna Engineer: may override the thickness if specific requirements exist.
   - Execution resumes at step 7 with the specified or default thickness recorded.

## Technology and Data Variations List

- Step 1: Material database entries include frequency-dependent properties (dispersion models: Debye, Lorentz, Drude), temperature-dependent properties, and isotropic vs. anisotropic material tensors. Built-in materials cover common RF engineering substances (copper, aluminum, gold, FR4, Rogers substrates, air, vacuum).
- Step 5: Boundary condition types and their physical meanings: PEC (tangential E-field = 0, currents flow on surface), PMC (normal H-field = 0, rarely used in open-space problems), radiation boundary (absorbs outgoing waves at finite distance, good for structures < 10 lambda), PML (graded complex permittivity/permeability absorbing waves with near-zero reflection, requires >= 1 wavelength thickness).

## Related Information

- **Priority:** 2 (important subfunction — material and boundary errors are among the most common causes of simulation inaccuracies)
- **Channels:** Invoked internally by UC-03 and UC-04; may be invoked directly for batch material library management.
- **Frequency:** Once per simulation setup during initial configuration; revisited during iterative design changes that modify materials or domain boundaries.
- **Related Use Cases:** Called by UC-03 (Import Geometry and Define Materials) and UC-04 (Define Ports and Boundary Conditions); produces validated assignments consumed by UC-05 (Generate and Validate Computational Mesh) and UC-12 (Solve Impedance Matrix Using Numerical Solver).
