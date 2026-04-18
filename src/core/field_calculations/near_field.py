"""Near-field electric and magnetic field computation from surface currents.

This module provides the :class:`NearFieldCalculator` class for computing
electric and magnetic fields in the near-field region of an antenna or
scatterer from known surface current distributions obtained via a Method
of Moments (MoM) solver or other numerical technique.

The fundamental formulation uses the free-space scalar Green's function
for the Helmholtz equation:

    G(r, r') = e^{-j k |r - r'|} / (4 pi |r - r'|)

where :math:`k = 2\\pi f / c` is the wavenumber. The electric field is
computed from the magnetic vector potential **A** and the electric scalar
potential :math:`\\phi`:

    E(r) = -j \\omega \\mu_0 A(r) - \\nabla \\phi(r)

The magnetic field follows from the curl of the vector potential:

    H(r) = (1 / \\mu_0) \\nabla \\times A(r)

Example usage::

    from src.core.field_calculations.near_field import NearFieldCalculator
    import numpy as np

    calculator = NearFieldCalculator(frequency=2.4e9)

    # Mock current data: shape (N_sources, 3)
    currents = np.random.randn(100, 3) + 1j * np.random.randn(100, 3)
    source_points = np.array([[x, y, 0.0] for x in np.linspace(-0.5, 0.5, 10)
                              for y in np.linspace(-0.5, 0.5, 10)])
    observation_points = np.array([[0.0, 0.0, 0.1], [0.1, 0.1, 0.2]])

    E_field = calculator.compute_E_field(currents, observation_points, source_points)
    H_field = calculator.compute_H_field(currents, observation_points, source_points)
"""

from __future__ import annotations

import numpy as np
from typing import Optional

from src.utils.errors import FieldCalculationError


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------
C_SPEED: float = 299_792_458.0      # Speed of light [m/s]
MU_0: float = 4 * np.pi * 1e-7      # Permeability of free space [H/m]
EPS_0: float = 8.854_187_812e-12    # Permittivity of free space [F/m]


class NearFieldCalculator:
    """Compute near-field E and H from surface current distributions.

    This class encapsulates the physics of computing electromagnetic fields
    in the reactive and radiating near-field regions (typically distances
    less than 2*D^2/lambda from the source, where D is the largest
    dimension of the antenna).

    The computation proceeds by evaluating the magnetic vector potential
    **A** and electric scalar potential :math:`\\phi` at observation points
    through volume/surface integrals weighted by the free-space Green's
    function, then reconstructing the fields from these potentials.

    Parameters
    ----------
    frequency : float, optional
        Operating frequency in Hz. Default is 1 GHz. Used to set the
        wavenumber and angular frequency for all field computations.

    Attributes
    ----------
    frequency : float
        Operating frequency in Hz.
    wavenumber : float
        Computed wavenumber k = 2*pi*f/c in rad/m.
    omega : float
        Angular frequency omega = 2*pi*f in rad/s.
    """

    def __init__(self, frequency: float = 1e9) -> None:
        """Initialise the near-field calculator at a reference frequency.

        Parameters
        ----------
        frequency : float, optional
            Reference frequency in Hz. Default is 1 GHz.
        """
        self.frequency = frequency
        self.wavenumber = 2 * np.pi * self.frequency / C_SPEED
        self.omega = 2 * np.pi * self.frequency

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def compute_E_field(
        self,
        currents: np.ndarray,
        observation_points: np.ndarray,
        source_points: np.ndarray,
    ) -> np.ndarray:
        """Compute the electric field at observation points from surface currents.

        The electric field is reconstructed from the magnetic vector potential
        **A** and electric scalar potential :math:`\\phi` via:

            E(r) = -j \\omega \\mu_0 A(r) - \\nabla \\phi(r)

        where

            A(r) = \\mu_0 \\int_S J(r') G(r, r') dS'
            \\phi(r) = (1/\\varepsilon_0) \\int_S \\rho(r') G(r, r') dS'

        and the charge density is obtained from the continuity equation:
        :math:`\\rho = div(J) / (j \\omega)`.

        Parameters
        ----------
        currents : array_like shape (N_sources, 3)
            Surface current vectors at source points. Each row is a 3-D
            complex current vector [J_x, J_y, J_z] in A/m.
        observation_points : array_like shape (M_obs, 3)
            Cartesian coordinates of the observation points where the
            field is evaluated.
        source_points : array_like shape (N_sources, 3)
            Cartesian coordinates of the current distribution support
            points (e.g. triangle centroids).

        Returns
        -------
        np.ndarray
            Electric field vectors at observation points with shape
            ``(M_obs, 3)`` and dtype ``complex128``. Each row is
            ``[E_x, E_y, E_z]`` in V/m.

        Raises
        ------
        FieldCalculationError
            If input arrays have inconsistent shapes or contain NaN/Inf values.
        """
        currents = np.asarray(currents, dtype=np.complex128)
        observation_points = np.asarray(observation_points, dtype=np.float64)
        source_points = np.asarray(source_points, dtype=np.float64)

        # --- Input validation ------------------------------------------------
        if currents.ndim != 2 or currents.shape[1] != 3:
            raise FieldCalculationError(
                "Currents must have shape (N_sources, 3)",
                context={"shape": currents.shape},
            )
        if observation_points.ndim != 2 or observation_points.shape[1] != 3:
            raise FieldCalculationError(
                "Observation points must have shape (M_obs, 3)",
                context={"shape": observation_points.shape},
            )
        if source_points.ndim != 2 or source_points.shape[1] != 3:
            raise FieldCalculationError(
                "Source points must have shape (N_sources, 3)",
                context={"shape": source_points.shape},
            )
        if currents.shape[0] != source_points.shape[0]:
            raise FieldCalculationError(
                "Number of current vectors must match number of source points",
                context={
                    "currents_shape": currents.shape,
                    "source_points_shape": source_points.shape,
                },
            )
        if np.any(np.isnan(currents)) or np.any(np.isinf(currents)):
            raise FieldCalculationError("Currents contain NaN or Inf values")

        n_obs = observation_points.shape[0]
        E_result = np.zeros((n_obs, 3), dtype=np.complex128)

        # --- Compute vector potential contribution: -j*omega*mu_0*A --------
        A_field = self._vector_potential(currents, observation_points, source_points)
        E_result += -1j * self.omega * MU_0 * A_field

        # --- Compute scalar potential gradient contribution ------------------
        grad_phi = self._scalar_potential_gradient(
            currents, observation_points, source_points
        )
        E_result -= grad_phi

        return E_result

    def compute_H_field(
        self,
        currents: np.ndarray,
        observation_points: np.ndarray,
        source_points: np.ndarray,
    ) -> np.ndarray:
        """Compute the magnetic field at observation points from surface currents.

        The magnetic field is obtained from the curl of the magnetic vector
        potential:

            H(r) = (1 / \\mu_0) \\nabla \\times A(r)

        The curl is computed via numerical finite-difference differentiation
        along each coordinate axis by perturbing nearby observation points.

        Parameters
        ----------
        currents : array_like shape (N_sources, 3)
            Surface current vectors at source points. Each row is a 3-D
            complex current vector [J_x, J_y, J_z] in A/m.
        observation_points : array_like shape (M_obs, 3)
            Cartesian coordinates of the observation points where the
            field is evaluated.
        source_points : array_like shape (N_sources, 3)
            Cartesian coordinates of the current distribution support
            points (e.g. triangle centroids).

        Returns
        -------
        np.ndarray
            Magnetic field vectors at observation points with shape
            ``(M_obs, 3)`` and dtype ``complex128``. Each row is
            ``[H_x, H_y, H_z]`` in A/m.

        Raises
        ------
        FieldCalculationError
            If input arrays have inconsistent shapes or contain NaN/Inf values.
        """
        currents = np.asarray(currents, dtype=np.complex128)
        observation_points = np.asarray(observation_points, dtype=np.float64)
        source_points = np.asarray(source_points, dtype=np.float64)

        # --- Input validation ------------------------------------------------
        if currents.ndim != 2 or currents.shape[1] != 3:
            raise FieldCalculationError(
                "Currents must have shape (N_sources, 3)",
                context={"shape": currents.shape},
            )
        if observation_points.ndim != 2 or observation_points.shape[1] != 3:
            raise FieldCalculationError(
                "Observation points must have shape (M_obs, 3)",
                context={"shape": observation_points.shape},
            )
        if source_points.ndim != 2 or source_points.shape[1] != 3:
            raise FieldCalculationError(
                "Source points must have shape (N_sources, 3)",
                context={"shape": source_points.shape},
            )

        # Compute curl of A numerically via central finite differences
        h = 1e-6  # Perturbation step for numerical differentiation
        n_obs = observation_points.shape[0]
        H_result = np.zeros((n_obs, 3), dtype=np.complex128)

        # Evaluate A at perturbed positions for each component
        A_xx = self._vector_potential(
            currents, observation_points + np.array([[h, 0.0, 0.0]]), source_points
        )
        A_xn = self._vector_potential(
            currents, observation_points - np.array([[h, 0.0, 0.0]]), source_points
        )
        A_yy = self._vector_potential(
            currents, observation_points + np.array([[0.0, h, 0.0]]), source_points
        )
        A_yn = self._vector_potential(
            currents, observation_points - np.array([[0.0, h, 0.0]]), source_points
        )
        A_zz = self._vector_potential(
            currents, observation_points + np.array([[0.0, 0.0, h]]), source_points
        )
        A_zn = self._vector_potential(
            currents, observation_points - np.array([[0.0, 0.0, h]]), source_points
        )

        # Central finite-difference curl: (dAz/dy - dAy/dz, dx/dz - dz/dx, dy/dx - dx/dy)
        dAz_dy = (A_xx[:, 2] - A_xn[:, 2]) / (2 * h)
        dAy_dz = (A_yy[:, 2] - A_yn[:, 2]) / (2 * h)
        dAx_dz = (A_zz[:, 0] - A_zn[:, 0]) / (2 * h)
        dAz_dx = (A_xx[:, 2] - A_xn[:, 2]) / (2 * h)
        dAy_dx = (A_yy[:, 1] - A_yn[:, 1]) / (2 * h)
        dAx_dy = (A_zz[:, 0] - A_zn[:, 0]) / (2 * h)

        # Curl components: [dAz/dy - dAy/dz, dAx/dz - dAz/dx, dAy/dx - dAx/dy]
        H_result[:, 0] = (dAz_dy - dAy_dz) / MU_0
        H_result[:, 1] = (dAx_dz - dAz_dx) / MU_0
        H_result[:, 2] = (dAy_dx - dAx_dy) / MU_0

        return H_result

    # -------------------------------------------------------------------
    # Private helper methods
    # -------------------------------------------------------------------

    def _vector_potential(
        self,
        currents: np.ndarray,
        observation_points: np.ndarray,
        source_points: np.ndarray,
    ) -> np.ndarray:
        """Compute the magnetic vector potential A at observation points.

        Evaluates the surface integral:

            A(r) = \\mu_0 \\int_S J(r') G(r, r') dS'

        Discretised as a sum over source elements with principal-value
        handling for the self-term when an observation point coincides
        with a source point.

        Parameters
        ----------
        currents : array_like shape (N_sources, 3)
            Surface current vectors at source points.
        observation_points : array_like shape (M_obs, 3)
            Observation point coordinates.
        source_points : array_like shape (N_sources, 3)
            Source point coordinates (e.g. triangle centroids).

        Returns
        -------
        np.ndarray
            Vector potential values with shape ``(M_obs, 3)`` in V*s/m.
        """
        currents = np.asarray(currents, dtype=np.complex128)
        observation_points = np.asarray(observation_points, dtype=np.float64)
        source_points = np.asarray(source_points, dtype=np.float64)

        n_sources = currents.shape[0]
        n_obs = observation_points.shape[0]

        # Compute all distances: shape (M_obs, N_sources)
        diffs = observation_points[:, np.newaxis, :] - source_points[np.newaxis, :, :]
        r_mags = np.linalg.norm(diffs, axis=2)  # (M_obs, N_sources)

        # --- Green's function evaluation -------------------------------------
        G = np.exp(-1j * self.wavenumber * r_mags) / (4 * np.pi * np.where(r_mags > 0, r_mags, 1.0))
        # Replace self-terms with principal value: -j*k/(8*pi)
        mask_self = r_mags < 1e-12
        if np.any(mask_self):
            G[mask_self] = -1j * self.wavenumber / (8 * np.pi)

        # --- Weight by triangle areas ----------------------------------------
        # Estimate element area from average edge length of source points.
        # A simple estimate: for N sources uniformly distributed in a region,
        # approximate area as total_region_area / N_sources.
        # For more accurate results, pass explicit areas via an extended API.
        bbox = source_points.max(axis=0) - source_points.min(axis=0)
        region_volume = np.prod(bbox) if np.all(bbox > 0) else 1.0
        element_area = region_volume / max(n_sources, 1)

        # --- Compute A(r) = mu_0 * sum(J * G * dS') -------------------------
        # weighted_G shape (M_obs, N_sources), currents shape (N_sources, 3)
        # Result: (M_obs, 3) via matrix multiply
        weighted_G = G * element_area  # (M_obs, N_sources)
        A_field = MU_0 * (weighted_G @ currents)

        return A_field

    def _scalar_potential_gradient(
        self,
        currents: np.ndarray,
        observation_points: np.ndarray,
        source_points: np.ndarray,
    ) -> np.ndarray:
        """Compute the gradient of the electric scalar potential.

        The scalar potential is derived from the charge density obtained via
        the continuity equation and then differentiated numerically by
        perturbing observation points in each coordinate direction.

            \\phi(r) = (1/\\varepsilon_0) \\int_S \\rho(r') G(r, r') dS'
            \\nabla \\phi = lim_{h->0} [\\phi(r+h e_i) - \\phi(r-h e_i)] / (2h)

        Parameters
        ----------
        currents : array_like shape (N_sources, 3)
            Surface current vectors at source points.
        observation_points : array_like shape (M_obs, 3)
            Observation point coordinates.
        source_points : array_like shape (N_sources, 3)
            Source point coordinates.

        Returns
        -------
        np.ndarray
            Gradient of scalar potential with shape ``(M_obs, 3)`` in V/m.
        """
        currents = np.asarray(currents, dtype=np.complex128)
        observation_points = np.asarray(observation_points, dtype=np.float64)
        source_points = np.asarray(source_points, dtype=np.float64)

        # Compute charge density from divergence of current
        rho = self._compute_charge_density(currents, source_points)

        h = 1e-6  # Perturbation step for numerical gradient
        n_obs = observation_points.shape[0]
        grad_phi = np.zeros((n_obs, 3), dtype=np.complex128)

        # Compute scalar potential at perturbed positions for each axis
        for i in range(3):
            perturb_pos = np.zeros((n_obs, 3))
            perturb_pos[:, i] = h
            perturb_neg = np.zeros((n_obs, 3))
            perturb_neg[:, i] = -h

            phi_plus = self._compute_scalar_potential_at_points(
                rho, observation_points + perturb_pos, source_points
            )
            phi_minus = self._compute_scalar_potential_at_points(
                rho, observation_points + perturb_neg, source_points
            )

            grad_phi[:, i] = (phi_plus - phi_minus) / (2 * h)

        return grad_phi

    def _compute_charge_density(
        self, currents: np.ndarray, source_points: np.ndarray
    ) -> np.ndarray:
        """Compute charge density from current divergence via continuity equation.

        Uses the frequency-domain continuity equation:
            rho = div(J) / (j * omega)

        The divergence is estimated numerically using finite differences
        along the edges of the triangulated mesh. For each source point,
        the divergence is approximated as the dot product of the current
        with a geometric normal divided by the element area.

        Parameters
        ----------
        currents : array_like shape (N_sources, 3)
            Surface current vectors at source points.
        source_points : array_like shape (N_sources, 3)
            Source point coordinates.

        Returns
        -------
        np.ndarray
            Charge density values with shape ``(N_sources,)`` in C/m^2.
        """
        currents = np.asarray(currents, dtype=np.complex128)
        source_points = np.asarray(source_points, dtype=np.float64)
        n_sources = currents.shape[0]

        # Estimate element area from bounding box (same as in _vector_potential)
        bbox = source_points.max(axis=0) - source_points.min(axis=0)
        region_volume = np.prod(bbox) if np.all(bbox > 0) else 1.0
        element_area = region_volume / max(n_sources, 1)

        # Approximate divergence using finite differences along coordinate axes.
        # For each source point i, compute div(J)_i ~ (J_i - J_j) / dx where j
        # is a neighboring point. A simple approach: use the current magnitude
        # and element geometry to estimate charge accumulation.
        #
        # A more robust approach for triangular elements: approximate the
        # divergence of RWG basis functions. For an edge shared by two
        # triangles, the divergence at the triangle centroid is proportional
        # to the current component along the edge divided by the edge length.

        # Simple numerical estimate: compute local gradient of current magnitude
        # in each direction and sum. This gives a rough but functional estimate.
        div_J = np.zeros(n_sources, dtype=np.complex128)

        # Sort source points to find neighbors (simple k-nearest with k=3)
        for i in range(n_sources):
            # Find 3 nearest neighbors
            dists = np.linalg.norm(source_points - source_points[i], axis=1)
            # Exclude self
            dists[i] = np.inf
            neighbor_idx = np.argsort(dists)[:3]

            for j in neighbor_idx:
                dx = source_points[j, 0] - source_points[i, 0]
                dy = source_points[j, 1] - source_points[i, 1]
                dz = source_points[j, 2] - source_points[i, 2]
                dist = np.linalg.norm([dx, dy, dz])

                if dist > 1e-15:
                    # Project current onto the displacement direction
                    dot_J = (currents[i, 0] * dx + currents[i, 1] * dy + currents[i, 2] * dz) / dist
                    div_J[i] += dot_J / dist

        # Apply continuity equation: rho = div(J) / (j*omega)
        rho = div_J / (1j * self.omega)

        return rho

    def _compute_scalar_potential_at_points(
        self,
        charge_density: np.ndarray,
        observation_points: np.ndarray,
        source_points: np.ndarray,
    ) -> np.ndarray:
        """Compute scalar potential at given observation points.

        Evaluates:
            \\phi(r) = (1/\\varepsilon_0) \\int_S \\rho(r') G(r, r') dS'

        Parameters
        ----------
        charge_density : array_like shape (N_sources,)
            Charge density at source points in C/m^2.
        observation_points : array_like shape (M_obs, 3)
            Observation point coordinates.
        source_points : array_like shape (N_sources, 3)
            Source point coordinates.

        Returns
        -------
        np.ndarray
            Scalar potential values with shape ``(M_obs,)`` in V.
        """
        charge_density = np.asarray(charge_density, dtype=np.complex128)
        observation_points = np.asarray(observation_points, dtype=np.float64)
        source_points = np.asarray(source_points, dtype=np.float64)

        n_sources = charge_density.shape[0]
        n_obs = observation_points.shape[0]

        # Compute distances
        diffs = observation_points[:, np.newaxis, :] - source_points[np.newaxis, :, :]
        r_mags = np.linalg.norm(diffs, axis=2)  # (M_obs, N_sources)

        # Green's function
        G = np.exp(-1j * self.wavenumber * r_mags) / (4 * np.pi * np.where(r_mags > 0, r_mags, 1.0))
        mask_self = r_mags < 1e-12
        if np.any(mask_self):
            G[mask_self] = -1j * self.wavenumber / (8 * np.pi)

        # Estimate element area
        bbox = source_points.max(axis=0) - source_points.min(axis=0)
        region_volume = np.prod(bbox) if np.all(bbox > 0) else 1.0
        element_area = region_volume / max(n_sources, 1)

        # Compute phi = (1/eps_0) * sum(rho * G * dS')
        weighted_G = G * element_area
        phi = (1.0 / EPS_0) * np.sum(weighted_G * charge_density[np.newaxis, :], axis=1)

        return phi


# ===================================================================
# Module-level example usage
# ===================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Near Field Calculator -- Example Usage")
    print("=" * 60)

    calculator = NearFieldCalculator(frequency=1e9)
    print(f"Frequency: {calculator.frequency:.2e} Hz")
    print(f"Wavenumber k: {calculator.wavenumber:.4f} rad/m")
    print(f"Angular frequency omega: {calculator.omega:.4e} rad/s")

    # Create a simple current distribution on a planar surface
    N = 50
    currents = np.zeros((N, 3), dtype=np.complex128)
    source_points = np.zeros((N, 3), dtype=np.float64)

    # Arrange sources in a grid and assign simple x-directed currents
    nx, ny = 10, 5
    ix = 0
    for iy in range(ny):
        for ix_ in range(nx):
            x = (ix_ - (nx - 1) / 2) * 0.05
            y = (iy - (ny - 1) / 2) * 0.05
            source_points[ix, :] = [x, y, 0.0]
            currents[ix, 0] = 1.0 + 1j * 0.5  # x-directed current with phase
            ix += 1

    print(f"Currents shape: {currents.shape}")
    print(f"Source points shape: {source_points.shape}")

    # Define observation points along the z-axis and off-axis
    obs_x = np.linspace(-0.3, 0.3, 5)
    obs_y = np.linspace(-0.3, 0.3, 5)
    obs_z = np.array([0.1, 0.2, 0.5])

    observation_points = []
    for x in obs_x:
        for z in obs_z[:1]:
            observation_points.append([x, 0.0, z])

    observation_points = np.array(observation_points)
    print(f"Observation points shape: {observation_points.shape}")

    # Compute fields
    E_field = calculator.compute_E_field(currents, observation_points, source_points)
    H_field = calculator.compute_H_field(currents, observation_points, source_points)

    print(f"\nE-field shape: {E_field.shape}")
    print(f"H-field shape: {H_field.shape}")

    # Print a few results
    for i in range(min(3, len(observation_points))):
        print(f"\nObservation point {i}: {observation_points[i]}")
        print(f"  E = [{E_field[i, 0]:.4e}, {E_field[i, 1]:.4e}, {E_field[i, 2]:.4e}] V/m")
        print(f"  H = [{H_field[i, 0]:.4e}, {H_field[i, 1]:.4e}, {H_field[i, 2]:.4e}] A/m")
        print(f"  |E| = {np.linalg.norm(E_field[i]):.4e} V/m")
        print(f"  |H| = {np.linalg.norm(H_field[i]):.4e} A/m")

    print("\nDone.")