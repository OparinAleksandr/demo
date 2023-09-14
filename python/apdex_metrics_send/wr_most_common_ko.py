# записывает определённое параметором ko_number
# количество самых  часто встречающихся в
# xml файлах выгрузки ключевых операций

import os
import glob
import yaml
import logging
from collections import Counter
import xml.etree.ElementTree as ET
from logging.handlers import RotatingFileHandler

from conf import wr_log
from conf import rd_conf_file
from conf import rd_ko_number
from conf import rd_apdex_folder
from conf import get_current_dir


# получение данных из xml
# и формирования списка
# ключевых операций
def get_ko_from_xml():
    ko_names = []
    list_of_xml_files = glob.glob(rd_apdex_folder() + "*.xml")
    xml_root = None
    if list_of_xml_files:
        for xml_file in list_of_xml_files:
            if xml_file != list_of_xml_files:
                try:
                    xml_tree = ET.parse(xml_file)
                    xml_root = xml_tree.getroot()
                    for ko_from_xml in xml_root:
                        ko_from_xml_dict = ko_from_xml.attrib
                        ko_names.append(ko_from_xml_dict["nameFull"])
                except ET.ParseError as error:
                    log_data = f"File {xml_file} parsing error: {error}"
                    wr_log(log_data)
    else:
        log_data = "Apdex folder is empty"
        wr_log(log_data)
    return ko_names


# выборка самых часто
# встречающихся операций
# в количестве равном ko_number
def count_mertics(ko_names):
    ko_count = Counter(ko_names)
    return ko_count.most_common(rd_ko_number())


# запись самых часто встречающихся операций
# в конфиг файл
def wr_most_common_kos(most_common_kos):
    conf = rd_conf_file()
    try:
        conf["ko_names"]
    except:
        conf["ko_names"] = []

    def wr_ko_names():
        for most_common_ko in most_common_kos:
            if most_common_ko[0] not in conf["ko_names"]:
                conf["ko_names"].append(most_common_ko[0])
        return conf

    if conf["ko_names"]:
        wr_ko_names()
    else:
        conf["ko_names"] = []
        wr_ko_names()
    conf_file_name = "conf.yaml"
    try:
        with open(
            os.path.join(get_current_dir(), conf_file_name), "w", encoding="utf-8"
        ) as conf_file:
            yaml.dump(conf, conf_file, sort_keys=False, allow_unicode=True)
    except Exception as exc:
        log_data = f"Error occurred write conf.yaml: {exc}"
        wr_log(log_data)


def main():

    log_dir_path = os.path.join(get_current_dir(), "apdex_send_log")
    if not os.path.exists(log_dir_path):
        os.makedirs(log_dir_path)
    path_to_log_file = os.path.join(log_dir_path, "wr_most_common_ko.log")
    logging.basicConfig(
        handlers=[
            RotatingFileHandler(path_to_log_file, maxBytes=300000, backupCount=5)
        ],
        level=logging.DEBUG,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    wr_most_common_kos(count_mertics(get_ko_from_xml()))


if __name__ == "__main__":
    main()
