"""GPU-accelerated solver kernels package.

Exports:
    GPUSolverAccelerator : Unified interface to CUDA-accelerated EM kernels.
"""

from __future__ import annotations

from .cuda_kernels import GPUSolverAccelerator

__all__ = ["GPUSolverAccelerator"]
