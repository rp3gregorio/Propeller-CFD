"""
Conventional 2-blade fixed-pitch propeller geometry.
Used as the baseline comparison against the toroidal designs.
"""

import numpy as np
from geometry.propeller_geometry import PropellerGeometry


class ConventionalPropeller(PropellerGeometry):
    """
    Standard 2-blade propeller with open (non-connected) blade tips.

    The geometry is the same as the radial portion of the toroidal propeller
    but without the tip arc connection.
    """

    def __init__(self, **kwargs):
        kwargs.setdefault("n_blades", 2)
        super().__init__(**kwargs)

    def generate_stl(self, filepath: str):
        """
        Generate STL surface mesh for one full revolution of the conventional
        propeller (all blades).
        """
        all_triangles = []
        blade_angles = np.linspace(0, 360, self.n_blades, endpoint=False)

        for blade_angle in blade_angles:
            triangles = self._generate_blade_triangles(blade_angle)
            all_triangles.extend(triangles)

        self._write_stl(all_triangles, filepath, "conventional_propeller")
        print(f"[STL] Written {len(all_triangles)} triangles → {filepath}")

    def _generate_blade_triangles(self, blade_angle_deg: float):
        """Generate surface triangles for one blade at given azimuthal angle."""
        r_stations = self.radial_stations()
        sections = [
            self.blade_section(r, blade_angle_deg) for r in r_stations
        ]

        triangles = self._loft_sections(sections)

        # Add end caps (hub and tip discs) — simplified as fan triangles
        triangles += self._end_cap(sections[0])   # hub cap
        triangles += self._end_cap(sections[-1])  # tip cap

        return triangles

    def _end_cap(self, section_pts):
        """Close the end of a blade section with a fan of triangles."""
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
