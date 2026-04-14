# UC-12: Calculate Antenna Metrics

* [ ] Implement gain calculation
* [ ] Implement directivity calculation (D = 4πU/Prad)
* [ ] Implement radiation efficiency (η)
* [ ] Implement front-to-back ratio
* [ ] Add bandwidth analysis (S11 threshold, impedance matching)
* [ ] Identify resonant frequencies

## CHARACTERISTIC INFORMATION

* **Goal in Context**: Compute key antenna performance metrics from simulation results
* **Scope**: Gain, directivity, efficiency, bandwidth
* **Level**: Post-Processing
* **Preconditions**: Field visualization (UC-11)
* **Success End Condition**: Metrics calculated and verified against theory
* **Failed End Condition**: Metrics incorrect or don't match expected values
* **Primary Actor**: Developer/AI Agent
* **Trigger**: After field calculations

## MAIN SUCCESS SCENARIO

1. Implement antenna metrics:
   - Directivity (D = 4πU/Prad)
   - Gain (G = η × D)
   - Radiation efficiency (η)
   - Front-to-back ratio
2. Add bandwidth analysis:
   - S11 threshold crossing detection
   - Impedance matching calculation
   - Resonant frequency identification
3. Create performance reports

## EXTENSIONS

1a. Step 1: Add additional metrics (axial ratio, beamwidth)
2a. Step 2: Implement automated bandwidth optimization

## SUB-VARIATIONS

1. Narrowband vs wideband analysis
2. Single metric vs comprehensive report

## RELATED INFORMATION

* **Priority**: Medium - Important for user analysis
* **Performance Target**: Complete within 1 week
* **Frequency**: After each simulation
