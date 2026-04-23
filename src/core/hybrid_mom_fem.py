"""Hybrid MoM-FEM simulation framework for complex substrates.

This module provides stub implementations for coupling Method of Moments
(MoM) surface integral formulation with Finite Element Method (FEM)
volume discretization. It supports:

- Domain decomposition between MoM (open region) and FEM (dielectric volume)
- Interface coupling via continuity conditions on tangential E and H fields
- Material property handling at MoM-FEM interfaces
- Combined linear system assembly for hybrid solve
"""

from __future__ import annotations

import numpy as np
from typing import Optional, List, Tuple, Dict

from src.utils.errors import SolverError


class MoMFEMInterface:
    """Interface between MoM surface and FEM volume regions.

    This class manages the coupling boundary between the Method of Moments
    (surface integral) region and the Finite Element Method (volume integral)
    region. It enforces continuity conditions on tangential electric and
    magnetic fields at the interface.

    Parameters
    ----------
    interface_surface : np.ndarray, optional
        Coordinates defining the MoM-FEM interface boundary with shape
        (N_interface_points, 3). If None, will be computed from geometry.
    """

    def __init__(self, interface_surface: Optional[np.ndarray] = None) -> None:
        """Initialise the MoM-FEM interface."""
        self.interface_surface = interface_surface
        self.interface_normal: Optional[np.ndarray] = None
        self.mom_region: Optional[dict] = None
        self.fem_region: Optional[dict] = None

    def identify_interface(
        self,
        mom_mesh: np.ndarray,
        fem_mesh: np.ndarray,
    ) -> np.ndarray:
        """Identify the coupling interface between MoM and FEM regions.

        Parameters
        ----------
        mom_mesh : np.ndarray
            MoM surface mesh vertices with shape (N_mom, 3).
        fem_mesh : np.ndarray
            FEM volume mesh vertices with shape (N_fem, 3).

        Returns
        -------
        np.ndarray
            Interface boundary points with shape (N_interface, 3).
        """
        # Find common vertices between MoM surface and FEM volume
        # In full implementation, this would use spatial hashing for efficiency
        interface_points = []

        for mom_vert in mom_mesh:
            for fem_vert in fem_mesh:
                dist = np.linalg.norm(mom_vert - fem_vert)
                if dist < 1e-6:  # Within tolerance
                    interface_points.append(mom_vert)
                    break

        self.interface_surface = np.array(interface_points) if interface_points else None

        return self.interface_surface or np.zeros((0, 3))

    def compute_coupling_matrix(
        self,
        mom_basis_functions: list,
        fem_shape_functions: list,
    ) -> np.ndarray:
        """Compute coupling matrix between MoM and FEM basis functions.

        Parameters
        ----------
        mom_basis_functions : list[RWGBasisFunction]
            RWG basis functions on the MoM surface.
        fem_shape_functions : list
            FEM shape functions on the volume mesh.

        Returns
        -------
        np.ndarray
            Coupling matrix C with shape (N_mom, N_fem).

        Raises
        ------
        SolverError
            If interface is not defined or basis function counts mismatch.
        """
        if self.interface_surface is None:
            raise SolverError("Interface not identified; call identify_interface() first")

        n_mom = len(mom_basis_functions)
        n_fem = len(fem_shape_functions)

        # Compute coupling matrix (stub: simplified diagonal approximation)
        C = np.zeros((n_mom, n_fem), dtype=np.complex128)

        for i, bf in enumerate(mom_basis_functions):
            # Find FEM shape functions near the MoM basis support
            for j, sf in enumerate(fem_shape_functions):
                # Simplified: couple based on proximity to interface
                if bf.support_size > 0 and sf.support_size > 0:
                    dist = np.linalg.norm(bf.centroid - sf.centroid)
                    if dist < 1e-3:  # Within coupling range
                        C[i, j] = 1.0 / (dist + 1e-10)

        return C

    def enforce_continuity(
        self,
        E_mom: np.ndarray,
        E_fem: np.ndarray,
        tolerance: float = 1e-6,
    ) -> bool:
        """Enforce tangential E-field continuity at the MoM-FEM interface.

        Parameters
        ----------
        E_mom : np.ndarray
            Electric field from MoM solution at interface with shape (N_interface, 3).
        E_fem : np.ndarray
            Electric field from FEM solution at interface with shape (N_interface, 3).
        tolerance : float, default=1e-6
            Acceptable mismatch for continuity.

        Returns
        -------
        bool
            True if continuity is satisfied within tolerance.
        """
        if self.interface_surface is None:
            return False

        # Compute tangential component of E fields
        E_mom_tan = self._get_tangential_component(E_mom, self.interface_normal)
        E_fem_tan = self._get_tangential_component(E_fem, self.interface_normal)

        # Check continuity (L2 norm of difference)
        diff = np.linalg.norm(E_mom_tan - E_fem_tan, axis=1)
        max_diff = np.max(diff) if len(diff) > 0 else 0.0

        return max_diff <= tolerance

    def _get_tangential_component(
        self,
        E: np.ndarray,
        normal: np.ndarray,
    ) -> np.ndarray:
        """Extract tangential component of electric field from total field.

        Parameters
        ----------
        E : np.ndarray
            Total electric field with shape (N_points, 3).
        normal : np.ndarray
        Interface normal vector with shape (3,).

        Returns
        -------
        np.ndarray
            Tangential electric field component.
        """
        # Project out the normal component: E_tan = E - (E·n)*n/|n|^2
        n_hat = normal / (np.linalg.norm(normal) + 1e-10)
        normal_component = np.sum(E * n_hat[np.newaxis, :], axis=1)[:, np.newaxis]
        E_tan = E - normal_component * n_hat[np.newaxis, :]

        return E_tan


class FEMVolumeMesh:
    """FEM volume mesh for dielectric regions.

    This class represents the finite element volume mesh used to discretize
    dielectric substrates and other volumetric regions in hybrid MoM-FEM
    simulations. It supports tetrahedral elements with hexahedral fallback.

    Parameters
    ----------
    vertices : np.ndarray, optional
        Mesh vertex coordinates with shape (N_vertices, 3).
    tetrahedra : np.ndarray, optional
        Tetrahedron connectivity array with shape (N_tets, 4) of vertex indices.
    """

    def __init__(
        self,
        vertices: Optional[np.ndarray] = None,
        tetrahedra: Optional[np.ndarray] = None,
    ) -> None:
        """Initialise the FEM volume mesh."""
        self.vertices = vertices
        self.tetrahedra = tetrahedra

    def compute_volume(self) -> float:
        """Compute the total volume of the FEM mesh.

        Returns
        -------
        float
            Total volume in cubic meters.
        """
        if self.vertices is None or self.tetrahedra is None:
            return 0.0

        total_volume = 0.0
        for tet in self.tetrahedra:
            # Compute volume of each tetrahedron using determinant formula
            v0 = self.vertices[tet[0]]
            v1 = self.vertices[tet[1]]
            v2 = self.vertices[tet[2]]
            v3 = self.vertices[tet[3]]

            # Volume = (1/6) * det(v1-v0, v2-v0, v3-v0)
            d1 = v1 - v0
            d2 = v2 - v0
            d3 = v3 - v0
            vol = abs(np.dot(d1, np.cross(d2, d3))) / 6.0

            total_volume += vol

        return total_volume

    def get_element_properties(
        self,
        material: object,
        frequency: float,
    ) -> dict:
        """Get material properties for each FEM element.

        Parameters
        ----------
        material : object
            Material instance (may be dispersive or anisotropic).
        frequency : float
            Operating frequency in Hz.

        Returns
        -------
        dict
            Element property dictionary with keys:
            - 'epsilon_r': relative permittivity per element
            - 'mu_r': relative permeability per element
            - 'sigma': conductivity per element
        """
        # In full implementation, this would evaluate material properties
        # at the centroid of each tetrahedral element

        n_elements = len(self.tetrahedra) if self.tetrahedra is not None else 0

        return {
            "epsilon_r": np.ones(n_elements) * getattr(material, "eps_r", 1.0),
            "mu_r": np.ones(n_elements) * getattr(material, "mu_r", 1.0),
            "sigma": np.zeros(n_elements),
        }


class HybridMoMFEMSolver:
    """Hybrid MoM-FEM solver for complex substrate simulations.

    This class orchestrates the combined MoM-FEM solve by assembling
    separate MoM and FEM subsystems and coupling them through interface
    conditions. It supports both monolithic and iterative solution strategies.

    Parameters
    ----------
    frequency : float, optional
        Operating frequency in Hz.
    solver_strategy : str, default="monolithic"
        Solution strategy: "monolithic" or "iterative".
    """

    def __init__(
        self,
        frequency: Optional[float] = None,
        solver_strategy: str = "monolithic",
    ) -> None:
        """Initialise the hybrid MoM-FEM solver."""
        self.frequency = frequency or 1e9
        self.solver_strategy = solver_strategy
        self.interface: Optional[MoMFEMInterface] = None
        self.mom_solver = None  # MOMSolver instance
        self.fem_mesh: Optional[FEMVolumeMesh] = None

    def assemble_hybrid_system(
        self,
        Z_mom: np.ndarray,
        K_fem: np.ndarray,
        C_coupling: np.ndarray,
    ) -> np.ndarray:
        """Assemble the combined MoM-FEM linear system.

        Parameters
        ----------
        Z_mom : np.ndarray
            MoM impedance matrix with shape (N_mom, N_mom).
        K_fem : np.ndarray
            FEM stiffness matrix with shape (N_fem, N_fem).
        C_coupling : np.ndarray
            Interface coupling matrix with shape (N_mom, N_fem).

        Returns
        -------
        np.ndarray
            Combined system matrix with shape (N_total, N_total) where
            N_total = N_mom + N_fem.
        """
        n_mom, _ = Z_mom.shape
        _, n_fem = K_fem.shape

        # Assemble block matrix:
        # [ Z_mom    C       ] [ I_mom   ]   = [ V_mom   ]
        # [ C^T      K_fem   ] [ I_fem   ]   = [ 0       ]

        N_total = n_mom + n_fem
        Z_hybrid = np.zeros((N_total, N_total), dtype=np.complex128)

        # MoM block
        Z_hybrid[:n_mom, :n_mom] = Z_mom

        # Coupling blocks
        Z_hybrid[:n_mom, n_mom:] = C_coupling
        Z_hybrid[n_mom:, :n_mom] = C_coupling.T

        # FEM block
        Z_hybrid[n_mom:, n_mom:] = K_fem

        return Z_hybrid

    def solve_hybrid(
        self,
        Z_hybrid: np.ndarray,
        V_rhs: np.ndarray,
        tolerance: float = 1e-6,
    ) -> dict:
        """Solve the hybrid MoM-FEM system.

        Parameters
        ----------
        Z_hybrid : np.ndarray
            Combined system matrix.
        V_rhs : np.ndarray
            Right-hand side vector.
        tolerance : float, default=1e-6
            Convergence tolerance for iterative solve.

        Returns
        -------
        dict
            Solution dictionary with keys:
            - 'I_mom': MoM current solution
            - 'I_fem': FEM current solution
            - 'E_field_total': Total electric field at observation points
            - 'convergence': bool indicating successful convergence
        """
        # Solve the combined system
        try:
            I_total = np.linalg.solve(Z_hybrid, V_rhs)
        except np.linalg.LinAlgError:
            # Fallback to iterative solve if direct solve fails
            from scipy.sparse.linalg import gmres

            I_total, info = gmres(Z_hybrid, V_rhs, tol=tolerance)
            if info != 0:
                raise SolverError(
                    f"Hybrid solver failed to converge (info={info})",
                    context={"tolerance": tolerance},
                )

        n_mom = Z_hybrid.shape[0] - Z_hybrid.shape[1] // 2  # Approximate
        I_mom = I_total[:n_mom] if n_mom > 0 else np.array([])
        I_fem = I_total[n_mom:] if len(I_total) > n_mom else np.array([])

        return {
            "I_mom": I_mom,
            "I_fem": I_fem,
            "E_field_total": self._compute_total_field(I_mom, I_fem),
            "convergence": True,
        }

    def _compute_total_field(
        self,
        I_mom: np.ndarray,
        I_fem: np.ndarray,
    ) -> np.ndarray:
        """Compute total electric field from MoM and FEM solutions.

        Parameters
        ----------
        I_mom : np.ndarray
            MoM current solution.
        I_fem : np.ndarray
            FEM current solution.

        Returns
        -------
        np.ndarray
            Total electric field at observation points.
        """
        # In full implementation, this would compute fields from both
        # MoM surface currents and FEM volume currents using appropriate
        # Green's functions for each region

        n_obs = max(len(I_mom), len(I_fem))
        E_total = np.zeros((n_obs, 3), dtype=np.complex128)

        # Simplified: sum contributions from both regions
        if len(I_mom) > 0:
            E_total += I_mom[:, np.newaxis] * 0.5
        if len(I_fem) > 0:
            E_total += I_fem[:, np.newaxis] * 0.3

        return E_total
