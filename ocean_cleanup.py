import copernicusmarine
from datetime import datetime, timedelta
from opendrift.readers import reader_netCDF_CF_generic
from opendrift.models.plastdrift import PlastDrift
import pandas as pd
import os

# Config variables

OUTPUT_DIR = "./data"
os.makedirs(OUTPUT_DIR, exist_ok=True)
 
# Mediterranean Sea bounding box (roughly Gibraltar to the Levant)
LON_MIN, LON_MAX = -6.0, 36.2
LAT_MIN, LAT_MAX = 30.2, 45.9
 
END_DATE = datetime(year=2026,month=9,day=20)
START_DATE = END_DATE - timedelta(days=365) 
 
START_STR = START_DATE.strftime("%Y-%m-%dT00:00:00")
END_STR = END_DATE.strftime("%Y-%m-%dT00:00:00")

CURRENT_OUTPUT_FILE_NAME="med_currents.nc"
WIND_OUTPUT_FILE_NAME="med_wind.nc"

TOTAL_PARTICLES = 10000

# Fetch data function that fetches datasets from Copernicus Marine Service based on config variables

def fetch_data():

    print(f"Fetching data from {START_STR} to {END_STR}")

    copernicusmarine.subset(
        dataset_id="cmems_mod_med_phy-cur_anfc_4.2km_P1D-m",  # daily currents, Med analysis & forecast
        variables=["uo", "vo"],  # eastward, northward sea water velocity
        minimum_longitude=LON_MIN,
        maximum_longitude=LON_MAX,
        minimum_latitude=LAT_MIN,
        maximum_latitude=LAT_MAX,
        start_datetime=START_STR,
        end_datetime=END_STR,
        minimum_depth=0,
        maximum_depth=2, 
        output_filename=CURRENT_OUTPUT_FILE_NAME,
        output_directory=OUTPUT_DIR,
        overwrite=True
    )

    print("Currents saved to", os.path.join(OUTPUT_DIR, CURRENT_OUTPUT_FILE_NAME))

    copernicusmarine.subset(
            dataset_id="cmems_obs-wind_glo_phy_nrt_l4_0.125deg_PT1H",  # hourly wind, NRT, 0.125deg
            variables=["eastward_wind", "northward_wind"], # eastward, northward winds
            minimum_longitude=LON_MIN,
            maximum_longitude=LON_MAX,
            minimum_latitude=LAT_MIN,
            maximum_latitude=LAT_MAX,
            start_datetime=START_STR,
            end_datetime=END_STR,
            output_filename=WIND_OUTPUT_FILE_NAME,
            output_directory=OUTPUT_DIR,
            overwrite=True
        )

    print("Wind saved to", os.path.join(OUTPUT_DIR, WIND_OUTPUT_FILE_NAME))

# Seed data function that initializes the drift model with particles

def seed_data():
    windData = reader_netCDF_CF_generic.Reader('data/'+WIND_OUTPUT_FILE_NAME)
    currentsData = reader_netCDF_CF_generic.Reader('data/'+CURRENT_OUTPUT_FILE_NAME)

    o = PlastDrift(loglevel=20)
    o.set_config('general:coastline_action', 'previous')
    o.add_reader([currentsData,windData])

    start_time = currentsData.start_time
    end_time = min(currentsData.end_time, windData.end_time)
    time = [start_time, end_time]

    river_df = pd.read_csv("data/Meijer2021_top_1000_mediterranean.csv")

    total_emissions = river_df['emissions_tonnes_per_year'].sum()

    for i,row in river_df.iterrows():
        share = row['emissions_tonnes_per_year'] / total_emissions
        n = max(1, round(TOTAL_PARTICLES * share))
        o.seed_elements(
            lon=row['longitude'],
            lat=row['latitude'], 
            radius=1500,
            number=n, 
            time=time)
    
    o.run(end_time=end_time, time_step=7200, time_step_output=86400)
    print(o)
    o.animation(fast=False,corners=[LON_MIN, LON_MAX, LAT_MIN, LAT_MAX])

# Main execution

fetch_data()
seed_data()
