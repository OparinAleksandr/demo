# общая логика для
# чтения конфиг файла
import os
import yaml
import codecs
import logging
from logging.handlers import RotatingFileHandler


def get_current_dir():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return current_dir


def wr_log(log_data):
    logger = logging.getLogger()
    logger.debug(log_data)


def rd_conf_file():

    conf_file_name = "conf.yaml"
    with codecs.open(
        os.path.join(get_current_dir(), conf_file_name), encoding="utf-8"
    ) as conf_file:
        return yaml.safe_load(conf_file)


conf = rd_conf_file()


def rd_env():
    return os.environ.get(conf.get("env"))


def rd_project():
    return conf.get("project")


def rd_base():
    return conf.get("base")


def rd_ko_number():
    return conf.get("ko_number")


def rd_ko_names():
    return conf.get("ko_names")


def rd_apdex_folder():
    return conf.get("apdex_folder")


def rd_time_zone():
    return conf.get("time_zone")


def mk_url_dom():
    cloud = conf.get("cloud")
    if cloud == "test":
        url_dom = "devapigwpriv"
    elif cloud == "prod":
        url_dom = "apigwpriv"
    else:
        url_dom = "apigwpriv"
    return url_dom
