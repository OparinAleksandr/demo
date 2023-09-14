#!/usr/bin/python3

import os
import copy
import json
import time
import requests
import subprocess
import logging
from logging.handlers import RotatingFileHandler

from rd_config import wr_log
from rd_config import rd_server_name
from rd_config import rd_project_name
from rd_config import rd_services_names

from get_iam import get_iam_token

# проверка статуса службы
def service_status(service_name):
    service_status = subprocess.run(['systemctl', 'is-active', service_name], 
                            capture_output=True, 
                            text=True).stdout.strip()
    log_data = f"Service {service_name} is {service_status}"
    wr_log(log_data)
    if service_status == 'active':
        return True
    else:
        return False   


# формирует массив метрик
def form_metrics(services_names):
    srv_name = rd_server_name()
    prj_name = rd_project_name()
    metrics_array = []
    metrics_data = {
        "name": "service_monitoring",
        "labels": {
            "project_name": prj_name,
            "server_name": srv_name,
        },
        "value": "",
    }
    for service_name in services_names.split(','):
        service_metrics = copy.deepcopy(metrics_data) 
        service_metrics["labels"]["service_name"] = service_name
        if service_status(service_name):
            service_metrics["value"] = 1
        else:
            service_metrics["value"] = -1
        metrics_array.append(service_metrics) 

    service_metrics = {"metrics": metrics_array}
    return service_metrics


# формирует url для отправки
# и отправляет массив метрик в мониторинг
def send_metrics(service_metrics):
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
        resp = requests.post(yc_url, data=json.dumps(service_metrics), headers=headers)
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
    log_dir_path = os.path.join(current_dir, "service_monitoring")
    if not os.path.exists(log_dir_path):
        os.makedirs(log_dir_path)
    log_file_path = os.path.join(log_dir_path, "service_monitoring.log")
    logging.basicConfig(
        handlers=[
            RotatingFileHandler(log_file_path, maxBytes=300000, backupCount=5),
            logging.StreamHandler(),
        ],
        level=logging.DEBUG,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    service_metrics = form_metrics(rd_services_names())
    for i in range(attempts):
        if send_metrics(service_metrics):
            log_data = f"Attempt num: {i}"
            wr_log(log_data)
            time.sleep(20)
            continue
        else:
            break


if __name__ == "__main__":
    main()