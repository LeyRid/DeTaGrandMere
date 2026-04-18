"""Field calculation sub-package for DeTaGrandMere antenna simulation.

This sub-package provides near-field and far-field electromagnetic field
computers that operate on surface current distributions obtained from
the Method of Moments (MoM) solver.

Sub-modules
-----------
near_field : Near-field E and H field computation from currents.
far_field  : Far-field transformation to radiation patterns.

Example usage::

    from src.core.field_calculations import near_field, far_field

    # Near-field computation
    calculator = near_field.NearFieldCalculator(frequency=2.4e9)
    E = calculator.compute_E_field(currents, obs_points, src_points)

    # Far-field transformation
    transformer = far_field.FarFieldTransformer(frequency=2.4e9)
    pattern = transformer.compute_far_field(currents, src_points, areas)
"""

from __future__ import annotations

from src.core.field_calculations.near_field import NearFieldCalculator
from src.core.field_calculations.far_field import FarFieldTransformer

__all__: list[str] = [
    "NearFieldCalculator",
    "FarFieldTransformer",
]
