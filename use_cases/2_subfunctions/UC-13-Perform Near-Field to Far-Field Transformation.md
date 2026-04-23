# USE CASE UC-13-Perform Near-Field to Far-Field Transformation

**Context of use:** The transformation component converts the computed near-field solution (surface current distribution on the antenna structure) into far-field radiation patterns at specified observation directions. This uses the equivalence principle and Green's function propagation to project near-field data to the far-field region where waves are approximately spherical and can be characterized by angular-dependent gain and polarization.

**Scope:** EM Simulation System — Subsystem scope, black box (transformation component)

**Level:** Subfunction

**Primary Actor:** Solver Engine (automated)

**Stakeholders & Interests:**
- RF Antenna Engineer (off-stage): Wants accurate far-field patterns computed efficiently, with the option to control angular resolution based on the intended use (quick overview vs. detailed publication-quality plots).
- System Owner: Wants transformation computation to be cached and reused when the same near-field solution is needed at multiple observation resolutions.

**Precondition:** A converged current distribution [I] exists on the antenna mesh from a completed solver run (UC-12). The operating frequency is known. Observation directions (angular grid) have been specified or will use default values.

**Minimal Guarantees:** Every transformation is logged with its source current data, observation angles, frequency, and the Green's function parameters used. Computed far-field values include both magnitude and phase information so that interference calculations and array factor computations can be performed externally.

**Success Guarantees:** Far-field radiation patterns are computed at all requested observation directions with accurate amplitude (in dB relative to peak) and phase values for both orthogonal polarization components. The transformation correctly accounts for the 1/R distance decay and e^(-jkR) phase delay from each radiating element to each observation point. Results are available in standard formats for pattern plotting and metric extraction.

**Trigger:** Transformation component receives a converged current distribution, operating frequency, and set of observation directions.

## Main Success Scenario

1. Transformation: computes the free-space Green's function G(r,r') = e^(-jkR) / (4piR) for each source-observation point pair, where R is the distance between the mesh element center and the observation direction projected onto a sphere of radius r.
2. Transformation: integrates the surface currents against the Green's function over all mesh elements to compute the radiated electric field E(theta, phi) at each observation angle.
3. Transformation: computes the magnetic field H(theta, phi) from E using the intrinsic impedance of free space (eta_0 = 377 ohms).
4. Transformation: calculates radiation intensity U(theta, phi) = (r^2 / 2*eta_0) * |E(theta, phi)|^2 at each observation point.
5. Transformation: normalizes the radiation pattern to peak value and computes derived metrics — directivity D = 4pi * U_max / integral(U dOmega), gain G = eta_rad * D where eta_rad is the radiation efficiency.
6. Transformation: outputs the complete far-field data set including E-field magnitude, phase, polarization components, directivity, and gain at all observation angles.

## Extensions

1a. Observation directions are not specified:
   - Transformation defaults to a uniform spherical grid with 5-degree angular resolution in both theta (0 to 180 degrees) and phi (0 to 360 degrees), producing approximately 11,500 observation points.
   - Execution resumes at step 2 with the default grid.

2a. Current distribution is not converged or is incomplete:
   - Transformation rejects the input and reports that far-field computation requires a fully converged current solution from UC-12.
   - RF Antenna Engineer: runs the solver first to obtain converged currents.
   - Execution ends at failure exit.

3a. Observation sphere radius is too small (less than 2 lambda from the antenna):
   - Transformation warns that the far-field approximation (R >> lambda) is violated and results may contain near-field contamination artifacts.
   - RF Antenna Engineer: increases the observation radius or accepts the result with reduced accuracy.
   - If accepted: execution resumes at step 2 with an accuracy warning flag.

5a. Radiation efficiency cannot be determined (material loss data is missing or incomplete):
   - Transformation computes directivity but flags gain values as unavailable, noting that eta_rad could not be computed due to missing loss parameters.
   - RF Antenna Engineer: provides the missing material loss data (conductivity, loss tangent) and re-runs the transformation.
   - Execution resumes at step 5 with efficiency data.

## Technology and Data Variations List

- Step 1: Green's function computation may be cached for repeated source-observation pairs when performing multi-frequency or multi-resolution pattern sweeps. For electrically large structures (>10 lambda), fast multipole method (FMM) acceleration reduces the O(N*M) complexity to approximately O(N log N).
- Step 5: Directivity integration uses numerical quadrature over the spherical surface. Default is Simpson's rule with the angular grid spacing; higher accuracy requires finer angular resolution or adaptive quadrature around sharp pattern features.

## Related Information

- **Priority:** 2 (important subfunction — essential for radiation pattern analysis but invoked only when far-field results are needed)
- **Channels:** Invoked internally by UC-08 (Analyze Radiation Patterns and Far-Field Results); may be invoked directly for batch processing of multiple frequencies.
- **Frequency:** Once per frequency point where far-field patterns are required; typically a subset of all swept frequencies.
- **Related Use Cases:** Called by UC-08 (Analyze Radiation Patterns and Far-Field Results); consumes output from UC-12 (Solve Impedance Matrix Using Numerical Solver).
