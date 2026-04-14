# UC-10: Verify with Simple Antennas

* [ ] Implement half-wave dipole test case
* [ ] Implement microstrip patch test case
* [ ] Implement loop antenna test case
* [ ] Compare results with analytical solutions
* [ ] Document verification results

## CHARACTERISTIC INFORMATION

* **Goal in Context**: Validate solver against known analytical solutions
* **Scope**: Test cases, comparison, verification documentation
* **Level**: Testing/Validation
* **Preconditions**: Full MoM solver (UC-09)
* **Success End Condition**: Results match theory within 5% tolerance
* **Failed End Condition**: Results exceed tolerance or show systematic errors
* **Primary Actor**: Developer/AI Agent
* **Trigger**: After solver implementation

## MAIN SUCCESS SCENARIO

1. Implement test cases:
   - Half-wave dipole (analytical solution known)
   - Rectangular microstrip patch
   - Loop antenna
2. Compare results with:
   - Analytical formulas
   - Commercial software (CST/HFSS if available)
   - Published benchmark data
3. Identify discrepancies and analyze causes
4. Document verification results

## EXTENSIONS

1a. Step 2: Cross-validate with multiple reference sources
2a. Step 3: Create automated regression tests

## SUB-VARIATIONS

1. Simple geometries vs complex assemblies
2. Low frequency vs high frequency regimes

## RELATED INFORMATION

* **Priority**: High - Essential for trust in solver
* **Performance Target**: Complete within 1 week
* **Frequency**: After major changes, before release
