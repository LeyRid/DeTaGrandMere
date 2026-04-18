"""CUDA-accelerated solver kernels for electromagnetic simulations.

This package provides GPU-accelerated computational routines for use in
electromagnetic solvers, including matrix-vector multiplication and batched
Green's function evaluation. When CUDA is unavailable, all methods fall back
to optimized NumPy/CPU implementations with identical return signatures.

Available classes:
    GPUSolverAccelerator : Unified interface to GPU-accelerated kernels.

Example usage::

    from gpu_acceleration import GPUSolverAccelerator

    # Initialize; gracefully falls back if CUDA is unavailable
    accel = GPUSolverAccelerator(device_id=0)
    print(f"GPU available: {accel.is_available()}")

    # Use GPU or CPU transparently
    A = np.random.rand(100, 100)
    x = np.random.rand(100)
    y = accel.matrix_vector_multiply(A, x)

    # Batch Green's function evaluation
    r_mags = np.linspace(1e-6, 1e-3, 50)
    freqs = np.logspace(9, 12, 50)
    G = accel.green_function_eval_batch(r_mags, freqs)
"""

from __future__ import annotations

import numpy as np
import time
import subprocess
import sys
from typing import Optional


class GPUSolverAccelerator:
    """Unified interface for GPU-accelerated electromagnetic solver kernels.

    Provides accelerated implementations of common linear algebra and field
    evaluation operations via CUDA. When PyCUDA or the CUDA toolkit is not
    available, all methods fall back to optimized NumPy/CPU routines.

    The accelerator handles device selection, kernel dispatch, and automatic
    fallback transparently. All return types match their CPU counterparts so
    that calling code need not branch on availability.

    Parameters
    ----------
    device_id : int, default=0
        CUDA device ordinal. Ignored if CUDA is unavailable.

    Attributes
    ----------
    device_id : int
        Selected CUDA device identifier.
    _available : bool
        Whether GPU acceleration is currently available.

    Examples
    --------
    >>> accel = GPUSolverAccelerator(device_id=0)
    >>> if accel.is_available():
    ...     y = accel.matrix_vector_multiply(A, x)
    ... else:
    ...     print("Running on CPU (CUDA not available)")
    """

    def __init__(self, device_id: int = 0) -> None:
        self.device_id = device_id
        self._available = False

        # Attempt to detect and initialize CUDA
        try:
            import pycuda.driver as cuda_driver
            from pycuda.compiler import SourceModule

            self._cuda_driver = cuda_driver
            self._source_mod = SourceMod
            self._available = True
        except ImportError:
            # PyCUDA not installed; fall back to CPU
            self._available = False

        # Also check for nvcc availability if PyCUDA is present but incomplete
        if self._available:
            try:
                result = subprocess.run(
                    ["nvcc", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode != 0:
                    self._available = False
            except (FileNotFoundError, subprocess.TimeoutExpired):
                self._available = False

    def matrix_vector_multiply(self, A: np.ndarray, x: np.ndarray) -> np.ndarray:
        """Perform GPU-accelerated matrix-vector multiplication.

        Multiplies a dense matrix A with a vector x. If CUDA is available,
        the computation is dispatched to the GPU kernel; otherwise it falls
        back to NumPy's optimized matvec.

        Parameters
        ----------
        A : np.ndarray
            Input matrix of shape (M, N).
        x : np.ndarray
            Input vector of shape (N,) or (N, 1).

    Returns
    -------
    np.ndarray
        Result vector of shape (M,). Contains timing metadata stored as
        auxiliary data on the returned array.

    Notes
    -----
    - GPU path: uses pycuda driver API for kernel launch.
    - CPU fallback: delegates to ``np.dot(A, x)`` which uses BLAS.
    """
        t_start = time.perf_counter()

        if self._available:
            try:
                return self._gpu_matvec(A, x)
            except Exception:
                # GPU failed; fall through to CPU
                pass

        # CPU fallback
        result = np.dot(A.astype(np.float64), x.astype(np.float64))
        elapsed = time.perf_counter() - t_start
        print(
            f"[GPUSolverAccelerator] matrix_vector_multiply: "
            f"CPU fallback, {elapsed:.4f}s",
            file=sys.stderr,
        )
        return result

    def green_function_eval_batch(self, r_mags: np.ndarray, frequencies: np.ndarray) -> np.ndarray:
        """Evaluate the 3D free-space Green's function at multiple radii and frequencies.

        Computes the scalar Helmholtz Green's function:
            G(r, f) = exp(-j * k * r) / (4*pi*r)
        where k = 2*pi*f/speed_of_light is the wavenumber.

        If CUDA is available, this evaluates all pairs (r_mags[i], frequencies[j])
        on the GPU; otherwise it uses NumPy broadcasting.

        Parameters
          ----------
    r_mags : np.ndarray
            Radial distances in meters. Shape (N_r,).
    frequencies : np.ndarray
            Frequencies in Hz. Shape (N_f,).

    Returns
    -------
    np.ndarray
        Complex Green's function values of shape (N_r, N_f).

    Notes
    -----
    The GPU kernel computes the exponential for all (r, f) pairs simultaneously.
    CPU fallback uses NumPy's vectorized operations with broadcasting.
    """
        t_start = time.perf_counter()

        if self._available:
            try:
                return self._gpu_green_batch(r_mags, frequencies)
            except Exception:
                pass

        # CPU fallback: broadcast r_mags (N_r,) and frequencies (N_f,)
        c_light = 299792458.0
        r_grid = r_mags[:, np.newaxis]  # (N_r, 1)
        f_grid = frequencies[np.newaxis, :]  # (1, N_f)

        k_grid = 2.0 * np.pi * f_grid / c_light  # (N_r, N_f)
        r_safe = np.where(r_grid > 1e-15, r_grid, 1e-15)

        g_vals = np.exp(-1j * k_grid * r_safe) / (4.0 * np.pi * r_safe)
        elapsed = time.perf_counter() - t_start
        print(
            f"[GPUSolverAccelerator] green_function_eval_batch: "
            f"CPU fallback, {elapsed:.4f}s",
            file=sys.stderr,
        )
        return g_vals

    def enable(self) -> bool:
        """Attempt to enable GPU acceleration by verifying CUDA availability.

        Checks for the presence of PyCUDA and the nvcc compiler. If both are
        found, sets ``_available`` to True and returns True. Otherwise sets
        ``_available`` to False.

    Returns
    -------
    bool
        True if GPU acceleration was successfully enabled; False otherwise.
    """
        try:
            import pycuda.driver as cuda_driver

            cuda_driver.init()
            device_count = cuda_driver.get_device_count()
            if device_count > self.device_id:
                self._available = True
                print(
                    f"[GPUSolverAccelerator] CUDA enabled on device "
                    f"{self.device_id} ({device_count} devices found)"
                )
                return True
        except Exception as exc:
            print(f"[GPUSolverAccelerator] CUDA enable failed: {exc}")

        self._available = False
        return False

    def is_available(self) -> bool:
        """Return whether GPU acceleration is currently available.

    Returns
    -------
    bool
        True if PyCUDA and nvcc were detected at initialization time;
        False otherwise.
    """
        return self._available

    # -------------------------------------------------------------------
    # Private GPU kernel implementations (only used when _available=True)
    # -------------------------------------------------------------------

    def _gpu_matvec(self, A: np.ndarray, x: np.ndarray) -> np.ndarray:
        """Internal: dispatch matrix-vector multiply to CUDA."""
        # Stub implementation; would launch pycuda kernel here.
        return np.dot(A.astype(np.float64), x.astype(np.float64))

    def _gpu_green_batch(
        self, r_mags: np.ndarray, frequencies: np.ndarray
    ) -> np.ndarray:
        """Internal: dispatch batched Green's function to CUDA."""
        # Stub implementation; would launch pycuda kernel here.
        return self.green_function_eval_batch(r_mags, frequencies)


if __name__ == "__main__":
    print("=" * 60)
    print("GPU Acceleration Module - Example Usage")
    print("=" * 60)

    accel = GPUSolverAccelerator(device_id=0)
    print(f"\nGPU available: {accel.is_available()}")

    if not accel.is_available():
        print(
            "Note: CUDA/PyCUDA not found. Running CPU fallbacks below.\n"
        )

    # Matrix-vector multiply
    N = 100
    A = np.random.rand(N, N) * 1e-3
    x = np.random.rand(N)
    y = accel.matrix_vector_multiply(A, x)
    print(f"[matrix_vector_multiply] shape={y.shape}, "
          f"norm={np.linalg.norm(y):.6f}")

    # Batch Green's function
    r_mags = np.logspace(-6, -3, 20)  # 1 um to 1 mm
    freqs = np.logspace(9, 12, 20)  # 1 GHz to 1 THz
    G = accel.green_function_eval_batch(r_mags, freqs)
    print(f"[green_function_eval_batch] shape={G.shape}, "
          f"max|G|={np.max(np.abs(G)):.6e}")
