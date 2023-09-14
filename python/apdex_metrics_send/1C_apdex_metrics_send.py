# из xml файлов
# считывает время выполнения
# для ключевых операций из конфига,
# отправляет в яндекс мониторинг

import os
import glob
import json
import logging
import requests
import xml.etree.ElementTree as ET
from transliterate import translit
from logging.handlers import RotatingFileHandler

from conf import rd_env
from conf import wr_log
from conf import rd_base
from conf import mk_url_dom
from conf import rd_project
from conf import rd_ko_names
from conf import rd_time_zone
from conf import rd_apdex_folder
from conf import get_current_dir


# читает имя последнего xml файла,
# с предыдущего запуска
# для сравнения его имени
# с именами файлов из каталога
def rd_last_xml_from_file(current_dir):
    last_read_xml_file = os.path.join(current_dir, "last_read_xml.log")
    try:
        with open(last_read_xml_file) as last_read_xml_file:
            last_read_xml = last_read_xml_file.readline()
        if last_read_xml:
            log_data = f"get metrics from {last_read_xml}"
            wr_log(log_data)
            return last_read_xml
        else:
            log_data = f"get metrics from last xml file in folder"
            wr_log(log_data)
            last_read_xml = 0
            return last_read_xml

    except Exception as exc:
        log_data = (
            f"Error occurred {exc} when read last_read_xml.log, "
            + "will be taken last xml file in folder"
        )
        wr_log(log_data)
        last_read_xml = 0
        return last_read_xml


# формирует список новых xml файлов из каталога на основе
# последнего считанного файла после предыдущего запуска
def mk_ls_of_new_xml_files(last_read_xml):
    new_xml_files = None
    try:
        xml_files_ls = glob.glob(rd_apdex_folder() + "*.xml")
        if last_read_xml:
            len_list_of_files = len(xml_files_ls)
            if last_read_xml in xml_files_ls:
                last_read_file_index = xml_files_ls.index(last_read_xml)
                if last_read_file_index < len_list_of_files - 1:
                    new_xml_files = xml_files_ls[
                        last_read_file_index + 1 : len_list_of_files
                    ]
                else:
                    new_xml_files = [max(xml_files_ls)]
            else:
                new_xml_files = [max(xml_files_ls)]
        else:
            new_xml_files = [max(xml_files_ls)]
    except Exception as exc:
        log_data = f"Error ocurred {exc} and will be taken last xml file in folder"
        wr_log(log_data)
    return new_xml_files


# распарсивает xml файлы из списка для формирования метрик
def get_data_from_xml(new_xml_files, last_read_xml_file):
    xml_files_roots = {}
    if new_xml_files:
        for xml_file in new_xml_files:
            if xml_file != last_read_xml_file:
                try:
                    xml_tree = ET.parse(xml_file)
                    xml_root = xml_tree.getroot()
                    xml_files_roots[xml_file] = xml_root
                except ET.ParseError as error:
                    log_data = f"File {xml_file} parsing error: {error}"
                    wr_log(log_data)
        return xml_files_roots
    else:
        log_data = "Apdex folder is empty"
        wr_log(log_data)


# считывает время выполнения для ключевых операций из конфига
# из списка xml файлов и формирует метрики, для отправки в мониторинг
def form_metrics(xml_file, xml_root, ko_names, project, base, time_zone):
    metrics_array = []
    if xml_root:
        for ko_name in ko_names:
            for ko_from_xml in xml_root:
                ko_from_xml_dict = ko_from_xml.attrib
                translit_ko_from_xml = translit(
                    ko_from_xml_dict["nameFull"], reversed=True
                ).replace("'", "_")
                translit_ko_from_xml = translit_ko_from_xml.replace(" ", "_")
                if ko_from_xml_dict["nameFull"] == ko_name:
                    log_data = (
                        f"Get metrics for {translit_ko_from_xml} from file {xml_file}"
                    )
                    wr_log(log_data)
                    for measurement in ko_from_xml:
                        measurement_dict = measurement.attrib
                        key_operation = translit_ko_from_xml
                        value = float(measurement_dict["value"])
                        ts = measurement_dict["tSaveUTC"] + time_zone
                        metrics_data = {
                            "name": "apdex",
                            "labels": {
                                "project_name": project,
                                "base_name": base,
                                "key_operation": key_operation,
                            },
                            "ts": ts,
                            "value": value,
                        }
                        metrics_array.append(metrics_data)
    else:
        log_data = f"{xml_file} does not contain any data"
        wr_log(log_data)
    apdex_metrics = {"metrics": metrics_array}
    log_data = {"metrics": metrics_array}
    wr_log(log_data)
    return apdex_metrics


# отправка метрик в монитороинг
def send_metrics(apdex_metrics, xml_file, url_dom, env):
    metrics_send = False
    try:
        yc_url = f"https://{url_dom}.bit-erp.ru/iam/monitor_token"
        headers = {"Authorization": "Bearer " + env}
        request_yc = requests.get(yc_url, headers=headers)
        iam_token = request_yc.json()["iamToken"]
        folderId = request_yc.json()["folderId"]
        yc_url = (
            "https://monitoring.api.cloud.yandex.net/monitoring/v2/data/write?service=custom&folderId="
            + folderId
        )
        headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": "Bearer " + iam_token,
        }
    except Exception as exc:
        log_data = f"Error occurred when form monitoring url: {exc}"
        wr_log(log_data)
    if apdex_metrics["metrics"]:
        try:
            requests.post(yc_url, data=json.dumps(apdex_metrics), headers=headers)
            log_data = f"Metrics for file {xml_file} are successfully send"
            wr_log(log_data)
            metrics_send = True
        except Exception as exc:
            log_data = f"Error occurred when metrics send: {exc}"
            wr_log(log_data)
    else:
        log_data = f"Metrics are empty, nothing to send from file {xml_file}"
        wr_log(log_data)
    return metrics_send


# запись имени последнего считанного xml в лог
def write_last_read_xml(last_read_xml, log_dir_path):
    try:
        with open(
            os.path.join(log_dir_path, "last_read_xml.log"), "w+"
        ) as last_read_xml_file_log:
            last_read_xml_file_log.write(last_read_xml)
        log_data = f"File {last_read_xml} write at last_read_xml_file.log"
        wr_log(log_data)
    except Exception as exc:
        log_data = f"Error occurred write last_read_xml_file_log: {exc}"
        wr_log(log_data)


def main():
    env = rd_env()
    base = rd_base()
    project = rd_project()
    ko_names = rd_ko_names()
    current_dir = get_current_dir()
    time_zone = rd_time_zone()
    url_dom = mk_url_dom()
    log_dir_path = os.path.join(current_dir, "apdex_send_log")
    if not os.path.exists(log_dir_path):
        os.makedirs(log_dir_path)
    path_to_log_file = os.path.join(log_dir_path, "apdex_metrics_send.log")
    logging.basicConfig(
        handlers=[
            RotatingFileHandler(path_to_log_file, maxBytes=300000, backupCount=5)
        ],
        level=logging.DEBUG,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    last_read_xml = rd_last_xml_from_file(current_dir)
    new_xml_files = mk_ls_of_new_xml_files(last_read_xml)
    xml_files_roots = get_data_from_xml(new_xml_files, last_read_xml)
    if xml_files_roots:
        for xml_file, xml_root in xml_files_roots.items():
            metrics_send = send_metrics(
                form_metrics(xml_file, xml_root, ko_names, project, base, time_zone),
                xml_file,
                url_dom,
                env,
            )
            if metrics_send:
                write_last_read_xml(xml_file, log_dir_path)


if __name__ == "__main__":
    main()
