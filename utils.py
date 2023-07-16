from git import Repo, RemoteProgress
from tqdm import tqdm
import importlib
import logging
import yaml
import sys
import os


def load_config_file(file_path: str):
    # load configuration file
    with open(file_path, "r") as config_file:
        try:
            config = yaml.safe_load(config_file)
            return config
        except yaml.YAMLError as err:
            logging.fatal(f"error while loading"
                          f" configuration file: {err}")
            sys.exit(1)


def import_parser(package_name: str, parser_name: str):
    # import class from python package
    try:
        module = importlib.import_module(package_name)
        return getattr(module, parser_name)
    except ModuleNotFoundError as err:
        logging.fatal(f"module {package_name} was not found: {err}")
        sys.exit(1)
    except AttributeError:
        logging.fatal(f"there is no parser {parser_name}"
                      f" for package {package_name}")
        sys.exit(1)


def lookup_bucket(bucket_name: str, bucket_group: str, config_data: dict):
    bucket_group = config_data.get(bucket_group)
    if bucket_name not in [bucket["name"]
                           for bucket in bucket_group]:
        logging.fatal(f"bucket {bucket_name} was not found")
        sys.exit(1)
    return bucket_name


def load_bucket_config(bucket_name: str, bucket_group: str, config_data: dict):
    bucket_group = config_data.get(bucket_group)
    bucket_config = next((bucket for bucket in bucket_group
                          if bucket["name"] == bucket_name), None)
    if not bucket_config:
        logging.fatal(f"unable to find configuration "
                      f"for bucket {bucket_name}")
        sys.exit(1)
    logging.debug(f"bucket {bucket_name} config: {bucket_config}")
    return bucket_config


class CustomRemoteProgress(RemoteProgress):
    def __init__(self):
        """
        implementation of progress bar for git clone operations
        """
        super().__init__()
        self.pbar = tqdm()

    def update(self, op_code, cur_count, max_count=None, message=""):
        self.pbar.total = max_count
        self.pbar.n = cur_count
        self.pbar.refresh()


def _clone_remote_repo(self, folder, repo):
    # overwrite _clone_remote_repo of pydriller.repository class
    # to support 'progress' param in underlying Repo.clone_from
    # function call to implement progress bar
    repo_folder = os.path.join(folder, self._get_repo_name_from_url(repo))
    if os.path.isdir(repo_folder):
        logging.debug(f"Reusing folder {repo_folder} for {repo}")
    else:
        logging.debug(f"Cloning {repo} in temporary folder {repo_folder}")
        Repo.clone_from(url=repo, to_path=repo_folder,
                        progress=CustomRemoteProgress())
    return repo_folder

