import os
import json
import requests
import pandas as pd
from tqdm import tqdm
from bs4 import BeautifulSoup
from codepile.dataset import DatasetInfo, DatasetSources, RawDataset, Scraper, Processor, Analyser, Dataset
from codepile.codepile import Config
from datetime import datetime
from boto3.session import Session
import boto3


LIST_DATASET = ['CodeContest', 'TopCoder', "GoogleCodeJam"]
CP_S3_BUCKET = "s-eai-neox"

class CPDataset(Dataset):
    def __init__(self, config):
        self.config = config
        self.info = DatasetInfo(
            id="CPDataset",
            description="Competitive Programming Dataset Take From CodeContest, Topcoder, Google CodeJam",
            size=3,
            source_uri="https://huggingface.co/datasets/deepmind/code_contests",
            dataset_pros="Programming Problem with Tutorial and Solution bring explicit context for language model",
            dataset_cons="Domain related to Competitive Programming Only",
            languages=["english"],
            coding_languages=["python", "c++", "java"],
            modalities=["source_code"],
            source_license="MIT",
            source_citation="CodeContest",
            data_owner="Duy Phung",
            contributers=["Duy Phung"],
            data_end=datetime(2022, 10, 6),
       )
    
    def info(self):
        return self.info
    
    def id(self):
        return self.info.id
    
    def make_format_code_contest(self, sample):
        title = sample['name']
        description = sample['description']
        difficulty = sample['difficulty']
        tags = sample['cf_tags']
        source = sample['source']
        time_limit = sample['time_limit']
        memory_limit = sample['memory_limit_bytes']
        solutions = sample['solutions']
        incorrect_solutions = sample['incorrect_solutions']
        hint = sample['hint_string']
        prompt = "Problem title: " + title + "\n"
        prompt = prompt + "Problem statement: " + description + "\n"
        prompt = prompt + "Problem categories: " + ','.join(tags) + "\n"
        prompt = prompt + "Time limit: " + time_limit + "\n"
        prompt = prompt + "Memory limit: " + memory_limit + "\n"
        prompt = prompt + "Difficulty: " + description + "\n"
        prompt = prompt + "Hint: " + hint + "\n"
        for sol in solutions:
            prompt = prompt + f"Here is a correct solution with {sol['language']} programming language: \n" + sol['solution'] + "\n"
        for sol in incorrect_solutions:
            prompt = prompt + f"Here is an incorrect solution with {sol['language']} programming language: \n" + sol['solution'] + "\n"
        return prompt
    
    def make_format_topcoder(self, sample):
        name = sample['name']
        description = sample['description']
        solutions = sample['solutions']
        prompt = "Problem title: " + name + "\n"
        prompt = prompt + "Problem statement: " + description + "\n"
        for sol in solutions:
            prompt = prompt + f"Here is a correct solution: \n" + sol.strip() + "\n"
        return prompt
    
    def make_format_ggcodejam(self, sample):
        name = sample['problem_name']
        description = sample['problem']
        analysis = sample['analysis']
        solutions = sample['solutions']

        prompt = "Problem title: " + name + "\n"
        prompt = prompt + "Problem statement: " + description + "\n"
        prompt = prompt + "Hint: " + analysis + "\n"
        for author in solutions:
            prompt = prompt + f"Here is a correct solution: \n" + solutions[author] + "\n"
        return prompt        


    def make_format(self, sample, source):
        if source == 'CodeContest':
            return self.make_format_code_contest(sample)
        elif source == 'TopCoder':
            return self.make_format_topcoder(sample)
        elif source == "GoogleCodeJam":
            return self.make_format_ggcodejam(sample)
        else:
            raise ValueError('Unknown source')

    def fetch_raw(self, return_df=True):
        
        if not os.path.exists(self.config.raw_data_dir):
            os.makedirs(self.config.raw_data_dir)

        if not os.path.exists(os.path.join(self.config.raw_data_dir, 'CodeContest_raw.pickle')):
            s3 = boto3.client('s3')
            s3.download_file(CP_S3_BUCKET, "data/codepile/cpdata/CodeContest_raw.pickle", os.path.join(self.config.raw_data_dir, 'CodeContest_raw.pickle'))
        
        if not os.path.exists(os.path.join(self.config.raw_data_dir, 'TopCoder_raw.pickle')):
            s3 = boto3.client('s3')
            s3.download_file(CP_S3_BUCKET, "data/codepile/cpdata/TopCoder_raw.pickle", os.path.join(self.config.raw_data_dir, 'TopCoder_raw.pickle'))
        
        if not os.path.exists(os.path.join(self.config.raw_data_dir, 'GoogleCodeJam_raw.pickle')):
            s3 = boto3.client('s3')
            s3.download_file(CP_S3_BUCKET, "data/codepile/cpdata/GoogleCodeJam_raw.pickle", os.path.join(self.config.raw_data_dir, 'GoogleCodeJam_raw.pickle'))

        if return_df:
            return {'CodeContest': pd.read_pickle(os.path.join(self.config.raw_data_dir, 'CodeContest_raw.pickle')),
                    'TopCoder': pd.read_pickle(os.path.join(self.config.raw_data_dir, 'TopCoder_raw.pickle')), 
                    'GoogleCodeJam': pd.read_pickle(os.path.join(self.config.raw_data_dir, 'GoogleCodeJam_raw.pickle'))}
    
    def download(self):
        self.fetch_raw(return_df=False)


if __name__=="__main__":
    if not os.path.exists("data/"):
        os.makedirs("data/")
    config = Config(
        raw_data_dir="data/",
        output_data_dir="data/",
        tmpdir="/tmp"
    )
    cp_dataset = CPDataset(config)
    cp_dataset.download()
