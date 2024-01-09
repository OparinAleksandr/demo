#!/usr/bin/env python3

import copy
import json
import psutil
import platform
import subprocess
import sqlite3 as sl
from modules.config import config
from modules.log_config import logging_config
from modules.monitoring import send_monitoring_metrics

logger = logging_config(__file__, main_module=True)

def get_disk_partitions():
    """
    формирует список разделов и путей
    для дисков linux, фильтрует разделы
    boot, swap и размером меньше 1ГБ
    """

    disk_partitions = {}
    try:
        lsblk = json.loads(
            subprocess.check_output(
                "lsblk --json -b -o NAME,MOUNTPOINT,SIZE,PATH", shell=True
            )
        )
    except Exception as exc:
        logger.error(f"Error get lsblk json: {exc}")

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


def metrics():
    """
    формирует массив метрик
    с доступным ресурсом ЦПУ в %
    с доступным объёмом оперативной памяти в %
    и доступным свободным местом на дисках в %
    """

    conf = config()["client"]
    srv_name = conf["server_name"]
    prj_name = conf["project_name"]
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
    logger.debug(f"CPU metrics {cpu_metrics}")
    ram_available = round(100 - psutil.virtual_memory().percent, 0)
    ram_metrics = copy.deepcopy(metrics_data)
    ram_metrics["labels"]["ram"] = "ram_available_%"
    ram_metrics["value"] = ram_available
    metrics_array.append(ram_metrics)
    logger.debug(f"RAM metrics {ram_metrics}")
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
                    logger.debug(f"HDD metrics {hdd_metrics}")
            except OSError as error:
                logger.debug(f"Error to get space on drive {drive} {error}")
    else:
        for partition, name in get_disk_partitions().items():
            try:
                disk_available = round(100 - psutil.disk_usage(partition).percent)
                hdd_metrics = copy.deepcopy(metrics_data)
                hdd_metrics["labels"]["hdd"] = "hdd_available_%"
                hdd_metrics["labels"]["drive"] = name
                hdd_metrics["value"] = disk_available
                metrics_array.append(hdd_metrics)
                logger.debug(f"HDD metrics {hdd_metrics}")
            except OSError as error:
                logger.debug(f"Error to get space on disk {error}")
    hardware_metrics = {"metrics": metrics_array}
    return hardware_metrics


def main():
    send_monitoring_metrics(__file__, metrics())


if __name__ == "__main__":
    main()
