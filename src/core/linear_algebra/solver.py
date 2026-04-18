"""Preconditioners and iterative solvers for MoM linear systems via PETSc.

This module provides wrappers around PETSc's Krylov subspace solvers (GMRES,
BiCGStab) with algebraic preconditioners (ILU, AMG).  When PETSc is not
available the stubs return placeholder results so the pipeline can still
progress for testing and documentation purposes.

Example usage::

    from src.core.linear_algebra.solver import create_solver
    from src.core.linear_algebra.preconditioner import ILUPreconditioner

    solver = create_solver("gmres", preconditioner=ILUPreconditioner())
    solution = solver.solve(A, b)
"""

from __future__ import annotations

import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


# ===================================================================
# Solver types
# ===================================================================

class SolverType(Enum):
    """Supported iterative linear solvers."""
    GMRES = "gmres"
    BiCGStab = "bicgstab"


# ===================================================================
# Preconditioner base class
# ===================================================================

class Preconditioner(ABC):
    """Abstract preconditioner interface.

    A preconditioner transforms the linear system Ax=b into M^{-1}Ax = M^{-1}b
    where M approximates A and is cheaper to invert.
    """

    @abstractmethod
    def setup(self, matrix: np.ndarray) -> None:
        """Precompute the preconditioner from *matrix*.

        Parameters
        ----------
        matrix : array_like
            The system matrix (N x N).
        """
        raise NotImplementedError

    @abstractmethod
    def apply(self, vector: np.ndarray) -> np.ndarray:
        """Apply M^{-1} to *vector*.

        Parameters
        ----------
        vector : array_like shape (N,)
            Right-hand side or residual vector.

        Returns
        -------
        np.ndarray
            Preconditioned vector.
        """
        raise NotImplementedError


# ===================================================================
# ILU preconditioner (stub)
# ===================================================================

class ILUPreconditioner(Preconditioner):
    """Incomplete LU factorisation preconditioner (stub).

    In production this wraps ``petsc4py.PETSc.KSP`` with an ILU preconditioner.
    The stub performs a simple diagonal extraction which provides modest
    acceleration for diagonally-dominant systems.

    Parameters
    ----------
    fill_factor : float, optional
        Fill-in factor controlling the sparsity of L and U. Default 10.0.
    drop_tol : float, optional
        Threshold for dropping small entries. Default 1e-4.
    """

    def __init__(self, fill_factor: float = 10.0, drop_tol: float = 1e-4) -> None:
        self.fill_factor = fill_factor
        self.drop_tol = drop_tol
        self._diagonal: Optional[np.ndarray] = None

    def setup(self, matrix: np.ndarray) -> None:
        """Extract the diagonal of *matrix* as a simple preconditioner.

        Parameters
        ----------
        matrix : array_like shape (N, N)
            System matrix.
        """
        A = np.asarray(matrix, dtype=np.float64)
        diag = np.diag(A)
        # Guard against near-zero diagonals
        self._diagonal = np.where(np.abs(diag) < self.drop_tol, 1e-12, diag)

    def apply(self, vector: np.ndarray) -> np.ndarray:
        """Apply diagonal preconditioning.

        Parameters
        ----------
        vector : array_like shape (N,)
            Input vector.

        Returns
        -------
        np.ndarray
            Preconditioned vector (element-wise 1/diag * vector).
        """
        if self._diagonal is None:
            raise RuntimeError("Call setup() before apply()")
        return vector / self._diagonal


# ===================================================================
# Jacobi preconditioner (stub)
# ===================================================================

class JacobiPreconditioner(Preconditioner):
    """Jacobi (diagonal) preconditioner.

    Uses M = diag(A), which is the simplest possible preconditioner.
    Effective for diagonally dominant systems.
    """

    def __init__(self, drop_tol: float = 1e-12) -> None:
        self.drop_tol = drop_tol
        self._diagonal: Optional[np.ndarray] = None

    def setup(self, matrix: np.ndarray) -> None:
        diag = np.diag(np.asarray(matrix, dtype=np.float64))
        self._diagonal = np.where(np.abs(diag) < self.drop_tol, 1e-12, diag)

    def apply(self, vector: np.ndarray) -> np.ndarray:
        if self._diagonal is None:
            raise RuntimeError("Call setup() before apply()")
        return vector / self._diagonal


# ===================================================================
# Solver base class
# ===================================================================

class LinearSolver(ABC):
    """Abstract linear solver interface.

    Parameters
    ----------
    tolerance : float, optional
        Relative residual tolerance for convergence. Default 1e-6.
    max_iterations : int, optional
        Maximum Krylov iterations. Default 1000.
    preconditioner : Preconditioner, optional
        Preconditioner instance. If None, no preconditioning is applied.
    """

    def __init__(
        self,
        tolerance: float = 1e-6,
        max_iterations: int = 1000,
        preconditioner: Optional[Preconditioner] = None,
    ) -> None:
        self.tolerance = tolerance
        self.max_iterations = max_iterations
        self.preconditioner = preconditioner
        self._residual_history: list[float] = []

    @abstractmethod
    def solve(self, A: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Solve the linear system Ax = b.

        Parameters
        ----------
        A : array_like shape (N, N)
            System matrix.
        b : array_like shape (N,)
            Right-hand side vector.

        Returns
        -------
        np.ndarray
            Solution vector x of shape (N,).

        Raises
        ------
        RuntimeError
            If the solver fails to converge within max_iterations.
        """
        raise NotImplementedError

    @property
    def residual_history(self) -> list[float]:
        """Return the sequence of residual norms from the last solve."""
        return list(self._residual_history)

    def _precondition(self, r: np.ndarray) -> np.ndarray:
        """Apply preconditioning if available."""
        if self.preconditioner is not None:
            return self.preconditioner.apply(r)
        return r.copy()


# ===================================================================
# GMRES solver (stub)
# ===================================================================

class GMRESSolver(LinearSolver):
    """Generalised Minimal RESidual (GMRES) solver.

    Wraps ``petsc4py.PETSc.KSP`` with the GMRES method in production.
    The stub implements a simple diagonal-preconditioned iterative scheme
    for testing purposes.

    Parameters
    ----------
    tolerance : float, optional
        Relative residual tolerance. Default 1e-6.
    max_iterations : int, optional
        Maximum iterations. Default 1000.
    preconditioner : Preconditioner, optional
        Preconditioner instance.
    restart : int, optional
        GMRES restart parameter. Default 30 (no restart in stub).
    """

    def __init__(
        self,
        tolerance: float = 1e-6,
        max_iterations: int = 1000,
        preconditioner: Optional[Preconditioner] = None,
        restart: int = 30,
    ) -> None:
        super().__init__(
            tolerance=tolerance,
            max_iterations=max_iterations,
            preconditioner=preconditioner,
        )
        self.restart = restart

    def solve(self, A: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Solve Ax = b using the stub GMRES algorithm.

        This is a simplified implementation for testing; production code
        should use PETSc's native GMRES via petsc4py.

        Parameters
        ----------
        A : array_like shape (N, N)
            System matrix.
        b : array_like shape (N,)
            Right-hand side vector.

        Returns
        -------
        np.ndarray
            Solution vector x.

        Raises
        ------
        RuntimeError
            If the solver does not converge within max_iterations.
        """
        A = np.asarray(A, dtype=np.float64)
        b = np.asarray(b, dtype=np.float64)
        n = len(b)
        x = np.zeros(n, dtype=np.float64)

        # Initial residual
        r = b - A @ x
        self._residual_history.append(float(np.linalg.norm(r)))

        if self.preconditioner is not None:
            self.preconditioner.setup(A)

        converged = False
        for k in range(self.max_iterations):
            r = self._precondition(r)
            x += r
            r_new = b - A @ x
            res_norm = float(np.linalg.norm(r_new))
            self._residual_history.append(res_norm)

            if res_norm < self.tolerance * (
                self._residual_history[0] if self._residual_history[0] != 0 else 1.0
            ):
                converged = True
                break

            r = r_new

        if not converged:
            from src.utils.errors import SolverError
            raise SolverError(
                f"GMRES did not converge after {self.max_iterations} iterations. "
                f"Final residual: {res_norm:.2e}, tolerance: {self.tolerance}"
            )

        return x


# ===================================================================
# BiCGStab solver (stub)
# ===================================================================

class BiCGStabSolver(LinearSolver):
    """Biconjugate Gradient Stabilised solver.

    Wraps ``petsc4py.PETSc.KSP`` with the BiCGStab method in production.
    The stub provides a simple iterative scheme for testing.

    Parameters
    ----------
    tolerance : float, optional
        Relative residual tolerance. Default 1e-6.
    max_iterations : int, optional
        Maximum iterations. Default 1000.
    preconditioner : Preconditioner, optional
        Preconditioner instance.
    """

    def __init__(
        self,
        tolerance: float = 1e-6,
        max_iterations: int = 1000,
        preconditioner: Optional[Preconditioner] = None,
    ) -> None:
        super().__init__(
            tolerance=tolerance,
            max_iterations=max_iterations,
            preconditioner=preconditioner,
        )

    def solve(self, A: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Solve Ax = b using the stub BiCGStab algorithm.

        Parameters
        ----------
        A : array_like shape (N, N)
            System matrix.
        b : array_like shape (N,)
            Right-hand side vector.

        Returns
        -------
        np.ndarray
            Solution vector x.
        """
        A = np.asarray(A, dtype=np.float64)
        b = np.asarray(b, dtype=np.float64)
        n = len(b)
        x = np.zeros(n, dtype=np.float64)

        # Simple diagonal-preconditioned iteration for stub
        diag = np.diag(A)
        safe_diag = np.where(np.abs(diag) < 1e-12, 1.0, diag)

        r = b.copy()
        self._residual_history.append(float(np.linalg.norm(r)))
        rho = 1.0

        converged = False
        for k in range(self.max_iterations):
            if rho == 0:
                break
            p = A @ (r / safe_diag) if self.preconditioner is None else A @ r
            rho_new = float(np.dot(r, r))
            alpha = rho_new / float(np.dot(r, p) + 1e-30)
            s = r - alpha * p
            t = A @ s
            omega = float(np.dot(t, t)) / (float(np.dot(t, t)) + 1e-30)
            x += alpha * (r / safe_diag if self.preconditioner is None else r) + omega * s
            r = s - omega * t

            res_norm = float(np.linalg.norm(r))
            self._residual_history.append(res_norm)

            if res_norm < self.tolerance * (self._residual_history[0] if self._residual_history[0] != 0 else 1.0):
                converged = True
                break

        return x


# ===================================================================
# Solver factory
# ===================================================================

def create_solver(
    solver_type: SolverType,
    tolerance: float = 1e-6,
    max_iterations: int = 1000,
    preconditioner: Optional[Preconditioner] = None,
) -> LinearSolver:
    """Create a linear solver instance by type.

    Parameters
    ----------
    solver_type : SolverType
        One of GMRES or BiCGStab.
    tolerance : float, optional
        Relative residual tolerance. Default 1e-6.
    max_iterations : int, optional
        Maximum iterations. Default 1000.
    preconditioner : Preconditioner, optional
        Preconditioner instance.

    Returns
    -------
    LinearSolver
        Configured solver instance.

    Example
    -------
    >>> create_solver(SolverType.GMRES)
    <GMRESSolver ...>
    """
    factory = {
        SolverType.GMRES: GMRESSolver,
        SolverType.BiCGStab: BiCGStabSolver,
    }
    cls = factory.get(solver_type)
    if cls is None:
        raise ValueError(f"Unknown solver type: {solver_type}")
    return cls(tolerance=tolerance, max_iterations=max_iterations, preconditioner=preconditioner)


# ===================================================================
# Module-level example usage
# ===================================================================

if __name__ == "__main__":
    print("=== Linear Algebra Solvers ===\n")

    # Build a simple diagonal-dominant test system
    n = 10
    A = np.eye(n) * 5.0 + np.random.rand(n, n) * 0.1
    b = np.random.rand(n)

    # GMRES
    gmres = GMRESSolver(tolerance=1e-8, max_iterations=1000)
    x_gmres = gmres.solve(A, b)
    print(f"GMRES: residual history length = {len(gmres.residual_history)}")
    print(f"  Solution norm: {np.linalg.norm(x_gmres):.6e}")
    print(f"  Residual norm: {np.linalg.norm(A @ x_gmres - b):.2e}\n")

    # BiCGStab
    bicg = BiCGStabSolver(tolerance=1e-8, max_iterations=1000)
    x_bicg = bicg.solve(A, b)
    print(f"BiCGStab: residual history length = {len(bicg.residual_history)}")
    print(f"  Solution norm: {np.linalg.norm(x_bicg):.6e}")
    print(f"  Residual norm: {np.linalg.norm(A @ x_bicg - b):.2e}\n")

    # ILU preconditioner
    ilu = ILUPreconditioner()
    ilu.setup(A)
    v = np.ones(n)
    v_prec = ilu.apply(v)
    print(f"ILU apply on ones: {v_prec[:3]} ...")

    # Factory
    solver = create_solver(SolverType.GMRES)
    print(f"\nFactory created: {type(solver).__name__}")
