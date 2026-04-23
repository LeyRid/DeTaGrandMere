# USE CASE UC-10-Export Simulation Results for Post-Processing

**Context of use:** RF Antenna Engineer exports simulation results in formats suitable for external analysis tools (MATLAB, Python, spreadsheet applications) or documentation (PDF reports, image files). This enables further custom analysis, inclusion in design reports, comparison with measured data, and sharing with team members who do not have access to the EM Simulation System.

**Scope:** EM Simulation System — System scope, black box

**Level:** User-goal

**Primary Actor:** RF Antenna Engineer

**Stakeholders & Interests:**
- RF Antenna Engineer: Wants results exported in formats that can be directly imported by their preferred analysis tools without manual data transformation.
- Team Members (supporting actor): Need access to simulation results in shareable formats for design review meetings and documentation.
- System Owner: Wants exports to preserve full metadata (simulation settings, mesh parameters, timestamps) so recipients understand the context of the exported data.

**Precondition:** One or more simulations have been completed with stored results including S-parameters, radiation patterns, field distributions, and convergence data. The engineer has identified which results need to be exported and in what formats.

**Minimal Guarantees:** Every export operation is logged with the files created, their formats, sizes, and the simulation results they contain. All exported data files include embedded metadata describing the simulation configuration so that external analysis can be performed with correct parameters. Export failures are reported with specific details about which data could not be written.

**Success Guarantees:** All requested result data is successfully written to files in the specified formats. Each file contains both the numerical data and sufficient metadata for independent interpretation. The engineer receives confirmation of export completion with a summary of exported files, their locations, and their sizes.

**Trigger:** RF Antenna Engineer initiates result export from the completed simulation project.

## Main Success Scenario

1. RF Antenna Engineer: selects the simulation results to export (S-parameters, radiation patterns, field distributions, convergence data) and specifies output formats.
2. System: validates that all selected results exist in the project store and are complete (no missing frequency points or angular resolutions).
3. System: formats the numerical data for each result type according to the selected output format standards.
4. System: embeds simulation metadata (geometry file, mesh parameters, solver settings, port definitions, material assignments) into the exported files or a companion metadata file.
5. System: writes all exported files to the specified output directory.
6. RF Antenna Engineer: verifies that the exported files are accessible and contain expected data.
7. System: logs the export operation with file list, sizes, and timestamps in the project audit trail.

## Extensions

1a. Selected results include data from multiple simulations or design iterations:
   - System offers to export all selected results as separate files (one per simulation) or combine them into a single multi-dataset file with simulation identifiers.
   - RF Antenna Engineer: chooses the organization approach.
   - Execution resumes at step 3 with the chosen organization applied.

2a. Export format is not supported for a selected result type (e.g., 3D field distribution requested as CSV):
   - System reports which result types are compatible with which formats and suggests alternative formats or additional steps (e.g., reducing dimensionality before export).
   - RF Antenna Engineer: selects compatible format/result combinations or removes incompatible selections.
   - Execution resumes at step 2 with corrected selections.

3a. Radiation pattern data is very large (high angular resolution across many frequencies):
   - System warns that the total export size may exceed the specified output directory's available space and suggests reducing angular resolution or selecting fewer frequencies.
   - RF Antenna Engineer: adjusts the export scope or authorizes the full export.
   - If authorized: execution resumes at step 5 with a warning flag in the audit log.

4a. Exported data needs to be compared with measured results:
   - System offers a specialized measurement-comparison export format that includes both simulated and measured S-parameter data in a single file with clear column labeling, plus a correlation analysis summary (RMSE, peak-to-peak error).
   - RF Antenna Engineer: provides the measurement data file or uploads it through the system interface.
   - Execution resumes at step 3 with combined simulation-measurement data formatted for comparison.

5a. Output directory does not exist or is not writable:
   - System prompts the engineer to specify an alternative output location.
   - RF Antenna Engineer: provides a valid directory path with write permissions.
   - Execution resumes at step 5 with the corrected output path.

6a. Some results are incomplete (e.g., simulation failed at certain frequencies, radiation patterns not computed):
   - System reports which result types have gaps and offers to export only complete data or include placeholder values for missing entries with clear gap indicators.
   - RF Antenna Engineer: chooses to exclude incomplete results or export with gap markers.
   - If including gaps: execution resumes at step 3 with placeholder data inserted.

## Technology and Data Variations List

- Step 1: Supported output formats include CSV (tabular numerical data), HDF5 (hierarchical multi-dataset format, recommended for large simulations), JSON (structured data with embedded metadata), VTK/VTP (visualization data compatible with ParaView, PyVista), PNG/SVG (pattern plots), and PDF (complete report with plots and tables).
- Step 3: S-parameter export formats include touchstone (.sNp) format for RF tool compatibility, CSV with frequency/magnitude/phase columns, and MATLAB .mat files. Radiation pattern export includes polar data (theta, phi, gain in dB), Cartesian data (azimuth, elevation, gain), and 3D field data (x, y, z coordinates with E-field and H-field vectors).
- Step 4: Metadata embedding follows a standardized schema including simulation method, mesh element count, solver settings, frequency range, port definitions, material properties, and timestamp.

## Related Information

- **Priority:** 3 (moderate — important for workflow integration but not required for core simulation functionality)
- **Channels:** Desktop application with export dialog, command-line interface with file path arguments
- **Frequency:** After every completed simulation where results need to be shared or further analyzed outside the system.
- **Open Issues:** Should the system support automated report generation (PDF/HTML) combining all analysis results into a single document? How to handle version control integration for exported simulation data?
