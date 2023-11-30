import pandas as pd
import threading
import logging
import shutil
import re
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from motu_utils import motu_api
from src import config
from src.motu_payload import MotuPayloadGenerator
from src.motu_options import MotuOptions
from src.nc_to_csv import NcToCsv

logger = logging.getLogger()


class ApiRequest:

    def __init__(self, data: Dict[str, pd.DataFrame], common_payload: Dict[str, Any], output_filename: str,
                 batch_num_calls: Optional[int] = 100):
        self.data = data
        self.common_payload = dict(common_payload)
        self.output_filename = output_filename
        self.year = list(self.data.keys())[0]
        self.batch_num_calls = batch_num_calls

    def _request(self, data: Dict[str, Any]):
        try:
            motu_api.execute_request(MotuOptions(data))
        except Exception as error:
            print("An exception occurred:", type(error).__name__, "–", error)

    def _create_dest_folder(self) -> Path:
        root_folder = Path(self.common_payload['out_dir'])
        dest_folder = root_folder / str(self.year)
        if dest_folder.exists() and dest_folder.is_dir():
            shutil.rmtree(dest_folder)
        dest_folder.mkdir(parents=True, exist_ok=True)
        return dest_folder

    def _build_result(self):
        # Convert all nc files to csv
        nc_folder = (config.NC_PATH / str(self.year))
        csv_folder = (config.CSV_PATH / str(self.year))
        nc_to_csv_processor = NcToCsv(nc_folder, csv_folder)
        nc_to_csv_processor.run()

    def _chunkify_list(self, items, chunk_size):
        for i in range(0, len(items), chunk_size):
            yield items[i:i + chunk_size]

    def _fetch_data(self, data: List[Dict]):
        pass

    def _get_min_max_ids(self, payloads: List[Dict]) -> Tuple:
        ids = []
        for payload in payloads:
            tokens = payload['out_name'].split("-")
            try:
                _id = re.search(r'\d+', tokens[0]).group()
            except TypeError:
                _id = tokens[0]
            ids.append(int(_id))
        return min(ids), max(ids)

    def _download_data(self, max_iterations: Optional[int] = None):
        '''Run number of api calls in batch simultaneously
        '''
        motu_payload_gen = MotuPayloadGenerator(self.data[self.year], self.common_payload, self.output_filename)
        motu_payloads = motu_payload_gen.run()
        offset = 0
        for payloads in self._chunkify_list(motu_payloads, self.batch_num_calls):
            min_id, max_id = self._get_min_max_ids(payloads)
            message = f"----------------> Downloading batch from {min_id} to {max_id}"
            logger.info(message)
            print(message)
            self._fetch_data(payloads)
            message = f"----------------> End of barch"
            logger.info(message)
            print(message)
            offset += self.batch_num_calls
            if max_iterations is not None and offset >= max_iterations:
                break

    def run(self, max_iterations: Optional[int] = None):
        dest_folder = self._create_dest_folder()
        self.common_payload['out_dir'] = str(dest_folder)
        self._download_data(max_iterations=max_iterations)
        self._build_result()


class ApiRequestMultipleThreads(ApiRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _fetch_data(self, data: List[Dict]):
        '''Download multiple files from Copernicus simultaneously
                '''

        running_threads = []
        for i in range(len(data)):
            thread = threading.Thread(target=self._request, args=(data[i],))
            thread.start()
            running_threads.append(thread)

        for thread in running_threads:
            thread.join()


class ApiRequestMonoThread(ApiRequest):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _fetch_data(self, data: List[Dict]):
        '''Download one single file at the time'''
        for i in range(len(data)):
            self._request(data[i])