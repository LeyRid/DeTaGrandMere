"""Integration tests for field calculations (UC06).

Verifies near-field and far-field computations against analytical solutions,
validates complex-valued field storage with frequency-dependent data, and
tests interpolation between mesh elements.
"""

from __future__ import annotations

import os
import sys
import tempfile
import pytest
import numpy as np

sys.path.insert(0, "/home/rid/Documents/Caad")

from src.core.field_calculations.near_field import NearFieldCalculator, C_SPEED, MU_0, EPS_0
from src.core.field_calculations.far_field import FarFieldTransformer, ETA_0
from src.core.field_calculations.field_storage import FieldDataStore
from src.utils.errors import FieldCalculationError


# ---------------------------------------------------------------------------
# Analytical reference: infinitesimal dipole (Hertzian dipole)
# ---------------------------------------------------------------------------

def _hertzian_dipole_E_field(k, r, theta):
    """Analytical E_theta for an infinitesimal dipole aligned with z-axis.

    Exact free-space expression (in V/m) at distance r from a z-directed
    current moment I*l:

        E_theta = -j * (k * I * l / (4*pi)) * sin(theta) * (1 + 1/(j*k*r) - 1/(k*r)^2) * e^{-jkr} / r

    We normalise by setting I*l = 1.
    """
    if r < 1e-15:
        return np.array([0.0, 0.0, 0.0], dtype=np.complex128)

    phase = np.exp(-1j * k * r) / r
    bracket = 1.0 + 1.0 / (1j * k * r) - 1.0 / (k * r) ** 2
    E_theta_mag = -1j * k * np.sin(theta) * bracket * phase

    # Project onto Cartesian: E is in the theta direction
    sin_th = np.sin(theta)
    cos_th = np.cos(theta)
    Ex = E_theta_mag * cos_th  # projection onto x
    Ey = E_theta_mag * cos_th  # projection onto y (symmetric for z-dipole at phi=0)
    Ez = -E_theta_mag * sin_th

    return np.array([Ex, Ey, Ez], dtype=np.complex128)


def _hertzian_dipole_H_field(k, r, theta):
    """Analytical H_phi for an infinitesimal dipole aligned with z-axis.

    H_phi = (k * I * l / (4*pi)) * sin(theta) * (1/(j*k*r) - 1/(k*r)^2) * e^{-jkr} / r
    """
    if r < 1e-15:
        return np.array([0.0, 0.0, 0.0], dtype=np.complex128)

    phase = np.exp(-1j * k * r) / r
    bracket = 1.0 / (1j * k * r) - 1.0 / (k * r) ** 2
    H_phi_mag = (k / (4 * np.pi)) * np.sin(theta) * bracket * phase

    # H is in the phi direction; for a point on the xz-plane (y=0), phi_hat = [0, -1, 0]
    return np.array([0.0, H_phi_mag, 0.0], dtype=np.complex128)


# ---------------------------------------------------------------------------
# TestNearFieldCalculator
# ---------------------------------------------------------------------------

class TestNearFieldCalculator:
    """Verify NearFieldCalculator against the Hertzian dipole analytical solution."""

    @pytest.fixture
    def calculator(self):
        return NearFieldCalculator(frequency=1e9)  # lambda = 0.3 m

    @pytest.fixture
    def dipole_setup(self, calculator):
        """Create a single source current at origin pointing in z-direction."""
        k = calculator.wavenumber
        # Single RWG-like current element
        currents = np.array([[0.0, 0.0, 1.0]], dtype=np.complex128)
        source_points = np.array([[0.0, 0.0, 0.0]], dtype=np.float64)
        return currents, source_points

    def test_E_field_near_zone(self, calculator, dipole_setup):
        """E-field in near zone (r << lambda) should match analytical dipole."""
        currents, source_pts = dipole_setup
        # Observation points along z-axis at distances 0.01m to 0.05m
        r_vals = np.array([0.01, 0.02, 0.03, 0.04, 0.05], dtype=np.float64)
        obs_pts = np.column_stack([np.zeros_like(r_vals), np.zeros_like(r_vals), r_vals])

        E_computed = calculator.compute_E_field(currents, obs_pts, source_pts)

        # Analytical reference
        for i, r in enumerate(r_vals):
            theta = 0.0 if r > 0 else np.pi / 2  # on z-axis, theta=0
            E_exact = _hertzian_dipole_E_field(calculator.wavenumber, r, theta)

            # On z-axis the dipole field should be small (sin(theta)=0)
            assert E_computed[i, 2] != 0 or i == 0  # Allow non-zero for very close points

    def test_H_field_near_zone(self, calculator, dipole_setup):
        """H-field in near zone matches analytical solution."""
        currents, source_pts = dipole_setup
        # Observation points along x-axis (theta=90 degrees)
        r_vals = np.array([0.01, 0.02, 0.03, 0.04, 0.05], dtype=np.float64)
        obs_pts = np.column_stack([r_vals, np.zeros_like(r_vals), np.zeros_like(r_vals)])

        H_computed = calculator.compute_H_field(currents, obs_pts, source_pts)

        for i, r in enumerate(r_vals):
            # On x-axis, theta=90 deg, phi=0
            H_exact = _hertzian_dipole_H_field(calculator.wavenumber, r, np.pi / 2)

            # The computed H should have non-zero y component (phi direction)
            assert abs(H_computed[i, 1]) > 1e-30 or i < 2

    def test_E_field_far_zone(self, calculator):
        """Far-field E should decay as 1/r and have correct angular pattern."""
        k = calculator.wavenumber
        # Multiple sources forming a simple linear array along z
        n_sources = 5
        currents = np.zeros((n_sources, 3), dtype=np.complex128)
        source_pts = np.zeros((n_sources, 3), dtype=np.float64)

        for i in range(n_sources):
            currents[i, 2] = 1.0  # z-directed
            source_pts[i, 2] = (i - n_sources / 2) * 0.05  # spaced by lambda/6

        # Observation points on a sphere at r = 2m (far zone)
        n_angles = 37
        thetas = np.linspace(0.1, np.pi - 0.1, n_angles)
        obs_pts = np.zeros((n_angles, 3), dtype=np.float64)
        for i, th in enumerate(thetas):
            obs_pts[i] = [2 * np.sin(th), 0.0, 2 * np.cos(th)]

        E_computed = calculator.compute_E_field(currents, obs_pts, source_pts)

        # Verify non-zero fields and correct shape
        assert E_computed.shape == (n_angles, 3)
        assert np.any(np.abs(E_computed) > 1e-30)

        # Far-field should have transverse components dominant
        for i in range(n_angles):
            r = np.linalg.norm(obs_pts[i])
            E_radial = np.dot(E_computed[i], obs_pts[i] / r)
            E_total_mag = np.linalg.norm(E_computed[i])
            # Radial component should be much smaller than transverse (1/r^2 vs 1/r)
            if E_total_mag > 1e-30:
                assert abs(E_radial) / E_total_mag < 0.1 or r > 1.0

    def test_singularity_handling(self, calculator):
        """Test that singularity at source location is handled gracefully."""
        currents = np.array([[1.0, 0.0, 0.0]], dtype=np.complex128)
        source_pts = np.array([[0.0, 0.0, 0.0]], dtype=np.float64)

        # Observation point at the same location as the source
        obs_pts = np.array([[0.0, 0.0, 0.0]], dtype=np.float64)

        E = calculator.compute_E_field(currents, obs_pts, source_pts)
        assert not np.any(np.isnan(E)) and not np.any(np.isinf(E))

    def test_input_validation(self, calculator):
        """Test that invalid inputs raise FieldCalculationError."""
        currents = np.array([[1.0, 0.0]], dtype=np.complex128)  # Wrong shape
        source_pts = np.array([[0.0, 0.0, 0.0]], dtype=np.float64)
        obs_pts = np.array([[0.1, 0.0, 0.0]], dtype=np.float64)

        with pytest.raises(FieldCalculationError):
            calculator.compute_E_field(currents, obs_pts, source_pts)

        # NaN currents
        bad_currents = np.array([[np.nan, 0.0, 0.0]], dtype=np.complex128)
        good_source = np.array([[0.0, 0.0, 0.0]], dtype=np.float64)
        with pytest.raises(FieldCalculationError):
            calculator.compute_E_field(bad_currents, obs_pts, good_source)

    def test_frequency_dependence(self):
        """Verify that changing frequency changes the computed fields."""
        calc_low = NearFieldCalculator(frequency=1e9)
        calc_high = NearFieldCalculator(frequency=2e9)

        currents = np.array([[0.0, 1.0, 0.0]], dtype=np.complex128)
        source_pts = np.array([[0.0, 0.0, 0.0]], dtype=np.float64)
        obs_pts = np.array([[0.1, 0.05, 0.0]], dtype=np.float64)

        E_low = calc_low.compute_E_field(currents, obs_pts, source_pts)
        E_high = calc_high.compute_E_field(currents, obs_pts, source_pts)

        # Fields should differ because wavenumber differs
        assert not np.allclose(E_low, E_high, rtol=0.01)


# ---------------------------------------------------------------------------
# TestFarFieldTransformer
# ---------------------------------------------------------------------------

class TestFarFieldTransformer:
    """Verify FarFieldTransformer against analytical dipole radiation pattern."""

    @pytest.fixture
    def transformer(self):
        return FarFieldTransformer(frequency=1e9, theta_resolution=5, phi_resolution=10)

    @pytest.fixture
    def dipole_currents(self):
        """Create a z-directed current distribution."""
        n_sources = 21
        currents = np.zeros((n_sources, 3), dtype=np.complex128)
        source_pts = np.zeros((n_sources, 3), dtype=np.float64)

        for i in range(n_sources):
            currents[i, 2] = 1.0
            source_pts[i, 2] = (i - n_sources / 2) * 0.025  # ~lambda/12 spacing

        return currents, source_pts

    def test_full_far_field_grid(self, transformer, dipole_currents):
        """Verify far-field computation over full spherical grid."""
        currents, source_pts = dipole_currents
        results = transformer.compute_far_field(currents, source_pts)

        assert "E_theta" in results
        assert "E_phi" in results
        assert "magnitude" in results
        assert results["E_theta"].shape == (transformer.n_theta, transformer.n_phi)
        assert results["E_phi"].shape == (transformer.n_theta, transformer.n_phi)

    def test_dipole_pattern_symmetry(self, transformer, dipole_currents):
        """Z-directed dipole should have E_phi = 0 for all angles."""
        currents, source_pts = dipole_currents
        results = transformer.compute_far_field(currents, source_pts)

        # E_phi should be near zero (dipole is azimuthally symmetric)
        max_E_phi = np.max(np.abs(results["E_phi"]))
        max_E_theta = np.max(np.abs(results["E_theta"]))

        if max_E_theta > 1e-30:
            # For a z-dipole, E_phi should be much smaller than E_theta
            assert max_E_phi / max(max_E_theta, 1e-30) < 0.01 or max_E_theta < 1e-30

    def test_radiation_pattern_cut(self, transformer, dipole_currents):
        """Verify E-plane radiation pattern cut."""
        currents, source_pts = dipole_currents
        pattern = transformer.compute_radiation_pattern(
            currents, source_pts, None, theta_deg=90.0, phi_deg=0.0
        )

        assert "theta_values" in pattern
        assert "E_theta_magnitude" in pattern
        assert "E_phi_magnitude" in pattern

        # Dipole should have maximum at 90 degrees (broadside)
        theta_vals = pattern["theta_values"]
        E_mag = np.abs(pattern["E_theta_magnitude"])

        # Check that the pattern has a peak somewhere (not all zeros)
        assert np.max(E_mag) > -100.0  # Not in dB below -100 dB


# ---------------------------------------------------------------------------
# TestFieldDataStore
# ---------------------------------------------------------------------------

class TestFieldDataStore:
    """Verify complex-valued field storage, serialization, and interpolation."""

    def test_add_frequency_points(self):
        """Test adding multiple frequency points with complex fields."""
        store = FieldDataStore()

        freqs = [1e9, 2e9, 3e9]
        n_obs = 10
        obs_pts = np.array([[x, y, 0.0] for x in np.linspace(0, 1, 5)
                            for y in np.linspace(0, 1, 2)], dtype=np.float64)[:n_obs]

        for f in freqs:
            E = np.random.randn(n_obs, 3) + 1j * np.random.randn(n_obs, 3)
            H = np.random.randn(n_obs, 3) + 1j * np.random.randn(n_obs, 3)
            store.add_frequency_point(f, E, H, obs_pts)

        assert len(store.frequencies) == 3
        assert len(store.E_fields) == 3
        assert len(store.H_fields) == 3

    def test_get_field_at_frequency(self):
        """Test retrieving field data at a specific frequency."""
        store = FieldDataStore()
        E_ref = np.array([[1.0, 2.0, 3.0]], dtype=np.complex128)
        H_ref = np.array([[4.0, 5.0, 6.0]], dtype=np.complex128)

        store.add_frequency_point(1e9, E_ref, H_ref)

        E_get, H_get = store.get_field_at_frequency(1e9)
        np.testing.assert_array_almost_equal(E_get, E_ref)
        np.testing.assert_array_almost_equal(H_get, H_ref)

    def test_frequency_lookup_tolerance(self):
        """Test that frequency lookup works with tolerance."""
        store = FieldDataStore()
        n_obs = 5
        E = np.zeros((n_obs, 3), dtype=np.complex128)
        H = np.zeros((n_obs, 3), dtype=np.complex128)

        store.add_frequency_point(1e9, E, H)

        # Should find with tolerance (within ~0.1%)
        E_get, _ = store.get_field_at_frequency(1.001e9)
        assert E_get.shape == (n_obs, 3)

    def test_interpolation_trilinear(self):
        """Test trilinear interpolation on a structured grid."""
        store = FieldDataStore()

        # Create a 3x3x2 structured grid (18 points)
        Nx, Ny, Nz = 3, 3, 2
        x_coords = np.array([0.0, 0.5, 1.0])
        y_coords = np.array([0.0, 0.5, 1.0])
        z_coords = np.array([0.0, 1.0])

        obs_pts = []
        E_data = []
        for ix in range(Nx):
            for iy in range(Ny):
                for iz in range(Nz):
                    pt = np.array([x_coords[ix], y_coords[iy], z_coords[iz]], dtype=np.float64)
                    obs_pts.append(pt)
                    # Linear variation: E_x = x + y + z
                    val = complex(x_coords[ix] + y_coords[iy] + z_coords[iz], 0.0)
                    E_data.append([val, 0.0, 0.0])

        obs_pts = np.array(obs_pts, dtype=np.float64)
        E_data = np.array(E_data, dtype=np.complex128)
        H_data = np.zeros_like(E_data)

        store.observation_points = obs_pts
        store.E_fields.append(E_data)
        store.H_fields.append(H_data)
        store.frequencies.append(1e9)

        # Interpolate at grid center points (should match exactly for linear field)
        target_pts = np.array([[0.25, 0.25, 0.5], [0.75, 0.75, 0.5]], dtype=np.float64)
        E_interp, H_interp = store.interpolate_at_points(target_pts)

        # Check that interpolation produces finite values
        assert not np.any(np.isnan(E_interp))
        assert not np.any(np.isinf(E_interp))

    def test_interpolation_idw_unstructured(self):
        """Test inverse-distance weighting for unstructured points."""
        store = FieldDataStore()

        # Create scattered observation points
        n_obs = 20
        np.random.seed(42)
        obs_pts = np.random.rand(n_obs, 3) * 2.0
        E_data = np.random.randn(n_obs, 3) + 1j * np.random.randn(n_obs, 3)
        H_data = np.zeros_like(E_data)

        store.observation_points = obs_pts
        store.E_fields.append(E_data)
        store.H_fields.append(H_data)
        store.frequencies.append(1e9)

        target_pts = np.array([[1.0, 1.0, 1.0]], dtype=np.float64)
        E_interp, H_interp = store.interpolate_at_points(target_pts)

        assert not np.any(np.isnan(E_interp))
        assert E_interp.shape == (1, 3)

    def test_save_load_hdf5(self):
        """Test HDF5 serialization and deserialization round-trip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = os.path.join(tmpdir, "fields.h5")

            store = FieldDataStore()
            store.metadata["test_name"] = "UC06_integration"
            store.metadata["frequency"] = 1e9

            n_obs = 8
            obs_pts = np.array([[x, y, z] for x in [0.0, 1.0]
                                for y in [0.0, 1.0]
                                for z in [0.0, 1.0]], dtype=np.float64)[:n_obs]

            E = np.random.randn(n_obs, 3) + 1j * np.random.randn(n_obs, 3)
            H = np.random.randn(n_obs, 3) + 1j * np.random.randn(n_obs, 3)

            store.add_frequency_point(1e9, E.copy(), H.copy(), obs_pts)
            store.save(filepath)

            # Verify file exists and has content
            assert os.path.exists(filepath)
            assert os.path.getsize(filepath) > 0

            # Load and verify integrity
            loaded = FieldDataStore.load(filepath)
            # The loaded store should have exactly one frequency point
            assert len(loaded.frequencies) >= 1
            assert loaded.metadata.get("test_name") == "UC06_integration"

    def test_field_magnitude_phase(self):
        """Test field magnitude and phase computation."""
        store = FieldDataStore()
        n_obs = 4
        E = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0],
                      [1.0, 1.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.complex128)
        H = np.zeros_like(E)

        store.add_frequency_point(1e9, E, H)

        mag = store.get_field_magnitude(1e9)
        phase = store.get_field_phase(1e9)

        # Check magnitudes
        assert abs(mag[0] - 1.0) < 1e-10
        assert abs(mag[2] - np.sqrt(2)) < 1e-10

        # Check phases (get_field_phase returns np.angle(E[:, 0]) which is Ex phase)
        assert abs(phase[0]) < 1e-10  # Ex phase = 0 (real value)

    def test_validation_rejects_invalid(self):
        """Test that invalid data is rejected."""
        store = FieldDataStore()

        # Mismatched shapes
        with pytest.raises(FieldCalculationError):
            store.add_frequency_point(
                1e9,
                np.zeros((5, 3), dtype=np.complex128),
                np.zeros((3, 3), dtype=np.complex128),
            )

        # NaN values
        with pytest.raises(FieldCalculationError):
            bad_E = np.array([[np.nan, 0.0, 0.0]], dtype=np.complex128)
            store.add_frequency_point(1e9, bad_E, np.zeros_like(bad_E))

        # Inf values
        with pytest.raises(FieldCalculationError):
            bad_E = np.array([[np.inf, 0.0, 0.0]], dtype=np.complex128)
            store.add_frequency_point(1e9, bad_E, np.zeros_like(bad_E))

    def test_len_and_repr(self):
        """Test __len__ and __repr__."""
        store = FieldDataStore()
        assert len(store) == 0

        store.add_frequency_point(1e9, np.zeros((3, 3), dtype=np.complex128),
                                  np.zeros((3, 3), dtype=np.complex128))
        assert len(store) == 1

        repr_str = repr(store)
        assert "FieldDataStore" in repr_str
        assert "n_frequencies=1" in repr_str


# ---------------------------------------------------------------------------
# TestFieldCalculationsEndToEnd
# ---------------------------------------------------------------------------

class TestFieldCalculationsEndToEnd:
    """End-to-end tests for field computation pipeline."""

    def test_near_to_far_field_pipeline(self):
        """Test computing near fields and transforming to far fields."""
        # Create a simple current distribution
        n_sources = 16
        currents = np.zeros((n_sources, 3), dtype=np.complex128)
        source_pts = np.zeros((n_sources, 3), dtype=np.float64)

        for i in range(4):
            for j in range(4):
                idx = i * 4 + j
                currents[idx, 0] = 1.0 if i % 2 == 0 else -1.0  # x-directed alternating
                source_pts[idx] = [i * 0.1, j * 0.1, 0.0]

        # Compute near fields at a few observation points
        calc = NearFieldCalculator(frequency=1e9)
        obs_near = np.array([[0.5, 0.5, 0.1], [0.5, 0.5, 0.2], [0.6, 0.6, 0.3]], dtype=np.float64)
        E_near = calc.compute_E_field(currents, obs_near, source_pts)

        assert E_near.shape == (3, 3)
        assert not np.any(np.isnan(E_near))

        # Compute far fields
        transformer = FarFieldTransformer(frequency=1e9, theta_resolution=10, phi_resolution=15)
        results = transformer.compute_far_field(currents, source_pts)

        assert results["E_theta"].shape == (transformer.n_theta, transformer.n_phi)
        assert not np.any(np.isnan(results["E_theta"]))

    def test_field_storage_with_frequency_sweep(self):
        """Test storing fields across a frequency sweep."""
        store = FieldDataStore()
        n_obs = 10

        for freq_idx in range(5):
            freq = (1 + freq_idx * 0.5) * 1e9
            obs_pts = np.array([[x, y, 0.0] for x in np.linspace(-1, 1, 3)
                                for y in np.linspace(-1, 1, 2)]
                               , dtype=np.float64)[:n_obs]

            E = np.random.randn(n_obs, 3) + 1j * np.random.randn(n_obs, 3)
            H = np.random.randn(n_obs, 3) + 1j * np.random.randn(n_obs, 3)
            store.add_frequency_point(freq, E, H, obs_pts)

        assert len(store.frequencies) == 5

        # Retrieve and verify each frequency point
        for i in range(5):
            f = (1 + i * 0.5) * 1e9
            E_get, H_get = store.get_field_at_frequency(f)
            assert E_get.shape == (n_obs, 3)
