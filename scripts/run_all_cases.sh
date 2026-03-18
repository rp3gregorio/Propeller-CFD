#!/bin/bash
# run_all_cases.sh
#
# Runs all OpenFOAM cases sequentially (or in parallel batches on HPC).
# Assumes cases have already been set up with setup_all_cases.sh.
#
# Usage:
#   bash scripts/run_all_cases.sh
#   bash scripts/run_all_cases.sh --parallel 2   (run 2 cases simultaneously)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUNS_DIR="$REPO_ROOT/runs"

PARALLEL_JOBS=1
for arg in "$@"; do
    case $arg in
        --parallel=*) PARALLEL_JOBS="${arg#*=}";;
        --parallel)   shift; PARALLEL_JOBS="$1";;
    esac
done

if [ ! -d "$RUNS_DIR" ]; then
    echo "ERROR: No runs/ directory found. Run setup_all_cases.sh first."
    exit 1
fi

. "$WM_PROJECT_DIR/bin/tools/RunFunctions" 2>/dev/null || true

echo "============================================================"
echo "  Running all OpenFOAM cases in: $RUNS_DIR"
echo "  Parallel batch size: $PARALLEL_JOBS"
echo "============================================================"

run_case() {
    local case_dir="$1"
    local name
    name=$(basename "$case_dir")
    echo "[START] $name"
    cd "$case_dir"
    bash Allrun > log.Allrun 2>&1 && echo "[DONE]  $name" || echo "[FAIL]  $name  (see $case_dir/log.Allrun)"
    cd "$REPO_ROOT"
}

export -f run_case
export REPO_ROOT

find "$RUNS_DIR" -maxdepth 1 -mindepth 1 -type d | \
    xargs -P "$PARALLEL_JOBS" -I{} bash -c 'run_case "$@"' _ {}

echo ""
echo "All cases finished. Post-process with:"
echo "  python postprocessing/extract_forces.py"
