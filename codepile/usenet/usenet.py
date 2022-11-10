from codepile.dataset import DatasetInfo, Dataset
from codepile.codepile import Config

from .forum import mbox
from .forum.utils import get_bad_strings_automaton
from .utils import create_dir_if_not_exists

import gzip
import shutil
import os
import glob
from datetime import datetime

import pandas as pd
import pyarrow.parquet as pq
import pyarrow as pa

import json


class UsenetDataset(Dataset):
    def __init__(self, config):
        self.config = config
        self.info = DatasetInfo(
            id='UsenetComp',
            description='Archive of all comp usenet discussions',
            size=2.4e11,
            source_uri='https://archive.org/details/usenet-comp',
            dataset_pros='Gold mine of conversations for major programming languages.',
            dataset_cons='Misses modern programming languages like Python.',
            languages=['english', ],
            coding_languages=['java', 'c', 'javascript', 'cobol', 'others', ],
            modalities=['discussion', 'source_code', ],
            source_license='none',
            source_citation='Usenet',
            data_owner='Jehoshaph A Chandran',
            contributers=['Jehoshaph A Chandran', ],
            data_end=datetime(2013, 8, 19),
            data_start=datetime(1980, 1, 1),
        )

    def info(self):
        return self.info

    def id(self):
        return self.info.id

    def download(self, *args, **kwargs):
        """
        Download and process the entire comp raw dataset (or) a subset of archives

        Skipping the download step, just make sure the raw folder has the following structure:

        usenet-97comp.jobs
            -> file1.mobx.gz
            -> file2.mbox.gz
        usenet-4ubox.fundgrube
            -> file1.mbox.gz
        """
        self.process()

    def process(self, *args, **kwargs):
        # Create a personal log file
        logfile = os.path.join(self.config.output_data_dir, f'usenet_{datetime.now().strftime("%Y%m%d%H%M%S")}.log')
        print(f'Starting... created logfile {logfile}')
        # Clearing the log file
        open(logfile, 'w').close()

        # Creating the global bad string automaton
        bad_strings_automaton = get_bad_strings_automaton('codepile/usenet/bad_strings.txt')

        # Making sure the output dir exists
        if not os.path.exists(self.config.output_data_dir):
            os.makedirs(self.config.output_data_dir)

        with open(logfile, 'a') as logf:
            # Usenet dirs
            usenet_dirs = glob.glob(os.path.join(self.config.raw_data_dir, '*'))
            for usenet_dir in usenet_dirs:
                # Empty the temp folder
                if os.path.exists(self.config.tmpdir):
                    shutil.rmtree(self.config.tmpdir)
                os.makedirs(self.config.tmpdir)

                base_name = os.path.basename(usenet_dir)
                for file in glob.glob(os.path.join(usenet_dir, '*')):
                    if file.endswith('.mbox.gz'):
                        # Unzip these mbox files to the temp dir
                        # Get a filename /some/path/file.mbox.gz -> file.mbox
                        filename = os.path.basename(file.rstrip('.gz'))
                        with gzip.open(file, 'rb') as f_in:
                            with open(os.path.join(self.config.tmpdir, filename), 'wb+') as f_out:
                                shutil.copyfileobj(f_in, f_out)

                # Processing each email group
                out_file = os.path.join(self.config.output_data_dir, f'{base_name}.parquet')

                for file in glob.glob(os.path.join(self.config.tmpdir, '*')):
                    if file.endswith('.mbox'):
                        try:
                            threads = mbox.process_forum(file, spam_automaton=bad_strings_automaton)
                            forum_content = []
                            forum_metadata = []
                            forum_name = os.path.basename(file)
                            for thread in threads:
                                # Forum content in plain text
                                forum_content.append(thread.export_string())

                                # Metadata for this forum's threads
                                m_metadata = thread.get_metadata()
                                m_metadata.update({'forum_name': forum_name})
                                forum_metadata.append(json.dumps(m_metadata))

                            forum_frame = pd.DataFrame({
                                'metadata': forum_metadata,
                                'content': forum_content,
                            })
                            forum_table = pa.Table.from_pandas(forum_frame)
                            pq.write_to_dataset(forum_table, root_path=out_file)

                            logf.write(f'Success {file}: includes {len(threads)}\n')

                        except Exception as e:
                            # Appending to the log file
                            logf.write('Error {file}: {e}\n'.format(file=file, e=str(e)))

        print('Finished!')


def main():
    """
    Use data/raw, data/temp, and data/output folders at this level
    """
    this_dir = os.path.dirname(__file__)
    output_dir = os.path.join(this_dir, 'data', 'output')
    temp_dir = os.path.join(this_dir, 'data', 'temp')
    raw_dir = os.path.join(this_dir, 'data', 'raw')

    create_dir_if_not_exists(output_dir)
    create_dir_if_not_exists(temp_dir)
    create_dir_if_not_exists(raw_dir)

    config = Config(
        output_data_dir=output_dir,
        raw_data_dir=raw_dir,
        tmpdir=temp_dir,
    )

    usenet_dataset = UsenetDataset(config)

    usenet_dataset.download()


if __name__ == '__main__':
    main()
