#!/usr/bin/env python3

import os
import glob
import json
import requests
import argparse
from tqdm import tqdm
import concurrent.futures
from datetime import datetime
from tqdm.utils import CallbackIOWrapper
from modules.files import *
from modules.config import config
from modules.log_config import logging_config
from modules.monitoring import send_monitoring_metrics, mk_url_dom, retry_attempts



def get_args():
    parser = argparse.ArgumentParser(description="Отправляет бэкапы БД на S3.")
    parser.add_argument(
        "--launch_period",
        default="daily",
        type=str,
        help="Время запуска, daily - ежедневный бэкап, weekly - еженедельный",
    )
    parser.add_argument(
        "--backup_type",
        default="db",
        type=str,
        help="Тип бэкапа: db - бэкап базы, files - файлов, sonar - для ВМ с сонаром",
    )
    args = parser.parse_args()
    return vars(args)


launch_period = get_args().get("launch_period")
logger = logging_config(f"{launch_period}_{__file__}", main_module=True)
CONFIG = config()

def mk_ls_last_bak_files_from_log(last_bak_log_file):
    """
    создаёт список последних считанных файлов из лога
    для сравнения с файлами из каталогов
    """

    last_bak_files_from_log = []
    try:
        with open(last_bak_log_file) as last_bak_log_file:
            last_bak_files_from_log = last_bak_log_file.read().splitlines()
        if last_bak_files_from_log:
            return last_bak_files_from_log
        else:
            logger.debug(f"File {last_bak_log_file} empty, last files in folders are will be zipped")
            last_bak_files_from_log = []
            return last_bak_files_from_log
    except:
        logger.debug(f"Error occurred when read {last_bak_log_file}, last files in folders are will be zipped")
        last_bak_files_from_log = []
        return last_bak_files_from_log


def mk_ls_last_bak_files_from_folders(backup_type):
    """
    создаёт список файлов из катлогов для сравнения со списком из лога
    """

    bak_files_path = CONFIG[f"{backup_type}_backup_conf"]["backup_path"]
    folders_ls = []
    ls_of_last_files = []
    ls_of_bak_files = []
    for root, folders, files in os.walk(bak_files_path):
        if folders != []:
            for folder in folders:
                folders_ls.append(os.path.join(root, folder))
        else:
            folders_ls.append(bak_files_path)
    for folder in folders_ls:
        ls_of_bak_files.append(glob.glob(os.path.join(folder, "*.ba*")))
    for bak_file in ls_of_bak_files:
        if bak_file:
            ls_of_last_files.append(max(bak_file))
    logger.debug(f"List of last files in folders: {ls_of_last_files}")
    return ls_of_last_files, bak_files_path


def mk_ls_of_last_bak_files(last_bak_log_file, backup_type):
    """
    сравнивает два списка файлов и возвращает список для отправки
    """

    ls_last_bak_files_from_log = mk_ls_last_bak_files_from_log(last_bak_log_file)
    ls_last_bak_files_from_folders, bak_files_path = mk_ls_last_bak_files_from_folders(backup_type)
    if ls_last_bak_files_from_log == ls_last_bak_files_from_folders:
        ls_of_last_bak_files = []
        logger.debug(
            f"All files in list from {last_bak_log_file} has already been sent "
            + f"and there are no new files in folder {bak_files_path}"
        )
    else:
        ls_of_last_bak_files = list(
            set(ls_last_bak_files_from_folders) - set(ls_last_bak_files_from_log)
        )
    return ls_of_last_bak_files


def bak_file_size(last_bak_file_name):
    """
    определяет объём файла\директории бэкапа
    """

    last_bak_file_size = 0
    if os.path.isdir(last_bak_file_name):
        for element in os.scandir(last_bak_file_name):
            last_bak_file_size += os.path.getsize(element)
    else:
        last_bak_file_size = os.path.getsize(last_bak_file_name)
    return last_bak_file_size


def zip_last_bak_file(token, last_bak_file_name, zip_files_path):
    """
    архивирует бэкапы, разделяя на части,
    если размер бэкапа больше 100Мб
    для отправки больших файлов частями
    возвращает флаг successfully_zipped и имя бэкапа
    """

    destination_file_name = os.path.splitext(os.path.basename(last_bak_file_name))[0]
    zip_prog = zip_prog_path()
    destination_file = os.path.join(zip_files_path, destination_file_name + ".zip")
    source_file = last_bak_file_name
    if bak_file_size(last_bak_file_name) > 100_000_000:
        zip_command = f""""{zip_prog}" a -ssw -v50M -mx5 -p{token} -mmt=2 -r0 {destination_file} {source_file}"""
    else:
        zip_command = f""""{zip_prog}" a -ssw -mx5 -p{token} -mmt=2 -r0 {destination_file} {source_file}"""
    zip_result = os.system(f"{zip_command}")
    if zip_result == 0:
        logger.debug(f"File {source_file} successfully zipped")
        successfully_zipped = 1
    else:
        logger.debug(f"File {source_file} not zipped")
        successfully_zipped = 0
    return successfully_zipped, source_file


def rd_ls_of_zip_files(zip_files_path, source_file):
    """
    создаёт список томов архива для получения ссылки на каждый том
    """

    ls_of_zip_parts = glob.glob(zip_files_path + "*.zip*")
    logger.debug(f"File {source_file} is successfully zipped and split by {len(ls_of_zip_parts)} parts")
    return ls_of_zip_parts
 

def get_presigned_link(headers, policy, amount, zip_file_name):
    """
    получает ссылку для загрузки каждого тома архива из списка
    """

    def get_presigned_link_func():
        try:
            yc_url = f"https://{mk_url_dom()}.bit-erp.ru/v2/s3/put/{policy}/{zip_file_name}"
            amount_of_parts = json.dumps({"amount": amount})
            response = requests.post(yc_url, data=amount_of_parts, headers=headers)
            logger.debug(f"Links is taken for file {zip_file_name}")
            return response.json()
        except:
            logger.debug(f"Presigned link is not taken for file {zip_file_name}")
            return False
    return retry_attempts(get_presigned_link_func)


def complete_upload(headers, complete_url):
    """
    запрос на сборку архива
    """
    def complete_upload_func():
        try:
            resp = requests.get(complete_url, headers=headers)
            if resp.status_code == 200:
                logger.debug("File is successfully upload to s3 and assembled")
                return True
        except Exception as exc:
            logger.debug(f"File is successfully upload to s3 but did not assembled because of exception {exc}")
            return False
    return retry_attempts(complete_upload_func)


def upload_part(file_name, presigned_link, part_number, amount):
    """
    загружает часть архива
    """

    def upload_part_func():
        try:
            file_size = os.stat(file_name).st_size
            with open(file_name, "rb") as binary_data:
                with tqdm(
                    total=file_size, unit="B", unit_scale=True, unit_divisor=1024,
                    desc=f"upload {part_number}/{amount} >>"
                ) as pr_bar:
                    wrapped_file = CallbackIOWrapper(
                        pr_bar.update, binary_data, "read"
                    )
                    requests.put(presigned_link, data=wrapped_file, timeout=60)
            return True
        except Exception as exc:
            log_data = f"File {file_name} is not upload to s3, exception {exc}"
            logger.debug(log_data)
            return False
    return retry_attempts(upload_part_func)


def s3_upload(token, policy, ls_of_zip_parts, timeout=120, max_workers=4):
    """
    в зависимости от параметров "cloud" и "ydb_policy" в конфиге
    получает ссылку для загрузки каждого тома архива из списка
    загружает все части в бакет S3
    в случае успешной загрузки даёт команду яндекс функции на сборку файлов
    """

    successfully_uploaded = False
    amount = len(ls_of_zip_parts)
    headers = {"Authorization": "Bearer " + token}
    if amount > 1:
        zip_file_name = str(os.path.splitext(os.path.basename(ls_of_zip_parts[0]))[0])
    else:
        zip_file_name = str(os.path.basename(ls_of_zip_parts[0]))
    links = get_presigned_link(headers, policy, amount, zip_file_name)
    if not links:
        successfully_uploaded = False
        logger.debug(f"File {zip_file_name} is not uploaded, presigned link is not taken")
        return successfully_uploaded
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        part_number = 1
        for file_name, presigned_link in zip(sorted(ls_of_zip_parts), links.get("partUrls")):
            futures.append(executor.submit(upload_part, file_name, presigned_link, part_number, amount))
            part_number += 1

        completed, _ = concurrent.futures.wait(futures, timeout=timeout)

        concurrently_uploaded = all(future.result() for future in completed)
        
        if concurrently_uploaded:
            successfully_uploaded = True
        else:
            for future in futures:
                future.cancel()
            concurrent.futures.wait(futures)
            successfully_uploaded = False
            logger.debug(f"File {zip_file_name} is not uploaded, concurrently uploading is not completed")

    if successfully_uploaded:
        if complete_upload(headers, links.get("complete")):
            successfully_uploaded = True
        else:
            successfully_uploaded = False

    return successfully_uploaded


def wr_ls_of_last_bak_files(last_bak_log_file, ls_bak_file_names=[]):
    """
    записывает последний отправленный файл в лог
    """

    if ls_bak_file_names:
        try:
            with open(last_bak_log_file, "w+") as last_bak_log_file:
                for bak_file_name in ls_bak_file_names:
                    last_bak_log_file.write(bak_file_name + "\n")
            logger.debug(f"File last_bak_files_{launch_period}.log is successfully wrote")
        except Exception as exc:
            logger.debug(f"Error occurred when write data in file {last_bak_log_file} exception {exc}")


def del_zip_parts(zip_files_path):
    """
    удаляет тома архива для очистки места
    """
    
    mk_dir(zip_files_path)
    if os.listdir(zip_files_path):
        for file_name in os.listdir(zip_files_path):
            os.remove(os.path.join(zip_files_path, file_name))
            logger.debug(f"File {file_name} delete from folder {zip_files_path}")
    else:
        logger.debug(f"Folder {zip_files_path} is empty nothing to delete")


def mk_monitoring_data(last_bak_file_name, successfully_uploaded, launch_period):
    """
    формирует метрики для отправки:
    имя проекта, имя базы, бакет и размер файла,
    для отправки в мониторинг, в случае неудачной отправки
    размер файла = -1
    """

    db_name = CONFIG["postgresql_conf"].get("db_name")
    if db_name:
        backup_name = db_name
    else:
        backup_name = os.path.basename(last_bak_file_name)
    if successfully_uploaded:
        file_size_bytes = bak_file_size(last_bak_file_name)
        file_size_mb = round(file_size_bytes / 1024 / 1024, 2)
    else:
        file_size_mb = -1
    upload_metrics = [
        {
            "name": "s3_upload",
            "labels": {
                "project_name": CONFIG["client"]["project_name"],
                "server_name": CONFIG["client"]["server_name"],
                "backup_name": backup_name,
                "launch_period": launch_period,
            },
            "value": file_size_mb,
        }
    ]
    monitoring_data = {"metrics": upload_metrics}
    return monitoring_data


def main():
    """
    для каждого файла из списка бэкапов
    запускает архивировани, загрузку на S3, отправку мониторига,
    удаление томов архива и устаревших бэкапов, логгирует процесс
    """

    start_time = datetime.now()
    current_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(current_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    log_file_name = f"s3_last_upload_file_{launch_period}.log"
    last_bak_log_file = os.path.join(logs_dir, log_file_name)
    backup_type = get_args().get("backup_type")
    zip_files_path = CONFIG[f"{backup_type}_backup_conf"]["backup_zip"]
    last_bak_files = mk_ls_of_last_bak_files(last_bak_log_file, backup_type)
    ls_bak_file_names = []
    token = os.environ.get(f"{CONFIG['token_env']}")
    del_zip_parts(zip_files_path)
    for last_bak_file in last_bak_files:
        if last_bak_file:
            successfully_zipped, bak_file_name = zip_last_bak_file(
                token, last_bak_file, zip_files_path
            )
            successfully_zipped = 1
            if successfully_zipped:
                ls_of_zip_parts = rd_ls_of_zip_files(zip_files_path, bak_file_name)
                successfully_uploaded = s3_upload(
                    token, launch_period, ls_of_zip_parts
                )
                if successfully_uploaded:
                    logger.debug(f"File {bak_file_name} is successfully uploaded start monitoring")
                    send_monitoring_metrics(__file__, mk_monitoring_data(
                        last_bak_file, successfully_uploaded, launch_period))
                    logger.debug(f"File {bak_file_name} is successfully uploaded end monitoring")
                    ls_bak_file_names.append(bak_file_name)
                    del_zip_parts(zip_files_path)
                    del_backup_files(os.path.dirname(last_bak_file), backup_type)
                else:
                    del_zip_parts(zip_files_path)
                    send_monitoring_metrics(__file__, mk_monitoring_data(
                        last_bak_file, successfully_uploaded, launch_period))
            else:
                logger.debug(f"Nothing to upload to s3 because folder {zip_files_path} is empty")
                del_zip_parts(zip_files_path)
        else:
            logger.debug(f"Nothing to upload to s3 - no new backup files in backup folder")
    wr_ls_of_last_bak_files(last_bak_log_file, ls_bak_file_names)
    exec_time = datetime.now() - start_time
    logger.debug(f"Script execution time is {exec_time}")


if __name__ == "__main__":
    main()