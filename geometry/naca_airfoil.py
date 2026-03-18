"""
NACA 4-digit airfoil coordinate generator.
Used to define cross-sectional profiles for propeller blade elements.
"""

import numpy as np


def naca4(code: str, n_points: int = 100, closed_te: bool = True):
    """
    Generate NACA 4-digit airfoil coordinates.

    Parameters
    ----------
    code : str  e.g. '4412'
    n_points : int  number of points per surface (upper + lower)
    closed_te : bool  force closed trailing edge

    Returns
    -------
    xu, zu : upper surface x, z  (chord-normalised, [0,1])
    xl, zl : lower surface x, z
    """
    m = int(code[0]) / 100.0   # max camber
    p = int(code[1]) / 10.0    # max camber position
    t = int(code[2:]) / 100.0  # max thickness

    # Cosine spacing for denser points near LE/TE
    beta = np.linspace(0, np.pi, n_points)
    x = (1 - np.cos(beta)) / 2.0

    # Thickness distribution (NACA 4-series formula)
    yt = (t / 0.20) * (
        0.2969 * np.sqrt(x)
        - 0.1260 * x
        - 0.3516 * x**2
        + 0.2843 * x**3
        - (0.1015 if closed_te else 0.1036) * x**4
    )

    # Camber line
    yc = np.where(
        x <= p,
        (m / p**2) * (2 * p * x - x**2),
        (m / (1 - p) ** 2) * ((1 - 2 * p) + 2 * p * x - x**2),
    )

    # Camber gradient
    dyc_dx = np.where(
        x <= p,
        (2 * m / p**2) * (p - x),
        (2 * m / (1 - p) ** 2) * (p - x),
    )

    theta = np.arctan(dyc_dx)

    xu = x - yt * np.sin(theta)
    zu = yc + yt * np.cos(theta)
    xl = x + yt * np.sin(theta)
    zl = yc - yt * np.cos(theta)

    return xu, zu, xl, zl


def naca4_coords(code: str = "4412", n_points: int = 100):
    """
    Return combined upper+lower coordinates as (x, z) arrays going
    from TE → upper surface → LE → lower surface → TE (closed loop).
    """
    xu, zu, xl, zl = naca4(code, n_points)
    # Upper: TE→LE, lower: LE→TE
    x = np.concatenate([xu[::-1], xl[1:]])
    z = np.concatenate([zu[::-1], zl[1:]])
    return x, z


def get_profile(chord: float, code: str = "4412", n_points: int = 50):
    """
    Return (x, z) profile scaled to given chord length [m].
    Profile is centred at the quarter-chord point.
    """
    x_norm, z_norm = naca4_coords(code, n_points)
    x = (x_norm - 0.25) * chord   # shift LE to x=-0.25c
    z = z_norm * chord
    return x, z
