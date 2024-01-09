#!/usr/bin/env python3

import os
import sys
import yaml
import subprocess
from .log_config import logging_config

PARENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PARENT_DIR, "conf.yml")
logger = logging_config(__name__, main_module=False)


def config():
    """
    запускает скрипт формирования конфига, если файл конфига не существует
    возвращает словарь с конфигом
    """

    mk_config_file_name = "make_config.py"
    mk_config_file_path = os.path.join(PARENT_DIR, mk_config_file_name)
    conf_dict = {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as conf_file:
            conf_dict = yaml.safe_load(conf_file)
            return conf_dict
    except FileNotFoundError:
        subprocess.call(f"python3 {mk_config_file_path}", shell=True)
        logger.warning(
            f"{CONFIG_PATH} does not exist and will be created, "
            + "run the script again to send the metrics"
        )
        sys.exit()
    except yaml.YAMLError:
        logger.error(
            f"Error in the configuration file {CONFIG_PATH}, "
            + "run the script again to send the metrics"
        )
        sys.exit()