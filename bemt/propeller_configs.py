"""
Propeller configuration definitions for BEMT analysis.

All four propeller configurations are defined here matching the paper:
  - Conventional 2-blade (baseline)
  - Toroidal low gap  (0.5 in = 12.7 mm)
  - Toroidal medium gap (1.5 in = 38.1 mm)  ← best performer in experiments
  - Toroidal high gap  (2.5 in = 63.5 mm)

Dimensions are derived from the paper's reported blade areas, aspect ratios,
and solidity values for the 8-inch (D=203.2 mm) propeller class.
"""

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Physical constants
# ─────────────────────────────────────────────────────────────────────────────
RHO_AIR   = 1.225   # [kg/m³] air density at sea level
NU_AIR    = 1.5e-5  # [m²/s]  kinematic viscosity

# ─────────────────────────────────────────────────────────────────────────────
# Shared geometry (same for all configurations)
# ─────────────────────────────────────────────────────────────────────────────
R_HUB  = 0.0127   # [m]  hub radius  (0.5 in)
R_TIP  = 0.1016   # [m]  tip radius  (4.0 in)
SPAN   = R_TIP - R_HUB   # = 0.0889 m  (3.5 in blade span)

# ─────────────────────────────────────────────────────────────────────────────
# Chord distributions (linear taper calibrated to match paper blade areas)
# ─────────────────────────────────────────────────────────────────────────────
# Paper reported blade areas (mm²) per blade:
#   Low gap   : 13,983   → mean chord ≈ 78.5 mm
#   Medium gap: 10,795   → mean chord ≈ 60.7 mm
#   High gap  :  8,367   → mean chord ≈ 47.0 mm
#   Conventional: assume similar to medium gap ≈ 58 mm

def _linear_chord(r, c_root, c_tip):
    return np.interp(r, [R_HUB, R_TIP], [c_root, c_tip])

def _linear_twist(r, theta_root=35.0, theta_tip=15.0):
    return np.interp(r, [R_HUB, R_TIP], [theta_root, theta_tip])


CONFIGS = {
    "conventional": {
        "label"       : "Conventional 2-blade",
        "short_name"  : "Conv",
        "color"       : "black",
        "linestyle"   : "-",
        "marker"      : "o",
        "n_blades"    : 2,
        "r_hub"       : R_HUB,
        "r_tip"       : R_TIP,
        "chord_func"  : lambda r: _linear_chord(r, c_root=0.068, c_tip=0.040),
        "twist_func"  : lambda r: _linear_twist(r, 35.0, 15.0),
        "tip_loss"    : True,   # standard Prandtl tip-loss correction
        "toroidal"    : False,
    },
    "toroidal_low_gap": {
        "label"       : "Toroidal 0.5-inch gap",
        "short_name"  : "Tor-LG",
        "color"       : "blue",
        "linestyle"   : "--",
        "marker"      : "s",
        "n_blades"    : 2,
        "r_hub"       : R_HUB,
        "r_tip"       : R_TIP,
        "chord_func"  : lambda r: _linear_chord(r, c_root=0.095, c_tip=0.055),
        "twist_func"  : lambda r: _linear_twist(r, 35.0, 15.0),
        "tip_loss"    : False,  # connected tips → negligible tip vortices
        "toroidal"    : True,
        "blade_gap"   : 0.0127,
    },
    "toroidal_medium_gap": {
        "label"       : "Toroidal 1.5-inch gap (Best)",
        "short_name"  : "Tor-MG",
        "color"       : "red",
        "linestyle"   : "-",
        "marker"      : "^",
        "n_blades"    : 2,
        "r_hub"       : R_HUB,
        "r_tip"       : R_TIP,
        "chord_func"  : lambda r: _linear_chord(r, c_root=0.075, c_tip=0.043),
        "twist_func"  : lambda r: _linear_twist(r, 35.0, 15.0),
        "tip_loss"    : False,
        "toroidal"    : True,
        "blade_gap"   : 0.0381,
    },
    "toroidal_high_gap": {
        "label"       : "Toroidal 2.5-inch gap",
        "short_name"  : "Tor-HG",
        "color"       : "green",
        "linestyle"   : ":",
        "marker"      : "D",
        "n_blades"    : 2,
        "r_hub"       : R_HUB,
        "r_tip"       : R_TIP,
        "chord_func"  : lambda r: _linear_chord(r, c_root=0.058, c_tip=0.033),
        "twist_func"  : lambda r: _linear_twist(r, 35.0, 15.0),
        "tip_loss"    : False,
        "toroidal"    : True,
        "blade_gap"   : 0.0635,
    },
}

# Ordered list for consistent plotting
CONFIG_ORDER = [
    "conventional",
    "toroidal_low_gap",
    "toroidal_medium_gap",
    "toroidal_high_gap",
]
