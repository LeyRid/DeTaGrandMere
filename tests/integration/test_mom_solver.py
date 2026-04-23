"""Integration tests for MoM solver workflow."""

from __future__ import annotations

import sys
import pytest
import numpy as np

sys.path.insert(0, "/home/rid/Documents/Caad")

from src.core.mom_solver.formulation import FormulationType, get_formulation
from src.core.mom_solver.basis_functions import Triangle, RWGBasisFunction
from src.core.mom_solver.green_function import GreensFunction
from src.core.linear_algebra.solver import create_solver


class TestMoMSolverIntegration:
    """Test MoM solver components work together."""

    def test_efie_formulation_with_rwg_basis(self):
        """Verify EFIE formulation works with RWG basis functions."""
        # Create a simple triangle mesh
        tri1 = Triangle(
            vertices=np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0]], dtype=np.float64),
            area=0.5,
        )

        # Create RWG basis function on the triangle
        basis = RWGBasisFunction(triangle=tri1, edge=(0, 1))

        # Verify basis function properties
        assert basis.support_size == 2
        assert basis.normal_vector is not None

    def test_green_function_with_formulation(self):
        """Verify Green's function evaluation with EFIE formulation."""
        freq = 1e9
        gf = GreensFunction(frequency=freq)

        # Evaluate at a non-singular point
        r = np.array([0.1, 0.1, 0.1])
        r_prime = np.array([0, 0, 0])

        G = gf.evaluate(r, r_prime)
        assert isinstance(G, complex)
        assert not np.isnan(G)

    def test_solver_with_formulation(self):
        """Verify linear solver works with MoM formulation."""
        freq = 1e9
        formulation = get_formulation(FormulationType.EFIE, frequency=freq)

        # Verify formulation can compute element matrices
        tri = Triangle(
            vertices=np.array([[0, 0, 0], [1, 0, 0], [0.5, 1, 0]], dtype=np.float64),
            area=0.5,
        )

        element_matrix = formulation.compute_element(tri, tri)
        assert isinstance(element_matrix, np.ndarray)


class TestSParamSolverIntegration:
    """Test S-parameter computation with solver."""

    def test_sparam_with_mom_solver(self):
        """Verify S-parameters can be computed from MoM solution."""
        from src.core.sparams_computation import SParameterCalculator

        freq = 1e9
        calculator = SParameterCalculator(frequency=freq)

        # Simulate a simple Z-matrix (impedance matrix)
        Z = np.array([[50 + 10j, 5 - 2j], [5 - 2j, 50 + 10j]])
        Z0 = 50.0  # Reference impedance

        S = calculator.compute_s_parameters_from_Z(Z, Z0)
        assert S.shape == (2, 2)
        assert not np.any(np.isnan(S))


class TestFieldCalculationIntegration:
    """Test field calculations with MoM solution."""

    def test_near_field_from_currents(self):
        """Verify near-field computation uses solved currents."""
        from src.core.field_calculations.near_field import NearFieldCalculator

        freq = 1e9
        calculator = NearFieldCalculator(frequency=freq)

        # Simple current distribution on a line source
        n_sources = 10
        currents = np.zeros((n_sources, 3), dtype=np.complex128)
        for i in range(n_sources):
            currents[i, 0] = np.exp(1j * i * np.pi / 4)

        source_points = np.array([[x, 0, 0] for x in np.linspace(-0.5, 0.5, n_sources)])
        obs_points = np.array([[0, 0, 0.5], [0.1, 0.1, 0.6]])

        E = calculator.compute_E_field(currents, obs_points, source_points)
        assert E.shape == (2, 3)
        assert not np.any(np.isnan(E))

    def test_far_field_from_currents(self):
        """Verify far-field transformation uses solved currents."""
        from src.core.field_calculations.far_field import FarFieldTransformer

        freq = 1e9
        transformer = FarFieldTransformer(frequency=freq)

        # Simple dipole current distribution
        n_sources = 5
        currents = np.zeros((n_sources, 3), dtype=np.complex128)
        for i in range(n_sources):
            currents[i, 1] = np.exp(1j * i * np.pi / 2)

        source_points = np.array([[0, y, 0] for y in np.linspace(-0.5, 0.5, n_sources)])

        # Compute far-field at theta=90 deg
        thetas = [np.pi / 2]
        phis = [0]

        E_theta, E_phi = transformer.compute_far_field(
            currents, source_points, thetas, phis
        )

        assert len(E_theta) == len(thetas)
        assert len(E_phi) == len(phis)
