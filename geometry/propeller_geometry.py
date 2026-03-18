"""
Base propeller geometry class.

Conventions
-----------
- Propeller disk lies in the X-Y plane, rotation axis = Z (positive Z = downstream thrust)
- Blade stations indexed from hub (r = r_hub) to tip (r = r_tip)
- Angles in degrees unless noted
"""

import numpy as np
from geometry.naca_airfoil import get_profile


class PropellerGeometry:
    """
    Base class for parametric propeller geometry.

    Parameters
    ----------
    r_hub : float   hub radius [m]
    r_tip : float   tip radius [m]
    n_blades : int  number of blades
    chord_func : callable   chord(r) -> chord length [m]
    twist_func : callable   twist(r) -> pitch angle [deg]  (local geometric pitch)
    airfoil : str           NACA 4-digit code
    n_radial : int          number of spanwise stations for geometry generation
    n_profile : int         number of chordwise profile points
    """

    # Propeller design parameters (physical, from paper)
    # 8-inch diameter propeller matching C3536 1050KV motor class
    D = 0.2032         # [m] propeller diameter
    R_HUB = 0.0127     # [m] hub radius  (0.5 in)
    R_TIP = 0.1016     # [m] tip radius  (4.0 in)

    def __init__(
        self,
        r_hub: float = R_HUB,
        r_tip: float = R_TIP,
        n_blades: int = 2,
        chord_func=None,
        twist_func=None,
        airfoil: str = "4412",
        n_radial: int = 40,
        n_profile: int = 40,
    ):
        self.r_hub = r_hub
        self.r_tip = r_tip
        self.n_blades = n_blades
        self.airfoil = airfoil
        self.n_radial = n_radial
        self.n_profile = n_profile

        # Default chord: linear taper, root=60mm, tip=35mm (matches ~medium-gap area)
        if chord_func is None:
            self.chord_func = lambda r: np.interp(
                r, [r_hub, r_tip], [0.060, 0.035]
            )
        else:
            self.chord_func = chord_func

        # Default twist: linear, 35° at root → 15° at tip
        if twist_func is None:
            self.twist_func = lambda r: np.interp(
                r, [r_hub, r_tip], [35.0, 15.0]
            )
        else:
            self.twist_func = twist_func

    @property
    def span(self):
        return self.r_tip - self.r_hub

    @property
    def mean_chord(self):
        r = np.linspace(self.r_hub, self.r_tip, 200)
        return np.trapz(self.chord_func(r), r) / self.span

    @property
    def blade_area(self):
        """Projected blade area (one blade) [m²]."""
        r = np.linspace(self.r_hub, self.r_tip, 200)
        return np.trapz(self.chord_func(r), r)

    @property
    def aspect_ratio(self):
        return self.span**2 / self.blade_area

    @property
    def solidity(self):
        """Rotor disk solidity σ = n_blades * blade_area / (π R²)."""
        return self.n_blades * self.blade_area / (np.pi * self.r_tip**2)

    def blade_section(self, r, blade_angle_deg: float = 0.0):
        """
        Return 3D coordinates of one blade cross-section at radius r.

        Parameters
        ----------
        r : float           radial station [m]
        blade_angle_deg : float  azimuthal angle of this blade [deg]

        Returns
        -------
        pts : ndarray (n_profile, 3)   [x, y, z] in propeller frame
        """
        chord = self.chord_func(r)
        twist = self.twist_func(r)

        # 2D airfoil profile (chordwise, thickness)
        xp, zp = get_profile(chord, self.airfoil, self.n_profile)

        # Rotate profile by local pitch angle (twist)
        twist_rad = np.radians(twist)
        xp_rot = xp * np.cos(twist_rad) - zp * np.sin(twist_rad)
        zp_rot = xp * np.sin(twist_rad) + zp * np.cos(twist_rad)

        # Place section at radius r, rotated by blade_angle_deg
        phi = np.radians(blade_angle_deg)
        x3d = r * np.cos(phi) - xp_rot * np.sin(phi)
        y3d = r * np.sin(phi) + xp_rot * np.cos(phi)
        z3d = zp_rot

        return np.column_stack([x3d, y3d, z3d])

    def radial_stations(self):
        """Array of radial stations from hub to tip."""
        return np.linspace(self.r_hub, self.r_tip, self.n_radial)

    def _loft_sections(self, sections):
        """
        Triangulate a lofted surface from a list of cross-section arrays.
        Each section must have the same number of points.

        Returns list of (v0, v1, v2, normal) tuples.
        """
        triangles = []
        n_sec = len(sections)
        n_pts = sections[0].shape[0]

        for i in range(n_sec - 1):
            s0 = sections[i]
            s1 = sections[i + 1]
            for j in range(n_pts - 1):
                # Two triangles per quad
                v00 = s0[j]
                v01 = s0[j + 1]
                v10 = s1[j]
                v11 = s1[j + 1]

                for tri in [(v00, v10, v01), (v10, v11, v01)]:
                    n = np.cross(tri[1] - tri[0], tri[2] - tri[0])
                    norm = np.linalg.norm(n)
                    if norm > 1e-12:
                        triangles.append((tri[0], tri[1], tri[2], n / norm))

        return triangles

    def _write_stl(self, triangles, filepath: str, solid_name: str = "propeller"):
        """Write triangle list to ASCII STL file."""
        with open(filepath, "w") as f:
            f.write(f"solid {solid_name}\n")
            for v0, v1, v2, n in triangles:
                f.write(
                    f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n"
                    f"    outer loop\n"
                    f"      vertex {v0[0]:.6e} {v0[1]:.6e} {v0[2]:.6e}\n"
                    f"      vertex {v1[0]:.6e} {v1[1]:.6e} {v1[2]:.6e}\n"
                    f"      vertex {v2[0]:.6e} {v2[1]:.6e} {v2[2]:.6e}\n"
                    f"    endloop\n"
                    f"  endfacet\n"
                )
            f.write(f"endsolid {solid_name}\n")

    def generate_stl(self, filepath: str):
        raise NotImplementedError("Subclasses must implement generate_stl()")
