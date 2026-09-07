# Climate change reshapes global shipping exposure to marine extremes

Analysis code for the manuscript. Each script names the Methods equations it
implements, so results in the paper can be traced back to the code that
produced them.

## Data policy

Two source datasets are licensed and cannot be redistributed:

| Dataset | Provider | Use |
|---|---|---|
| Vessel-level AIS positions, 2021 | MarineTraffic | fixed shipping footprint, traffic weights |
| Open-ocean accident records, 2002–2022 | Lloyd's List Intelligence | accident-consequence models |

Everything else (ERA5, CMIP6, the continuous wave projection) is public; see the
Data availability statement.

The `prepare_*.py` scripts are the only stage that touches those sources. They
write normalised, non-identifying products into `data_public/`, and **every
later script reads from `data_public/` only** — so the figures and Table 1 can
be reproduced from this folder alone, without the licensed data.

What leaves the prepare stage:

* traffic **shares**, never vessel identities, on a 1° × 1° grid — the monthly
  weights sum to 1 within each normalisation group, and the annual footprint
  shares sum to 1 globally
* exposure days, which are traffic-weighted means and carry no counts
* fitted model summaries for Table 1

The single absolute quantity anywhere in `data_public/` is the `unique_mmsi`
column of `basin_traffic_2021.csv`: the number of distinct cargo vessels
entering each of the 14 AR6 basins during 2021. It is a basin-level aggregate
from which no individual vessel or voyage can be recovered, it is what the
Fig 4 bubble scale encodes, and the same figures are already printed in that
figure's legend. It is therefore included deliberately. The file also carries
`vessel_days_share`, a purely relative alternative summing to 1, should a
counts-free version of Fig 4 ever be wanted.

Accident counts in `table1_accident_models.csv` (per-category `n`, `n_obs`,
`n_reference`) are sample sizes reported in Table 1 itself. The `n_cells` /
`cell_used` / `cell_total` columns of `exposure_month.parquet` count climate
grid cells, not vessels.

One intermediate table — the row-level accident panel — still contains licensed
records. It is written **outside this folder**, to
`G:\WRH_data\restricted_intermediate\`, so that archiving or zipping this
folder can never distribute it.

## Layout

```
code/                  analysis scripts, flat
notebooks/             generated interactive copies, one per script
tools/                 make_notebooks.py
data_public/           derived data shipped with the code
README.md
requirements.txt       verified package versions
LICENSE                MIT for code, CC BY 4.0 for data_public
CITATION.cff
```

`code/` holds, in the order they run:

| Script | Does | Methods |
|---|---|---|
| `config.py` | all paths and analysis constants | — |
| `prepare_traffic_density.py` | AIS footprint → monthly traffic weights | Eq 1, 2, 13 |
| `prepare_exposure_projected.py` | strips traffic volumes from the P99 exposure tables | Eq 3–4 |
| `prepare_exposure_fixed.py` | collects the fixed-threshold exposure series | Eq 4 |
| `prepare_historical.py` | 1980–2024 trends, ECDs and exposure | Eq 4–5, 8 |
| `prepare_accident_panel.py` | accident × threshold matching, four categories | Eq 11 |
| `accident_models.py` | logit and OLS → **Table 1** | Eq 10–12 |
| `service_life_exposure.py` | 25-year delivery-cohort sums | Eq 9 |
| `fig1_historical.py` | **Fig 1** | — |
| `fig2_global_projection.py` | **Fig 2** | Eq 9 |
| `fig3_corridor_exposure.py` | **Fig 3** | Eq 9 |
| `fig4_regional_exposure_ratio.py` | **Fig 4** | Eq 13 |
| `ed_fig3_annual_projection.py` | **Extended Data Fig 3** | Eq 4 |

The `.py` files are the source of truth. `notebooks/` mirrors them cell by cell
for interactive checking; regenerate after editing a script with
`python tools/make_notebooks.py`.

## Reproducing

```bash
pip install -r requirements.txt
```

The five `prepare_*` scripts and `accident_models.py` read the licensed source
data. Run without it, they stop with an explanation rather than a traceback, and
point at the outputs already provided. Everything needed for the figures is in
`data_public/`, so **the paper's display items reproduce from this folder
alone**. If the licensed data lives somewhere other than `G:\WRH_data`, set the
`WRH_RAW` environment variable.

```bash
# needs the licensed sources; already run, outputs are in data_public/
python code/prepare_traffic_density.py
python code/prepare_exposure_projected.py
python code/prepare_exposure_fixed.py
python code/prepare_historical.py
python code/prepare_accident_panel.py

# everything below runs from data_public/ alone
python code/accident_models.py
python code/service_life_exposure.py
python code/fig1_historical.py
python code/fig2_global_projection.py
python code/fig3_corridor_exposure.py
python code/fig4_regional_exposure_ratio.py
python code/ed_fig3_annual_projection.py
```

Figure scripts open the figure with `plt.show()`; nothing is written to disk.

**Environment note.** On Windows/conda, `pyarrow` must be imported before
`cartopy`: cartopy loads GEOS/PROJ shared libraries that shadow one of
pyarrow's, after which the parquet engine fails to load. `fig1` and `fig3` pin
the order explicitly.

## Upstream steps not included

This code starts from pre-computed intermediate products rather than from the
raw ERA5 and CMIP6 fields. Three upstream stages therefore live outside it, in
the working notebooks under `Desktop\WRH\paper code\`:

| Stage | Produces | Where |
|---|---|---|
| Basin/month P95, P99 thresholds | `local_threshold/AR6_basin_month_*_1deg_2002_2022.csv` | `basin_historical_threshold.ipynb`, `corridor_historical_threshold.ipynb` |
| Projected exceedance days → basin/corridor exposure | `new_climate/exposure/exposure_annual.csv` | `basin_corridor_extreme_days.ipynb` |
| Historical grid-cell trends and exposure fields | `figure1_source/data/*.npz`, `*.parquet` | `figure1_source/regenerate_derived_data.py` |

## data_public/ contents

| File | Contents | Used by |
|---|---|---|
| `footprint_global.parquet` | C_ij as a share of 2021 global traffic, plus cumulative share | Fig 1b |
| `density_global_month.parquet` | W_ij,m, sums to 1 within each calendar month | Eq 2 |
| `density_basin_month.parquet` | the same weights renormalised within each of 14 AR6 basins | Eq 13 |
| `density_corridor_month.parquet` | the same weights renormalised within each of 4 corridors | Fig 3a |
| `basin_traffic_2021.csv` | unique vessels and traffic share per basin | Fig 4 |
| `exposure_annual.csv` | basin and corridor exposure days, **basin/month P99**, two 25-yr windows | Fig 4 |
| `exposure_month.parquet` | the monthly version of the same | — |
| `exposure_fixed_annual.csv` | global and corridor exposure days, **fixed thresholds**, 2015–2100 | Figs 2, 3, ED 3 |
| `service_life_global.csv`, `service_life_global_per_model.csv` | 25-year cohort sums by delivery year | Fig 2b |
| `table1_accident_models.csv` | odds ratios, AMEs, HCI effects, CIs | Table 1 |
| `historical_gridcell_trend.npz` | per-cell OLS slope and p-value, 1980–2024 | Fig 1a |
| `historical_exposure_share.npz` | per-cell % of global traffic-weighted exposure | Fig 1c |
| `historical_annual.csv`, `historical_month.csv` | annual ECDs, exposure days, monthly climatology | Fig 1d, 1e |

### Two threshold definitions, deliberately kept apart

* **Fixed physical thresholds** (U10 ≥ 17.2 m s⁻¹, SWH ≥ 6 m) drive Figs 1–3 →
  `exposure_fixed_annual.csv`
* **Basin- and month-specific P95/P99** drive Fig 4 and Table 1 →
  `exposure_annual.csv`

They live in separate files so the two are never mixed by accident.
