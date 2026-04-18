"""Boundary condition module for electromagnetic simulation domains.

This module defines types and managers for applying boundary conditions to
simulation meshes, including perfect electric conductors (PEC), perfect
magnetic conductors (PMC), radiation boundaries, and perfectly matched
layers (PML).

Example usage::

    from boundary_conditions import BoundaryConditionManager, BoundaryConditionType

    manager = BoundaryConditionManager()
    manager.apply_pec(surface_ids=[1, 2])
    manager.apply_pml(surface_ids=[3], layers=4)
    conditions = manager.get_conditions_for_surface(1)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import numpy as np

from .errors import CADError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums & Data classes
# ---------------------------------------------------------------------------


class BoundaryConditionType(Enum):
    """Types of electromagnetic boundary conditions.

    Members
    -------
    PEC
        Perfect electric conductor -- tangential electric field is zero.
    PMC
        Perfect magnetic conductor -- tangential magnetic field is zero.
    RADIATION
        Absorbing radiation boundary for open-region simulations.
    PML
        Perfectly matched layer configuration for absorbing outgoing waves.
    """

    PEC = "PEC"
    PMC = "PMC"
    RADIATION = "RADIATION"
    PML = "PML"


@dataclass
class BoundaryCondition:
    """Describes a single boundary condition attached to mesh surfaces.

    Attributes
    ----------
    type : BoundaryConditionType
        The kind of boundary condition.
    surface_ids : list[int]
            Identifiers of the mesh surfaces this condition applies to.
    parameters : dict
        Condition-specific configuration (e.g. PML layers, radiation params).
    """

    type: BoundaryConditionType
    surface_ids: List[int] = field(default_factory=list)
    parameters: Dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# BoundaryConditionManager
# ---------------------------------------------------------------------------


class BoundaryConditionManager:
    """Manages boundary conditions on mesh surfaces.

    Provides convenience methods for common boundary types and tools for
    querying and validating condition assignments.

    Example usage::

        mgr = BoundaryConditionManager()
        bc_id = mgr.add_condition(BoundaryConditionType.PEC, surface_ids=[0])
        mgr.remove_condition(bc_id)
        mgr.apply_pec([1, 2])
        mgr.apply_pml([3], layers=5)
    """

    def __init__(self) -> None:
        self._conditions: Dict[str, BoundaryCondition] = {}
        self._next_id = 0

    # ------------------------------------------------------------------ CRUD -------------------------------

    def add_condition(
        self,
        bc_type: BoundaryConditionType,
        surface_ids: Optional[List[int]] = None,
        **params,
    ) -> str:
        """Create and register a new boundary condition.

        Parameters
        ----------
        bc_type : BoundaryConditionType
            The type of the boundary condition.
        surface_ids : list[int] or None
            Mesh surface identifiers to attach the condition to.
        **params
            Arbitrary keyword arguments stored as condition-specific parameters.

        Returns
        -------
        str
            Unique identifier for the created condition.
        """
        bc_id = f"bc_{self._next_id:04d}"
        self._next_id += 1
        self._conditions[bc_id] = BoundaryCondition(
            type=bc_type,
            surface_ids=surface_ids if surface_ids is not None else [],
            parameters=dict(params),
        )
        logger.debug("Added condition %s of type %s", bc_id, bc_type.value)
        return bc_id

    def remove_condition(self, bc_id: str) -> None:
        """Remove a boundary condition.

        Parameters
        ----------
        bc_id : str
            Identifier of the condition to remove.

        Raises
        ------
        CADError
            If *bc_id* is not registered.
        """
        if bc_id not in self._conditions:
            raise CADError(f"Boundary condition '{bc_id}' not found.")
        del self._conditions[bc_id]
        logger.debug("Removed condition %s", bc_id)

    def get_condition(self, bc_id: str) -> Optional[BoundaryCondition]:
        """Retrieve a boundary condition by its identifier.

        Parameters
        ----------
        bc_id : str
            Condition identifier.

        Returns
        -------
        BoundaryCondition or None
            The requested condition, or ``None`` if not found.
        """
        return self._conditions.get(bc_id)

    # ------------------------------------------------------------------ convenience methods ---------------------------------

    def apply_pec(self, surface_ids: List[int]) -> str:
        """Apply a perfect electric conductor (PEC) boundary to surfaces.

        PEC enforces a tangential electric field of zero on the specified
        surfaces.  This models ideal metallic conductors.

        Parameters
        ----------
        surface_ids : list[int]
            Mesh surface identifiers.

        Returns
        -------
        str
            Identifier of the created boundary condition.
        """
        return self.add_condition(BoundaryConditionType.PEC, surface_ids=surface_ids)

    def apply_pmc(self, surface_ids: List[int]) -> str:
        """Apply a perfect magnetic conductor (PMC) boundary to surfaces.

        PMC enforces a tangential magnetic field of zero on the specified
        surfaces.  Useful for symmetry planes in certain formulations.

        Parameters
        ----------
        surface_ids : list[int]
            Mesh surface identifiers.

        Returns
        -------
        str
            Identifier of the created boundary condition.
        """
        return self.add_condition(BoundaryConditionType.PMC, surface_ids=surface_ids)

    def apply_radiation_boundary(
        self, surface_ids: List[int], params: Optional[Dict] = None
    ) -> str:
        """Apply an absorbing radiation boundary to surfaces.

        The radiation boundary mimics an open domain by absorbing outgoing
        waves with minimal reflection.  Suitable for antenna and scattering
        simulations.

        Parameters
        ----------
        surface_ids : list[int]
            Mesh surface identifiers.
        params : dict or None
            Additional parameters such as ``reflection_coefficient`` (default
            1e-3) and ``min_distance`` in wavelengths.

        Returns
        -------
        str
            Identifier of the created boundary condition.
        """
        defaults: Dict = {"reflection_coefficient": 1e-3, "min_distance": 0.5}
        if params:
            defaults.update(params)
        return self.add_condition(
            BoundaryConditionType.RADIATION, surface_ids=surface_ids, **defaults
        )

    def apply_pml(
        self,
        surface_ids: List[int],
        layers: int = 3,
        params: Optional[Dict] = None,
    ) -> str:
        """Apply a perfectly matched layer (PML) to surfaces.

        PML zones absorb outgoing waves without reflection, effectively
        extending the computational domain to infinity.

        Parameters
        ----------
        surface_ids : list[int]
            Mesh surface identifiers defining the PML interface.
        layers : int
            Number of PML sub-layers (default 3).
        params : dict or None
            Additional parameters such as ``pml_type`` (e.g. "UPML", "CPML")
            and ``conductivity_profile``.

        Returns
        -------
        str
            Identifier of the created boundary condition.
        """
        defaults: Dict = {"layers": layers, "pml_type": "UPML"}
        if params:
            defaults.update(params)
        return self.add_condition(
            BoundaryConditionType.PML, surface_ids=surface_ids, **defaults
        )

    # ------------------------------------------------------------------ queries ---------------------------------

    def get_conditions_for_surface(self, surface_id: int) -> List[BoundaryCondition]:
        """Return all boundary conditions that reference a given surface.

        Parameters
        ----------
        surface_id : int
            Mesh surface identifier.

        Returns
        -------
        list[BoundaryCondition]
            All conditions whose *surface_ids* list contains *surface_id*.
        """
        return [
            bc
            for bc in self._conditions.values()
            if surface_id in bc.surface_ids
        ]

    def validate_assignments(self, mesh) -> dict:
        """Validate all boundary condition assignments against a mesh.

        Checks for orphaned conditions, empty surfaces, and conflicting
        types on the same surface.

        Parameters
        ----------
        mesh
            A mesh-like object that supports ``get_surface_count()``.

        Returns
        -------
        dict
            Keys ``warnings`` and ``errors``, each a list of human-readable
            strings.
        """
        warnings: List[str] = []
        errors: List[str] = []

        # Determine the set of all surfaces referenced by conditions
        surface_set: set = set()
        for bc_id, bc in self._conditions.items():
            for sid in bc.surface_ids:
                surface_set.add(sid)

        # Check that referenced surfaces exist in the mesh
        try:
            max_surface = mesh.get_surface_count()
        except AttributeError:
            warnings.append(
                "Mesh object does not expose get_surface_count(); "
                "surface existence checks skipped."
            )
            max_surface = None

        if max_surface is not None:
            for sid in surface_set:
                if sid >= max_surface:
                    errors.append(
                        f"Surface {sid} referenced by a boundary condition "
                        f"is out of range (mesh has {max_surface} surfaces)."
                    )

        # Check for conflicting types on the same surface
        surface_to_conds: Dict[int, List[str]] = {}
        for bc_id, bc in self._conditions.items():
            for sid in bc.surface_ids:
                surface_to_conds.setdefault(sid, []).append(bc_id)

        for sid, bc_ids in surface_to_conds.items():
            types = {self._conditions[bid].type for bid in bc_ids}
            if len(types) > 1:
                warnings.append(
                    f"Surface {sid} has conflicting boundary condition types "
                    f"({', '.join(t.value for t in types)})."
                )

        # Check for conditions with no surface assignment
        for bc_id, bc in self._conditions.items():
            if not bc.surface_ids:
                warnings.append(f"Condition {bc_id} has no surface assignment.")

        return {"warnings": warnings, "errors": errors}

    def clear(self) -> None:
        """Remove all boundary conditions."""
        self._conditions.clear()
        logger.info("Cleared all boundary conditions")


# ---------------------------------------------------------------------------
# Module-level example usage
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mgr = BoundaryConditionManager()

    # Apply common BC types
    pec_id = mgr.apply_pec([0, 1])
    print(f"PEC applied: {pec_id}")

    pmc_id = mgr.apply_pmc([2])
    print(f"PMC applied: {pmc_id}")

    rad_id = mgr.apply_radiation_boundary([3], {"reflection_coefficient": 1e-4})
    print(f"Radiation applied: {rad_id}")

    pml_id = mgr.apply_pml([4, 5], layers=5)
    print(f"PML applied: {pml_id}")

    # Query conditions
    for sid in range(6):
        conds = mgr.get_conditions_for_surface(sid)
        print(f"Surface {sid}: {[c.type.value for c in conds]}")

    # Validate (mock mesh)
    class MockMesh:
        def get_surface_count(self):
            return 10

    result = mgr.validate_assignments(MockMesh())
    print("Validation:", result)
