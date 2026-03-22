"""
Extract thrust and torque from OpenFOAM forces function object output.

OpenFOAM writes force data to:
  <case>/postProcessing/propellerForces/<time>/force.dat

The file columns are:
  time  Fx  Fy  Fz  Mx  My  Mz  (pressure + viscous)

For a propeller with rotation axis = Z:
  Thrust T = Fz  (total force in axial direction)
  Torque Q = Mz  (total moment about Z axis)

Usage
-----
    python postprocessing/extract_forces.py --runs_dir runs/

Outputs:
  results/cfd_results.csv  — one row per case with converged T, Q, P, CT, etc.
"""

import os
import sys
import re
import math
import numpy as np
import pandas as pd
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RHO = 1.225   # air density [kg/m³]
D   = 0.2032  # propeller diameter [m]


def parse_case_name(case_name: str) -> dict:
    """
    Extract metadata from directory name.
    Expected format:  <config>_<rpm>rpm_<case_type>[_<vms>ms]
    Example:  toroidal_medium_gap_4000rpm_wind_tunnel_9ms
    """
    meta = {"config": None, "rpm": None, "case_type": None, "v_inf": 0.0}

    m = re.search(r"_(\d+)rpm_", case_name)
    if m:
        meta["rpm"] = float(m.group(1))

    m = re.search(r"_(wind_tunnel|static_thrust)_?(\d+)?ms?", case_name)
    if m:
        meta["case_type"] = m.group(1)
        meta["v_inf"]     = float(m.group(2)) if m.group(2) else 0.0
    else:
        meta["case_type"] = "static_thrust"
        meta["v_inf"]     = 0.0

    # Config is everything before the RPM portion
    m2 = re.match(r"^(.*?)_\d+rpm", case_name)
    if m2:
        meta["config"] = m2.group(1)

    return meta


def read_forces(case_dir: str) -> tuple[float, float] | None:
    """
    Read converged thrust (Fz) and torque (Mz) from the forces output.
    Returns (T_N, Q_Nm) or None if data not found.
    """
    forces_base = os.path.join(case_dir, "postProcessing", "propellerForces")
    if not os.path.isdir(forces_base):
        return None

    # Find the latest time directory
    time_dirs = sorted(
        [d for d in os.listdir(forces_base) if os.path.isdir(os.path.join(forces_base, d))],
        key=lambda x: float(x) if _is_number(x) else 0,
    )
    if not time_dirs:
        return None

    force_file = os.path.join(forces_base, time_dirs[-1], "force.dat")
    if not os.path.isfile(force_file):
        return None

    # Read last 50 rows and average (converged solution)
    try:
        data = []
        with open(force_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                # Format: time (Fp_x Fp_y Fp_z) (Fv_x Fv_y Fv_z) (Mp_x ...) (Mv_x ...)
                numbers = re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", line)
                if len(numbers) >= 13:
                    data.append([float(x) for x in numbers[:13]])

        if not data:
            return None

        arr = np.array(data[-50:])  # last 50 iterations
        # Column layout: time (Fpx Fpy Fpz) (Fvx Fvy Fvz) (Mpx Mpy Mpz) (Mvx Mvy Mvz)
        #                 0     1   2   3     4   5   6     7   8   9     10  11  12
        # Total Fz = pressure Fz (col 3) + viscous Fz (col 6)
        Fz = arr[:, 3] + arr[:, 6]
        # Total Mz = pressure Mz (col 9) + viscous Mz (col 12)
        Mz = arr[:, 9] + arr[:, 12] if arr.shape[1] > 12 else arr[:, 9]

        T = float(Fz.mean())
        Q = float(Mz.mean())
        return T, Q

    except Exception as e:
        print(f"  [WARN] Could not parse {force_file}: {e}")
        return None


def compute_coefficients(T: float, Q: float, rpm: float, v_inf: float) -> dict:
    """Compute CT, CQ, CP, J, eta from forces."""
    n = rpm / 60.0
    omega = n * 2 * math.pi

    CT  = T  / (RHO * n**2 * D**4) if n > 0 else 0.0
    CQ  = Q  / (RHO * n**2 * D**5) if n > 0 else 0.0
    CP  = 2 * math.pi * CQ
    J   = v_inf / (n * D)           if n > 0 else 0.0
    P   = Q * omega
    eta = J * CT / CP               if CP > 1e-9 else 0.0

    return {
        "T_N"      : T,
        "T_gf"     : T / 9.81 * 1000,   # gram-force
        "Q_Nm"     : Q,
        "P_W"      : P,
        "CT"       : CT,
        "CQ"       : CQ,
        "CP"       : CP,
        "J"        : J,
        "eta"      : eta,
    }


def extract_all(runs_dir: str, output_csv: str = None):
    """
    Extract forces from all case directories under runs_dir.
    """
    if output_csv is None:
        results_dir = os.path.join(os.path.dirname(__file__), "..", "results")
        os.makedirs(results_dir, exist_ok=True)
        output_csv = os.path.join(results_dir, "cfd_results.csv")

    rows = []
    case_dirs = sorted([
        d for d in os.listdir(runs_dir)
        if os.path.isdir(os.path.join(runs_dir, d))
    ])

    for case_name in case_dirs:
        case_dir = os.path.join(runs_dir, case_name)
        meta = parse_case_name(case_name)

        result = read_forces(case_dir)
        if result is None:
            print(f"  [SKIP] {case_name}  (no force data — case not run yet)")
            continue

        T, Q = result
        coeffs = compute_coefficients(T, Q, meta["rpm"], meta["v_inf"])

        row = {
            "case"       : case_name,
            "config"     : meta["config"],
            "rpm"        : meta["rpm"],
            "v_inf_ms"   : meta["v_inf"],
            "case_type"  : meta["case_type"],
            **coeffs,
        }
        rows.append(row)
        print(
            f"  {case_name:55s}  "
            f"T={coeffs['T_gf']:7.1f} gf  "
            f"Q={coeffs['Q_Nm']:.4f} Nm  "
            f"η={coeffs['eta']:.3f}"
        )

    if rows:
        df = pd.DataFrame(rows)
        df.to_csv(output_csv, index=False)
        print(f"\nResults saved to: {output_csv}")
    else:
        print("\nNo completed cases found. Run the OpenFOAM cases first.")

    return rows


def _is_number(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract CFD forces from OpenFOAM cases")
    parser.add_argument("--runs_dir", default="runs",
                        help="Directory containing OpenFOAM case subdirectories")
    parser.add_argument("--output", default=None,
                        help="Output CSV path")
    args = parser.parse_args()

    extract_all(
        runs_dir=os.path.abspath(args.runs_dir),
        output_csv=args.output,
    )
