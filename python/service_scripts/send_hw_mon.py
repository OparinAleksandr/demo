# отправляет метрики в Яндекс-мониторинг
# по нагрузке аппаратных ресурсов

import os
import copy
import time
import json
import psutil
import logging
import requests
import platform
import subprocess
from logging.handlers import RotatingFileHandler

from rd_config import wr_log
from rd_config import rd_server_name
from rd_config import rd_project_name

from get_iam import get_iam_token


# формирует список разделов и путей
# для дисков linux, фильтрует разделы
# boot, swap и размером меньше 1ГБ
def get_disk_partitions():
    disk_partitions = {}
    try:
        lsblk = json.loads(
            subprocess.check_output(
                "lsblk --json -b -o NAME,MOUNTPOINT,SIZE,PATH", shell=True
            )
        )
    except Exception as exc:
        logging.error(f"Error get lsblk json: {exc}")

    def not_in_black_lst(blockdevice):
        in_list = 0
        GB = 1073741824
        checked = []
        black_lst = ["boot", "SWAP"]
        mountpoint = blockdevice["mountpoint"]
        size = blockdevice["size"]
        if mountpoint and size > GB:
            for mount in black_lst:
                if mountpoint not in checked:
                    if mount not in mountpoint:
                        checked.append(mountpoint)
                        in_list = 1
                        break
                    else:
                        checked.append(mountpoint)
                        in_list = 0
        else:
            in_list = 0
        return in_list

    for blockdevice in lsblk["blockdevices"]:
        child = blockdevice.get("children")
        if child != None:
            for child in blockdevice["children"]:
                if not_in_black_lst(child):
                    disk_partitions[child["mountpoint"]] = child["path"]
                sub_children = child.get("children")
                if sub_children != None:
                    for sub_child in sub_children:
                        if not_in_black_lst(sub_child):
                            disk_partitions[sub_child["mountpoint"]] = sub_child["path"]
        else:
            if not_in_black_lst(blockdevice):
                disk_partitions[blockdevice.get("mountpoint")] = blockdevice.get("path")

    return disk_partitions


# формирует массив метрик
# с доступным ресурсом ЦПУ в %
# с доступным объёмом оперативной памяти в %
# и доступным свободным местом на дисках в %
def form_metrics():
    srv_name = rd_server_name()
    prj_name = rd_project_name()
    metrics_array = []
    metrics_data = {
        "name": "hardware_server_monitoring",
        "labels": {
            "project_name": prj_name,
            "server_name": srv_name,
        },
        "value": "",
    }
    cpu_available = round(100 - psutil.cpu_percent(4), 0)
    cpu_metrics = copy.deepcopy(metrics_data)
    cpu_metrics["labels"]["cpu"] = "cpu_available_%"
    cpu_metrics["value"] = cpu_available
    metrics_array.append(cpu_metrics)
    log_data = f"CPU metrics {cpu_metrics}"
    wr_log(log_data)
    ram_available = round(100 - psutil.virtual_memory().percent, 0)
    ram_metrics = copy.deepcopy(metrics_data)
    ram_metrics["labels"]["ram"] = "ram_available_%"
    ram_metrics["value"] = ram_available
    metrics_array.append(ram_metrics)
    log_data = f"RAM metrics {ram_metrics}"
    wr_log(log_data)
    if platform.system() == "Windows":
        for sdiskpart in psutil.disk_partitions():
            try:
                drive = sdiskpart.device.split("\\")[0]
                fstype = sdiskpart.fstype
                disk_available = round(
                    100 - psutil.disk_usage(sdiskpart.device).percent, 0
                )
                if fstype != "CDFS":
                    hdd_metrics = copy.deepcopy(metrics_data)
                    hdd_metrics["labels"]["hdd"] = "hdd_available_%"
                    hdd_metrics["labels"]["drive"] = drive
                    hdd_metrics["value"] = disk_available
                    metrics_array.append(hdd_metrics)
                    log_data = f"HDD metrics {hdd_metrics}"
                    wr_log(log_data)
            except OSError as error:
                log_data = f"Error to get space on drive {drive} {error}"
                wr_log(log_data)
    else:
        for partition, name in get_disk_partitions().items():
            try:
                disk_available = round(100 - psutil.disk_usage(partition).percent)
                hdd_metrics = copy.deepcopy(metrics_data)
                hdd_metrics["labels"]["hdd"] = "hdd_available_%"
                hdd_metrics["labels"]["drive"] = name
                hdd_metrics["value"] = disk_available
                metrics_array.append(hdd_metrics)
                log_data = f"HDD metrics {hdd_metrics}"
                wr_log(log_data)
            except OSError as error:
                log_data = f"Error to get space on disk {error}"
                wr_log(log_data)
    hardware_metrics = {"metrics": metrics_array}
    return hardware_metrics


# формирует url для отправки
# и отправляет массив метрик в мониторинг
def send_metrics(hardware_metrics):
    send_error = 0
    iam_token = os.environ.get("IAM_TOKEN")
    folderId = os.environ.get("FOLDER_ID")
    if not iam_token and not folderId:
        get_iam_token()
        iam_token = os.environ.get("IAM_TOKEN")
        folderId = os.environ.get("FOLDER_ID")
    yc_url = (
        "https://monitoring.api.cloud.yandex.net/monitoring/v2/data/write?service=custom&folderId="
        + folderId
    )
    headers = {
        "Content-type": "application/json",
        "Accept": "*/*",
        "Authorization": "Bearer " + iam_token,
    }
    try:
        resp = requests.post(yc_url, data=json.dumps(hardware_metrics), headers=headers)
        if resp.status_code == 200:
            log_data = f"Monitoring for hardware is successfully send"
            wr_log(log_data)
        elif resp.status_code > 400:
            get_iam_token()
            log_data = f"Get iam token and folderId"
            wr_log(log_data)
    except Exception as exc:
        log_data = f"Error occurred when metrics send: {exc}"
        wr_log(log_data)
        send_error = 1
    return send_error


# формирует и отправляет метрики
# используя 10 попыток
def main():
    attempts = 10
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir_path = os.path.join(current_dir, "send_hw_log")
    if not os.path.exists(log_dir_path):
        os.makedirs(log_dir_path)
    log_file_path = os.path.join(log_dir_path, "send_hw_mon.log")
    logging.basicConfig(
        handlers=[
            RotatingFileHandler(log_file_path, maxBytes=300000, backupCount=5),
            logging.StreamHandler(),
        ],
        level=logging.DEBUG,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    hardware_metrics = form_metrics()
    for i in range(attempts):
        if send_metrics(hardware_metrics):
            log_data = f"Attempt num: {i}"
            wr_log(log_data)
            time.sleep(20)
            continue
        else:
            break


if __name__ == "__main__":
    main()
