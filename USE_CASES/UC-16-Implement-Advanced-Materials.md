# UC-16: Implement Advanced Materials

* [ ] Implement Debye/Cole-Cole frequency-dependent models
* [ ] Implement Drude/Lorentz dispersive materials
* [ ] Support anisotropic permittivity/permeability
* [ ] Add multi-port excitation
* [ ] Implement coupled ports analysis
* [ ] Add broadband frequency sweep

## CHARACTERISTIC INFORMATION

* **Goal in Context**: Support advanced material models and excitations
* **Scope**: Advanced materials, multi-port, broadband
* **Level**: Advanced Features
* **Preconditions**: Basic solver working (UC-09)
* **Success End Condition**: Dispersion models work, multi-port S-parameters computed
* **Failed End Condition**: Models don't converge or produce incorrect results
* **Primary Actor**: Developer/AI Agent
* **Trigger**: After basic solver complete

## MAIN SUCCESS SCENARIO

1. Implement advanced materials:
   - Debye/Cole-Cole models
   - Drude/Lorentz dispersive materials
   - Anisotropic permittivity/permeability
2. Add multi-port excitation:
   - Multiple sources
   - Coupled ports
   - Power distribution analysis
3. Implement time-domain solver (FDTD)
4. Add broadband frequency sweep

## EXTENSIONS

1a. Step 1: Support user-defined material models
2a. Step 3: Implement FDTD-MoM hybrid

## SUB-VARIATIONS

1. Lossy vs lossless materials
2. Linear vs nonlinear materials

## RELATED INFORMATION

* **Priority**: Low - Advanced use cases
* **Performance Target**: Complete within 3 weeks
* **Frequency**: Optional advanced feature
