from utils import import_parser, load_config_file
from utils import load_bucket_config, lookup_bucket
import argparse
import logging


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config_file",
                        help="buckets configuration file path",
                        action="store",
                        type=str,
                        required=True)
    parser.add_argument("--releases_file",
                        help="releases file path that contains"
                             " additional commit information"
                             " to merge with buckets config file",
                        action="store",
                        type=str,
                        required=False)
    parser.add_argument("-d", "--debug",
                        help="debug mode",
                        action="store_true",
                        required=False)
    return parser.parse_args()


def process_bucket(bucket_name: str, bucket_group: str, config_data: dict,
                   repo_extra_params: dict = None):
    # repo_extra_params is a dictionary to pass additional
    # parameters to repository_params arguments of parser classes
    parsers_package = "parsers"
    bucket_name = lookup_bucket(bucket_name, bucket_group, config_data)
    bucket_config = load_bucket_config(bucket_name,
                                       bucket_group,
                                       config_data)
    bucket_parser = import_parser(parsers_package, bucket_config.get("parser"))
    repo_params = {**bucket_config.get("repository_params"),
                   **(repo_extra_params or {})}
    parser_params = bucket_config.get("parser_params")
    return bucket_parser(repo_params, parser_params)


def main():
    args = get_arguments()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO,
                        format="%(asctime)s - "
                               "%(name)s - "
                               "%(levelname)s - "
                               "%(message)s")
    logging.getLogger("pydriller").setLevel(logging.DEBUG if args.debug
                                            else logging.WARNING)

    config_data = load_config_file(args.config_file)
    bucket_key = "buckets"

    # process releases file if provided
    if args.releases_file:

        logging.info(f"releases file was provided - processing it "
                     f"based on default configuration file {args.config_file}")

        release_data = load_config_file(args.releases_file)

        for release_bucket in release_data.get("buckets"):
            # look up bucket with a similar name in config file
            bucket_name = lookup_bucket(release_bucket["name"], bucket_key, config_data)
            logging.info(f"processing release bucket {bucket_name}")
            # look up release bucket configuration in releases file
            release_bucket_config = load_bucket_config(bucket_name,
                                                       bucket_key,
                                                       release_data)
            release_commit_data = release_bucket_config["commits"]
            # set additional parameters for parent bucket parser call
            extra_repo_params = {
                "to_commit": release_commit_data["to_commit"],
                "from_commit": release_commit_data["from_commit"]
            }
            process_bucket(bucket_name, bucket_key, config_data,
                           extra_repo_params)

    # process default config yaml if releases file is not provided
    else:
        logging.info(f"releases file was not provided - "
                     f"processing default configuration file {args.config_file}")

        for bucket in config_data.get("buckets"):
            bucket_name = bucket["name"]
            process_bucket(bucket_name, bucket_key, config_data)


if __name__ == "__main__":
    main()
