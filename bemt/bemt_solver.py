"""
Blade Element Momentum Theory (BEMT) solver for propeller thrust and torque.

Implements:
  - Classical BEM iteration with Glauert correction for high inflow
  - Prandtl tip-loss factor (switchable — set to 1.0 for toroidal propellers)
  - Sweep over RPM and advance ratios to produce performance polars

Reference: Leishman, J.G. (2006) "Principles of Helicopter Aerodynamics"
           Branlard (2017) "Wind Turbine Aerodynamics and Vorticity-Based Methods"

Usage
-----
    from bemt.bemt_solver import BEMTSolver
    from bemt.propeller_configs import CONFIGS

    solver = BEMTSolver(CONFIGS["toroidal_medium_gap"])
    results = solver.sweep_rpm(rpm_range=range(1000, 6001, 500), V_inf=0.0)
"""

import numpy as np
from bemt.airfoil_polar import get_cl_cd_array
from bemt.propeller_configs import RHO_AIR, NU_AIR


class BEMTSolver:
    """
    Blade Element Momentum Theory solver.

    Parameters
    ----------
    config : dict   propeller configuration dict (from propeller_configs.CONFIGS)
    rho    : float  air density [kg/m³]
    nu     : float  kinematic viscosity [m²/s]
    n_sections : int  number of radial blade elements
    """

    def __init__(
        self,
        config: dict,
        rho: float = RHO_AIR,
        nu: float = NU_AIR,
        n_sections: int = 50,
    ):
        self.cfg = config
        self.rho = rho
        self.nu = nu
        self.n_sections = n_sections

        self.r_hub    = config["r_hub"]
        self.r_tip    = config["r_tip"]
        self.n_blades = config["n_blades"]
        self.chord_fn = config["chord_func"]
        self.twist_fn = config["twist_func"]
        self.use_tip_loss = config.get("tip_loss", True)
        self.is_toroidal  = config.get("toroidal", False)

        # Radial stations (Gauss-Legendre quadrature would be better, but
        # uniform is sufficient for n_sections ≥ 40)
        r_frac = np.linspace(0.05, 0.975, n_sections)   # avoid singularities at hub/tip
        self.r = self.r_hub + r_frac * (self.r_tip - self.r_hub)
        self.dr = (self.r_tip - self.r_hub) / n_sections

        self.chord = self.chord_fn(self.r)
        self.twist = self.twist_fn(self.r)   # [deg]

    # ──────────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────────

    def solve(self, rpm: float, V_inf: float = 0.0) -> dict:
        """
        Solve for thrust and torque at given RPM and freestream velocity.

        Returns
        -------
        dict with keys:
          T    [N]   thrust
          Q    [N·m] torque
          P    [W]   power
          CT         thrust coefficient
          CQ         torque coefficient
          CP         power coefficient
          J          advance ratio
          eta        propulsive efficiency
          dT  [N/m]  thrust per unit span (array)
          dQ [N·m/m] torque per unit span (array)
        """
        omega = rpm * 2 * np.pi / 60.0    # [rad/s]
        n_rps = rpm / 60.0                # [rev/s]
        D     = 2 * self.r_tip            # propeller diameter

        a, a_prime = self._solve_induction(omega, V_inf)

        Vt = omega * self.r * (1 + a_prime)     # tangential velocity seen by blade
        Va = V_inf + a * omega * self.r          # axial velocity seen by blade (approximation)
        # More precise: Va = V_inf*(1+a) for momentum theory
        # Here use Va = V_inf + a * omega * self.r for consistency

        # Use standard BEMT axial inflow
        Va = V_inf * (1.0 + a) if V_inf > 0 else a * omega * self.r

        V_rel = np.sqrt(Va**2 + Vt**2)           # relative velocity
        phi   = np.arctan2(Va, Vt)                # inflow angle [rad]
        alpha = np.radians(self.twist) - phi      # angle of attack [rad]
        alpha_deg = np.degrees(alpha)

        # Reynolds number at each section
        re = V_rel * self.chord / self.nu

        Cl, Cd = get_cl_cd_array(alpha_deg, re.mean())

        # Prandtl tip-loss factor
        F = self._tip_loss(phi, omega, V_inf)

        # Differential thrust and torque per unit span [per blade]
        dT = F * 0.5 * self.rho * V_rel**2 * self.chord * (
            Cl * np.cos(phi) - Cd * np.sin(phi)
        )
        dQ = F * 0.5 * self.rho * V_rel**2 * self.chord * (
            Cl * np.sin(phi) + Cd * np.cos(phi)
        ) * self.r

        T = self.n_blades * np.trapz(dT, self.r)
        Q = self.n_blades * np.trapz(dQ, self.r)
        P = Q * omega

        # Non-dimensional coefficients (using n in rev/s convention)
        rho, n, D = self.rho, n_rps, D
        CT  = T  / (rho * n**2 * D**4)
        CQ  = Q  / (rho * n**2 * D**5)
        CP  = P  / (rho * n**3 * D**5)
        J   = V_inf / (n * D) if n > 0 else 0.0
        eta = J * CT / CP if CP > 1e-9 else 0.0

        return {
            "T":   T,
            "Q":   Q,
            "P":   P,
            "CT":  CT,
            "CQ":  CQ,
            "CP":  CP,
            "J":   J,
            "eta": eta,
            "dT":  dT,
            "dQ":  dQ,
            "r":   self.r,
        }

    def sweep_rpm(
        self,
        rpm_range=range(1000, 6001, 500),
        V_inf: float = 0.0,
    ) -> dict:
        """
        Sweep over a range of RPM values.

        Returns
        -------
        dict of arrays: rpm, T, Q, P, CT, CQ, CP, J, eta
        """
        rpms = list(rpm_range)
        keys = ["T", "Q", "P", "CT", "CQ", "CP", "J", "eta"]
        results = {k: [] for k in keys}
        results["rpm"] = rpms

        for rpm in rpms:
            r = self.solve(rpm, V_inf)
            for k in keys:
                results[k].append(r[k])

        for k in keys:
            results[k] = np.array(results[k])

        return results

    def sweep_advance(
        self,
        rpm: float,
        J_range=np.linspace(0, 0.8, 30),
    ) -> dict:
        """
        Sweep over advance ratio at fixed RPM by varying V_inf.

        Returns
        -------
        dict of arrays: J, V_inf, T, Q, P, CT, CQ, CP, eta
        """
        n_rps = rpm / 60.0
        D = 2 * self.r_tip
        keys = ["T", "Q", "P", "CT", "CQ", "CP", "J", "eta", "V_inf"]
        results = {k: [] for k in keys}

        for J in J_range:
            V = J * n_rps * D
            r = self.solve(rpm, V)
            for k in ["T", "Q", "P", "CT", "CQ", "CP", "J", "eta"]:
                results[k].append(r[k])
            results["V_inf"].append(V)

        for k in keys:
            results[k] = np.array(results[k])

        return results

    # ──────────────────────────────────────────────────────────────────────
    # Internal methods
    # ──────────────────────────────────────────────────────────────────────

    def _solve_induction(self, omega: float, V_inf: float, n_iter: int = 50):
        """
        Iterative BEMT induction factor solution using the Newton-Raphson
        approach from the paper (12 iterations to convergence).

        Returns
        -------
        a      : axial induction factor  (array, per radial station)
        a_prime: tangential induction factor (array)
        """
        r    = self.r
        c    = self.chord
        B    = self.n_blades

        # Blade element local solidity
        sigma = B * c / (2 * np.pi * r)

        a      = np.zeros(len(r))
        a_prime = np.zeros(len(r))

        for _ in range(n_iter):
            # Local velocities
            if V_inf > 0:
                Va = V_inf * (1 + a)
            else:
                Va = a * omega * r + 1e-6   # static thrust: Va ~ induced velocity

            Vt  = omega * r * (1 - a_prime)
            phi = np.arctan2(Va, Vt)        # inflow angle [rad]

            alpha_deg = self.twist - np.degrees(phi)
            re = np.sqrt(Va**2 + Vt**2) * c / self.nu

            Cl, Cd = get_cl_cd_array(alpha_deg, re.mean())

            # Prandtl tip-loss factor
            F = self._tip_loss(phi, omega, V_inf)
            F = np.maximum(F, 0.01)

            # Normal and tangential force coefficients
            Cn = Cl * np.cos(phi) + Cd * np.sin(phi)
            Ct_blade = Cl * np.sin(phi) - Cd * np.cos(phi)

            # Updated induction factors (momentum theory)
            denom_a  = (4 * F * np.sin(phi)**2) / (sigma * Cn) + 1
            denom_ap = (4 * F * np.sin(phi) * np.cos(phi)) / (sigma * Ct_blade) - 1

            a_new      = 1.0 / denom_a
            a_prime_new = 1.0 / denom_ap if np.all(np.abs(denom_ap) > 1e-6) else np.zeros_like(r)

            # Glauert correction for high inflow (a > 0.4)
            a_new = self._glauert_correction(a_new)

            # Relaxation for stability
            a      = 0.5 * a + 0.5 * a_new
            a_prime = 0.5 * a_prime + 0.5 * np.clip(a_prime_new, -0.5, 0.5)

        return a, a_prime

    def _tip_loss(self, phi: np.ndarray, omega: float, V_inf: float) -> np.ndarray:
        """
        Prandtl tip-loss factor.
        For toroidal propellers, returns 1.0 (no tip loss — connected tips
        suppress the tip vortex, which is the key advantage of the toroidal design).
        """
        if not self.use_tip_loss or self.is_toroidal:
            return np.ones(len(self.r))

        B = self.n_blades
        r = self.r
        R = self.r_tip

        # Guard against zero phi
        phi_safe = np.maximum(np.abs(phi), 1e-4) * np.sign(phi + 1e-10)

        f = (B / 2.0) * (R - r) / (r * np.abs(np.sin(phi_safe)))
        F = (2.0 / np.pi) * np.arccos(np.exp(-f))
        return np.maximum(F, 0.01)

    @staticmethod
    def _glauert_correction(a: np.ndarray) -> np.ndarray:
        """
        Glauert empirical correction for high axial induction (a > 0.4).
        Uses the Buhl modification to prevent non-physical divergence.
        """
        a_out = a.copy()
        high = a > 0.4
        CT_high = 8.0 / 9.0 + (4.0 * a[high] - 40.0 / 9.0) * a[high]
        a_out[high] = (18.0 * a[high] - 20.0 - 3.0 * np.sqrt(CT_high * (50.0 - 36.0 * a[high]) + 12.0 * a[high] * (3.0 * a[high] - 4.0))) / (36.0 * a[high] - 50.0)
        return np.clip(a_out, 0, 0.9)
