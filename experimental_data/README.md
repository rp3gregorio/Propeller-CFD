# Experimental Data

This directory contains tabulated experimental results from the paper:

> Palileo, M.A.T., Sabanal, J.A.G., Delicano, J.A., & Gregorio, R.P. III.
> "Performance Analysis of Toroidal Blade Propellers for Small Fixed-Wing UAVs"
> Ateneo de Davao University / Tokyo Institute of Science.

## Files

| File | Description |
|------|-------------|
| `static_thrust.csv` | Static thrust (V∞=0) vs RPM for all 4 configs |
| `wind_tunnel_3ms.csv` | Thrust and efficiency at V∞=3 m/s |
| `wind_tunnel_9ms.csv` | Thrust and efficiency at V∞=9 m/s |
| `wind_tunnel_15ms.csv` | Thrust and efficiency at V∞=15 m/s |
| `all_experimental.csv` | All data combined (used by plot scripts) |

## Columns

- `config` — propeller configuration (`conventional`, `toroidal_low_gap`, `toroidal_medium_gap`, `toroidal_high_gap`)
- `rpm` — rotational speed [RPM]
- `v_inf_ms` — freestream velocity [m/s]
- `T_gf` — measured thrust [gram-force]
- `T_N` — measured thrust [Newton]
- `CT` — thrust coefficient  CT = T / (ρ n² D⁴)
- `CP` — power coefficient   CP = P / (ρ n³ D⁵)
- `J` — advance ratio        J = V∞ / (n D)
- `eta` — propulsive efficiency

## Notes

- **These values are approximate reconstructions** from reported trends, figures,
  and findings in the paper. The exact digitised data points should be replaced
  with the authors' original dataset when available.
- Thrust values are consistent with the reported finding that the medium-gap
  toroidal configuration outperforms the conventional at RPM > 3000.
- At V∞=0, the conventional propeller and toroidal propellers are within ~10%
  at low RPM, with toroidal designs diverging positively at higher RPM.

## Test Equipment (from paper)

- **Motor:** Surpass Hobby C3536 1050KV
- **ESC:** BLHeli Series 60A
- **Battery:** Tiger Lipo 3S 2200mAh 11.1V
- **Load cell:** 20-kg HX711
- **RPM sensor:** G.T. Power RC tachometer
- **Wind tunnel:** Westenberg WT 8600100-E (max 100 m/s, 600 mm jet diameter)
- **3D printing:** FDM with PETG filament
