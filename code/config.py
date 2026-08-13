"""
Central path / constant configuration.

Three roots:
  RAW        - restricted source data (commercial AIS, Lloyd's accidents, ERA5,
               CMIP6). Not redistributable; present only on the authors' machines.
  RESTRICTED - intermediate tables that still contain licensed row-level records.
               Deliberately placed OUTSIDE this repository so that archiving or
               zipping the repository can never distribute them.
  PUBLIC     - derived, non-identifying products shipped with the repository.
               Every analysis script downstream of the prepare_* stage reads
               from here, so the pipeline is reproducible without the
               restricted sources.
"""
import os
from pathlib import Path

# --------------------------------------------------------------------------
# roots
# --------------------------------------------------------------------------
# Root of the licensed source data. Absent for anyone without a MarineTraffic
# and Lloyd's List Intelligence licence; override with the WRH_RAW environment
# variable. Only the prepare_* scripts read from here -- their outputs are
# shipped in data_public/, so nothing else in this repository needs it.
RAW = Path(os.environ.get("WRH_RAW", r"G:\WRH_data"))
RESTRICTED = RAW / "restricted_intermediate"
REPO = Path(__file__).resolve().parents[1]
PUBLIC = REPO / "data_public"

# --------------------------------------------------------------------------
# restricted sources (RAW)
# --------------------------------------------------------------------------
# 2021 AIS-derived traffic
AIS_MONTH_GRID = RAW / "cargo_all_data" / "df_mainlane_monthly_grid"   # 2021MM.parquet
AIS_FOOTPRINT_99 = RAW / "cargo_all_data" / "df_flow_core99.parquet"
TRAF_DIR = RAW / "traffic_monthly"
TRAF_BASIN = TRAF_DIR / "traffic_month_basin.parquet"
TRAF_CORRIDOR = TRAF_DIR / "traffic_month_corridor.parquet"
BASIN_MMSI = TRAF_DIR / "basin_unique_mmsi_2021.csv"
CORRIDOR_GRID_DIR = RAW / "ship_corridors"      # grid_{corridor}_1deg_unique_mmsi_main99.csv

# ERA5 (1 deg regridded)
ERA5_WIND = RAW / "weather_wind_combine" / "regrid"      # {year}_wind_1deg.nc  var wind_speed10
ERA5_WAVE = RAW / "weather_swh_regrid"                   # {year}_SWH_1deg.nc   var swh
LSM_FILE = RAW.parent / "era5_lsm_0.25deg_20210101.nc"

# basin/month percentile thresholds (ERA5 2002-2022)
THR_DIR = RAW / "local_threshold"                        # AR6_basin_month_{var}_1deg_2002_2022.csv

# projections / exposure products
EXPOSURE_DIR = RAW / "new_climate" / "exposure"
EXPOSURE_ANNUAL = EXPOSURE_DIR / "exposure_annual.csv"
EXPOSURE_MONTH = EXPOSURE_DIR / "exposure_month.csv"

# pre-computed Figure 1 derived data (ERA5 trends + AIS-weighted exposure),
# produced by paper code/figure1_source/regenerate_derived_data.py
FIG1_SRC = Path(r"c:\Users\ranyan\Desktop\WRH\paper code\figure1_source\data")

# accidents (Lloyd's List Intelligence, restricted)
ACCIDENT_DIR = RAW / "maritime accident"

# --------------------------------------------------------------------------
# analysis constants (Methods)
# --------------------------------------------------------------------------
YEAR_AIS = 2021                 # fixed shipping footprint year
HIST_YEARS = (1980, 2024)       # historical ERA5 period
THR_YEARS = (2002, 2022)        # percentile-threshold reference period
PERIOD_RECENT = "2030-2054"     # "recent future"
PERIOD_LATE = "2076-2100"       # "late century"
SERVICE_LIFE = 25               # years, Eq 9

WIND_THRESHOLD = 17.2           # m/s,  U10 gale force
WAVE_THRESHOLD = 6.0            # m,    SWH hazardous high seas
FOOTPRINT_SHARE = 0.99          # cumulative traffic share defining Omega_ship

SSPS = ["SSP1-2.6", "SSP2-4.5", "SSP5-8.5"]
WIND_MODELS = ["ACCESS-CM2", "CMCC-CM2-SR5", "IPSL-CM6A-LR",
               "MPI-ESM1-2-LR", "MRI-ESM2-0"]

BASINS = ["ARS", "BOB", "CAR", "EAO", "EIO", "EPO", "MED",
          "NAO", "NPO", "SAO", "SEA", "SIO", "SOO", "SPO"]
CORRIDORS = ["NE_ASIA_LALB", "NE_ASIA_SG", "RT_NY", "SG_RT"]
CORRIDOR_LABEL = {"NE_ASIA_LALB": "YRD-LA/LB", "NE_ASIA_SG": "YRD-SG",
                  "RT_NY": "RT-NY", "SG_RT": "RT-SG"}

# --------------------------------------------------------------------------
# public products written by the prepare_* scripts
# --------------------------------------------------------------------------
DENSITY_GLOBAL = PUBLIC / "density_global_month.parquet"
DENSITY_BASIN = PUBLIC / "density_basin_month.parquet"
DENSITY_CORRIDOR = PUBLIC / "density_corridor_month.parquet"
FOOTPRINT_PUBLIC = PUBLIC / "footprint_global.parquet"
BASIN_TRAFFIC_PUBLIC = PUBLIC / "basin_traffic_2021.csv"


def require_raw(*paths):
    """Explain what is missing instead of raising a bare FileNotFoundError."""
    missing = [p for p in paths if not Path(p).exists()]
    if not missing:
        return
    listing = ''.join(f'    {p}\n' for p in missing)
    raise SystemExit(
        f"\nThis script reads the licensed source data, which is not redistributable"
        f" and is not part of this repository.\nMissing:\n{listing}"
        f"\nCurrent source root: {RAW}"
        f"\nSet the WRH_RAW environment variable if it lives elsewhere.\n"
        f"\nYou do not need to run this script to reproduce the paper: "
        f"its outputs are already in data_public/. See README.md.\n")


def ensure_dirs():
    PUBLIC.mkdir(parents=True, exist_ok=True)
    RESTRICTED.mkdir(parents=True, exist_ok=True)
