"""
OpenFOAM case generator for toroidal propeller CFD simulations.

Creates a ready-to-run OpenFOAM case directory from templates by:
  1. Copying the appropriate template (static_thrust or wind_tunnel)
  2. Substituting parameters (RPM → omega, V_inf, n_procs)
  3. Copying the propeller STL into constant/triSurface/

Usage
-----
    # Single case
    python openfoam/generate_case.py \
        --config toroidal_medium_gap \
        --case_type static_thrust \
        --rpm 4000 \
        --output_dir runs/toroidal_medium_gap_4000rpm_static

    # All cases (calls this script in a loop)
    bash scripts/setup_all_cases.sh
"""

import argparse
import os
import shutil
import math
import sys

# Repo root on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates")
STL_DIR      = os.path.join(os.path.dirname(__file__), "..", "geometry", "stl")

# Mapping config name → STL filename
STL_MAP = {
    "conventional"        : "conventional.stl",
    "toroidal_low_gap"    : "toroidal_low_gap.stl",
    "toroidal_medium_gap" : "toroidal_medium_gap.stl",
    "toroidal_high_gap"   : "toroidal_high_gap.stl",
}


def generate_case(
    config: str,
    case_type: str,        # "static_thrust", "wind_tunnel", or "wind_tunnel_openjet"
    rpm: float,
    v_inf: float = 0.0,    # freestream velocity [m/s]
    n_procs: int = 4,
    output_dir: str = None,
):
    """
    Generate an OpenFOAM case directory.

    Parameters
    ----------
    config     : propeller configuration key
    case_type  : "static_thrust" or "wind_tunnel"
    rpm        : rotational speed [RPM]
    v_inf      : freestream velocity [m/s]  (0 for static thrust)
    n_procs    : number of parallel processes for decomposeParDict
    output_dir : where to write the case (default: runs/<config>_<rpm>rpm_<case_type>)
    """
    if output_dir is None:
        runs_dir = os.path.join(os.path.dirname(__file__), "..", "runs")
        os.makedirs(runs_dir, exist_ok=True)
        label = f"{config}_{int(rpm)}rpm_{case_type}"
        if case_type in ("wind_tunnel", "wind_tunnel_openjet"):
            label += f"_{int(v_inf)}ms"
        output_dir = os.path.join(runs_dir, label)

    template_src = os.path.join(TEMPLATE_DIR, case_type)
    if not os.path.isdir(template_src):
        raise FileNotFoundError(f"Template not found: {template_src}")

    # Copy template to output
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir)
    shutil.copytree(template_src, output_dir)

    # Rename 0.orig → 0
    orig_dir = os.path.join(output_dir, "0.orig")
    zero_dir = os.path.join(output_dir, "0")
    if os.path.exists(orig_dir):
        shutil.copytree(orig_dir, zero_dir)

    # Compute omega [rad/s]
    omega = rpm * 2 * math.pi / 60.0

    # Turbulence inlet conditions for open-jet template (k-omega SST)
    # TI = 1%  (typical low-turbulence subsonic wind tunnel)
    # L_t = 0.03 m  (~5% of 600-mm jet diameter)
    TI  = 0.01
    L_t = 0.03
    Cmu = 0.09
    v_ref = max(v_inf, 1.0)   # guard against V_inf=0 (not physical for open-jet)
    turb_k     = 1.5 * (TI * v_ref) ** 2
    turb_omega = math.sqrt(turb_k) / (Cmu ** 0.25 * L_t)

    # Substitute placeholders in all text files
    substitutions = {
        "OMEGA_RAD_S" : f"{omega:.4f}",
        "V_INF_MS"    : f"{v_inf:.4f}",
        "N_PROCS"     : str(n_procs),
        "TURB_K"      : f"{turb_k:.6f}",
        "TURB_OMEGA"  : f"{turb_omega:.4f}",
    }
    _substitute_in_dir(output_dir, substitutions)

    # Copy propeller STL to constant/triSurface/
    stl_filename = STL_MAP.get(config)
    if stl_filename:
        stl_src = os.path.join(STL_DIR, stl_filename)
        tri_dir = os.path.join(output_dir, "constant", "triSurface")
        os.makedirs(tri_dir, exist_ok=True)
        if os.path.isfile(stl_src):
            shutil.copy(stl_src, os.path.join(tri_dir, "propeller.stl"))
        else:
            print(
                f"  [WARN] STL not found at {stl_src}. "
                "Run `python geometry/generate_stl.py` first, "
                "or place your CAD export as geometry/stl/{stl_filename}."
            )

    # Write a simple Allrun script
    _write_allrun(output_dir, n_procs)
    _write_allclean(output_dir)

    print(
        f"[case] {os.path.basename(output_dir):50s}  "
        f"RPM={rpm:.0f}  ω={omega:.2f} rad/s  V∞={v_inf:.1f} m/s  "
        f"nProcs={n_procs}"
    )
    return output_dir


def _substitute_in_dir(root: str, subs: dict):
    """Replace placeholder tokens in all text files under root."""
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, "r") as f:
                    content = f.read()
                modified = content
                for key, val in subs.items():
                    modified = modified.replace(key, val)
                if modified != content:
                    with open(fpath, "w") as f:
                        f.write(modified)
            except (UnicodeDecodeError, PermissionError):
                pass   # skip binary files


def _write_allrun(case_dir: str, n_procs: int):
    script = f"""#!/bin/bash
# Allrun — execute full OpenFOAM workflow for this case
# Usage:  bash Allrun
set -euo pipefail
cd "$(dirname "$0")"

. $WM_PROJECT_DIR/bin/tools/RunFunctions   # load OpenFOAM run helpers

echo "=== Step 1: blockMesh ==="
runApplication blockMesh

echo "=== Step 2: snappyHexMesh ==="
runApplication snappyHexMesh -overwrite

echo "=== Step 3: Check mesh ==="
runApplication checkMesh

echo "=== Step 4: Copy initial conditions ==="
cp -r 0.orig 0

echo "=== Step 5: Run simpleFoam ==="
if [ {n_procs} -gt 1 ]; then
    runApplication decomposePar
    runParallel simpleFoam
    runApplication reconstructPar
else
    runApplication simpleFoam
fi

echo "=== Done ==="
"""
    with open(os.path.join(case_dir, "Allrun"), "w") as f:
        f.write(script)
    os.chmod(os.path.join(case_dir, "Allrun"), 0o755)


def _write_allclean(case_dir: str):
    script = """#!/bin/bash
# Allclean — remove generated files
cd "$(dirname "$0")"
rm -rf 0 [1-9]* constant/polyMesh processor* postProcessing log.* *.log
"""
    with open(os.path.join(case_dir, "Allclean"), "w") as f:
        f.write(script)
    os.chmod(os.path.join(case_dir, "Allclean"), 0o755)


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate OpenFOAM case")
    parser.add_argument("--config",      required=True,
                        choices=list(STL_MAP.keys()),
                        help="Propeller configuration")
    parser.add_argument("--case_type",   required=True,
                        choices=["static_thrust", "wind_tunnel", "wind_tunnel_openjet"],
                        help="Simulation type")
    parser.add_argument("--rpm",         type=float, required=True,
                        help="Rotational speed [RPM]")
    parser.add_argument("--v_inf",       type=float, default=0.0,
                        help="Freestream velocity [m/s] (default: 0 for static)")
    parser.add_argument("--n_procs",     type=int, default=4,
                        help="Number of parallel processes")
    parser.add_argument("--output_dir",  default=None,
                        help="Output directory (auto-named if omitted)")
    args = parser.parse_args()

    generate_case(
        config=args.config,
        case_type=args.case_type,
        rpm=args.rpm,
        v_inf=args.v_inf,
        n_procs=args.n_procs,
        output_dir=args.output_dir,
    )
