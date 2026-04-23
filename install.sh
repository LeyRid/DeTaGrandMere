#!/usr/bin/env bash
# DeTaGrandMere — Installation Script
# Installs only the dependencies specified in the project requirements.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"

echo "=========================================="
echo " DeTaGrandMere Antenna Simulation Software"
echo " Installation Script"
echo "=========================================="
echo ""

# ------------------------------------------------------------------
# 1. Verify Python version (>= 3.9)
# ------------------------------------------------------------------
PY_VERSION=$($PYTHON -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 9 ]; }; then
    echo "ERROR: Python 3.9+ required (found $PY_VERSION)"
    exit 1
fi
echo "[OK] Python $PY_VERSION"

# ------------------------------------------------------------------
# 2. Create virtual environment if not exists
# ------------------------------------------------------------------
VENV_DIR="$SCRIPT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    $PYTHON -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

echo "[OK] Virtual environment ready"

# ------------------------------------------------------------------
# 3. Install core dependencies (specified only)
# ------------------------------------------------------------------
echo ""
echo "--- Installing core dependencies ---"
pip install --upgrade pip setuptools wheel

pip install numpy scipy matplotlib pyvista h5py

echo "[OK] Core dependencies installed"

# ------------------------------------------------------------------
# 4. Install CAD libraries (optional, with error handling)
# ------------------------------------------------------------------
echo ""
echo "--- Installing CAD libraries (optional) ---"

echo "Note: opencascade-core and cgal-python3 require system-level C++"
echo "libraries. If installation fails, install them manually:"
echo "  pip install opencascade-core   # or occt-pybind11"
echo "  pip install cgal-python3"
echo ""

read -p "Install CAD libraries now? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install opencascade-core || echo "[WARN] opencascade-core failed (may need system packages)"
    pip install cgal-python3 || echo "[WARN] cgal-python3 failed (may need system packages)"
else
    echo "Skipping CAD libraries. You can install them later."
fi

# ------------------------------------------------------------------
# 5. Install linear algebra libraries (optional)
# ------------------------------------------------------------------
echo ""
echo "--- Installing linear algebra libraries (optional) ---"

read -p "Install petsc4py and mpi4py? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install petsc4py || echo "[WARN] petsc4py failed (may need PETSc system library)"
    pip install mpi4py || echo "[WARN] mpi4py failed"
else
    echo "Skipping linear algebra libraries. They are stubs in the codebase."
fi

# ------------------------------------------------------------------
# 6. Install development tools
# ------------------------------------------------------------------
echo ""
echo "--- Installing development tools ---"
pip install pytest pytest-cov black flake8 mypy

echo "[OK] Development tools installed"

# ------------------------------------------------------------------
# 7. Install the project itself (editable mode)
# ------------------------------------------------------------------
echo ""
echo "--- Installing DeTaGrandMere package ---"
cd "$SCRIPT_DIR"
pip install -e . || echo "[WARN] Editable install failed; using PYTHONPATH instead"

echo ""
echo "=========================================="
echo " Installation Complete!"
echo "=========================================="
echo ""
echo "To activate the virtual environment:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "To run simulations:"
echo "  python run.py simulate --frequency 1e9 --solver-type EFIE"
echo ""
echo "To launch the GUI (when available):"
echo "  python gui_launcher.py"
echo ""
echo "To run tests:"
echo "  pytest tests/unit/ -v"
echo ""
