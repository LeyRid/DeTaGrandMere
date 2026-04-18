"""MoM Solver Engine — assemble and solve the Method of Moments linear system.

This module provides the ``MOMSolver`` class which orchestrates the full MoM
simulation pipeline:

    1. Mesh setup with RWG basis functions
    2. Green's function evaluation for each matrix element pair
    3. Impedance matrix assembly (EFIE / MFIE / CFIE)
    4. Right-hand side construction from port excitations
    5. PETSc-backed iterative solve (GMRES / BiCGStab)
    6. Surface current extraction

Example usage::

    from src.core.mom_solver.solver_engine import MOMSolver
    from src.core.mom_solver.formulation import FormulationType

    solver = MOMSolver(
        formulation=FormulationType.EFIE,
        frequency=1e9,
        max_iterations=500,
        tolerance=1e-6,
    )
    solver.setup_mesh(mesh)  # mesh from CGALMeshing
    solver.compute_system_matrix()
    solver.solve(rhs_vector)
    currents = solver.extract_solution()
"""

from __future__ import annotations

import numpy as np
from typing import Optional
from enum import Enum

# Import local modules
from src.core.mom_solver.formulation import (
    IntegralEquationFormulation,
    FormulationType,
    get_formulation,
)
from src.core.mom_solver.basis_functions import Triangle, RWGBasisFunction, BasisFunctionManager
from src.core.mom_solver.green_function import GreensFunction, GreenEvaluator
from src.core.linear_algebra.solver import (
    LinearSolver,
    SolverType,
    create_solver,
    Preconditioner,
)
from src.utils.errors import SolverError, ConvergenceError


# ===================================================================
# Enumerations
# ===================================================================

class SolveStatus(Enum):
    """Status of the solver after a solve attempt."""
    SUCCESS = "success"
    FAILED_CONVERGENCE = "failed_convergence"
    ERROR = "error"


# ===================================================================
# MOMSolver class
# ===================================================================

class MOMSolver:
    """Method of Moments solver engine.

    Assembles and solves the MoM linear system Z * I = V where Z is the
    impedance matrix, I is the vector of RWG basis function coefficients
    (surface currents), and V is the excitation vector from ports.

    Parameters
    ----------
    formulation : FormulationType
        Integral equation type: EFIE, MFIE, or CFIE.
    frequency : float
            Operating frequency in Hz.
    max_iterations : int, optional
        Maximum Krylov iterations for the linear solver. Default 1000.
    tolerance : float, optional
        Relative residual tolerance. Default 1e-6.
    solver_type : SolverType, optional
        Iterative solver method. Default ``SolverType.GMRES``.
    preconditioner : Preconditioner, optional
        Linear algebra preconditioner.
    """

    def __init__(
        self,
        formulation: FormulationType = FormulationType.EFIE,
        frequency: float = 1e9,
        max_iterations: int = 1000,
        tolerance: float = 1e-6,
        solver_type: SolverType = SolverType.GMRES,
        preconditioner: Optional[Preconditioner] = None,
    ) -> None:
        self.formulation = formulation
        self.frequency = frequency
        self.max_iterations = max_iterations
        self.tolerance = tolerance
        self.solver_type = solver_type

        # --- Components ---------------------------------------------------
        self._formulation: IntegralEquationFormulation = get_formulation(formulation)
        self._greens_function = GreensFunction(frequency=frequency)
        self._green_evaluator = GreenEvaluator(self._greens_function, cache_size=50000)
        self._solver: Optional[LinearSolver] = None
        self._preconditioner = preconditioner

        # --- State --------------------------------------------------------
        self._mesh: Optional[object] = None
        self._basis_manager: Optional[BasisFunctionManager] = None
        self._Z: Optional[np.ndarray] = None  # Impedance matrix
        self._V: Optional[np.ndarray] = None  # Excitation vector
        self._I: Optional[np.ndarray] = None  # Solution (currents)
        self._status: SolveStatus = SolveStatus.ERROR
        self._residual_history: list[float] = []

    # ------------------------------------------------------------------
    # Mesh setup
    # ------------------------------------------------------------------

    def setup_mesh(self, mesh: object) -> None:
        """Register the mesh and create RWG basis functions.

        Parameters
        ----------
        mesh : object
            A mesh object with ``num_triangles`` and ``num_edges`` attributes.
            In production this would be a ``Mesh`` from cgal_meshing.py.
        """
        self._mesh = mesh
        num_triangles = getattr(mesh, "num_triangles", 0)
        num_edges = getattr(mesh, "num_edges", 0)
        self._basis_manager = BasisFunctionManager(
            num_triangles=num_triangles,
            num_edges=num_edges,
        )

        # Register RWG basis functions for each internal edge
        for edge_idx in range(num_edges):
            source_tri = edge_idx % max(num_triangles, 1)
            self._basis_manager.add_basis_function(edge_idx, source_tri)

    # ------------------------------------------------------------------
    # Frequency management
    # ------------------------------------------------------------------

    def set_frequency(self, frequency: float) -> None:
        """Update the operating frequency and reconfigure components.

        Parameters
        ----------
        frequency : float
            New frequency in Hz.
        """
        self.frequency = frequency
        self._greens_function.set_frequency(frequency)
        self._green_evaluator.gf.set_frequency(frequency)

    # ------------------------------------------------------------------
    # System matrix assembly
    # ------------------------------------------------------------------

    def compute_system_matrix(self, Z: Optional[np.ndarray] = None) -> np.ndarray:
        """Assemble the MoM impedance matrix Z.

        For each pair of basis functions (source *n*, test *m*), computes
        Z_{mn} using the selected formulation (EFIE/MFIE/CFIE) and Green's
        function.

        Parameters
        ----------
        Z : array_like shape (N, N), optional
            Pre-allocated matrix. If None, a new matrix is created.

        Returns
        -------
        np.ndarray
            The assembled impedance matrix of shape (N, N).
        """
        num_bf = len(self._basis_manager) if self._basis_manager else 0
        if num_bf == 0:
            raise RuntimeError("Mesh not set up. Call setup_mesh() first.")

        if Z is not None:
            self._Z = np.asarray(Z, dtype=np.complex128)
        else:
            self._Z = np.zeros((num_bf, num_bf), dtype=np.complex128)

        # --- Assemble upper triangle and mirror (symmetric-ish structure) ---
        for m in range(num_bf):
            for n in range(m, num_bf):
                element = self._formulation.compute_element(
                    source_triangle_idx=n,
                    test_triangle_idx=m,
                    frequency=self.frequency,
                    mesh=self._mesh,
                )
                self._Z[m, n] = element
                if m != n:
                    self._Z[n, m] = element  # approximate reciprocity

        return self._Z

    # ------------------------------------------------------------------
    # Right-hand side construction
    # ------------------------------------------------------------------

    def compute_rhs(
        self,
        port_indices: Optional[list[int]] = None,
        excitation_amplitude: float = 1.0,
        excitation_phase: float = 0.0,
    ) -> np.ndarray:
        """Construct the excitation (right-hand side) vector V.

        Parameters
        ----------
        port_indices : list[int], optional
            Indices of active ports. If None, all basis functions are excited.
        excitation_amplitude : float, optional
            Voltage amplitude for lumped ports. Default 1.0.
        excitation_phase : float, optional
            Phase in radians. Default 0.

        Returns
        -------
        np.ndarray
            Excitation vector V of shape (N,).
        """
        num_bf = len(self._basis_manager) if self._basis_manager else 0
        if num_bf == 0:
            raise RuntimeError("Mesh not set up.")

        self._V = np.zeros(num_bf, dtype=np.complex128)

        if port_indices is None:
            # Excite all basis functions uniformly (for testing)
            phase_factor = np.exp(1j * excitation_phase)
            self._V[:] = excitation_amplitude * phase_factor
        else:
            for idx in port_indices:
                if 0 <= idx < num_bf:
                    phase_factor = np.exp(1j * excitation_phase)
                    self._V[idx] = excitation_amplitude * phase_factor

        return self._V

    # ------------------------------------------------------------------
    # Solve
    # ------------------------------------------------------------------

    def solve(self, V: Optional[np.ndarray] = None) -> np.ndarray:
        """Solve the linear system Z * I = V.

        Parameters
        ----------
        V : array_like shape (N,), optional
            Right-hand side vector. If None, uses the internally stored V.

        Returns
        -------
        np.ndarray
            Solution vector I (surface current coefficients) of shape (N,).

        Raises
        ------
        SolverError
            If Z has not been assembled or V has not been computed.
        ConvergenceError
            If the iterative solver fails to converge.
        """
        if self._Z is None:
            raise SolverError("Impedance matrix Z not assembled. Call compute_system_matrix().")

        if V is not None:
            self._V = np.asarray(V, dtype=np.complex128)
        elif self._V is None:
            raise SolverError("Excitation vector V not computed. Call compute_rhs().")

        # --- Create solver --------------------------------------------------
        self._solver = create_solver(
            solver_type=self.solver_type,
            tolerance=self.tolerance,
            max_iterations=self.max_iterations,
            preconditioner=self._preconditioner,
        )

        # --- Solve ----------------------------------------------------------
        try:
            self._I = self._solver.solve(self._Z, self._V)
            self._residual_history = list(self._solver.residual_history)
            self._status = SolveStatus.SUCCESS
        except SolverError as e:
            self._status = SolveStatus.FAILED_CONVERGENCE
            raise ConvergenceError(
                f"MoM solver failed: {e}",
                context={
                    "residual_history": self._residual_history,
                    "tolerance": self.tolerance,
                    "max_iterations": self.max_iterations,
                },
            )

        return self._I

    # ------------------------------------------------------------------
    # Solution extraction
    # ------------------------------------------------------------------

    def extract_solution(self) -> np.ndarray:
        """Return the solved surface current vector.

        Returns
        -------
        np.ndarray
            Current coefficients I of shape (N,).

        Raises
        ------
        SolverError
            If solve() has not been called yet.
        """
        if self._I is None:
            raise SolverError("No solution available. Call solve() first.")
        return self._I.copy()

    @property
    def status(self) -> SolveStatus:
        """Current solver status."""
        return self._status

    @property
    def residual_history(self) -> list[float]:
        """Residual norm history from the last solve."""
        return list(self._residual_history)

    @property
    def impedance_matrix(self) -> Optional[np.ndarray]:
        """The assembled impedance matrix Z (if available)."""
        return self._Z.copy() if self._Z is not None else None

    # ------------------------------------------------------------------
    # MPI parallel support (stub)
    # ------------------------------------------------------------------

    def enable_mpi_parallel(
        self, num_ranks: int = 1, domain_decomposition: str = "spatial"
    ) -> None:
        """Enable MPI parallel matrix assembly and solve.

        In production this distributes the mesh across PETSc's parallel
        vectors and matrices.  The stub records the configuration for
        future integration.

        Parameters
        ----------
        num_ranks : int, optional
            Number of MPI ranks. Default 1 (serial).
        domain_decomposition : str, optional
            Decomposition strategy: ``"spatial"`` or ``"modal"``. Default "spatial".
        """
        self._mpi_enabled = True
        self._num_ranks = num_ranks
        self._decomposition = domain_decomposition

    def is_mpi_enabled(self) -> bool:
        """Check if MPI parallel mode is enabled."""
        return getattr(self, "_mpi_enabled", False)


# ===================================================================
# Module-level example usage
# ===================================================================

if __name__ == "__main__":
    print("=== MoM Solver Engine ===\n")

    # --- Mock mesh object for testing -----------------------------------
    class MockMesh:
        num_triangles = 50
        num_edges = 75

    solver = MOMSolver(
        formulation=FormulationType.EFIE,
        frequency=1e9,
        max_iterations=500,
        tolerance=1e-6,
    )

    # Setup mesh
    mock_mesh = MockMesh()
    solver.setup_mesh(mock_mesh)
    print(f"Basis functions registered: {len(solver._basis_manager)}")

    # Assemble system matrix
    Z = solver.compute_system_matrix()
    print(f"Impedance matrix shape: {Z.shape}")
    print(f"  Max real part: {np.max(np.real(Z)):.6e}")
    print(f"  Max imag part: {np.max(np.imag(Z)):.6e}\n")

    # Compute RHS and solve
    V = solver.compute_rhs(port_indices=[0, 1, 2], excitation_amplitude=1.0)
    print(f"Excitation vector shape: {V.shape}")

    I = solver.solve()
    print(f"Solution norm: {np.linalg.norm(I):.6e}")
    print(f"Residual history length: {len(solver.residual_history)}")
    print(f"Final status: {solver.status.value}")
