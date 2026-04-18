"""Far-field transformation from surface current distributions.

This module provides the :class:`FarFieldTransformer` class for computing
far-field radiation patterns from known surface current distributions
obtained via a Method of Moments (MoM) solver or other numerical technique.

The far-field transformation evaluates the vector potential at large
distances using the asymptotic form of the Green's function:

    G(r, r') ~ e^{-j k r} / (4 pi r) * e^{j k r' \\cdot \\hat{r}}

where :math:`\\hat{r}` is the unit vector in the observation direction.
The far-field electric field is then obtained from the radiation integral
and projected onto spherical coordinate basis vectors:

    E_\\theta = -j k \\mu_0 F_\\theta
    E_\\phi   = -j k \\mu_0 F_\\phi

with :math:`F` being the vector far-field pattern.

Example usage::

    from src.core.field_calculations.far_field import FarFieldTransformer
    import numpy as np

    transformer = FarFieldTransformer(
        frequency=2.4e9,
        theta_resolution=3,   # 3-degree steps in theta (0..180)
        phi_resolution=6,     # 6-degree steps in phi (0..360)
    )

    currents = np.random.randn(100, 3) + 1j * np.random.randn(100, 3)
    source_points = np.array([[x, y, 0.0] for x in np.linspace(-0.5, 0.5, 10)
                              for y in np.linspace(-0.5, 0.5, 10)])

    # Compute full spherical far-field pattern
    results = transformer.compute_far_field(currents, source_points, None)
    print(f"E_theta shape: {results['E_theta'].shape}")
    print(f"Theta range: {results['theta'][0]:.1f} - {results['theta'][-1]:.1f} deg")

    # Compute a specific cut plane (e.g., E-plane at phi=90 deg)
    pattern = transformer.compute_radiation_pattern(
        currents, source_points, None, theta_deg=90, phi_deg=90
    )
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
ETA_0: float = np.sqrt(MU_0 / EPS_0)  # Intrinsic impedance of free space ~ 376.73 ohm


class FarFieldTransformer:
    """Transform surface currents to far-field radiation patterns.

    This class implements the far-field transformation that converts known
    current distributions (e.g., from a MoM solution) into far-field
    radiation patterns over a spherical angular grid.

    The far-field approximation assumes observation distances much larger
    than both the wavelength and the largest dimension of the antenna
    (typically > 2*D^2/lambda). Under this assumption, the field decays
    as 1/r and only the transverse components survive.

    Parameters
    ----------
    frequency : float, optional
        Operating frequency in Hz. Default is 1 GHz. Used to set the
        wavenumber and angular frequency for all computations.
    theta_resolution : int, optional
        Angular resolution in degrees for the theta scan (0 to 180).
        The number of theta points is ceil(180 / resolution). Default is 3,
        yielding 60 theta points.
    phi_resolution : int, optional
        Angular resolution in degrees for the phi scan (0 to 360).
        The number of phi points is ceil(360 / resolution). Default is 6,
        yielding 60 phi points.

    Attributes
    ----------
    frequency : float
        Operating frequency in Hz.
    wavenumber : float
        Computed wavenumber k = 2*pi*f/c in rad/m.
    omega : float
        Angular frequency omega = 2*pi*f in rad/s.
    theta_values : np.ndarray
        Theta angles in degrees used for computation.
    phi_values : np.ndarray
        Phi angles in degrees used for computation.
    n_theta : int
        Number of theta grid points.
    n_phi : int
        Number of phi grid points.
    """

    def __init__(
        self,
        frequency: float = 1e9,
        theta_resolution: int = 3,
        phi_resolution: int = 6,
    ) -> None:
        """Initialise the far-field transformer at a reference frequency.

        Parameters
        ----------
        frequency : float, optional
            Reference frequency in Hz. Default is 1 GHz.
        theta_resolution : int, optional
            Theta step size in degrees. Default is 3 (60 points over 0-180).
        phi_resolution : int, optional
            Phi step size in degrees. Default is 6 (60 points over 0-360).
        """
        self.frequency = frequency
        self.wavenumber = 2 * np.pi * self.frequency / C_SPEED
        self.omega = 2 * np.pi * self.frequency

        # Build angular grid
        self.theta_values = np.arange(0, 180 + theta_resolution, theta_resolution) % 180
        # Ensure we have points at both extremes
        if self.theta_values[0] == 0:
            self.theta_values = np.insert(self.theta_values, 0, 0)
        elif self.theta_values[-1] != 0 and self.theta_values[-1] != 180:
            self.theta_values = np.concatenate(
                ([0], self.theta_values, [180])
            )
        # Remove duplicates and sort
        self.theta_values = np.unique(self.theta_values)

        self.phi_values = np.arange(0, 360 + phi_resolution, phi_resolution) % 360
        if self.phi_values[0] != 0:
            self.phi_values = np.insert(self.phi_values, 0, 0)
        elif self.phi_values[-1] != 0:
            self.phi_values = np.concatenate(
                (self.phi_values, [0])
            )
        self.phi_values = np.unique(self.phi_values)

        self.n_theta = len(self.theta_values)
        self.n_phi = len(self.phi_values)

    def compute_far_field(
        self,
        currents: np.ndarray,
        source_points: np.ndarray,
        triangles_area: Optional[np.ndarray] = None,
    ) -> dict:
        """Compute the far-field E_theta and E_phi over the full angular grid.

        Evaluates the vector far-field pattern at every (theta, phi) point
        on the predefined spherical grid and returns both field components
        along with derived quantities (magnitude, phase).

        The far-field electric field components are computed from the
        radiation integral:

            F(\\theta, \\phi) = \\int_S J(r') e^{j k r' \\cdot \\hat{r}} dS'

        and projected onto the spherical unit vectors :math:`\\hat{\\theta}`
        and :math:`\\hat{\\phi}`.

        Parameters
        ----------
        currents : array_like shape (N_sources, 3)
            Surface current vectors at source points. Each row is a 3-D
            complex current vector [J_x, J_y, J_z] in A/m.
        source_points : array_like shape (N_sources, 3)
            Cartesian coordinates of the current distribution support
            points (e.g. triangle centroids).
        triangles_area : array_like shape (N_sources,), optional
            Area associated with each source element. If not provided,
            areas are estimated from the bounding box of the source region.

        Returns
        -------
        dict
            Dictionary containing:
            - ``theta`` (np.ndarray): Theta angles in degrees, shape ``(N_theta,)``.
            - ``phi`` (np.ndarray): Phi angles in degrees, shape ``(N_phi,)``.
            - ``E_theta`` (np.ndarray): E_theta field components, shape ``(N_theta, N_phi)``.
            - ``E_phi`` (np.ndarray): E_phi field components, shape ``(N_theta, N_phi)``.
            - ``magnitude`` (np.ndarray): |E| = sqrt(|E_theta|^2 + |E_phi|^2), shape ``(N_theta, N_phi)``.
            - ``phase`` (np.ndarray): Phase of the total E field in radians, shape ``(N_theta, N_phi)``.

        Raises
        ------
        FieldCalculationError
            If input arrays have inconsistent shapes or contain NaN/Inf values.
        """
        currents = np.asarray(currents, dtype=np.complex128)
        source_points = np.asarray(source_points, dtype=np.float64)

        # --- Input validation ------------------------------------------------
        if currents.ndim != 2 or currents.shape[1] != 3:
            raise FieldCalculationError(
                "Currents must have shape (N_sources, 3)",
                context={"shape": currents.shape},
            )
        if source_points.ndim != 2 or source_points.shape[1] != 3:
            raise FieldCalculationError(
                "Source points must have shape (N_sources, 3)",
                context={"shape": source_points.shape},
            )
        if np.any(np.isnan(currents)) or np.any(np.isinf(currents)):
            raise FieldCalculationError("Currents contain NaN or Inf values")

        n_sources = currents.shape[0]

        # --- Determine element areas -----------------------------------------
        if triangles_area is not None:
            triangles_area = np.asarray(triangles_area, dtype=np.float64)
            if triangles_area.ndim != 1 or len(triangles_area) != n_sources:
                raise FieldCalculationError(
                    "Triangles area must have shape (N_sources,)",
                    context={"shape": triangles_area.shape},
                )
        else:
            # Estimate from bounding box
            bbox = source_points.max(axis=0) - source_points.min(axis=0)
            region_volume = np.prod(bbox) if np.all(bbox > 0) else 1.0
            triangles_area = np.full(n_sources, region_volume / max(n_sources, 1))

        # --- Build angular grid ----------------------------------------------
        theta_rad = np.radians(self.theta_values)  # (N_theta,)
        phi_rad = np.radians(self.phi_values)      # (N_phi,)

        # --- Compute field components over full grid -------------------------
        E_theta_grid, E_phi_grid = self._compute_field_components(
            currents, source_points, triangles_area, theta_rad, phi_rad
        )

        # --- Compute magnitude and phase -------------------------------------
        total_E = np.sqrt(np.abs(E_theta_grid) ** 2 + np.abs(E_phi_grid) ** 2)
        phase = np.angle(E_theta_grid + 1j * E_phi_grid)

        return {
            "theta": self.theta_values,
            "phi": self.phi_values,
            "E_theta": E_theta_grid,
            "E_phi": E_phi_grid,
            "magnitude": total_E,
            "phase": phase,
        }

    def _compute_field_components(
        self,
        currents: np.ndarray,
        source_points: np.ndarray,
        triangles_area: np.ndarray,
        theta: np.ndarray,
        phi: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute E_theta and E_phi for given observation angles.

        Uses the far-field approximation where the vector potential at
        distance r is:

            A(r) ~ (e^{-j k r} / r) * F(theta, phi)

        with the radiation integral:

            F(theta, phi) = \\int_S J(r') e^{j k r' \\cdot \\hat{r}} dS'

        The far-field electric field is transverse and given by:

            E_\\theta = -j k \\mu_0 F_\\theta
            E_\\phi   = -j k \\mu_0 F_\\phi

        where :math:`F_\\theta = F \\cdot \\hat{\\theta}` and
        :math:`F_\\phi = F \\cdot \\hat{\\phi}`.

        Parameters
        ----------
        currents : array_like shape (N_sources, 3)
            Surface current vectors at source points.
        source_points : array_like shape (N_sources, 3)
            Source point coordinates.
        triangles_area : array_like shape (N_sources,)
            Area associated with each source element.
        theta : array_like
            Theta angles in radians for evaluation. Shape ``(N_theta,)``.
        phi : array_like
            Phi angles in radians for evaluation. Shape ``(N_phi,)``.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            (E_theta, E_phi) with shapes ``(N_theta, N_phi)`` each.
        """
        currents = np.asarray(currents, dtype=np.complex128)
        source_points = np.asarray(source_points, dtype=np.float64)
        triangles_area = np.asarray(triangles_area, dtype=np.float64)

        n_sources = currents.shape[0]
        n_theta = len(theta)
        n_phi = len(phi)

        # Pre-allocate output arrays
        E_theta_grid = np.zeros((n_theta, n_phi), dtype=np.complex128)
        E_phi_grid = np.zeros((n_theta, n_phi), dtype=np.complex128)

        # --- Compute for each (theta, phi) pair ------------------------------
        # Vectorise over theta and phi dimensions for efficiency.
        # For each observation direction:
        #   1. Compute unit vector r_hat = [sin(theta)*cos(phi), sin(theta)*sin(phi), cos(theta)]
        #   2. Compute phase factor exp(j*k*r'·r_hat) for all source points
        #   3. Integrate: F = sum(J * exp(...) * area)
        #   4. Project onto theta_hat and phi_hat

        # Theta_hat and phi_hat unit vectors (in Cartesian):
        # theta_hat = [cos(theta)*cos(phi), cos(theta)*sin(phi), -sin(theta)]
        # phi_hat   = [-sin(phi), cos(phi), 0]

        for it, th in enumerate(theta):
            for ip, ph in enumerate(phi):
                # Observation direction unit vector
                sin_th = np.sin(th)
                cos_th = np.cos(th)
                sin_ph = np.sin(ph)
                cos_ph = np.cos(ph)

                r_hat = np.array([
                    sin_th * cos_ph,
                    sin_th * sin_ph,
                    cos_th,
                ])

                # Theta and phi unit vectors
                theta_hat = np.array([
                    cos_th * cos_ph,
                    cos_th * sin_ph,
                    -sin_th,
                ])
                phi_hat = np.array([
                    -sin_ph,
                    cos_ph,
                    0.0,
                ])

                # Phase factor: exp(j*k*r'·r_hat) for each source point
                phase_factor = np.exp(
                    1j * self.wavenumber * np.dot(source_points, r_hat)
                )  # (N_sources,)

                # Radiation integral: F = sum(J * phase * area)
                weighted_currents = currents * phase_factor[:, np.newaxis] * triangles_area[:, np.newaxis]
                F = np.sum(weighted_currents, axis=0)  # (3,) vector in Cartesian

                # Project onto theta and phi directions
                F_theta = np.dot(F, theta_hat)
                F_phi = np.dot(F, phi_hat)

                # Far-field E components: E = -j*k*mu_0 * F_component
                E_theta_grid[it, ip] = -1j * self.wavenumber * MU_0 * F_theta
                E_phi_grid[it, ip] = -1j * self.wavenumber * MU_0 * F_phi

        return E_theta_grid, E_phi_grid

    def compute_radiation_pattern(
        self,
        currents: np.ndarray,
        source_points: np.ndarray,
        triangles_area: Optional[np.ndarray],
        theta_deg: float = 90.0,
        phi_deg: float = 0.0,
    ) -> dict:
        """Compute the radiation pattern at a specific cut plane.

        Evaluates E_theta and E_phi along a specified angular cut (either
        an E-plane or H-plane cut) across the full theta range from 0 to
        180 degrees while holding phi constant.

        This is useful for plotting standard antenna radiation pattern
        cuts such as the E-plane (phi = 0 or 180) or H-plane (phi = 90).

        Parameters
        ----------
        currents : array_like shape (N_sources, 3)
            Surface current vectors at source points.
        source_points : array_like shape (N_sources, 3)
            Source point coordinates.
        triangles_area : array_like shape (N_sources,), optional
            Area associated with each source element. If not provided,
            areas are estimated from the bounding box of the source region.
        theta_deg : float, optional
            Fixed theta angle in degrees for E-plane/H-plane cut. Default is 90
            (broadside). Used primarily for reference display.
        phi_deg : float, optional
            Fixed phi angle in degrees defining the cut plane. Default is 0
            (E-plane).

        Returns
        -------
        dict
            Dictionary containing:
            - ``theta_values`` (np.ndarray): Theta angles in degrees from 0 to 180.
            - ``E_theta_magnitude`` (np.ndarray): |E_theta| in dB, shape ``(N_theta,)``.
            - ``E_phi_magnitude`` (np.ndarray): |E_phi| in dB, shape ``(N_theta,)``.

        Raises
        ------
        FieldCalculationError
            If input arrays have inconsistent shapes or contain NaN/Inf values.
        """
        currents = np.asarray(currents, dtype=np.complex128)
        source_points = np.asarray(source_points, dtype=np.float64)

        # --- Input validation ------------------------------------------------
        if currents.ndim != 2 or currents.shape[1] != 3:
            raise FieldCalculationError(
                "Currents must have shape (N_sources, 3)",
                context={"shape": currents.shape},
            )
        if source_points.ndim != 2 or source_points.shape[1] != 3:
            raise FieldCalculationError(
                "Source points must have shape (N_sources, 3)",
                context={"shape": source_points.shape},
            )

        n_sources = currents.shape[0]

        # --- Determine element areas -----------------------------------------
        if triangles_area is not None:
            triangles_area = np.asarray(triangles_area, dtype=np.float64)
            if triangles_area.ndim != 1 or len(triangles_area) != n_sources:
                raise FieldCalculationError(
                    "Triangles area must have shape (N_sources,)",
                    context={"shape": triangles_area.shape},
                )
        else:
            bbox = source_points.max(axis=0) - source_points.min(axis=0)
            region_volume = np.prod(bbox) if np.all(bbox > 0) else 1.0
            triangles_area = np.full(n_sources, region_volume / max(n_sources, 1))

        # --- Evaluate at phi = phi_deg for all theta -------------------------
        n_theta_cut = 181  # 1-degree resolution for the cut
        theta_cut_rad = np.radians(np.arange(0, 181))  # (N_theta,) in radians
        phi_cut_rad = np.array([np.radians(phi_deg)])  # (1,)

        E_theta_cut, E_phi_cut = self._compute_field_components(
            currents, source_points, triangles_area, theta_cut_rad, phi_cut_rad
        )

        # --- Extract the single-column results -------------------------------
        E_theta_vals = E_theta_cut[:, 0]  # (N_theta,)
        E_phi_vals = E_phi_cut[:, 0]      # (N_theta,)

        # --- Convert to dB relative to max -----------------------------------
        max_E_theta = np.max(np.abs(E_theta_vals)) if np.any(E_theta_vals) else 1.0
        max_E_phi = np.max(np.abs(E_phi_vals)) if np.any(E_phi_vals) else 1.0

        # Avoid log(0)
        E_theta_mag_db = 20 * np.log10(np.where(np.abs(E_theta_vals) > 1e-30,
                                                   np.abs(E_theta_vals) / max_E_theta,
                                                   1e-30))
        E_phi_mag_db = 20 * np.log10(np.where(np.abs(E_phi_vals) > 1e-30,
                                                np.abs(E_phi_vals) / max_E_phi,
                                                1e-30))

        return {
            "theta_values": np.arange(0, 181),  # degrees
            "E_theta_magnitude": E_theta_mag_db,
            "E_phi_magnitude": E_phi_mag_db,
        }


# ===================================================================
# Module-level example usage
# ===================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Far Field Transformer -- Example Usage")
    print("=" * 60)

    transformer = FarFieldTransformer(
        frequency=1e9,
        theta_resolution=5,   # Coarser for demo: 37 points in theta
        phi_resolution=15,    # Coarser for demo: 24 points in phi
    )
    print(f"Frequency: {transformer.frequency:.2e} Hz")
    print(f"Wavenumber k: {transformer.wavenumber:.4f} rad/m")
    print(f"Theta grid: {transformer.n_theta} points ({transformer.theta_values[0]} to {transformer.theta_values[-1]} deg)")
    print(f"Phi grid: {transformer.n_phi} points ({transformer.phi_values[0]} to {transformer.phi_values[-1]} deg)")

    # Create a simple current distribution on a planar patch antenna
    N = 81
    currents = np.zeros((N, 3), dtype=np.complex128)
    source_points = np.zeros((N, 3), dtype=np.float64)

    nx, ny = 9, 9
    ix = 0
    for iy in range(ny):
        for ix_ in range(nx):
            x = (ix_ - (nx - 1) / 2) * 0.05
            y = (iy - (ny - 1) / 2) * 0.05
            source_points[ix, :] = [x, y, 0.0]
            # Simple x-polarized current with quadratic phase taper
            currents[ix, 0] = np.cos(np.pi * ix_ / (nx - 1)) * np.exp(1j * 0.3 * ix_)
            ix += 1

    print(f"\nCurrents shape: {currents.shape}")
    print(f"Source points shape: {source_points.shape}")

    # Compute full far-field pattern
    results = transformer.compute_far_field(currents, source_points)
    print(f"\nFar-field results:")
    print(f"  E_theta shape: {results['E_theta'].shape}")
    print(f"  E_phi shape:   {results['E_phi'].shape}")
    print(f"  Magnitude range: [{results['magnitude'].min():.4e}, {results['magnitude'].max():.4e}]")

    # Find peak direction
    peak_idx = np.unravel_index(np.argmax(results['magnitude']), results['magnitude'].shape)
    print(f"  Peak at theta={results['theta'][peak_idx[0]]} deg, phi={results['phi'][peak_idx[1]]} deg")
    print(f"  Peak magnitude: {results['magnitude'][peak_idx]:.4e}")

    # Compute a specific cut (E-plane at phi=0)
    pattern = transformer.compute_radiation_pattern(
        currents, source_points, None, theta_deg=90, phi_deg=0
    )
    print(f"\nE-plane radiation pattern (phi=0 deg):")
    print(f"  Theta range: {pattern['theta_values'][0]} to {pattern['theta_values'][-1]} deg")
    print(f"  E_theta max: {np.max(pattern['E_theta_magnitude']):.2f} dB")
    print(f"  E_phi max:   {np.max(pattern['E_phi_magnitude']):.2f} dB")

    # Print a few values
    for i in [0, 45, 90, 135, 180]:
        idx = i // 1
        if idx < len(pattern['theta_values']):
            print(f"  theta={pattern['theta_values'][idx]} deg: "
                  f"E_theta={pattern['E_theta_magnitude'][idx]:.2f} dB, "
                  f"E_phi={pattern['E_phi_magnitude'][idx]:.2f} dB")

    print("\nDone.")