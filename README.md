# Toroidal Propeller CFD

Computational Fluid Dynamics (CFD) simulation repository for the study:

> **"Performance Analysis of Toroidal Blade Propellers for Small Fixed-Wing UAVs"**
> Palileo, Sabanal, Delicano & Gregorio — Ateneo de Davao University / Tokyo Institute of Science

This repository reproduces the experimental thrust and efficiency results using:
1. **Blade Element Momentum Theory (BEMT)** — fast Python solver, runs on Google Colab
2. **OpenFOAM CFD** — full 3D RANS simulation with MRF rotating reference frame

---

## Propeller Configurations

| Config | Blade Gap | Gap % of Span | Blade Area (mm²) | Aspect Ratio | Solidity |
|--------|-----------|---------------|------------------|--------------|---------|
| Conventional 2-blade (baseline) | — | — | ~10,600 | ~4.6 | ~0.24 |
| Toroidal Low Gap | 0.5 in (12.7 mm) | 14.3% | 13,983 | 3.74 | 0.20 |
| Toroidal Medium Gap ★ | 1.5 in (38.1 mm) | 42.9% | 10,795 | 4.84 | 0.26 |
| Toroidal High Gap | 2.5 in (63.5 mm) | 71.4% | 8,367 | 6.25 | 0.34 |

★ Best performer in experiments

**Motor:** Surpass Hobby C3536 1050KV | **Propeller diameter:** ~8 inches (203 mm)

---

## Quick Start — Google Colab (BEMT, no install needed)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/rp3gregorio/Propeller-CFD/blob/claude/add-cfd-propeller-simulation-EEQqr/notebooks/01_BEMT_Analysis.ipynb)

```
notebooks/01_BEMT_Analysis.ipynb    ← BEMT solver + comparison plots (Colab-ready)
notebooks/02_OpenFOAM_Setup.ipynb   ← Full CFD setup and execution (installs OpenFOAM)
```

---

## Repository Structure

```
Propeller-CFD/
├── geometry/                          # Parametric propeller geometry
│   ├── naca_airfoil.py                # NACA 4-digit airfoil coordinates
│   ├── propeller_geometry.py          # Base class (lofting, STL export)
│   ├── conventional_propeller.py      # Standard 2-blade propeller
│   ├── toroidal_propeller.py          # Toroidal (closed-loop) propeller
│   └── generate_stl.py                # Generate all 4 STL files
│
├── bemt/                              # Blade Element Momentum Theory solver
│   ├── bemt_solver.py                 # Main BEMT solver (Glauert + Prandtl)
│   ├── propeller_configs.py           # Configuration definitions
│   └── airfoil_polar.py               # NACA 4412 Cl/Cd data
│
├── openfoam/                          # OpenFOAM CFD setup
│   ├── generate_case.py               # Case generator (templates → run dirs)
│   └── templates/
│       ├── static_thrust/             # Static thrust case template
│       │   ├── 0.orig/                # Boundary conditions (V∞=0)
│       │   ├── constant/              # Transport + turbulence + MRF props
│       │   └── system/                # blockMesh + snappyHexMesh + solver
│       └── wind_tunnel/               # Wind tunnel case template (V∞=3/9/15 m/s)
│
├── postprocessing/
│   ├── extract_forces.py              # Parse OpenFOAM force.dat → CSV
│   └── plot_comparison.py             # CFD + BEMT + Experimental plots
│
├── experimental_data/                 # Digitised experimental results
│   ├── static_thrust.csv
│   ├── wind_tunnel_3ms.csv
│   ├── wind_tunnel_9ms.csv
│   ├── wind_tunnel_15ms.csv
│   └── all_experimental.csv
│
├── scripts/
│   ├── setup_all_cases.sh             # Generate all 48 OpenFOAM cases
│   └── run_all_cases.sh               # Execute all cases
│
└── notebooks/
    ├── 01_BEMT_Analysis.ipynb         # BEMT analysis (Colab-compatible)
    └── 02_OpenFOAM_Setup.ipynb        # Full CFD workflow on Colab
```

---

## OpenFOAM Workflow (Local / HPC)

### Prerequisites
- OpenFOAM v2212 (ESI) — [install guide](https://www.openfoam.com/download/openfoam-installation)
- Python ≥ 3.10 with `numpy`, `matplotlib`, `pandas`

### Step-by-step

```bash
# 1. Generate propeller STL geometry
python geometry/generate_stl.py

# 2. Generate all OpenFOAM case directories
bash scripts/setup_all_cases.sh

# 3. Run all cases (add --parallel N for N simultaneous cases)
bash scripts/run_all_cases.sh

# 4. Extract forces from completed cases
python postprocessing/extract_forces.py --runs_dir runs/

# 5. Generate comparison plots
python postprocessing/plot_comparison.py --source both --runs_dir runs/
```

### Single case (example)
```bash
python openfoam/generate_case.py \
    --config toroidal_medium_gap \
    --case_type wind_tunnel \
    --rpm 4000 \
    --v_inf 9 \
    --n_procs 8

cd runs/toroidal_medium_gap_4000rpm_wind_tunnel_9ms
bash Allrun
```

---

## CFD Methodology

| Setting | Value |
|---------|-------|
| Solver | `simpleFoam` (steady-state incompressible RANS) |
| Turbulence model | k-ω SST |
| Rotation model | Multiple Reference Frame (MRF) |
| Near-wall treatment | ω-wall function (y+ ≈ 30–100) |
| Meshing | `blockMesh` + `snappyHexMesh` |
| Domain (static) | Cube 10D × 10D × 10D |
| Domain (wind tunnel) | Box 10D × 10D, 10D upstream + 30D downstream |
| Rotating zone | Cylinder 1.6D diameter × 0.36D height |

### Test conditions matching the paper

| Case type | Wind speeds | RPM range |
|-----------|-------------|-----------|
| Static thrust | 0 m/s | 1000–6000 RPM |
| Wind tunnel | 3, 9, 15 m/s | 1000–6000 RPM |

---

## BEMT Physics

The BEMT solver captures the key aerodynamic difference between toroidal and conventional propellers:

- **Conventional**: Prandtl tip-loss factor applied (F < 1 near blade tips)
- **Toroidal**: Tip-loss factor = 1.0 (connected tips suppress tip vortices)

This is the primary mechanism behind the toroidal propeller's thrust advantage at high RPM.

Additional BEMT features:
- Glauert correction for high axial induction (a > 0.4)
- Newton-Raphson iteration for induction factor convergence
- NACA 4412 polar data with Reynolds number correction

---

## Replacing the Parametric Geometry

The STL geometry files in `geometry/stl/` are generated parametrically from the paper's design parameters. To use your actual CAD models:

1. Export your propeller CAD as STL (ensure units are **metres**)
2. Place the file at `geometry/stl/<config_name>.stl` where `<config_name>` is one of:
   - `conventional.stl`
   - `toroidal_low_gap.stl`
   - `toroidal_medium_gap.stl`
   - `toroidal_high_gap.stl`
3. Re-run `bash scripts/setup_all_cases.sh` to propagate the STL into all cases

---

## Citation

If you use this code, please cite:

```
Palileo, M.A.T., Sabanal, J.A.G., Delicano, J.A., & Gregorio, R.P. III.
"Performance Analysis of Toroidal Blade Propellers for Small Fixed-Wing UAVs"
Department of Aerospace Engineering, Ateneo de Davao University.
Department of Transdisciplinary Science and Engineering, Tokyo Institute of Science.
```
