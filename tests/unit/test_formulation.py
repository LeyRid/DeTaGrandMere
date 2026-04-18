"""Unit tests for integral equation formulation types and factory function.

This module provides comprehensive pytest-based unit tests covering:

- FormulationType enum values (EFIE, MFIE, CFIE)
- get_formulation() factory for EFIE, MFIE, and CFIE types
- ValueError raised on unknown/unrecognised formulation type

All tests are self-contained using only numpy and pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

# Import the modules under test
from src.core.mom_solver.formulation import (
    IntegralEquationFormulation,
    EFIEFormulation,
    MFIEFormulation,
    CFIEFormulation,
    FormulationType,
    get_formulation,
)


# ===================================================================
# Test FormulationType enum
# ===================================================================

class TestFormulationTypeEnum:
    """Tests for the FormulationType enumeration."""

    def test_formulation_type_enum(self) -> None:
        """Verify FormulationType enum values.

        The FormulationType enum must have exactly three members:
        - EFIE with string value "EFIE"
        - MFIE with string value "MFIE"
        - CFIE with string value "CFIE"
        """
        # Check that all expected enum members exist
        assert hasattr(FormulationType, "EFIE"), "FormulationType missing EFIE"
        assert hasattr(FormulationType, "MFIE"), "FormulationType missing MFIE"
        assert hasattr(FormulationType, "CFIE"), "FormulationType missing CFIE"

        # Verify string values
        assert FormulationType.EFIE.value == "EFIE", \
            f"FormulationType.EFIE.value = {FormulationType.EFIE.value}"
        assert FormulationType.MFIE.value == "MFIE", \
            f"FormulationType.MFIE.value = {FormulationType.MFIE.value}"
        assert FormulationType.CFIE.value == "CFIE", \
            f"FormulationType.CFIE.value = {FormulationType.CFIE.value}"

        # Verify that enum members are distinct
        assert FormulationType.EFIE != FormulationType.MFIE
        assert FormulationType.EFIE != FormulationType.CFIE
        assert FormulationType.MFIE != FormulationType.CFIE

        # Verify we can iterate over all members
        members = list(FormulationType)
        assert len(members) == 3, \
            f"Expected 3 enum members, got {len(members)}"


# ===================================================================
# Test get_formulation factory function
# ===================================================================

class TestGetFormulationFactory:
    """Tests for the get_formulation() factory function."""

    def test_get_formulation_factory(self) -> None:
        """Test factory for EFIE, MFIE, and CFIE types.

        Verify that get_formulation returns the correct class instance
        for each FormulationType member, and that the instances are
        subclasses of IntegralEquationFormulation.
        """
        # Test EFIE
        efie = get_formulation(FormulationType.EFIE)
        assert isinstance(efie, EFIEFormulation), \
            f"get_formulation(EFIE) returned {type(efie)}, expected EFIEFormulation"
        assert isinstance(efie, IntegralEquationFormulation), \
            "EFIE instance should be subclass of IntegralEquationFormulation"

        # Test MFIE
        mfie = get_formulation(FormulationType.MFIE)
        assert isinstance(mfie, MFIEFormulation), \
            f"get_formulation(MFIE) returned {type(mfie)}, expected MFIEFormulation"
        assert isinstance(mfie, IntegralEquationFormulation), \
            "MFIE instance should be subclass of IntegralEquationFormulation"

        # Test CFIE (default coupling factor = 0.5)
        cfie = get_formulation(FormulationType.CFIE)
        assert isinstance(cfie, CFIEFormulation), \
            f"get_formulation(CFIE) returned {type(cfie)}, expected CFIEFormulation"
        assert isinstance(cfie, IntegralEquationFormulation), \
            "CFIE instance should be subclass of IntegralEquationFormulation"
        assert cfie.get_weighting_factor() == 0.5, \
            f"Default CFIE weighting factor = {cfie.get_weighting_factor()}, expected 0.5"

    def test_get_formulation_with_kwargs(self) -> None:
        """Test factory passing kwargs (e.g., coupling_factor for CFIE)."""
        cfie = get_formulation(FormulationType.CFIE, coupling_factor=0.6)
        assert isinstance(cfie, CFIEFormulation), \
            f"get_formulation(CFIE, **kwargs) returned {type(cfie)}"
        assert np.isclose(cfie.get_weighting_factor(), 0.6, rtol=1e-10), \
            f"CFIE weighting factor = {cfie.get_weighting_factor()}, expected 0.6"

    def test_get_formulation_returns_different_instances(self) -> None:
        """Test that each call to get_formulation returns a new instance."""
        efie1 = get_formulation(FormulationType.EFIE)
        efie2 = get_formulation(FormulationType.EFIE)

        assert efie1 is not efie2, \
            "get_formulation should return different instances each call"

    def test_get_formulation_efie_compute_element(self) -> None:
        """Test that the EFIE instance can compute elements correctly."""
        frequency = 1e9
        efie = get_formulation(FormulationType.EFIE)

        # Self-term (diagonal) should return a regularised complex value
        self_elem = efie.compute_element(0, 0, frequency)
        assert isinstance(self_elem, (complex, np.complexfloating)), \
            f"EFIE self-element returned {type(self_elem)}, expected complex"

        # Off-diagonal should also be complex and finite
        off_elem = efie.compute_element(0, 5, frequency)
        assert isinstance(off_elem, (complex, np.complexfloating))
        assert np.isfinite(off_elem), \
            f"EFIE off-element returned non-finite: {off_elem}"

    def test_get_formulation_mfie_compute_element(self) -> None:
        """Test that the MFIE instance computes elements with 0.5 factor."""
        frequency = 1e9
        mfie = get_formulation(FormulationType.MFIE)

        self_elem = mfie.compute_element(0, 0, frequency)
        assert np.isclose(self_elem.real, 0.5, rtol=1e-10), \
            f"MFIE self-element real part {self_elem.real} != 0.5"


# ===================================================================
# Test invalid formulation type
# ===================================================================

class TestInvalidFormulationType:
    """Tests for error handling on unknown formulation types."""

    def test_invalid_formulation_type(self) -> None:
        """Test ValueError on unknown type.

        The get_formulation factory should raise a ValueError when
        passed a FormulationType value that is not EFIE, MFIE, or CFIE.
        """
        # Since FormulationType is an Enum with fixed members, we need to
        # simulate passing an unknown type. We can do this by creating
        # a mock object that compares equal to nothing in the factory dict.

        class UnknownFormulationType:
            """A fake enum-like object not recognised by the factory."""
            def __init__(self) -> None:
                self.value = "UNKNOWN"

        unknown_type = UnknownFormulationType()

        with pytest.raises(ValueError, match="Unknown formulation type"):
            get_formulation(unknown_type)  # type: ignore[arg-type]

    def test_get_formulation_value_error_message(self) -> None:
        """Test that the ValueError message is informative."""
        class BadType:
            pass

        bad = BadType()

        with pytest.raises(ValueError) as exc_info:
            get_formulation(bad)  # type: ignore[arg-type]

        error_msg = str(exc_info.value)
        assert "Unknown formulation type" in error_msg, \
            f"Error message should mention 'Unknown formulation type': {error_msg}"


# ===================================================================
# Test weighting factors
# ===================================================================

class TestWeightingFactors:
    """Tests for formulation weighting factor methods."""

    def test_efie_weighting_factor(self) -> None:
        """EFIE weighting factor should always be 1.0."""
        efie = EFIEFormulation()
        assert np.isclose(efie.get_weighting_factor(), 1.0), \
            f"EFIE weighting factor = {efie.get_weighting_factor()}, expected 1.0"

    def test_mfie_weighting_factor(self) -> None:
        """MFIE weighting factor should always be 1.0."""
        mfie = MFIEFormulation()
        assert np.isclose(mfie.get_weighting_factor(), 1.0), \
            f"MFIE weighting factor = {mfie.get_weighting_factor()}, expected 1.0"

    def test_cfie_weighting_factor_varies(self) -> None:
        """CFIE weighting factor should equal the coupling factor."""
        for alpha in [0.3, 0.5, 0.8]:
            cfie = CFIEFormulation(coupling_factor=alpha)
            assert np.isclose(cfie.get_weighting_factor(), alpha), \
                f"CFIE weighting factor {cfie.get_weighting_factor()} != {alpha}"


# ===================================================================
# Test base class interface
# ===================================================================

class TestBaseClassInterface:
    """Tests for the IntegralEquationFormulation abstract base class."""

    def test_base_class_is_abstract(self) -> None:
        """Test that IntegralEquationFormulation cannot be instantiated directly.

        Since it is an ABC with abstract methods, attempting to instantiate
        it should raise a TypeError (Python's standard behaviour for ABCs).
        """
        with pytest.raises(TypeError):
            IntegralEquationFormulation()  # type: ignore[abstract]

    def test_concrete_classes_implement_compute_element(self) -> None:
        """Verify all concrete classes implement compute_element."""
        frequency = 1e9

        for formulation_cls in [EFIEFormulation, MFIEFormulation, CFIEFormulation]:
            form = formulation_cls()
            result = form.compute_element(0, 0, frequency)
            assert isinstance(result, (complex, np.complexfloating)), \
                f"{formulation_cls.__name__}.compute_element returned {type(result)}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
