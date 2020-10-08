import os
import logging.config
import yaml

calling_dir = os.path.dirname(os.path.abspath(__file__))

config_file = os.path.join(calling_dir, 'logging.yml')

with open(config_file, 'r') as f:
    log_cfg = yaml.safe_load(f.read())

logging.config.dictConfig(log_cfg)
