import logging
import pandas as pd
import time
import shutil
from src import config
from src.payload_generator import CpmtbPayloadGenerator
from src.csv_parameter_splitter import CsvParameterSplitter
from src.api_request import DataRequest
from src.nearest_point_finder import NearestDataframePointFinder
from src.nc_to_csv import NcToCsv

logger = logging.getLogger()

if __name__ == "__main__":

    start_time = time.time()

    # (1) Read input parameters
    input_data = pd.read_csv(config.DATA_PATH / config.INPUT_FILENAME)
    input_data['time'] = pd.to_datetime(input_data['time'], format='%d/%m/%Y %H:%M')

    # (2) Split inputs into daily records
    csv_proc = CsvParameterSplitter(input_data,
                                    min_year=config.settings['years'][0],
                                    max_year=config.settings['years'][-1],
                                    time_offset=config.settings['time_offset'])
    api_params_by_dates = csv_proc.get_min_max_boundaries_per_dates()
    df_by_dates = csv_proc.get_dataframes_split_by_dates()

    # (3) Create product folder and sub-folders
    ret_root_folder = config.OUTPUT_PATH / config.settings['dataset_id']
    ret_nc_folder = ret_root_folder / 'nc'
    ret_csv_folder = ret_root_folder / 'csv'

    if ret_root_folder.exists() and config.settings['start_mode'] == 0:
        shutil.rmtree(ret_root_folder)
    ret_root_folder.mkdir(parents=True, exist_ok=True)
    ret_nc_folder.mkdir(parents=True, exist_ok=True)
    ret_csv_folder.mkdir(parents=True, exist_ok=True)

    # (3) Generate all payloads required to fetch the desired data
    common_payload = {
        'output_directory': str(ret_nc_folder),
        'dataset_id': config.settings['dataset_id'],
        'variables': config.settings['variables']
    }

    payload_generators = CpmtbPayloadGenerator(api_params_by_dates, common_payload, config.OUTPUT_FILENAME)
    motu_payloads = payload_generators.run()

    # (4) Do we need start where left the last time?
    data_request = DataRequest()
    start_mode = config.settings['start_mode']
    if start_mode != 1:
        full_results = pd.DataFrame()
    else:
        nc_to_csv_converter = NcToCsv()
        full_results = nc_to_csv_converter.read_and_merge(ret_nc_folder)

    # (5) Fetch the actual data from Copernicus and merge into input parameters
    for _date, payload_data in motu_payloads.items():
        logger.info(
            f"------> Processing date = {_date} delimited by ({payload_data['minimum_longitude']},"
            f"{payload_data['minimum_latitude']}) and "
            f"({payload_data['maximum_longitude']},{payload_data['minimum_latitude']})")
        ret_api_data = data_request.fetch_from_net(
            payload_data) if start_mode != 2 else data_request.fetch_from_disk(payload_data)
        if ret_api_data is None:
            logger.error("No data was returned. See log for further details")
        else:
            input_data = df_by_dates[_date]
            npf = NearestDataframePointFinder(input_data, ret_api_data, var_names=config.settings['variables'])
            partial_results = npf.find_and_merge()
            full_results = pd.concat([full_results, partial_results])
        logger.info("-------> END")
    full_results.to_csv(ret_csv_folder / f"{config.settings['dataset_id']}.csv")

    end_time = time.time()
    execution_time = start_time - end_time
    print("Data reading, api-fetching and processing time:", execution_time)
