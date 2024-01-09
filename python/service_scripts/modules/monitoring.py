#!/usr/bin/env python3

import os
import json
import time
import requests
import platform
import subprocess
from .config import config
from .log_config import logging_config

logger = logging_config(__name__, main_module=False)

def _set_env(iam_token, folderId):
    """
    устанавливает переменные окружения для токена и folderId  
    """

    iam_token_previous = os.environ.get("IAM_TOKEN")
    folderId_previous = os.environ.get("FOLDER_ID")
    if not iam_token_previous and not folderId_previous:
        try:
            subprocess.check_output(
                f"echo IAM_TOKEN={iam_token} >> /etc/environment", shell=True
            )
            logger.info("iam token is successfully write to /etc/environment")
            subprocess.check_output(
                f"echo FOLDER_ID={folderId} >> /etc/environment", shell=True
            )
            logger.info("folderId is successfully write to /etc/environment")
        except Exception as exc:
            logger.error(f"Error write environments: {exc}")
    else:
        subprocess.check_output(
            f'sed -i "s/IAM_TOKEN=.*/IAM_TOKEN={iam_token}/" /etc/environment', shell=True 
        )
        subprocess.check_output(
            f'sed -i "s/FOLDER_ID=.*/FOLDER_ID={folderId}/" /etc/environment', shell=True
        )


def mk_url_dom():
    """
    формирует url для отправки метрик в Яндекс-мониторинг
    """

    cloud = config()["cloud"]
    if cloud == "test":
        url_dom = "devapigwpriv"
    elif cloud == "prod":
        url_dom = "apigwpriv"
    return url_dom


def retry_attempts(func, attempts=20, delay=10, 
                    *args, **kwargs):
    """
    Вызывает функцию с повторными попытками
    """

    while attempts > 0:
        result = func(*args, **kwargs)
        if result:
            return result
        else:
            time.sleep(delay)
            attempts -= 1 
    else:
        return False


def get_iam_token():
    """
    в зависимости от параметра "cloud" из конфига
    получает iam токен для Яндекс-мониторинга
    при помощи Яндекс-функции iam/monitor_token    
    """

    def get_iam_token_func():
        yc_url = f"https://{mk_url_dom()}.bit-erp.ru/iam/monitor_token"
        headers = {"Authorization": f"Bearer {os.environ.get(config()['token_env'])}"}
        resp = requests.get(yc_url, headers=headers)
        if resp.ok:
            if platform.system() != "Windows":
                _set_env(resp.json()["iamToken"], resp.json()["folderId"])
            logger.debug("iam token is successfully get")
            return resp.json()
        else:
            logger.debug(f"Error occurred when form monitoring url: {resp.status_code} >> {resp.text}")
            return False
    
    return retry_attempts(get_iam_token_func)


def send_monitoring_metrics(name, metrics):
    """
    формирует url и параметры для отправки
    и отправляет массив метрик в мониторинг
    """

    def send_monitoring_metrics_func():
        if platform.system() == "Windows":
            token_folder = get_iam_token()
            iam_token = token_folder["iamToken"]
            folderId = token_folder["folderId"]
        else:
            iam_token = os.environ.get("IAM_TOKEN")
            folderId = os.environ.get("FOLDER_ID")
            if not iam_token and not folderId:
                logger.debug("iam token and folderId is not set")
                token_folder = get_iam_token()
                iam_token = token_folder["iamToken"]
                folderId = token_folder["folderId"]
        yc_url = (
        "https://monitoring.api.cloud.yandex.net/monitoring/v2/data/write?service=custom&folderId="
        + folderId
        )
        headers = {
            "Content-type": "application/json",
            "Accept": "*/*",
            "Authorization": "Bearer " + iam_token,
        }
        resp = requests.post(yc_url, data=json.dumps(metrics), headers=headers)
        if resp.ok:
            logger.debug(f"Monitoring for {os.path.basename(name)} is successfully send")
            return True
        else:
            logger.debug("Gen new iam token and folderId")
            token_folder = get_iam_token()
            iam_token = token_folder["iamToken"]
            folderId = token_folder["folderId"]
            logger.debug(f"Error when send metrics for {os.path.basename(name)}: {resp.status_code} >> {resp.text}")
            return False
    
    retry_attempts(send_monitoring_metrics_func)
