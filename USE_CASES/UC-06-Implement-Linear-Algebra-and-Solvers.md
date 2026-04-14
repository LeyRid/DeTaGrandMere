# UC-06: Implement Linear Algebra & Solvers

* [ ] Implement sparse matrix structures using PETSc
* [ ] Add preconditioners (ILU, multigrid)
* [ ] Implement iterative solvers (GMRES, BiCGStab)
* [ ] Create convergence monitoring
* [ ] Test solver on benchmark problems

## CHARACTERISTIC INFORMATION

* **Goal in Context**: Build core numerical solver infrastructure
* **Scope**: PETSc integration, sparse matrices, iterative solvers
* **Level**: Core Implementation
* **Preconditions**: Material and boundary setup (UC-05)
* **Success End Condition**: Solvers converge on test problems with preconditioners
* **Failed End Condition**: Solvers diverge or converge too slowly
* **Primary Actor**: Developer/AI Agent
* **Trigger**: After physics setup

## MAIN SUCCESS SCENARIO

1. Implement sparse matrix structures:
   - Use PETSc for sparse matrices
   - Create matrix assembly utilities
2. Add preconditioners:
   - ILU (Incomplete LU) via PETSc
   - Multigrid support
3. Implement iterative solvers:
   - GMRES (via PETSc)
   - BiCGStab (via PETSc)
   - Convergence monitoring
4. Create linear algebra testing suite
5. Test solvers on benchmark problems

## EXTENSIONS

1a. Step 2: Add AMG (Algebraic Multigrid) preconditioner
2a. Step 3: Implement adaptive stopping criteria

## SUB-VARIATIONS

1. Direct vs iterative solvers
2. Single precision vs double precision

## RELATED INFORMATION

* **Priority**: Critical - Core of MoM solver
* **Performance Target**: Complete within 2 weeks
* **Frequency**: Used in every simulation solve
