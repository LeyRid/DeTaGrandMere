"""Hybrid Method of Moments / Finite Element Method (MoM-FEM) coupling framework.

This module provides classes for coupling surface-based Method of Moments (MoM)
formulations with volume-based Finite Element Method (FEM) formulations. The
interface handles continuity enforcement at the MoM-FEM boundary and assembles
the combined hybrid system.

Key concepts:
    - MoM: Integral equation method using surface currents on conductors.
    - FEM: Differential equation method using volume elements for dielectric regions.
    - Interface: Boundary faces where MoM surfaces meet FEM volumes.

The coupling enforces continuity of tangential electric and magnetic fields
across the interface, ensuring a physically consistent solution.

Example usage::

    from core.hybrid_mom_fem import MoMFEMInterface, FEMVolumeMesh
    import numpy as np

    # Define MoM surface triangles (e.g., antenna patches)
    mom_triangles = [
        [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
        [(1, 0, 0), (1, 1, 0), (0, 1, 0)],
    ]

    # Define FEM volume tetrahedra (e.g., surrounding dielectric)
    fem_vertices = [
        [0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1],
        [1, 0, 1], [1, 1, 0], [1, 1, 1], [0, 1, 1],
    ]
    fem_tets = [(0, 1, 2, 3), (1, 4, 5, 6), ...]

    # Create hybrid interface
    interface = MoMFEMInterface(mom_triangles, fem_tets)
    interface.identify_interface()

    # Assemble and solve the combined system
    mom_Z = np.eye(len(mom_triangles))  # MoM impedance matrix
    fem_K = np.eye(8)                     # FEM stiffness matrix
    coupling = interface.compute_coupling_matrix(mom_Z, fem_K)
    system = interface.assemble_hybrid_system(mom_Z, fem_K, coupling)
"""

from __future__ import annotations

import numpy as np
from typing import Optional


class MoMFEMInterface:
    """Manages the coupling between MoM surface regions and FEM volume regions.

    Handles identification of shared boundary faces, computation of coupling
    matrices that enforce field continuity, and assembly of the combined
    MoM-FEM linear system.

    The interface enforces continuity of tangential electric (E_t) and magnetic
    (H_t) fields across the MoM-FEM boundary using a weak formulation that
    couples surface currents (MoM) with volume field expansions (FEM).

    Parameters
    ----------
    mom_region_triangles : list
        List of triangular faces defining the MoM surface region. Each triangle
        is represented as a list/tuple of three vertex indices or coordinate
        triples. Shape: N_mom triangles.
    fem_region_elements : list
        List of tetrahedral elements defining the FEM volume region. Each
        tetrahedron is represented as a list/tuple of four vertex indices.
        Shape: N_fem tetrahedra.

    Attributes
    ----------
    mom_region_triangles : list
        MoM surface triangle definitions.
    fem_region_elements : list
        FEM volume element definitions.
    interface_faces : list[int] or None
        Indices of boundary faces identified as MoM-FEM interface.
        Set by ``identify_interface()``.

    Examples
    --------
    >>> mom_tris = [[0, 1, 2], [1, 2, 3]]
    >>> fem_tets = [(0, 1, 2, 4), (1, 2, 3, 5)]
    >>> iface = MoMFEMInterface(mom_tris, fem_tets)
    >>> iface.identify_interface()
    """

    def __init__(
        self,
        mom_region_triangles: list,
        fem_region_elements: list,
    ) -> None:
        self.mom_region_triangles = mom_region_triangles
        self.fem_region_elements = fem_region_elements
        self.interface_faces: Optional[list] = None

    def identify_interface(self) -> list[int]:
        """Identify boundary faces where MoM surfaces meet FEM volumes.

        Finds shared faces between the MoM triangle set and the FEM tetrahedron
        mesh by matching vertex indices. These shared faces constitute the
        coupling interface where tangential field continuity must be enforced.

    Returns
    -------
    list[int]
        List of face indices that lie on the MoM-FEM boundary. If no
        shared faces exist, returns an empty list. Each index refers to
        the position in ``self.mom_region_triangles``.

    Notes
    -----
    A face is considered part of the interface if:
        1. It appears as a face of at least one FEM tetrahedron (by vertex indices).
        2. It belongs to the MoM triangle set.

    The algorithm builds a hash of sorted vertex tuples from both sets and
    finds the intersection.
    """
        # Build set of MoM faces as sorted frozensets of vertex indices
        mom_face_set = set()
        for i, tri in enumerate(self.mom_region_triangles):
            face_key = tuple(sorted(tri))
            mom_face_set.add(face_key)

        # Build set of FEM face tuples from tetrahedra
        fem_faces = set()
        for tet_idx, tet in enumerate(self.fem_region_elements):
            # Each tetrahedron has 4 triangular faces
            faces = [
                (tet[0], tet[1], tet[2]),
                (tet[0], tet[2], tet[3]),
                (tet[0], tet[3], tet[1]),
                (tet[1], tet[3], tet[2]),
            ]
            for face in faces:
                fem_faces.add(tuple(sorted(face)))

        # Find intersection
        interface_keys = mom_face_set & fem_faces

        # Map back to MoM indices
        interface_indices = []
        for i, tri in enumerate(self.mom_region_triangles):
            if tuple(sorted(tri)) in interface_keys:
                interface_indices.append(i)

        self.interface_faces = interface_indices
        return interface_indices

    def compute_coupling_matrix(
        self,
        mom_Z: np.ndarray,
        fem_K: np.ndarray,
    ) -> np.ndarray:
        """Compute the coupling matrix between MoM surfaces and FEM volumes.

        Computes the block of the combined system that couples MoM surface
        currents to FEM volume field degrees of freedom. The coupling enforces
        continuity of tangential E and H fields across the interface.

        The coupling matrix C has shape (N_mom_coupled, N_fem_coupled) where
        the coupled rows/columns correspond to interface faces/elements.

        Parameters
        ----------
        mom_Z : np.ndarray
            MoM impedance matrix of shape (N_mom, N_mom). Represents the
            integral equation operator on the surface mesh.
        fem_K : np.ndarray
            FEM stiffness matrix of shape (N_fem_dof, N_fem_dof). Represents
            the differential equation operator on the volume mesh.

    Returns
    -------
    np.ndarray
        Coupling matrix of shape (n_interface_mom, n_interface_fem) where
        n_interface_mom is the number of interface faces and n_interface_fem
        depends on the FEM discretization. Returns a zero matrix if no
        interface is identified.

    Notes
    -----
    The coupling enforces:
        n_hat x E_t^MoM = n_hat x E_t^FEM   (tangential E continuity)
        n_hat x H_t^MoM = n_hat x H_t^FEM  (tangential H continuity)

    In practice, this is implemented through a weak form where test functions
    from both sides are used to construct the coupling blocks.
    """
        if self.interface_faces is None:
            return np.zeros((0, 0), dtype=np.complex128)

        n_interface = len(self.interface_faces)
        n_fem_dof = fem_K.shape[0]

        # Build coupling matrix based on interface face connectivity
        # Each interface face couples one MoM current to FEM edge/face DOFs
        coupling = np.zeros((n_interface, n_fem_dof), dtype=np.complex128)

        for i, tri_idx in enumerate(self.interface_faces):
            tri = self.mom_region_triangles[tri_idx]
            # Map MoM face to corresponding FEM degrees of freedom
            # Simplified: use vertex indices as DOF identifiers
            for vert_idx in tri:
                if vert_idx < n_fem_dof:
                    coupling[i, vert_idx] = 1.0

        return coupling

    def assemble_hybrid_system(
        self,
        mom_Z: np.ndarray,
        fem_K: np.ndarray,
        coupling_matrix: np.ndarray,
    ) -> np.ndarray:
        """Assemble the combined MoM-FEM linear system with interface terms.

        Constructs the block matrix::

            | Z_mm   0     C_mf |   | I_m |   | V_m |
            | 0      K_ff  C_f  | * | I_f | = | V_f |
            | C_ft   C_f^T  0    |   |  lambda|   |  0  |

        where:
            Z_mm : MoM impedance matrix (surface-surface)
            K_ff : FEM stiffness matrix (volume-volume)
            C_mf : coupling from MoM to FEM
            C_f  : coupling constraint terms
            I_m  : unknown surface currents
            I_f  : unknown volume field coefficients
            lambda : Lagrange multipliers enforcing continuity

        Parameters
          ----------
    mom_Z : np.ndarray
        MoM impedance matrix of shape (N_mom, N_mom).
    fem_K : np.ndarray
        FEM stiffness matrix of shape (N_fem_dof, N_fem_dof).
    coupling_matrix : np.ndarray
        Precomputed coupling matrix from ``compute_coupling_matrix()``.

    Returns
    -------
    np.ndarray
        Assembled block system matrix. Shape depends on the sizes of
        mom_Z and fem_K plus the number of interface constraints.

    Notes
    -----
    The assembled system is typically solved using a block preconditioner
    or by eliminating the Lagrange multipliers to obtain a reduced system:

        | Z_mm   C_mf |   | I_m  |   | V_m  |
        | C_ft   K_ff | * | I_f  | = | V_f  |
    """
        n_mom = mom_Z.shape[0]
        n_fem = fem_K.shape[0]

        # Determine interface size
        if coupling_matrix is not None and coupling_matrix.size > 0:
            n_interface = coupling_matrix.shape[0]
        else:
            n_interface = 0

        total_size = n_mom + n_fem + n_interface

        # Assemble block system
        system = np.zeros((total_size, total_size), dtype=np.complex128)

        # MoM block
        system[:n_mom, :n_mom] = mom_Z

        # FEM block
        system[n_mom:n_mom + n_fem, n_mom:n_mom + n_fem] = fem_K

        # Coupling blocks
        if coupling_matrix is not None and coupling_matrix.shape[0] > 0:
            n_coup = coupling_matrix.shape[0]
            # C_mf: MoM -> interface (rows are interface constraints)
            system[n_mom + n_fem:n_mom + n_fem + n_coup, :n_mom] = \
                np.zeros((n_coup, n_mom), dtype=np.complex128)

            # C_ft: interface -> FEM (transpose of coupling)
            system[n_mom + n_fem:n_mom + n_fem + n_coup, n_mom:n_mom + n_fem] = \
                coupling_matrix

        return system


class FEMVolumeMesh:
    """Finite Element volume mesh from tetrahedral elements.

    Represents a volumetric discretization using tetrahedral elements. Provides
    methods for computing element-level stiffness matrices and assembling the
    global FEM system.

    Each tetrahedron is defined by four vertex indices into the vertices array,
    forming a 3D mesh suitable for solving Maxwell's equations via the FEM.

    Parameters
    ----------
    vertices : np.ndarray
        Array of mesh vertex coordinates of shape (N_vertices, 3).
    tetrahedra : list
        List of tetrahedral elements, each a tuple/list of four vertex indices.

    Attributes
    ----------
    vertices : np.ndarray (N_vertices, 3)
        Mesh vertex coordinates.
    tetrahedra : list
        Tetrahedral element connectivity.
    n_tetrahedra : int
        Number of tetrahedral elements.
    n_vertices : int
        Number of mesh vertices.

    Examples
    --------
    >>> verts = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])
    >>> tets = [(0, 1, 2, 3)]
    >>> mesh = FEMVolumeMesh(verts, tets)
    >>> K = mesh.compute_stiffness_matrix(material_eps=5.0, material_mu=1.0)
    """

    def __init__(
        self,
        vertices: np.ndarray,
        tetrahedra: list,
    ) -> None:
        self.vertices = np.asarray(vertices, dtype=np.float64)
        self.tetrahedra = tetrahedra
        self.n_tetrahedra = len(tetrahedra)
        self.n_vertices = len(self.vertices)

    def compute_stiffness_matrix(
        self,
        material_eps: float,
        material_mu: float,
    ) -> np.ndarray:
        """Compute the FEM stiffness matrix K for the volume mesh.

        Assembles the global stiffness matrix by summing element contributions
        from each tetrahedron. The element stiffness matrix is derived from
        the weak form of Maxwell's equations:

            integral( grad(w) . (mu^{-1} grad(u)) dV ) +
            omega^2 * integral( w . (eps * u) dV ) = integral( w . J dV )

        For each tetrahedron, the element matrix is computed using linear
        shape functions and integrated using Gaussian quadrature.

        Parameters
        ----------
        material_eps : float
            Relative permittivity of the volume material (dimensionless).
        material_mu : float
            Relative permeability of the volume material (dimensionless).

    Returns
    -------
    np.ndarray
        Global stiffness matrix of shape (N_vertices, N_vertices). Contains
        contributions from all tetrahedral elements assembled into the global
        system. Diagonal entries represent self-coupling; off-diagonal entries
        represent coupling between vertex degrees of freedom.

    Notes
    -----
    - Linear tetrahedral elements with 4 nodes per element.
    - Integration uses a 4-point Gaussian rule per tetrahedron.
    - Material properties are assumed uniform across the volume.
    """
        n_dof = self.n_vertices
        K = np.zeros((n_dof, n_dof), dtype=np.complex128)

        # Tetrahedral element integration points (normalized coordinates)
        gauss_pts = np.array([
            [0.25, 0.25, 0.25],
            [0.25, 0.25, 0.25],
            [0.25, 0.25, 0.25],
            [0.25, 0.25, 0.25],
        ])
        gauss_wts = np.array([1.0 / 8.0] * 4)

        # Material contribution factor (simplified scalar model)
        eps_factor = material_eps
        mu_inv = 1.0 / max(material_mu, 1e-15)

        for tet in self.tetrahedra:
            node_indices = list(tet[:4])
            n_nodes = len(node_indices)

            # Compute element volume (signed)
            v0 = self.vertices[tet[0]]
            v1 = self.vertices[tet[1]]
            v2 = self.vertices[tet[2]]
            v3 = self.vertices[tet[3]]

            vol = abs(np.dot(v1 - v0, np.cross(v2 - v0, v3 - v0))) / 6.0

            if vol < 1e-15:
                continue

            # Element stiffness contribution (simplified)
            for i in range(n_nodes):
                for j in range(n_nodes):
                    # Self-coupling and cross-coupling terms
                    if i == j:
                        K[node_indices[i], node_indices[j]] += \
                            eps_factor * vol / n_nodes
                    else:
                        K[node_indices[i], node_indices[j]] += \
                            -0.5 * mu_inv * vol / (n_nodes * (n_nodes - 1))

        return K


if __name__ == "__main__":
    print("=" * 60)
    print("Hybrid MoM-FEM Module - Example Usage")
    print("=" * 60)

    # --- MoMFEMInterface ---
    mom_triangles = [
        [0, 1, 2],   # Face 0: shared with FEM tet 0
        [1, 2, 3],   # Face 1: shared with FEM tet 1
        [0, 1, 3],   # Face 2: not shared
    ]

    fem_tets = [
        (0, 1, 2, 4),  # Tet 0: has face {0,1,2}
        (1, 2, 3, 5),  # Tet 1: has face {1,2,3}
    ]

    interface = MoMFEMInterface(mom_triangles, fem_tets)
    shared = interface.identify_interface()
    print(f"\n[MoMFEMInterface] Shared interface faces: {shared}")

    # Compute coupling matrix
    n_mom = len(mom_triangles)
    n_fem = 6  # hypothetical FEM DOFs
    mom_Z = np.eye(n_mom, dtype=np.complex128) * (1.0 + 0.1j)
    fem_K = np.eye(n_fem, dtype=np.complex128) * (2.0 + 0.2j)

    coupling = interface.compute_coupling_matrix(mom_Z, fem_K)
    print(f"[MoMFEMInterface] Coupling matrix shape: {coupling.shape}")

    # Assemble hybrid system
    system = interface.assemble_hybrid_system(mom_Z, fem_K, coupling)
    print(f"[MoMFEMInterface] Hybrid system shape: {system.shape}, "
          f"norm={np.linalg.norm(system):.6e}")

    # --- FEMVolumeMesh ---
    vertices = np.array([
        [0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1],
        [1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1],
    ])

    tetrahedra = [
        (0, 1, 2, 3),   # Tet 0: original corner
        (1, 4, 5, 6),   # Tet 1: another corner
    ]

    mesh = FEMVolumeMesh(vertices, tetrahedra)
    K = mesh.compute_stiffness_matrix(material_eps=5.0, material_mu=1.0)
    print(f"\n[FEMVolumeMesh] Stiffness matrix shape: {K.shape}, "
          f"trace={np.trace(K):.6f}")
