# UC-08: Implement RWG Basis Functions

* [ ] Implement RWG basis functions
* [ ] Create Jacobian calculations
* [ ] Support triangle properties
* [ ] Test orthogonality and integration accuracy
* [ ] Implement matrix assembly utilities

## CHARACTERISTIC INFORMATION

* **Goal in Context**: Implement Rao-Wilton-Glisson basis functions for surface currents
* **Scope**: RWG implementation, testing, matrix assembly
* **Level**: Core Implementation
* **Preconditions**: MoM formulations (UC-07), solvers (UC-06)
* **Success End Condition**: RWG functions integrate correctly, matrix assembly works
* **Failed End Condition**: Basis functions don't integrate or assemble correctly
* **Primary Actor**: Developer/AI Agent
* **Trigger**: After MoM formulation

## MAIN SUCCESS SCENARIO

1. Implement RWG basis functions:
   - Define function definitions
   - Calculate Jacobians
   - Support triangle properties
2. Create basis function tests:
   - Orthogonality verification
   - Integration accuracy checks
3. Implement matrix assembly:
   - System matrix construction using PETSc
   - Right-hand side vector setup
   - Source excitation handling
4. Add Green's function evaluation

## EXTENSIONS

1a. Step 2: Test with known analytical solutions
2a. Step 3: Support hierarchical basis functions

## SUB-VARIATIONS

1. Standard RWG vs hierarchical extensions
2. Triangle vs quadrilateral elements

## RELATED INFORMATION

* **Priority**: Critical - Essential for MoM

* **Frequency**: Used in every simulation matrix assembly
