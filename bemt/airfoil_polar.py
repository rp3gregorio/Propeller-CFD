"""
Airfoil polar data for propeller blade element analysis.

NACA 4412 lift and drag coefficients as functions of angle of attack [deg].
Data derived from XFOIL calculations at Re = 100,000 – 500,000,
representative of small UAV propeller blade elements.

The `cl_cd` function interpolates linearly between table values.
"""

import numpy as np

# -----------------------------------------------------------------
# NACA 4412 polar table  [alpha_deg, Cl, Cd]
# Re = 200,000 (typical mid-span blade element at moderate RPM)
# -----------------------------------------------------------------
_POLAR_NACA4412 = np.array([
    # alpha   Cl       Cd
    [-10.0, -0.750,  0.0250],
    [ -8.0, -0.540,  0.0180],
    [ -6.0, -0.340,  0.0120],
    [ -4.0, -0.120,  0.0095],
    [ -2.0,  0.100,  0.0082],
    [  0.0,  0.320,  0.0075],
    [  2.0,  0.530,  0.0075],
    [  4.0,  0.740,  0.0080],
    [  6.0,  0.940,  0.0090],
    [  8.0,  1.130,  0.0110],
    [ 10.0,  1.280,  0.0140],
    [ 12.0,  1.380,  0.0190],
    [ 14.0,  1.390,  0.0300],
    [ 16.0,  1.300,  0.0600],
    [ 18.0,  1.100,  0.1000],
    [ 20.0,  0.900,  0.1500],
])

_alpha = _POLAR_NACA4412[:, 0]
_cl    = _POLAR_NACA4412[:, 1]
_cd    = _POLAR_NACA4412[:, 2]


def get_cl_cd(alpha_deg: float, re: float = 200_000) -> tuple[float, float]:
    """
    Return (Cl, Cd) for NACA 4412 at given angle of attack.

    Parameters
    ----------
    alpha_deg : float  angle of attack [deg]
    re        : float  Reynolds number (used for Cd scaling at low Re)

    Returns
    -------
    cl : float
    cd : float
    """
    # Simple Re correction for Cd (Prandtl-Schlichting flat-plate analogy)
    re_ref = 200_000.0
    re_factor = (re_ref / max(re, 1e4)) ** 0.2

    cl = float(np.interp(alpha_deg, _alpha, _cl))
    cd = float(np.interp(alpha_deg, _alpha, _cd)) * re_factor

    return cl, cd


def get_cl_cd_array(alpha_arr: np.ndarray, re: float = 200_000) -> tuple[np.ndarray, np.ndarray]:
    """Vectorised version of get_cl_cd."""
    re_ref = 200_000.0
    re_factor = (re_ref / max(re, 1e4)) ** 0.2

    cl = np.interp(alpha_arr, _alpha, _cl)
    cd = np.interp(alpha_arr, _alpha, _cd) * re_factor
    return cl, cd
