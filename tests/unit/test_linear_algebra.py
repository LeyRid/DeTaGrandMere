"""Unit tests for the linear algebra solver and preconditioners.

This module provides comprehensive pytest-based unit tests covering:

- ILUPreconditioner setup and apply (diagonal extraction)
- JacobiPreconditioner (diagonal) preconditioning
- GMRES solver on a diagonal system
- BiCGStab solver on a diagonal system
- create_solver factory function for both solver types

All tests are self-contained using only numpy and pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

# Import the modules under test
from src.core.linear_algebra.solver import (
    SolverType,
    Preconditioner,
    ILUPreconditioner,
    JacobiPreconditioner,
    LinearSolver,
    GMRESSolver,
    BiCGStabSolver,
    create_solver,
)


# ===================================================================
# Test ILU preconditioner
# ===================================================================

class TestILUPreconditioner:
    """Tests for the ILU (Incomplete LU) preconditioner stub."""

    def test_ilu_preconditioner_setup_apply(self) -> None:
        """Test ILU diagonal extraction and application.

        The ILU preconditioner stub extracts the diagonal of the matrix
        and uses it as a simple diagonal preconditioner. Verify that:
        - setup() extracts the diagonal correctly
        - apply() divides by the diagonal elements
        - RuntimeError is raised if apply() is called before setup()
        """
        # Build a known diagonal-dominant matrix
        diag_values = np.array([2.0, 4.0, 8.0, 16.0, 32.0], dtype=np.float64)
        n = len(diag_values)
        A = np.diag(diag_values)

        ilu = ILUPreconditioner()

        # setup extracts the diagonal
        ilu.setup(A)

        # apply should divide by the diagonal
        test_vector = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
        result = ilu.apply(test_vector)

        expected = test_vector / diag_values
        assert np.allclose(result, expected), \
            f"ILU apply {result} != expected {expected}"

    def test_ilu_preconditioner_requires_setup(self) -> None:
        """Test that ILU raises RuntimeError if apply is called before setup."""
        ilu = ILUPreconditioner()
        with pytest.raises(RuntimeError, match="setup"):
            ilu.apply(np.array([1.0, 2.0]))

    def test_ilu_preconditioner_drop_tol(self) -> None:
        """Test that near-zero diagonal entries are guarded by drop_tol."""
        A = np.diag(np.array([1e-15, 1.0, 1e-15], dtype=np.float64))
        ilu = ILUPreconditioner(drop_tol=1e-4)

        ilu.setup(A)

        # Near-zero diagonals should be replaced with drop_tol (or similar guard)
        assert ilu._diagonal is not None
        for i in range(3):
            if abs(np.diag(A)[i]) < 1e-4:
                assert ilu._diagonal[i] != 0.0, \
                    f"Near-zero diagonal entry {i} was not guarded"


# ===================================================================
# Test Jacobi preconditioner
# ===================================================================

class TestJacobiPreconditioner:
    """Tests for the Jacobi (diagonal) preconditioner."""

    def test_jacobi_preconditioner(self) -> None:
        """Test Jacobi (diagonal) preconditioning.

        The Jacobi preconditioner uses M = diag(A). Verify that:
        - setup extracts the diagonal correctly
        - apply divides by the diagonal elements
        - It behaves identically to ILU for diagonal-dominant matrices
        """
        # Build a known matrix with specific diagonal
        diag_values = np.array([3.0, 6.0, 9.0], dtype=np.float64)
        n = len(diag_values)
        A = np.diag(diag_values)

        jacobi = JacobiPreconditioner()
        jacobi.setup(A)

        test_vector = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        result = jacobi.apply(test_vector)

        expected = test_vector / diag_values
        assert np.allclose(result, expected), \
            f"Jacobi apply {result} != expected {expected}"

    def test_jacobi_requires_setup(self) -> None:
        """Test that Jacobi raises RuntimeError if apply is called before setup."""
        jacobi = JacobiPreconditioner()
        with pytest.raises(RuntimeError, match="setup"):
            jacobi.apply(np.array([1.0, 2.0]))

    def test_jacobi_matches_ilu_for_diagonal_matrix(self) -> None:
        """Test that Jacobi and ILU give the same result for diagonal matrices."""
        A = np.diag(np.array([2.0, 4.0, 6.0], dtype=np.float64))

        ilu = ILUPreconditioner()
        ilu.setup(A)

        jacobi = JacobiPreconditioner()
        jacobi.setup(A)

        test_vector = np.ones(3, dtype=np.float64)
        ilu_result = ilu.apply(test_vector)
        jacobi_result = jacobi.apply(test_vector)

        assert np.allclose(ilu_result, jacobi_result), \
            f"ILU {ilu_result} != Jacobi {jacobi_result} for diagonal matrix"


# ===================================================================
# Test GMRES solver
# ===================================================================

class TestGMRESSolver:
    """Tests for the GMRES iterative solver stub."""

    def test_gmres_solve_diagonal_system(self) -> None:
        """Solve a simple diagonal system and verify solution.

        For a diagonal matrix A = diag([1, 2, 3]) and b = [1, 1, 1],
        the exact solution is x = [1, 0.5, 1/3]. Verify that GMRES
        converges to this solution when using a preconditioner.
        """
        # Simple diagonal system: Ax = b where A = diag([1, 2, 3])
        A = np.diag(np.array([1.0, 2.0, 3.0], dtype=np.float64))
        b = np.array([1.0, 1.0, 1.0], dtype=np.float64)

        # Exact solution: x[i] = b[i] / A[i,i]
        expected_x = np.array([1.0, 0.5, 1.0 / 3.0], dtype=np.float64)

        # Use Jacobi preconditioner to help convergence
        jacobi = JacobiPreconditioner()
        solver = GMRESSolver(tolerance=1e-6, max_iterations=1000, preconditioner=jacobi)
        x = solver.solve(A, b)

        assert isinstance(x, np.ndarray), \
            f"Solution should be np.ndarray, got {type(x)}"
        assert x.shape == (3,), \
            f"Solution shape {x.shape} != (3,)"

        # Verify solution is close to expected
        assert np.allclose(x, expected_x, rtol=1e-4), \
            f"GMRES solution {x} != expected {expected_x}"

        # Verify residual is small
        residual = A @ x - b
        assert np.linalg.norm(residual) < 1e-4, \
            f"Residual norm {np.linalg.norm(residual)} > 1e-4"

        # Solver should have recorded residual history
        hist = solver.residual_history
        assert len(hist) > 0, "Residual history should not be empty"

    def test_gmres_residual_history(self) -> None:
        """Test that GMRES records residual history during iterations."""
        A = np.diag(np.array([1.0, 2.0, 3.0], dtype=np.float64))
        b = np.ones(3, dtype=np.float64)

        jacobi = JacobiPreconditioner()
        solver = GMRESSolver(tolerance=1e-6, max_iterations=500, preconditioner=jacobi)
        x = solver.solve(A, b)

        hist = solver.residual_history
        assert len(hist) > 1, \
            f"Expected multiple residuals, got {len(hist)}"

        # Residual should decrease (or at least not grow unbounded)
        assert hist[-1] < hist[0], \
            "Final residual should be smaller than initial"


# ===================================================================
# Test BiCGStab solver
# ===================================================================

class TestBiCGStabSolver:
    """Tests for the BiCGStab iterative solver stub."""

    def test_bicgstab_solve_diagonal_system(self) -> None:
        """Solve a diagonal system with BiCGStab and verify solution.

        Uses the same test case as GMRES: A = diag([1, 2, 3]), b = [1, 1, 1].
        The exact solution is x = [1, 0.5, 1/3].
        """
        A = np.diag(np.array([1.0, 2.0, 3.0], dtype=np.float64))
        b = np.array([1.0, 1.0, 1.0], dtype=np.float64)

        expected_x = np.array([1.0, 0.5, 1.0 / 3.0], dtype=np.float64)

        solver = BiCGStabSolver(tolerance=1e-8, max_iterations=1000)
        x = solver.solve(A, b)

        assert isinstance(x, np.ndarray), \
            f"Solution should be np.ndarray, got {type(x)}"
        assert x.shape == (3,), \
            f"Solution shape {x.shape} != (3,)"

        # Verify solution is close to expected
        assert np.allclose(x, expected_x, rtol=1e-5), \
            f"BiCGStab solution {x} != expected {expected_x}"

        # Verify residual is small
        residual = A @ x - b
        assert np.linalg.norm(residual) < 1e-6, \
            f"Residual norm {np.linalg.norm(residual)} > 1e-6"

    def test_bicgstab_residual_history(self) -> None:
        """Test that BiCGStab records residual history."""
        A = np.diag(np.array([1.0, 2.0, 3.0], dtype=np.float64))
        b = np.ones(3, dtype=np.float64)

        solver = BiCGStabSolver(tolerance=1e-6, max_iterations=500)
        x = solver.solve(A, b)

        hist = solver.residual_history
        assert len(hist) > 0, \
            f"Residual history should not be empty, got {len(hist)}"


# ===================================================================
# Test solver factory
# ===================================================================

class TestSolverFactory:
    """Tests for the create_solver factory function."""

    def test_solver_factory(self) -> None:
        """Test create_solver factory function for both GMRES and BiCGStab.

        Verify that:
        - create_solver(SolverType.GMRES) returns a GMRESSolver instance
        - create_solver(SolverType.BiCGStab) returns a BiCGStabSolver instance
        - Parameters (tolerance, max_iterations, preconditioner) are passed through
        """
        # Test GMRES factory
        gmres = create_solver(
            solver_type=SolverType.GMRES,
            tolerance=1e-8,
            max_iterations=500,
            preconditioner=None,
        )
        assert isinstance(gmres, GMRESSolver), \
            f"Expected GMRESSolver, got {type(gmres)}"
        assert gmres.tolerance == 1e-8
        assert gmres.max_iterations == 500

        # Test BiCGStab factory
        bicg = create_solver(
            solver_type=SolverType.BiCGStab,
            tolerance=1e-7,
            max_iterations=300,
            preconditioner=None,
        )
        assert isinstance(bicg, BiCGStabSolver), \
            f"Expected BiCGStabSolver, got {type(bicg)}"
        assert bicg.tolerance == 1e-7
        assert bicg.max_iterations == 300

    def test_solver_factory_with_preconditioner(self) -> None:
        """Test that the factory passes through preconditioner instances."""
        ilu = ILUPreconditioner()
        solver = create_solver(
            solver_type=SolverType.GMRES,
            tolerance=1e-6,
            max_iterations=100,
            preconditioner=ilu,
        )
        assert isinstance(solver, GMRESSolver)
        assert solver.preconditioner is ilu

    def test_solver_factory_unknown_type(self) -> None:
        """Test that create_solver raises ValueError for unknown types."""
        # Use a plain object (not an Enum member) to simulate an unknown type.
        class UnknownSolverType:
            value = "unknown"

        with pytest.raises(ValueError, match="Unknown solver type"):
            create_solver(solver_type=UnknownSolverType())  # type: ignore[arg-type]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
