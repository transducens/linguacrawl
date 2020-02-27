#!/usr/bin/env python3

from cerberus import Validator
import argparse
import signal
import sys
from multi_site_crawler import MultiSiteCrawler
import yaml
import os
from bitext_scout import BitextScout

# SET THE SEED FOR REPRODUCIBILITY TESTS
# SEED=4
# random.seed(SEED)


def validate_config(config):
    schema = {
        'user_agent': {'required': True, 'type': 'string'},
        'langs_of_interest': {'required': True, 'type': 'list'},
        'crawl_delay': {'required': False, 'type': 'integer', 'default': 3},
        'max_time_per_site': {'required': False, 'type': 'integer'},
        'max_size_per_site': {'required': False, 'type': 'integer'},
        'connection_timeout': {'required': False, 'type': 'integer'},
        'max_jobs': {'required': False, 'type': 'integer', 'default': 1},
        'resume_crawling': {'required': False, 'type': 'boolean', 'default': False},
        'accepted_tlds': {'required': False, 'type': 'list'},
        'seed_urls': {'required': False, 'type': 'list'},
        'seed_urls_from_file': {'required': False, 'type': 'string'},
        'prefix_filter': {'required': False, 'type': 'string', 'default': ''},
        'output_dir': {'required': True, 'type': 'string'},
        'verbose': {'required': False, 'type': 'boolean', 'default': False},
        'accepted_content': {'required': False, 'type': 'string', 'default': '(text/html)'},
        'max_folder_tree_depth': {'required': False, 'type': 'integer', 'default': 20},
        'max_attempts': {'required': False, 'type': 'integer', 'default': 3},
        'scout_steps': {'required': False, 'type': 'integer', 'default': 200},
        'min_langs_in_site': {'required': False, 'type': 'integer', 'default': 2},
        'mandatory_lang': {'required': False, 'type': 'string', 'default': None},
        'min_percent_mandatory_lang': {'required': False, 'type': 'integer', 'default': 10},
        'url_blacklist': {'required': False, 'type': 'list', 'default': []}
    }

    v = Validator(schema)
    b = v.validate(config)

    if not b:
        sys.stderr.write("Validation error. Stopping: "+str(v.errors))
        exit(-1)

    if "seed_urls" not in config and "seed_urls_from_file" not in config:
        sys.stderr.write("A set of seed URLs must be provided, either setting option 'seed_urls' (list of URLs) or "
                         + "'seed_urls_from_file' (path to a file with a list of URLs)\n")
        exit(-1)

    os.makedirs(config["output_dir"], exist_ok=True)
    return v.normalized(config)


oparser = argparse.ArgumentParser(
    description="Script that crawls a website and prints the downloaded documents"
                "in standard output using WARC format.")
oparser.add_argument("config", metavar="FILE", nargs="?", help="Config file of the crawler", default=None)
options = oparser.parse_args()

with open(options.config, 'r') as ymlfile:
    config = yaml.safe_load(ymlfile)

config = validate_config(config)

seed_urls = []
if config["seed_urls"] is None:
    with open(config.seed_urls_from_file, "r") as reader:
        for line in reader:
            seed_urls.append(line.strip())
else:
    for line in config["seed_urls"]:
        seed_urls.append(line)

crawler = MultiSiteCrawler(config, BitextScout(config["scout_steps"], config["langs_of_interest"], config["min_langs_in_site"],
                                               config["mandatory_lang"], config["min_percent_mandatory_lang"]))

# crawler.add_url_filter('\.(jpg|jpeg|gif|png|js|css|swf)$')
signal.signal(signal.SIGTERM, crawler.termsighandler)
signal.signal(signal.SIGINT, crawler.termsighandler)
crawler.start_crawling()
