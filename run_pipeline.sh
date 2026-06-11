#!/usr/bin/env bash
# run_pipeline.sh
# Bootstraps the environment and runs the full ETL pipeline end-to-end.
#
# Usage (from the project root):
#   chmod +x run_pipeline.sh
#   ./run_pipeline.sh

set -euo pipefail

VENV_DIR=".venv"
SEPARATOR="============================================================"

print_step() {
    echo ""
    echo "$SEPARATOR"
    echo "  $1"
    echo "$SEPARATOR"
}

# ---------------------------------------------------------------------------
# 1. Check Python availability
# ---------------------------------------------------------------------------
print_step "Checking Python installation"

if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.8+."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python version: $PYTHON_VERSION"

# Require Python 3.8+
REQUIRED_MAJOR=3
REQUIRED_MINOR=8
ACTUAL_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
ACTUAL_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$ACTUAL_MAJOR" -lt "$REQUIRED_MAJOR" ] || \
   ([ "$ACTUAL_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$ACTUAL_MINOR" -lt "$REQUIRED_MINOR" ]); then
    echo "ERROR: Python $REQUIRED_MAJOR.$REQUIRED_MINOR+ is required (found $PYTHON_VERSION)."
    exit 1
fi

# ---------------------------------------------------------------------------
# 2. Create virtual environment (once) and install dependencies
# ---------------------------------------------------------------------------
print_step "Setting up virtual environment"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
echo "Virtual environment activated"

echo "Installing/verifying dependencies from requirements.txt ..."
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
echo "Dependencies ready"

# ---------------------------------------------------------------------------
# 3. Create runtime directories
# ---------------------------------------------------------------------------
mkdir -p data outputs logs

# ---------------------------------------------------------------------------
# 4. Populate MySQL with sample data
# ---------------------------------------------------------------------------
print_step "Step 1/2 — Setting up MySQL database (setup_db.py)"

python3 setup_db.py
echo "Database setup complete"

# ---------------------------------------------------------------------------
# 5. Run the ETL pipeline
# ---------------------------------------------------------------------------
print_step "Step 2/2 — Running ETL pipeline (pipeline.py)"

python3 pipeline.py

# ---------------------------------------------------------------------------
# 6. Done
# ---------------------------------------------------------------------------
print_step "Pipeline finished"
echo "  CSV output : data/sales_cleaned.csv"
echo "  Plots      : outputs/*.png"
echo "  Metrics    : outputs/model_metrics.json"
echo "  Summary    : outputs/summary.json"
echo "  Logs       : logs/pipeline_*.log"
echo "$SEPARATOR"
