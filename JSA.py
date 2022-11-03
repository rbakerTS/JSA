import shutil
from random import random
from typing import Union

from arcgis.features import FeatureLayerCollection, FeatureLayer
from AGO_Manager import AGO_manager
import json
import os
import time
import pandas as pd
from datetime import datetime, date, timedelta


class JSA:
    def __init__(self, search_title: str, search_type: str, start_date: str, end_date: str, filter_field: str,
                 filter_criteria: Union[str, list]):
        self.search_title = search_title
        self.search_type = search_type
        self.filter_start_date = start_date
        self.filter_end_date = end_date
        self.filter_field = filter_field
        self.filter_criteria = [x.replace("'", '').replace(" ", "_") for x in filter_criteria]
        self.date = date.today()
        self.output_folder = f'downloads/{self.search_title}_{self.date}'
        os.makedirs(self.output_folder, exist_ok=True)
        self.start_date = datetime.strptime(self.filter_start_date, "%Y-%m-%d")
        self.end_date = datetime.strptime(self.filter_end_date, "%Y-%m-%d")

        with open('secrets.json') as file:
            x = json.load(file)

        username = x['user']
        password = x['password']

        self.manager = AGO_manager(username, password)

    def items_search(self):
        self.search_results = self.manager.content_search(title_search=self.search_title, max_items=10000,
                                                          item_type=self.search_type)
        self.search_items = self.search_results['items']
        self.search_count = len(self.search_items)
        return self.search_items

    def download_search_items(self):
        download_successful = 0
        s = 30
        files = os.listdir(self.output_folder)
        for number, item in enumerate(self.search_items, start=1):
            item_name = item.title
            os.makedirs(self.output_folder, exist_ok=True)
            csv_name = f'{item_name}_{self.date}.csv'
            if csv_name not in files:
                try:
                    item_df = item.layers[0].query().sdf
                    success = item_df.to_csv('/'.join([self.output_folder, csv_name]))
                    if success is None:
                        download_successful += 1
                        print(f"Downloaded {csv_name}")
                    else:
                        print(f"Failed to download {csv_name}")
                except Exception as e:
                    print(f"Attempt to download {item_name} encountered the following exception:")
                    print(e)
                    try_again = input(f"Try again in {s} seconds? (y/n)")
                    if try_again.lower().strip() == 'y':
                        print(f'Sleeping for {s} seconds')
                        print(f"Resuming at {datetime.strftime(datetime.now() + timedelta(seconds=s), '%I:%M:%S %p')}")
                        time.sleep(s)
                    else:
                        print(f"Skipping {item_name}")
                        break
            else:
                print(f"{csv_name} already exists")
        print(f"Downloaded {download_successful} of {self.search_count} successfully")

    def merge_csvs(self):
        print(f"Merging files in {self.output_folder}")
        self.files = os.listdir(self.output_folder)
        master_file = self.files[0]
        master_filepath = self.output_folder + "/" + master_file
        master_df = pd.read_csv(master_filepath)
        for file in self.files[1:]:
            filepath = self.output_folder + "/" + file
            x = pd.read_csv(filepath)
            master_df = pd.concat([master_df, x], ignore_index=True)
        output_name = f'0{self.search_title}_{self.date}_merged.csv'
        self.merged_csv_name = f'{self.output_folder}/{output_name}'
        master_df.to_csv(self.merged_csv_name, index=False)
        print(f"Merged files from {self.output_folder} into {self.merged_csv_name}")

    def filter_csv(self):
        print(f"Querying for records between {self.filter_start_date} and {self.filter_end_date}")
        df = pd.read_csv(self.merged_csv_name)
        df['start_date'] = self.start_date
        df['end_date'] = self.end_date
        df['criteria'] = ','.join(self.filter_criteria)
        df['date'] = df['briefing_date'].apply(lambda x: datetime.strptime(x.split(' ')[0], "%Y-%m-%d"))
        df_filtered = pd.DataFrame(columns=df.columns)
        if self.filter_field == 'tech':
            cols = [x for x in df.columns if 'tech' in x]
            for i, row in df.iterrows():
                values = [v for i, v in row.items() if i in cols]
                if values[1] != 'None':
                    if any(item in self.filter_criteria for item in values):
                        df_filtered = pd.concat([df_filtered, row.to_frame().T])
        elif isinstance(self.filter_criteria, list):
            for item in self.filter_criteria:
                df_filtered = pd.concat(
                    [df_filtered, df.query(f'start_date <= date & date <= end_date & {self.filter_field} == {item}')])
        else:
            df_filtered = pd.concat(
                [df_filtered,
                 df.query(f'start_date <= date & date <= end_date & {self.filter_field} == {self.filter_criteria}')])
        filtered_csv_name = f'0{self.search_title}_{self.filter_start_date}_to_{self.filter_end_date}_{self.filter_field}.csv'
        filtered_csv_path = "/".join([self.output_folder, filtered_csv_name])
        df_filtered.to_csv(filtered_csv_path, index=False)
        print(f"Exported {filtered_csv_name}")

    def Run(self):
        self.items_search()
        self.download_search_items()
        self.merge_csvs()
        self.filter_csv()

if __name__ == '__main__':
    jsa = JSA(
        search_title='JSA',
        search_type='Feature Layer',
        start_date='2020-07-01',
        end_date='2022-10-31',
        filter_field='tech',
        filter_criteria=['Cory Hicks',
                         'Clayton Pruitt',
                         'Justin Ham',
                         'Ernan Vasquez',
                         'Ryan Todd',
                         'Justis Blackmon',
                         'Wade Salmon',
                         'Kenneth Campbell',
                         'Kevin Pilkinton',
                         'Ryan Gray',
                         'Braydon Kepaa',
                         "Tre' Faniel",
                         'Conner Jackson',
                         'Cory Melton',
                         'Paul Wood',
                         'Dustin Ramsey',
                         'Piper Mazander',
                         'Brian Rowell']
    )

    jsa.Run()
