import pandas as pd
from typing import Dict, Union
from datetime import datetime


class CsvProcessing:

    def __init__(self, data: pd.DataFrame):
        self.data = data

    def _split_csv_per_year(self, data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        data['year'] = data['time'].dt.year
        return {
            y: data[data['year'] == y] for y in data['year'].unique()
        }

    def _get_max_bounding_box(self, data: pd.DataFrame) -> Dict[str, float]:
        return {
            'longitude_min': min(data['lon']),
            'longitude_max': max(data['lon']),
            'latitude_min': min(data['lat']),
            'latitude_max': max(data['lat'])
        }

    def _get_min_max_date(self, data: pd.DataFrame) -> Dict[str, datetime]:
        return {
            'date_min': min(data['time']),
            'date_max': max(data['time'])
        }

    def _get_min_max_depth(self, data: pd.DataFrame) -> Dict[str, datetime]:
        return {
            'depth_min': min(data['depth']),
            'depth_max': max(data['depth'])
        }

    def get_max_area_per_dates(self) -> Dict[str, Dict]:
        df_by_years = self._split_csv_per_year(self.data)
        data = {}
        for year, df in df_by_years.items():
            coords = self._get_max_bounding_box(df)
            dates = self._get_min_max_date(df)
            depths = self._get_min_max_depth(df)
            coords.update(**dates, **depths)
            data[year] = coords
        return data
