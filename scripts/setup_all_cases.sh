#!/bin/bash
# setup_all_cases.sh
#
# Generates all OpenFOAM case directories for the toroidal propeller study.
# Run this AFTER generating STL files:
#   python geometry/generate_stl.py
#
# Cases generated:
#   - 4 propeller configurations
#   - RPM: 2000, 4000, 6000 (representative subset; add more as needed)
#   - Static thrust (V_inf=0) + 3 wind tunnel speeds (3, 9, 15 m/s)
#
# Usage:
#   bash scripts/setup_all_cases.sh
#   bash scripts/setup_all_cases.sh --n_procs 8   (for HPC)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

N_PROCS="${N_PROCS:-4}"
for arg in "$@"; do
    case $arg in
        --n_procs=*) N_PROCS="${arg#*=}";;
        --n_procs)   shift; N_PROCS="$1";;
    esac
done

CONFIGS=(
    "conventional"
    "toroidal_low_gap"
    "toroidal_medium_gap"
    "toroidal_high_gap"
)

RPMS=(2000 4000 6000)
WIND_SPEEDS=(3 9 15)

echo "==========================================================="
echo "  Toroidal Propeller CFD — OpenFOAM Case Setup"
echo "  n_procs = $N_PROCS"
echo "==========================================================="

# ─── Static thrust cases ────────────────────────────────────────────
echo ""
echo "--- Static Thrust Cases ---"
for cfg in "${CONFIGS[@]}"; do
    for rpm in "${RPMS[@]}"; do
        python openfoam/generate_case.py \
            --config "$cfg" \
            --case_type static_thrust \
            --rpm "$rpm" \
            --v_inf 0 \
            --n_procs "$N_PROCS"
    done
done

# ─── Wind tunnel cases ───────────────────────────────────────────────
echo ""
echo "--- Wind Tunnel Cases ---"
for cfg in "${CONFIGS[@]}"; do
    for rpm in "${RPMS[@]}"; do
        for v in "${WIND_SPEEDS[@]}"; do
            python openfoam/generate_case.py \
                --config "$cfg" \
                --case_type wind_tunnel \
                --rpm "$rpm" \
                --v_inf "$v" \
                --n_procs "$N_PROCS"
        done
    done
done

echo ""
echo "==========================================================="
echo "  All cases created in: $REPO_ROOT/runs/"
echo "  To run a case:  cd runs/<case_name> && bash Allrun"
echo "  To run all:     bash scripts/run_all_cases.sh"
echo "==========================================================="
