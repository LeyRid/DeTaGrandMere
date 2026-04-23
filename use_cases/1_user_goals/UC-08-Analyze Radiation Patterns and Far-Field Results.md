# USE CASE UC-08-Analyze Radiation Patterns and Far-Field Results

**Context of use:** RF Antenna Engineer computes and interprets far-field radiation patterns from the near-field simulation solution, extracting key metrics including directivity, gain, front-to-back ratio, polarization characteristics, and beamwidth. This analysis determines whether the antenna radiates energy in the intended direction with sufficient strength and acceptable side-lobe levels.

**Scope:** EM Simulation System — System scope, black box

**Level:** User-goal

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants accurate far-field patterns that faithfully represent the antenna's radiation behavior in all directions, with extracted metrics for quantifying performance.
- System Owner: Wants far-field computation to be efficient — only at frequencies of interest, with appropriate angular resolution.
- Auditor (off-stage): Needs the near-to-far-field transformation parameters recorded so results can be independently verified.

**Precondition:** A simulation has been completed with converged current distribution on the antenna structure. Near-field data is available over a closed surface surrounding the antenna. The operating frequency for pattern computation is known.

**Minimal Guarantees:** Every far-field pattern calculation is logged with its source near-field data, transformation parameters, and the frequency at which it was computed. All extracted pattern metrics (directivity, gain, beamwidth) include their computation method so they can be reproduced.

**Success Guarantees:** Far-field radiation patterns are computed at all requested frequencies and angular resolutions. Key metrics are extracted: peak directivity and gain (accounting for efficiency losses), half-power beamwidth in E-plane and H-plane, front-to-back ratio, side-lobe levels, and polarization characteristics. Patterns are normalized to peak value and available in standard formats for comparison with measurements or other simulations.

**Trigger:** RF Antenna Engineer initiates far-field pattern computation on a completed simulation with available near-field data.

## Main Success Scenario

1. RF Antenna Engineer: selects the frequency(ies) at which to compute far-field patterns.
2. System: performs the near-to-far-field transformation using the computed surface currents and Green's function propagation.
3. System: computes radiation intensity in all directions over a spherical coordinate grid (theta, phi).
4. RF Antenna Engineer: selects pattern display options (polar plot, Cartesian plot, 3D radiation sphere) and planes of interest (E-plane, H-plane, or custom cut).
5. System: generates the radiation pattern plots with normalized amplitude (0 dB at peak).
6. System: extracts key metrics — directivity, gain (with efficiency factor), front-to-back ratio, half-power beamwidth, and side-lobe levels.
7. RF Antenna Engineer: reviews the patterns and metrics to assess whether radiation characteristics meet design requirements.
8. System: stores all pattern data, extracted metrics, and display settings in the project results store.

## Extensions

1a. Only a single frequency is specified but the simulation computed multiple frequencies:
   - System offers to compute patterns at all computed frequencies or allows engineer to select specific ones.
   - RF Antenna Engineer: chooses which frequencies to include.
   - Execution resumes at step 2 with the selected frequencies.

2a. Near-field data surface is too close to the antenna for accurate far-field transformation:
   - System warns that the observation surface should be at least several wavelengths from the antenna and suggests re-running the simulation with a larger domain.
   - RF Antenna Engineer: adjusts the simulation domain size and re-runs, or proceeds with caution noting reduced accuracy.
   - If proceeding: execution resumes at step 2 with an accuracy warning flag.

3a. Computed directivity seems unphysically high (exceeding theoretical limits for the antenna type):
   - System flags the value and suggests checking mesh quality near edges, boundary condition settings, or material assignments that may cause artificial field enhancement.
   - RF Antenna Engineer: investigates the flagged settings or accepts the result if justified by the antenna design.
   - Execution resumes at step 5 with the anomaly noted in metadata.

4a. Gain is significantly lower than directivity (efficiency < 50%):
   - System highlights that losses are high and suggests checking conductor conductivity, dielectric loss tangent values, and surface roughness settings.
   - RF Antenna Engineer: reviews material properties for accuracy or accepts the efficiency as representing a real-world lossy design.
   - Execution resumes at step 5 with low efficiency noted in results.

5a. Engineer wants patterns at multiple angular resolutions:
   - System allows specifying coarse resolution (for quick overview, e.g., 10-degree steps) and fine resolution (for detailed analysis, e.g., 1-degree steps around the main beam).
   - RF Antenna Engineer: defines the resolution strategy per plane or per frequency.
   - Execution resumes at step 2 with multi-resolution data computed.

6a. Polarization analysis is requested:
   - System decomposes the far-field into orthogonal polarization components and computes axial ratio, polarization ellipse parameters, and cross-polarization discrimination.
   - RF Antenna Engineer: selects which polarization metrics to include in the report.
   - Execution resumes at step 6 with polarization data appended to the metric extraction.

## Technology and Data Variations List

- Step 2: Near-to-far-field transformation uses the equivalence principle — surface currents on a closed boundary are integrated against the free-space Green's function G(r,r') = e^(-jkR)/(4piR) to compute fields at far-field observation points.
- Step 3: Angular grid resolution determines pattern accuracy. Typical default is 5-degree steps; resonance regions and high-gain antennas may require 1-degree steps for accurate beamwidth measurement.
- Step 6: Directivity D = 4pi / Omega_A where Omega_A is the beam solid angle. Gain G = eta * D where eta is radiation efficiency accounting for conductor and dielectric losses.

## Related Information

- **Priority:** 2 (high — core analysis task; critical for antenna performance evaluation)
- **Channels:** Desktop application with interactive 3D radiation sphere, polar/Cartesian plot viewers, command-line interface producing pattern data files
- **Frequency:** After every simulation where far-field results are needed; typically computed at a subset of the frequency sweep points (only at frequencies of engineering interest).
- **Open Issues:** Should the system support automated pattern comparison with measured data? How to handle patterns for electrically large structures (>10 lambda) where PO or GTD methods would be more efficient than full-wave computation?
