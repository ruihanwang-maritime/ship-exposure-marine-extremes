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

Everything else (ERA5, CMIP6, the continuous wave projection) is public; see the Data availability statement.

The `prepare_*.py` scripts are the only stage that accesses the licensed source data. They write normalised, non-identifying products into `data_public/`.
The figure and service-life scripts use these derived products, whereas re-estimation of the accident-consequence models requires the licensed row-level accident records. The fitted model summaries reported in Table 1 are provided in `data_public/table1_accident_models.csv`.

What leaves the prepare stage:

* traffic **shares**, never vessel identities, on a 1° × 1° grid — the monthly
  weights sum to 1 within each normalisation group, and the annual footprint
  shares sum to 1 globally
* exposure days, which are traffic-weighted means and carry no counts
* fitted model summaries for Table 1

The single absolute quantity in `data_public/` is the `unique_mmsi`
column of `basin_traffic_2021.csv`, which records the number of distinct cargo
vessels entering each of the 14 AR6 basins during 2021. It is a basin-level
aggregate from which no individual vessel or voyage can be recovered. This
quantity determines the bubble scale in Main Fig. 5 and is also reported in
the figure legend. The file additionally contains `vessel_days_share`, a
relative traffic measure that sums to one.

Accident counts in `table1_accident_models.csv` (per-category `n`, `n_obs`,
`n_reference`) are sample sizes reported in Table 1 itself. The `n_cells` /
`cell_used` / `cell_total` columns of `exposure_month.parquet` count climate
grid cells, not vessels.

One intermediate table — the row-level accident panel — still contains licensed
records. It is written **outside this folder**, to
`G:\WRH_data\restricted_intermediate\`, so that archiving or zipping this
folder can never distribute it.

## Layout

```text
code/                  analysis scripts
tools/                 optional utilities
data_public/           derived data supplied with the code
README.md
requirements.txt       verified package versions
LICENSE                MIT for code, CC BY 4.0 for data_public
CITATION.cff

`code/` holds, in the order they run:

| Script | Output | Methods |
|---|---|---|
| `config.py` | analysis paths and constants | — |
| `prepare_traffic_density.py` | monthly traffic weights | Eqs. 1, 2 and 13 |
| `prepare_exposure_projected.py` | projected exposure products | Eqs. 3 and 4 |
| `prepare_exposure_fixed.py` | fixed-threshold exposure series | Eq. 4 |
| `prepare_historical.py` | historical ECD and exposure trends | Eqs. 4, 5 and 8 |
| `prepare_accident_panel.py` | accident-weather matching | Eq. 11 |
| `accident_models.py` | Table 1 | Eqs. 10–12 |
| `service_life_exposure.py` | 25-year service-life exposure | Eq. 9 |
| `fig1_historical.py` | Main Fig. 1 | — |
| `fig2_global_projection.py` | Main Fig. 3 | Eq. 9 |
| `fig3_corridor_exposure.py` | Main Fig. 4 | Eq. 9 |
| `fig4_regional_exposure_ratio.py` | Main Fig. 5 | Eq. 13 |
| `ed_fig3_annual_projection.py` | Supplementary Fig. 9 | Eq. 4 |

The `.py` files in `code/` are the source of truth. The optional
`tools/make_notebooks.py` utility can be used to generate interactive notebook
copies locally.

## Reproducing

```bash
pip install -r requirements.txt
```

The five `prepare_*` scripts access licensed source data and have already been
run to generate the non-identifying products supplied in `data_public/`.
Without access to the licensed source data, these preparation scripts stop with
an explanatory message.

The downstream exposure and figure scripts can be run using the derived
products in `data_public/`. They support Main Figs. 1 and 3--5,
Supplementary Fig. 9 and the service-life exposure estimates. Main Fig. 2 and
additional Supplementary analyses require upstream processing of large ERA5,
CMIP6 and wave-projection fields and are not reproduced directly by this
compact repository.

Re-estimation of the accident-consequence models requires the licensed
row-level accident panel. The corresponding fitted estimates are supplied in
`data_public/table1_accident_models.csv`.

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

## Upstream processing not included

This compact repository starts from pre-computed intermediate products.
Generation of the basin- and month-specific thresholds, processing of the full
ERA5 and CMIP6 fields, and construction of historical grid-cell fields require
large source datasets and upstream workflows that are not included here. The
derived products required for the downstream analyses are supplied in
`data_public/`.

| Stage | Produces | Where |
|---|---|---|
| Basin/month P95, P99 thresholds | `local_threshold/AR6_basin_month_*_1deg_2002_2022.csv` | `basin_historical_threshold.ipynb`, `corridor_historical_threshold.ipynb` |
| Projected exceedance days → basin/corridor exposure | `new_climate/exposure/exposure_annual.csv` | `basin_corridor_extreme_days.ipynb` |
| Historical grid-cell trends and exposure fields | `figure1_source/data/*.npz`, `*.parquet` | `figure1_source/regenerate_derived_data.py` |

## data_public/ contents

```markdown
| File | Contents | Used by |
|---|---|---|
| `footprint_global.parquet` | 2021 global traffic shares and cumulative shares | Main Fig. 1b |
| `density_global_month.parquet` | Monthly global traffic weights | Eq. 2 |
| `density_basin_month.parquet` | Monthly traffic weights normalised within 14 AR6 basins | Eq. 13 and Main Fig. 5 |
| `density_corridor_month.parquet` | Monthly traffic weights normalised within four corridors | Main Fig. 4a |
| `basin_traffic_2021.csv` | Unique vessels and traffic shares by basin | Main Fig. 5 |
| `exposure_annual.csv` | Basin- and corridor-level P99 exposure for two 25-year periods | Main Fig. 5 |
| `exposure_month.parquet` | Monthly version of the basin- and corridor-level exposure data | — |
| `exposure_fixed_annual.csv` | Global and corridor exposure under fixed thresholds, 2015–2100 | Main Figs. 3 and 4; Supplementary Fig. 9 |
| `service_life_global.csv` | 25-year service-life exposure by delivery year | Main Fig. 3b |
| `service_life_global_per_model.csv` | Model-specific wind service-life exposure | Main Fig. 3b |
| `table1_accident_models.csv` | Odds ratios, probability effects, HCI effects and confidence intervals | Table 1 |
| `historical_gridcell_trend.npz` | Grid-cell historical trends, 1980–2024 | Main Fig. 1a |
| `historical_exposure_share.npz` | Grid-cell shares of global traffic-weighted exposure | Main Fig. 1c |
| `historical_annual.csv` | Annual ECD and exposure series | Main Fig. 1d |
| `historical_month.csv` | Monthly exposure climatology | Main Fig. 1e |

### Two threshold definitions

* **Fixed physical thresholds** (`U10 ≥ 17.2 m s⁻¹` and `SWH ≥ 6 m`) are used
  for the historical and global/corridor projection analyses in Main
  Figs. 1, 3 and 4.
* **Basin- and month-specific P95/P99 thresholds** are used for the
  accident-consequence analysis and regional exposure ratios in Table 1 and
  Main Fig. 5.

The corresponding data are stored separately to prevent the two threshold
definitions from being mixed.

They live in separate files so the two are never mixed by accident.
