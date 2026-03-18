"""
Main geometry generation script.

Usage
-----
    python geometry/generate_stl.py

Generates STL files for all four propeller configurations into
geometry/stl/ directory.  STL files are then used by snappyHexMesh.

Replace the STL files with your actual CAD exports (same filenames)
when higher-fidelity geometry becomes available.
"""

import os
import sys

# Ensure the repo root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from geometry.conventional_propeller import ConventionalPropeller
from geometry.toroidal_propeller import ToroidalPropeller

STL_DIR = os.path.join(os.path.dirname(__file__), "stl")


def main():
    os.makedirs(STL_DIR, exist_ok=True)

    configs = {
        "conventional": ConventionalPropeller(n_radial=30, n_profile=40),
        "toroidal_low_gap":    ToroidalPropeller(blade_gap=ToroidalPropeller.GAP_LOW,    n_radial=30, n_profile=40),
        "toroidal_medium_gap": ToroidalPropeller(blade_gap=ToroidalPropeller.GAP_MEDIUM, n_radial=30, n_profile=40),
        "toroidal_high_gap":   ToroidalPropeller(blade_gap=ToroidalPropeller.GAP_HIGH,   n_radial=30, n_profile=40),
    }

    for name, prop in configs.items():
        out = os.path.join(STL_DIR, f"{name}.stl")
        prop.generate_stl(out)
        _print_stats(name, prop)

    print("\nAll STL files generated in:", STL_DIR)


def _print_stats(name, prop):
    print(f"\n  {name}")
    print(f"    Diameter       : {prop.r_tip * 2 * 1000:.1f} mm")
    print(f"    Hub radius     : {prop.r_hub * 1000:.1f} mm")
    print(f"    Blade span     : {prop.span * 1000:.1f} mm")
    print(f"    Mean chord     : {prop.mean_chord * 1000:.1f} mm")
    print(f"    Blade area     : {prop.blade_area * 1e6:.0f} mm²  (×{prop.n_blades} blades)")
    print(f"    Aspect ratio   : {prop.aspect_ratio:.2f}")
    print(f"    Solidity       : {prop.solidity:.3f}")
    if hasattr(prop, "blade_gap"):
        print(f"    Blade gap      : {prop.blade_gap * 1000:.1f} mm  ({prop.blade_gap / prop.span * 100:.1f}% of span)")


if __name__ == "__main__":
    main()
