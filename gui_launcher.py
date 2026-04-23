#!/usr/bin/env python3
"""DeTaGrandMere — GUI Launcher Application.

Provides a simple PyQt5/PyQt6-based graphical interface for launching
simulations, viewing results, and managing configuration.

Usage::

    python gui_launcher.py

Requires: PyQt5 or PyQt6 (install separately if needed).
If not available, falls back to matplotlib-based inline visualization.
"""

from __future__ import annotations

import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _try_import_qt():
    """Try importing PyQt6 first, then PyQt5."""
    try:
        from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
        from PyQt6.QtWidgets import QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox
        from PyQt6.QtWidgets import QFileDialog, QMessageBox, QGroupBox, QScrollArea
        from PyQt6.QtCore import Qt, pyqtSignal
        from PyQt6.QtGui import QFont, QIcon

        return "PyQt6", QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, \
               QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QFileDialog, \
               QMessageBox, QGroupBox, QScrollArea, Qt, QFont, QIcon
    except ImportError:
        pass

    try:
        from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout
        from PyQt5.QtWidgets import QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox
        from PyQt5.QtWidgets import QFileDialog, QMessageBox, QGroupBox, QScrollArea
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QFont

        return "PyQt5", QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, \
               QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QFileDialog, \
               QMessageBox, QGroupBox, QScrollArea, Qt, QFont
    except ImportError:
        return None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None


# ------------------------------------------------------------------
# Main GUI Application
# ------------------------------------------------------------------

class DeTaGrandMereGUI:
    """Main GUI application window for DeTaGrandMere."""

    def __init__(self):
        """Initialize the GUI application."""
        self.qt_version, *qt_classes = _try_import_qt()
        if self.qt_version is None:
            print("WARNING: PyQt5/PyQt6 not available. Launching CLI mode instead.")
            self._run_cli_fallback()
            return

        (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
         QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QFileDialog,
         QMessageBox, QGroupBox, QScrollArea, Qt, QFont) = qt_classes

        self.app = QApplication(sys.argv)
        self.window = QMainWindow()
        self.window.setWindowTitle("DeTaGrandMere — Antenna Simulation")
        self.window.resize(900, 700)

        # Central widget
        central = QWidget()
        self.window.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Title
        title_label = QLabel("DeTaGrandMere — Planar Antenna Simulation Software")
        title_label.setFont(QFont("Sans", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # Simulation configuration group
        sim_group = QGroupBox("Simulation Configuration")
        sim_layout = QVBoxLayout()

        # Frequency
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Frequency (Hz):"))
        self.freq_input = QLineEdit("1e9")
        freq_layout.addWidget(self.freq_input)
        sim_layout.addLayout(freq_layout)

        # Solver type
        solver_layout = QHBoxLayout()
        solver_layout.addWidget(QLabel("Solver Type:"))
        self.solver_combo = QComboBox()
        self.solver_combo.addItems(["EFIE", "MFIE", "CFIE"])
        solver_layout.addWidget(self.solver_combo)
        sim_layout.addLayout(solver_layout)

        # Tolerance
        tol_layout = QHBoxLayout()
        tol_layout.addWidget(QLabel("Tolerance:"))
        self.tol_input = QLineEdit("1e-6")
        tol_layout.addWidget(self.tol_input)
        sim_layout.addLayout(tol_layout)

        # Run button
        self.run_button = QPushButton("Run Simulation")
        self.run_button.setFont(QFont("Sans", 12, QFont.Bold))
        self.run_button.clicked.connect(self._run_simulation)
        sim_layout.addWidget(self.run_button)

        sim_group.setLayout(sim_layout)
        main_layout.addWidget(sim_group)

        # Output text area
        output_label = QLabel("Simulation Output:")
        main_layout.addWidget(output_label)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Courier", 10))
        main_layout.addWidget(self.output_text)

        # Status bar
        status_label = QLabel("Ready")
        status_label.setFont(QFont("Sans", 10))
        main_layout.addWidget(status_label)
        self.status_label = status_label

        self.window.show()
        sys.exit(self.app.exec())

    def _run_simulation(self):
        """Run simulation from GUI."""
        frequency = self.freq_input.text()
        solver_type = self.solver_combo.currentText()
        tolerance = self.tol_input.text()

        # Capture stdout to show in GUI
        import io
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()

        try:
            from src.core.workflow import SimulationWorkflow
            from src.utils.cli_parser import parse_arguments

            # Build CLI args manually
            class MockArgs:
                command = "simulate"
                frequency = float(frequency)
                solver_type = solver_type
                tolerance = float(tolerance)

            args = MockArgs()
            workflow = SimulationWorkflow(cli_args=args)
            workflow.run()

            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            self.output_text.append(output)
            self.status_label.setText("Simulation complete")

        except Exception as e:
            sys.stdout = old_stdout
            self.output_text.append(f"ERROR: {str(e)}")
            self.status_label.setText(f"Error: {str(e)}")

    def _run_cli_fallback(self):
        """Fall back to CLI mode if Qt is unavailable."""
        from src.utils.cli_parser import parse_arguments
        args = parse_arguments(["simulate", "--frequency", "1e9", "--solver-type", "EFIE"])
        print(f"Parsed args: {vars(args)}")
        print("GUI not available — use CLI instead:")
        print("  python run.py simulate --frequency 1e9 --solver-type EFIE")


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

if __name__ == "__main__":
    DeTaGrandMereGUI()
