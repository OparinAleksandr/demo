import os
import logging
import requests
import subprocess

from rd_config import wr_log
from rd_config import rd_token_env
from rd_config import mk_url_dom

# в зависимости от параметра "cloud" из файла conf
# получает iam токен для Яндекс-мониторинга
# при помощи Яндекс-функции iam/monitor_token
def get_iam_token():
    token = rd_token_env()
    url_dom = mk_url_dom()
    try:
        yc_url = f"https://{url_dom}.bit-erp.ru/iam/monitor_token"
        headers = {"Authorization": "Bearer " + token}
        request_yc = requests.get(yc_url, headers=headers)
        iam_token = request_yc.json()["iamToken"]
        folderId = request_yc.json()["folderId"]
        _set_env(iam_token, folderId)
    except Exception as exc:
        log_data = f"Error occurred when form monitoring url: {exc}"
        wr_log(log_data)



def _set_env(iam_token, folderId):
    iam_token_previous = os.environ.get("IAM_TOKEN")
    folderId_previous = os.environ.get("FOLDER_ID")
    if not iam_token_previous and not folderId_previous:
        try:
            subprocess.check_output(
                f"echo IAM_TOKEN={iam_token} >> /etc/environment", shell=True
            )
            logging.info("iam token is successfully write to /etc/environment")
            subprocess.check_output(
                f"echo FOLDER_ID={folderId} >> /etc/environment", shell=True
            )
            logging.info("folderId is successfully write to /etc/environment")
        except Exception as exc:
            logging.error(f"Error write environments: {exc}")
    else:
        subprocess.check_output(
            f'sed -i "s/IAM_TOKEN=.*/IAM_TOKEN={iam_token}/" /etc/environment', shell=True 
        )
        subprocess.check_output(
            f'sed -i "s/FOLDER_ID=.*/FOLDER_ID={folderId}/" /etc/environment', shell=True
        )

