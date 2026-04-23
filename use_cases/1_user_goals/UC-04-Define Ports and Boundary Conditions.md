# USE CASE UC-04-Define Ports and Boundary Conditions

**Context of use:** RF Antenna Engineer defines the electrical ports (excitation points) and boundary conditions (simulation domain limits) for an antenna simulation. This determines how energy enters the structure and how the finite computational domain approximates infinite free space. Incorrect port or boundary settings are among the most common causes of inaccurate results.

**Scope:** EM Simulation System — System scope, black box

**Level:** User-goal

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants ports and boundaries configured to accurately represent the physical feed structure and radiation environment so simulation matches real-world behavior.
- System Owner: Wants invalid configurations detected before solver execution to prevent wasted computation.
- Auditor (off-stage): Needs a record of port types, sizes, orientations, and boundary condition choices for reproducibility.

**Precondition:** Geometry has been imported and material properties assigned. The engineer knows the operating frequency or frequency range of the antenna.

**Minimal Guarantees:** All port definitions are recorded with their location, size, type, and orientation. All boundary conditions are recorded with their region assignment and parameter values. Any configuration that violates physical constraints is rejected with an explanation.

**Success Guarantees:** Every feed point on the antenna has a properly sized and oriented port assigned. The simulation domain boundary uses appropriate absorbing conditions (radiation boundary or PML) at sufficient distance from the antenna. All settings are validated against wavelength-based minimum size requirements.

**Trigger:** RF Antenna Engineer initiates port and boundary configuration for an imported geometry.

## Main Success Scenario

1. RF Antenna Engineer: selects the feed location(s) on the antenna geometry where ports will be placed.
2. System: calculates the operating wavelength from the specified frequency and determines minimum recommended port size (lambda/10).
3. RF Antenna Engineer: specifies the port type (lumped or waveguide) and confirms port dimensions.
4. System: validates that each port meets minimum size requirements and is positioned on a valid surface or edge of the geometry.
5. RF Antenna Engineer: selects boundary condition types for the simulation domain outer surfaces (radiation boundary, PML, PEC, or PMC).
6. System: verifies boundary condition selections are physically appropriate for the antenna type and domain size.
7. System: records all port and boundary configurations in the project metadata store.

## Extensions

1a. No feed location is visible on the geometry (e.g., aperture-coupled or proximity-fed structure):
   - System offers alternative port definition methods (waveguide port on an opening, lumped port across a gap).
   - RF Antenna Engineer: selects an appropriate alternative method and specifies the excitation region.
   - Execution resumes at step 2.

2a. Specified frequency is outside the system's supported range:
   - System reports the supported frequency range (e.g., 100 MHz to 100 GHz) and suggests adjusting the operating point.
   - RF Antenna Engineer: provides a valid frequency or cancels configuration.
   - If cancelled: execution ends at failure exit.

3a. Port dimensions are below the minimum recommended size for the wavelength:
   - System warns that the port may not capture the fundamental mode accurately and shows the minimum recommended size.
   - RF Antenna Engineer: increases port dimensions or confirms the smaller size with an understanding of the risk.
   - If confirmed: execution resumes at step 4 with a warning flag in metadata.

4a. Port placement conflicts with existing geometry features (port overlaps radiating element, port crosses material boundary):
   - System highlights the conflict and suggests valid alternative locations.
   - RF Antenna Engineer: moves the port to a non-conflicting location.
   - Execution resumes at step 3.

5a. Boundary condition selection is inappropriate for the problem type (e.g., PEC on outer boundary for radiation problem):
   - System warns that PEC on the outer boundary will create artificial reflections and recommends radiation boundary or PML.
   - RF Antenna Engineer: selects a more appropriate boundary condition type.
   - Execution resumes at step 5.

6a. PML thickness is insufficient (less than one wavelength):
   - System warns that inadequate PML thickness causes residual reflections and recommends the minimum thickness.
   - RF Antenna Engineer: increases PML thickness or confirms the reduced value.
   - If confirmed: execution resumes at step 7 with a warning flag.

## Technology and Data Variations List

- Step 3: Lumped port models a voltage source with series impedance, suitable for structures smaller than lambda/10. Waveguide port uses modal expansion and is required for waveguide feeds and larger structures.
- Step 5: Boundary condition options include PEC (perfect electric conductor), PMC (perfect magnetic conductor), radiation boundary (absorbs outgoing waves at finite distance), and PML (perfectly matched layer with graded damping).
- Step 6: For small structures under 10 lambda, a radiation boundary is adequate. For larger structures, PML provides better accuracy with its smooth damping profile.

## Related Information

- **Priority:** 1 (critical — port and boundary errors are the #1 cause of inaccurate antenna simulations)
- **Channels:** Desktop application with interactive 3D geometry viewer, command-line interface with configuration file
- **Frequency:** Once per simulation setup; may be revisited during iterative design optimization.
- **Open Issues:** Should the system auto-suggest port types based on geometry analysis? How to handle multi-port mutual coupling calculations automatically?
