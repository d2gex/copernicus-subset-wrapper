import logging
import pandas as pd
import time
from src.motu_options import MotuOptions
from src.motu_payload import MotuPayloadGenerator
from src.nc_to_csv import NcToCsv
from src.csv_processing import CsvProcessing
from motu_utils import motu_api
from src import config

logger = logging.getLogger()

if __name__ == "__main__":
    start_time = time.time()
    input_data = pd.read_csv(config.DATA_PATH / config.INPUT_FILENAME)
    input_data['time'] = pd.to_datetime(input_data['time'], format='%d/%m/%Y %H:%M')
    csv_proc = CsvProcessing(input_data)
    bb_by_dates = csv_proc.get_max_area_per_dates()
    common_payload = {
        'motu': config.settings['base_url'],
        "auth_mode": 'cas',
        'out_dir': str(config.NC_PATH),
        'user': config.COPERNICUS_USERNAME,
        'pwd': config.COPERNICUS_PASSWORD,
        'service_id': config.settings['service_id'],
        'product_id': config.settings['product_id'],
        'variable': config.settings['variables']
    }
    payload_generators = MotuPayloadGenerator(bb_by_dates, common_payload, config.OUTPUT_FILENAME)
    motu_payloads = payload_generators.run()

    # Fetch .data from Coperniculs in .nc format
    for _id, payload_data in motu_payloads.items():
        logger.info(
            f"------> Processing area  for ID = {_id} delimited by ({payload_data['longitude_min']},{payload_data['latitude_min']}) and "
            f"({payload_data['longitude_max']},{payload_data['latitude_max']})")
        motu_api.execute_request(MotuOptions(payload_data))
        logger.info("-------> END")

    # Convert all nc files to csv
    (NcToCsv(config.NC_PATH, config.CSV_PATH))()
    end_time = time.time()
    execution_time = start_time - end_time
    print("Data reading, api-fetching and processing time:", execution_time)
