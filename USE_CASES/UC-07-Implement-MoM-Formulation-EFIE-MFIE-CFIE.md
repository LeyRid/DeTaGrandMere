# UC-07: Implement MoM Formulation (EFIE/MFIE/CFIE)

* [ ] Implement Electric Field Integral Equation (EFIE)
* [ ] Implement Magnetic Field Integral Equation (MFIE)
* [ ] Implement Combined Field Integral Equation (CFIE)
* [ ] Create mathematical reference for each formulation
* [ ] Verify formulations against literature

## CHARACTERISTIC INFORMATION

* **Goal in Context**: Implement core MoM integral equation formulations
* **Scope**: EFIE, MFIE, CFIE implementation and verification
* **Level**: Core Implementation
* **Preconditions**: Linear algebra solvers (UC-06)
* **Success End Condition**: All three formulations implemented and verified
* **Failed End Condition**: Formulations don't match theoretical expectations
* **Primary Actor**: Developer/AI Agent
* **Trigger**: After solver infrastructure

## MAIN SUCCESS SCENARIO

1. Implement EFIE formulation:
   - Define surface current unknowns
   - Implement Green's function integration
   - Define testing procedure
2. Implement MFIE formulation:
   - Implement local operators
   - Define testing procedure
3. Implement CFIE (combination of EFIE+MFIE)
4. Create mathematical reference for each formulation
5. Verify formulations against published literature

## EXTENSIONS

1a. Step 1: Add rooftop basis functions variant
2a. Step 3: Implement various CFIE weighting schemes

## SUB-VARIATIONS

1. Electric field vs magnetic field formulation
2. Closed vs open surfaces

## RELATED INFORMATION

* **Priority**: Critical - Core MoM implementation

* **Frequency**: One-time implementation per problem type
