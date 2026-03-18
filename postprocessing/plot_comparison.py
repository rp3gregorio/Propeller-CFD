"""
Plot CFD (OpenFOAM / BEMT) results vs experimental data.

Generates:
  1. Thrust vs RPM  (static thrust, all 4 configurations)
  2. Thrust vs RPM  (wind tunnel at 3, 9, 15 m/s)
  3. CT vs J       (advance ratio sweep)
  4. CP vs J
  5. Efficiency vs J

Usage
-----
    # BEMT only (no OpenFOAM needed)
    python postprocessing/plot_comparison.py --source bemt

    # OpenFOAM results
    python postprocessing/plot_comparison.py --source cfd --runs_dir runs/

    # Both overlaid
    python postprocessing/plot_comparison.py --source both --runs_dir runs/
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from bemt.bemt_solver import BEMTSolver
from bemt.propeller_configs import CONFIGS, CONFIG_ORDER

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "results")
PLOTS_DIR   = os.path.join(os.path.dirname(__file__), "..", "results", "plots")
EXP_DIR     = os.path.join(os.path.dirname(__file__), "..", "experimental_data")

RPM_RANGE = list(range(1000, 6001, 500))
WIND_SPEEDS = [0.0, 3.0, 9.0, 15.0]


# ─────────────────────────────────────────────────────────────────────────────
# BEMT sweep
# ─────────────────────────────────────────────────────────────────────────────

def run_bemt_sweep():
    """Run BEMT for all configs and wind speeds."""
    bemt_results = {}
    for name in CONFIG_ORDER:
        cfg = CONFIGS[name]
        solver = BEMTSolver(cfg, n_sections=60)
        bemt_results[name] = {}
        for v in WIND_SPEEDS:
            res = solver.sweep_rpm(RPM_RANGE, V_inf=v)
            bemt_results[name][v] = res
    return bemt_results


# ─────────────────────────────────────────────────────────────────────────────
# Plotting helpers
# ─────────────────────────────────────────────────────────────────────────────

def _style(name):
    cfg = CONFIGS[name]
    return dict(
        color=cfg["color"],
        linestyle=cfg["linestyle"],
        marker=cfg["marker"],
        label=cfg["label"],
        markevery=2,
        markersize=5,
        linewidth=1.5,
    )


def plot_thrust_vs_rpm(bemt_results, exp_data=None, v_inf=0.0, ax=None, show_exp=True):
    """Static or wind-tunnel thrust vs RPM for all 4 configs."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 5))

    for name in CONFIG_ORDER:
        res = bemt_results[name][v_inf]
        ax.plot(res["rpm"], res["T"] / 9.81 * 1000, **_style(name))

    if show_exp and exp_data is not None:
        _plot_exp_thrust(ax, exp_data, v_inf)

    title = f"Static Thrust" if v_inf == 0 else f"Thrust at V∞ = {v_inf:.0f} m/s"
    ax.set_title(title)
    ax.set_xlabel("RPM")
    ax.set_ylabel("Thrust [gf]")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(1000, 6000)
    ax.set_ylim(bottom=0)
    return ax


def plot_ct_vs_j(bemt_results, ax=None):
    """CT vs J for a representative RPM (4000 RPM)."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 5))

    rpm_ref = 4000
    J_range = np.linspace(0.0, 0.8, 40)
    for name in CONFIG_ORDER:
        cfg = CONFIGS[name]
        solver = BEMTSolver(cfg, n_sections=60)
        res = solver.sweep_advance(rpm_ref, J_range)
        ax.plot(res["J"], res["CT"], **_style(name))

    ax.set_title(f"CT vs Advance Ratio J  (RPM = {rpm_ref})")
    ax.set_xlabel("Advance ratio J")
    ax.set_ylabel("Thrust coefficient CT")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    return ax


def plot_efficiency_vs_j(bemt_results, ax=None):
    """Propulsive efficiency vs J at 4000 RPM."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 5))

    rpm_ref = 4000
    J_range = np.linspace(0.05, 0.75, 40)
    for name in CONFIG_ORDER:
        cfg = CONFIGS[name]
        solver = BEMTSolver(cfg, n_sections=60)
        res = solver.sweep_advance(rpm_ref, J_range)
        ax.plot(res["J"], np.clip(res["eta"], 0, 1), **_style(name))

    ax.set_title(f"Propulsive Efficiency η vs J  (RPM = {rpm_ref})")
    ax.set_xlabel("Advance ratio J")
    ax.set_ylabel("Efficiency η")
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)
    return ax


def _plot_exp_thrust(ax, exp_data: pd.DataFrame, v_inf: float):
    """Overlay experimental scatter points."""
    subset = exp_data[np.isclose(exp_data["v_inf_ms"], v_inf, atol=0.5)]
    config_map = {
        "conventional"         : ("Exp Conv",    "k", "o"),
        "toroidal_low_gap"     : ("Exp LG",      "b", "s"),
        "toroidal_medium_gap"  : ("Exp MG",      "r", "^"),
        "toroidal_high_gap"    : ("Exp HG",      "g", "D"),
    }
    for cfg_key, (label, color, marker) in config_map.items():
        rows = subset[subset["config"] == cfg_key]
        if not rows.empty:
            ax.scatter(
                rows["rpm"], rows["T_gf"],
                color=color, marker=marker, s=40,
                zorder=5, label=f"{label} (exp)",
                facecolors="none", linewidths=1.5,
            )


def make_summary_figure(bemt_results, exp_data=None, output_path=None):
    """4-panel summary: static + 3 wind speeds."""
    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    fig.suptitle(
        "Toroidal vs Conventional Propeller — Thrust Performance\n"
        "(BEMT predictions vs experimental data)",
        fontsize=13,
    )

    for ax, v in zip(axes.flat, WIND_SPEEDS):
        plot_thrust_vs_rpm(bemt_results, exp_data, v_inf=v, ax=ax, show_exp=True)

    handles, labels = axes[0, 0].get_legend_handles_labels()
    for ax in axes.flat:
        ax.get_legend().remove()

    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8,
               bbox_to_anchor=(0.5, 0.01))
    plt.tight_layout(rect=[0, 0.07, 1, 0.96])

    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"  Saved: {output_path}")
    return fig


def overlay_cfd(ax, cfd_df: pd.DataFrame, v_inf: float):
    """Overlay OpenFOAM CFD points on a thrust-vs-RPM plot."""
    subset = cfd_df[np.isclose(cfd_df["v_inf_ms"], v_inf, atol=0.5)]
    for name in CONFIG_ORDER:
        cfg = CONFIGS[name]
        rows = subset[subset["config"] == name]
        if not rows.empty:
            ax.scatter(
                rows["rpm"], rows["T_gf"],
                color=cfg["color"], marker="*", s=120,
                zorder=6, label=f"{cfg['short_name']} (CFD)",
            )


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main(source="bemt", runs_dir=None):
    os.makedirs(PLOTS_DIR, exist_ok=True)

    print("Running BEMT sweep...")
    bemt_results = run_bemt_sweep()

    # Load experimental data if available
    exp_data = None
    exp_file = os.path.join(EXP_DIR, "all_experimental.csv")
    if os.path.isfile(exp_file):
        exp_data = pd.read_csv(exp_file)
        print(f"Loaded experimental data: {len(exp_data)} rows")

    # Load CFD data if requested
    cfd_df = None
    if source in ("cfd", "both") and runs_dir:
        cfd_file = os.path.join(RESULTS_DIR, "cfd_results.csv")
        if os.path.isfile(cfd_file):
            cfd_df = pd.read_csv(cfd_file)
            print(f"Loaded CFD results: {len(cfd_df)} rows")
        else:
            print("CFD results not found. Run extract_forces.py first.")

    # ── Figure 1: Summary thrust plots ──────────────────────────────
    fig1_path = os.path.join(PLOTS_DIR, "thrust_comparison.png")
    make_summary_figure(bemt_results, exp_data, fig1_path)

    # ── Figure 2: CT vs J ───────────────────────────────────────────
    fig2, ax2 = plt.subplots(figsize=(7, 5))
    plot_ct_vs_j(bemt_results, ax2)
    fig2.savefig(os.path.join(PLOTS_DIR, "CT_vs_J.png"), dpi=150, bbox_inches="tight")
    print(f"  Saved: {os.path.join(PLOTS_DIR, 'CT_vs_J.png')}")

    # ── Figure 3: Efficiency vs J ────────────────────────────────────
    fig3, ax3 = plt.subplots(figsize=(7, 5))
    plot_efficiency_vs_j(bemt_results, ax3)
    fig3.savefig(os.path.join(PLOTS_DIR, "efficiency_vs_J.png"), dpi=150, bbox_inches="tight")
    print(f"  Saved: {os.path.join(PLOTS_DIR, 'efficiency_vs_J.png')}")

    # ── Figure 4: CFD overlay (if available) ────────────────────────
    if cfd_df is not None:
        fig4, axes4 = plt.subplots(2, 2, figsize=(13, 9))
        fig4.suptitle("CFD (OpenFOAM ★) vs BEMT (lines) vs Experiment (○△□◇)")
        for ax, v in zip(axes4.flat, WIND_SPEEDS):
            plot_thrust_vs_rpm(bemt_results, exp_data, v_inf=v, ax=ax)
            overlay_cfd(ax, cfd_df, v)
        plt.tight_layout()
        fig4_path = os.path.join(PLOTS_DIR, "cfd_vs_bemt_vs_exp.png")
        fig4.savefig(fig4_path, dpi=150, bbox_inches="tight")
        print(f"  Saved: {fig4_path}")

    print(f"\nAll plots saved to: {PLOTS_DIR}")
    plt.close("all")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=["bemt", "cfd", "both"], default="bemt")
    parser.add_argument("--runs_dir", default=None)
    args = parser.parse_args()
    main(args.source, args.runs_dir)
