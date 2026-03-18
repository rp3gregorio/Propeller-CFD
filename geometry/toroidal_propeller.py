"""
Toroidal blade propeller geometry generator.

The toroidal propeller consists of two conventional blade halves whose tips
are connected by a smooth arc, forming a closed-loop structure.
The 'blade gap' is the axial (z-axis) distance between the two arcs at
the outermost radius — this is the key design variable from the paper.

Three configurations are implemented:
  - Low gap  : 0.5 in = 12.7 mm  (≈14% of blade span)
  - Medium gap: 1.5 in = 38.1 mm  (≈43% of blade span)
  - High gap  : 2.5 in = 63.5 mm  (≈71% of blade span)
"""

import numpy as np
from geometry.propeller_geometry import PropellerGeometry


class ToroidalPropeller(PropellerGeometry):
    """
    Toroidal (closed-loop) 2-blade propeller.

    Parameters
    ----------
    blade_gap : float   axial gap at the tip connection [m]
                        Low=0.0127, Medium=0.0381, High=0.0635
    n_arc     : int     number of sections in the tip-arc connector
    All other parameters inherited from PropellerGeometry.
    """

    # Gap presets (from paper)
    GAP_LOW    = 0.0127   # 0.5 in
    GAP_MEDIUM = 0.0381   # 1.5 in
    GAP_HIGH   = 0.0635   # 2.5 in

    def __init__(self, blade_gap: float = GAP_MEDIUM, n_arc: int = 12, **kwargs):
        kwargs.setdefault("n_blades", 2)
        super().__init__(**kwargs)
        self.blade_gap = blade_gap
        self.n_arc = n_arc

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_stl(self, filepath: str):
        """Generate full toroidal propeller STL."""
        all_triangles = []

        # Two blades at 0° and 180°
        blade_angles = [0.0, 180.0]

        for blade_angle in blade_angles:
            # Blade 1: z goes from 0 to +half_gap  (upper half)
            # Blade 2: z goes from 0 to -half_gap  (lower half, same blade_angle+180°)
            # Each blade is the "radial" sweep; tip arcs connect the two blades
            all_triangles.extend(self._blade_triangles(blade_angle, z_sign=+1))

        # Two tip arcs (at 0° and 180°) connecting the blade tips
        all_triangles.extend(self._arc_triangles(0.0))
        all_triangles.extend(self._arc_triangles(180.0))

        # Hub discs (close the root ends)
        all_triangles.extend(self._hub_ring())

        self._write_stl(all_triangles, filepath, "toroidal_propeller")
        print(
            f"[STL] Toroidal propeller (gap={self.blade_gap*1000:.1f} mm) "
            f"— {len(all_triangles)} triangles → {filepath}"
        )

    # ------------------------------------------------------------------
    # Internal geometry builders
    # ------------------------------------------------------------------

    def _blade_triangles(self, blade_angle_deg: float, z_sign: float):
        """
        Radial sweep of one blade half.

        The blade sits at azimuthal angle blade_angle_deg.
        z_sign = +1 for the forward (upper) blade, -1 for the aft (lower) blade.
        The two halves are connected at the tip via the arc.
        """
        r_stations = self.radial_stations()
        half_gap = self.blade_gap / 2.0
        sections = []

        for r in r_stations:
            chord = self.chord_func(r)
            twist = self.twist_func(r)

            # Fraction along the blade (0=hub, 1=tip)
            frac = (r - self.r_hub) / self.span

            # Z position: linearly interpolate from 0 at hub to ±half_gap at tip
            z_offset = z_sign * frac * half_gap

            xp, zp = self._profile_2d(chord, twist)

            # Translate z by z_offset
            phi = np.radians(blade_angle_deg)
            x3d = r * np.cos(phi) - xp * np.sin(phi)
            y3d = r * np.sin(phi) + xp * np.cos(phi)
            z3d = zp + z_offset

            sections.append(np.column_stack([x3d, y3d, z3d]))

        triangles = self._loft_sections(sections)
        # Hub cap
        triangles += self._end_cap(sections[0])
        return triangles

    def _arc_triangles(self, blade_angle_deg: float):
        """
        Smooth circular arc connecting the two blade tips at blade_angle_deg
        and blade_angle_deg + 180°.

        The arc sweeps in the z-direction from +half_gap to -half_gap
        at the tip radius, forming the toroidal connection.
        """
        half_gap = self.blade_gap / 2.0
        r_tip = self.r_tip
        phi = np.radians(blade_angle_deg)
        chord_tip = self.chord_func(r_tip)
        twist_tip = self.twist_func(r_tip)

        # Arc parameterisation: theta goes from π/2 to -π/2 (upper → lower)
        theta_vals = np.linspace(np.pi / 2, -np.pi / 2, self.n_arc + 1)

        # Arc centre is at the tip radius, z=0
        arc_radius = half_gap   # radius of the connecting arc in the r-z plane

        sections = []
        for theta in theta_vals:
            # Radial offset due to arc (the blade tip curves slightly inward)
            r_arc = r_tip - arc_radius * (1 - np.cos(theta))
            z_arc = arc_radius * np.sin(theta)

            xp, zp = self._profile_2d(chord_tip, twist_tip)

            x3d = r_arc * np.cos(phi) - xp * np.sin(phi)
            y3d = r_arc * np.sin(phi) + xp * np.cos(phi)
            z3d = zp + z_arc

            sections.append(np.column_stack([x3d, y3d, z3d]))

        return self._loft_sections(sections)

    def _hub_ring(self):
        """
        Close the hub ends of both blades with simple triangulated caps.
        This prevents OpenFOAM from complaining about open surfaces.
        """
        triangles = []
        r = self.r_hub
        half_gap = self.blade_gap / 2.0
        chord = self.chord_func(r)
        twist = self.twist_func(r)
        xp, zp = self._profile_2d(chord, twist)

        for blade_angle, z_sign in [(0.0, +1), (180.0, -1)]:
            phi = np.radians(blade_angle)
            z_off = z_sign * 0.0  # hub is at z=0

            x3d = r * np.cos(phi) - xp * np.sin(phi)
            y3d = r * np.sin(phi) + xp * np.cos(phi)
            z3d = zp + z_off
            section = np.column_stack([x3d, y3d, z3d])
            triangles.extend(self._end_cap(section))

        return triangles

    def _profile_2d(self, chord: float, twist_deg: float):
        """Return 2D airfoil profile (chordwise x, thickness z), rotated by twist."""
        from geometry.naca_airfoil import get_profile

        xp, zp = get_profile(chord, self.airfoil, self.n_profile)

        twist_rad = np.radians(twist_deg)
        xp_rot = xp * np.cos(twist_rad) - zp * np.sin(twist_rad)
        zp_rot = xp * np.sin(twist_rad) + zp * np.cos(twist_rad)

        return xp_rot, zp_rot

    def _end_cap(self, section_pts):
        """Fan-triangulate an end cap for a section."""
        centre = section_pts.mean(axis=0)
        triangles = []
        n = len(section_pts)
        for i in range(n - 1):
            v0 = section_pts[i]
            v1 = section_pts[i + 1]
            edge = v1 - v0
            to_c = centre - v0
            normal = np.cross(edge, to_c)
            norm = np.linalg.norm(normal)
            if norm > 1e-12:
                triangles.append((centre, v0, v1, normal / norm))
        return triangles
