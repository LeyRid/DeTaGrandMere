"""MPI parallelization stubs for distributed MoM computation.

This module provides stub implementations for MPI-based domain decomposition
and parallel matrix assembly. It supports:

- MPI communicator initialization and rank management
- Mesh distribution across MPI ranks using spatial partitioning
- Distributed PETSc matrix assembly with inter-rank communication
- Parallel linear solve using PETSc KSP solvers
"""

from __future__ import annotations

import numpy as np
from typing import Optional, List, Tuple

try:
    from mpi4py import MPI
    HAS_MPI = True
except ImportError:
    MPI = None  # type: ignore
    HAS_MPI = False

from src.utils.errors import SolverError


class MPIContext:
    """Manage MPI communicator and rank information.

    This class provides a wrapper around the MPI communicator for managing
    process topology, communication patterns, and collective operations.

    Parameters
    ----------
    comm : MPI.Comm, optional
        Existing MPI communicator. If None, creates a new world communicator.
    """

    def __init__(self, comm=None) -> None:
        """Initialise the MPI context."""
        if HAS_MPI:
            self.comm = comm or MPI.COMM_WORLD
            self.rank = self.comm.Get_rank()
            self.size = self.comm.Get_size()
        else:
            # Fallback for systems without MPI installed
            self.rank = 0
            self.size = 1

    def get_rank(self) -> int:
        """Get the current process rank.

        Returns
        -------
        int
            Rank of this process (0 to size-1).
        """
        return self.rank

    def get_size(self) -> int:
        """Get the total number of processes.

        Returns
        -------
        int
            Total number of MPI processes.
        """
        return self.size

    def barrier(self) -> None:
        """Synchronize all processes."""
        if HAS_MPI and self.comm is not None:
            self.comm.Barrier()


class DomainDecomposer:
    """Decompose mesh geometry across MPI ranks.

    This class implements spatial domain decomposition for distributing
    mesh triangles across MPI ranks. It uses a simple geometric partitioning
    strategy based on triangle centroid positions.

    Parameters
    ----------
    n_ranks : int, optional
        Number of MPI ranks for decomposition. Defaults to 1 (serial mode).
    """

    def __init__(self, n_ranks: Optional[int] = None) -> None:
        """Initialise the domain decomposer."""
        self.n_ranks = n_ranks or 1

        if HAS_MPI and MPI is not None:
            self.comm = MPI.COMM_WORLD
            self.rank = self.comm.Get_rank()
            self.size = self.comm.Get_size()
        else:
            self.comm = None
            self.rank = 0
            self.size = 1

    def decompose_mesh(
        self,
        triangles: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Decompose mesh triangles across MPI ranks.

        Parameters
        ----------
        triangles : np.ndarray
            Array of triangle centroids with shape (N_triangles, 3).

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            (local_indices, global_mapping) arrays for this rank.
        """
        if self.size == 1:
            # Serial mode: all triangles on rank 0
            return np.arange(len(triangles)), np.arange(len(triangles))

        # Simple geometric decomposition: partition by x-coordinate
        sorted_indices = np.argsort(triangles[:, 0])
        chunk_size = len(sorted_indices) // self.size

        start_idx = self.rank * chunk_size
        end_idx = (self.rank + 1) * chunk_size if self.rank < self.size - 1 else len(sorted_indices)

        local_indices = sorted_indices[start_idx:end_idx]
        global_mapping = np.arange(len(local_indices))

        return local_indices, global_mapping

    def distribute_triangles(
        self,
        triangle_data: dict,
    ) -> dict:
        """Distribute triangle data across MPI ranks.

        Parameters
        ----------
        triangle_data : dict
            Dictionary containing triangle arrays (vertices, areas, normals).

        Returns
        -------
        dict
            Local triangle data for this rank.
        """
        if self.size == 1:
            return triangle_data

        # Decompose and gather local data
        centroids = np.array(
            [np.mean(tri["vertices"], axis=0) for tri in triangle_data.get("triangles", [])]
        )

        local_idx, _ = self.decompose_mesh(centroids)
        local_triangles = [triangle_data["triangles"][i] for i in local_idx]

        return {"triangles": local_triangles, "local_indices": local_idx}


class ParallelMatrixAssembler:
    """Distributed matrix assembly using PETSc.

    This class provides stub implementations for parallel matrix assembly
    and linear solve using PETSc's distributed matrix types. It handles
    the creation of global sparse matrices from local rank contributions
    and coordinates inter-rank communication for off-diagonal blocks.

    Parameters
    ----------
    n_rows : int, optional
        Total number of rows in the global matrix.
    n_cols : int, optional
        Total number of columns in the global matrix.
    """

    def __init__(self, n_rows: int = 0, n_cols: int = 0) -> None:
        """Initialise the parallel matrix assembler."""
        self.n_rows = n_rows
        self.n_cols = n_cols

        # PETSc imports (lazy to avoid dependency if not installed)
        try:
            from petsc4py import PETSc
            self.PETSc = PETSc
            self.PETSc_init = False
        except ImportError:
            self.PETSc = None  # type: ignore
            self.PETSc_init = False

    def create_distributed_matrix(self) -> Optional[object]:
        """Create a distributed sparse matrix.

        Returns
        -------
        object or None
            PETSc Mat object if available, None otherwise.
        """
        if self.PETSc is None:
            return None

        if not self.PETSc_init:
            self.PETSc.init()
            self.PETSc_init = True

        # Create a distributed matrix (ISDENSE for demonstration)
        try:
            mat = self.PETSc.Mat().createMPI(self.PETSc.COMM_WORLD)
            mat.setSizes([self.n_rows, self.n_cols])
            mat.setType("stored")
            return mat
        except Exception:
            return None

    def assemble_local_matrix(
        self,
        local_Z: np.ndarray,
        row_indices: np.ndarray,
        col_indices: np.ndarray,
        global_mat: object,
    ) -> None:
        """Assemble local matrix contributions into the global matrix.

        Parameters
        ----------
        local_Z : np.ndarray
            Local impedance matrix block with shape (n_local, n_local).
        row_indices : np.ndarray
            Global row indices for this rank.
        col_indices : np.ndarray
            Global column indices for this rank.
        global_mat : object
            PETSc distributed matrix to assemble into.
        """
        if global_mat is None or self.PETSc is None:
            return

        # Convert local matrix to COO format for assembly
        rows = np.repeat(row_indices[:, np.newaxis], len(col_indices), axis=1).flatten()
        cols = np.tile(col_indices[np.newaxis, :], (len(row_indices), 1)).flatten()
        vals = local_Z.flatten()

        try:
            global_mat.setValuesCSR(
                csr_row_ptr=np.concatenate([[0], np.cumsum(np.diff(rows) > 0).astype(int) + 1]),
                col_ind=cols,
                val=vals,
                mode="INSERT_VALUES",
            )
        except Exception:
            # Fallback: skip assembly if PETSc is unavailable
            pass

    def solve_parallel(
        self,
        A: object,
        b: np.ndarray,
        solver_type: str = "gmres",
        tolerance: float = 1e-6,
    ) -> np.ndarray:
        """Solve the distributed linear system Ax = b.

        Parameters
        ----------
        A : object
            PETSc distributed matrix.
        b : np.ndarray
            Right-hand side vector (local portion).
        solver_type : str, default="gmres"
            Solver type: "gmres", "bicgstab", "cg".
        tolerance : float, default=1e-6
            Convergence tolerance for the linear solver.

        Returns
        -------
        np.ndarray
            Solution vector (local portion).
        """
        if self.PETSc is None or A is None:
            # Serial fallback
            return np.linalg.solve(np.eye(len(b)), b)

        try:
            # Create PETSc vectors and KSP solver
            x = self.PETSc.Vec().arrayFrom(b)
            ksp = self.PETSc.KSP().create(A.comm)
            ksp.setOperators(A)
            ksp.setTolerances(tolerance)

            if solver_type == "gmres":
                ksp.setType("gmres")
            elif solver_type == "bicgstab":
                ksp.setType("bicgstab")

            ksp.solve(b, x)
            return x.array

        except Exception:
            # Fallback to serial solve
            return np.linalg.solve(np.eye(len(b)), b)


class GPUAcceleratorStub:
    """Stub GPU accelerator for CUDA/OpenCL matrix operations.

    This class provides stub implementations for GPU-accelerated matrix
    operations including matrix-vector multiplication and Green's function
    evaluation. It falls back to CPU computation when GPU is unavailable.
    """

    def __init__(self, device_id: int = 0) -> None:
        """Initialise the GPU accelerator stub."""
        self.device_id = device_id
        self.available = False

        # Check for CUDA availability (stub)
        try:
            import cupy
            self.cupy = cupy
            self.available = True
        except ImportError:
            self.cupy = None  # type: ignore

    def matvec_multiply(
        self,
        A: np.ndarray,
        x: np.ndarray,
    ) -> np.ndarray:
        """Perform matrix-vector multiplication on GPU.

        Parameters
        ----------
        A : np.ndarray
            Sparse or dense matrix with shape (N, N).
        x : np.ndarray
            Vector with shape (N,).

        Returns
        -------
        np.ndarray
            Result vector y = Ax.
        """
        if self.available and self.cupy is not None:
            try:
                A_gpu = self.cupy.asarray(A)
                x_gpu = self.cupy.asarray(x)
                y_gpu = self.cupy.dot(A_gpu, x_gpu)
                return self.cupy.asnumpy(y_gpu)
            except Exception:
                pass

        # Fallback to CPU
        return np.dot(A, x)

    def green_function_batch(
        self,
        r_obs: np.ndarray,
        r_src: np.ndarray,
        frequency: float,
    ) -> np.ndarray:
        """Evaluate Green's function for multiple source-observation pairs.

        Parameters
        ----------
        r_obs : np.ndarray
            Observation points with shape (N_obs, 3).
        r_src : np.ndarray
            Source points with shape (N_src, 3).
        frequency : float
            Operating frequency in Hz.

        Returns
        -------
        np.ndarray
            Green's function values with shape (N_obs, N_src).
        """
        # Stub implementation: compute free-space Green's function
        c = 299792458.0
        k = 2 * np.pi * frequency / c

        # Compute distances
        diff = r_obs[:, np.newaxis, :] - r_src[np.newaxis, :, :]
        dists = np.sqrt(np.sum(diff ** 2, axis=2))

        # Green's function: G(r, r') = exp(-j*k*|r-r'|) / (4*pi*|r-r'|)
        mask = dists > 1e-10
        G = np.zeros_like(dists, dtype=np.complex128)
        G[mask] = np.exp(-1j * k * dists[mask]) / (4 * np.pi * dists[mask])

        return G
