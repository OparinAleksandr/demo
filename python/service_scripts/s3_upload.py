# создаёт шифрованный архив с бэкапом
# отправляет архив в определённую корзину S3
# отправляет метрику в яндекс мониторинг:
# имя проекта, имя базы, размер архива
# удаляет бэкапы, которые старше backup_lifetime
# удаляет файл архива

import os
import glob
import json
import time
import shutil
import logging
import platform
import requests
import argparse
from tqdm import tqdm
from datetime import datetime
from tqdm.utils import CallbackIOWrapper
from logging.handlers import RotatingFileHandler

from rd_config import wr_log
from rd_config import mk_url_dom
from rd_config import rd_db_name
from rd_config import rd_token_env
from rd_config import rd_server_name
from rd_config import rd_project_name
from rd_config import rd_backup_lifetime
from rd_config import rd_log_files_path
from rd_config import rd_zip_files_path
from rd_config import rd_bak_files_path


def get_args():
    parser = argparse.ArgumentParser(description="Отправляет бэкапы БД на S3.")
    parser.add_argument(
        "--launch_period",
        default="daily",
        type=str,
        help="Время запуска, daily - ежедневный бэкап, weekly - еженедельный",
    )
    args = parser.parse_args()
    return vars(args)


# создаёт список последних считанных файлов из лога
# для сравнения с файлами из каталогов
def mk_ls_last_bak_files_from_log(launch_period):
    log_file_name = f"last_bak_files_{launch_period}.log"
    last_bak_log_file = os.path.join(rd_log_files_path(), log_file_name)
    last_bak_files_from_log = []
    try:
        with open(last_bak_log_file) as last_bak_log_file:
            last_bak_files_from_log = last_bak_log_file.read().splitlines()
        if last_bak_files_from_log:
            return last_bak_files_from_log, log_file_name
        else:
            log_data = f"File {last_bak_log_file} is empty last files in folders are will be zipped"
            wr_log(log_data)
            last_bak_files_from_log = []
            return last_bak_files_from_log, log_file_name
    except:
        log_data = f"Error occurred when read {last_bak_log_file}, last files in folders are will be zipped"
        wr_log(log_data)
        last_bak_files_from_log = []
        return last_bak_files_from_log, log_file_name


# создаёт список файлов из катлогов для сравнения со
# списком из лога
def mk_ls_last_bak_files_from_folders():
    bak_files_path = rd_bak_files_path()
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
    return ls_of_last_files, bak_files_path


# сравнивает два списка файлов
# и возвращает список для отправки
def mk_ls_of_last_bak_files(launch_period):
    ls_last_bak_files_from_log, log_file_name = mk_ls_last_bak_files_from_log(launch_period)
    ls_last_bak_files_from_folders, bak_files_path = mk_ls_last_bak_files_from_folders()
    if ls_last_bak_files_from_log == ls_last_bak_files_from_folders:
        ls_of_last_bak_files = []
        log_data = (
            f"All files in list from {log_file_name} has already been sent "
            + f"and there are no new files in folder {bak_files_path}"
        )
        print(log_data)
        wr_log(log_data)
    else:
        ls_of_last_bak_files = list(
            set(ls_last_bak_files_from_folders) - set(ls_last_bak_files_from_log)
        )
    return ls_of_last_bak_files


# определяет путь до программы 7z
def zip_prog_path():
    if platform.system() == "Windows":
        zip_prog_path = "C:\\Program Files\\7-Zip\\7z.exe"
    else:
        zip_prog_path = "7z"
    return zip_prog_path

# определяет объём файла\директории бэкапа
def bak_file_size(last_bak_file_name):
    last_bak_file_size = 0
    if os.path.isdir(last_bak_file_name):
        for element in os.scandir(last_bak_file_name):
            last_bak_file_size += os.path.getsize(element)
    else:
        last_bak_file_size = os.path.getsize(last_bak_file_name)
    return last_bak_file_size

# архивирует бэкапы, разделяя на части,
# если размер бэкапа больше 400Мб
# для отправки больших файлов частями
# возвращает флаг successfully_zipped и имя бэкапа
def zip_last_bak_file(token, last_bak_file_name, zip_files_path):
    destination_file_name = os.path.splitext(os.path.basename(last_bak_file_name))[0]
    zip_prog = zip_prog_path()
    destination_file = os.path.join(zip_files_path, destination_file_name + ".zip")
    source_file = last_bak_file_name
    if bak_file_size(last_bak_file_name) > 400_000_000:
        zip_command = f""""{zip_prog}" a -ssw -v200M -mx5 -p{token} -r0 {destination_file} {source_file}"""
    else:
        zip_command = f""""{zip_prog}" a -ssw -mx5 -p{token} -r0 {destination_file} {source_file}"""
    zip_result = os.system(f"{zip_command}")
    if zip_result == 0:
        log_data = f"File {source_file} is successfully zipped"
        wr_log(log_data)
        successfully_zipped = 1
    else:
        log_data = f"File {source_file} is not zipped"
        wr_log(log_data)
        successfully_zipped = 0
    return successfully_zipped, source_file


# создаёт список томов архива
# для получения ссылки на каждый том
def rd_ls_of_zip_files(zip_files_path, source_file):
    ls_of_zip_parts = glob.glob(zip_files_path + "*.zip*")
    log_data = f"File {source_file} is successfully zipped and split by {len(ls_of_zip_parts)} parts"
    print(log_data)
    wr_log(log_data)
    return ls_of_zip_parts


# в зависимости от параметров "cloud" и "ydb_policy" в конфиге
# получает ссылку для загрузки каждого тома архива из списка
# отправляет каждую часть в корзину на S3
# в случае успешной загрузки даёт команду яндекс функции на сборку файлв
def s3_upload(token, policy, url_dom, ls_of_zip_parts, number_of_attempts=10):
    attempts = number_of_attempts
    if len(ls_of_zip_parts) > 1:
        zip_file_name = str(os.path.splitext(os.path.basename(ls_of_zip_parts[0]))[0])
    else:
        zip_file_name = str(os.path.basename(ls_of_zip_parts[0]))
    while attempts >= 0:
        try:
            yc_url = f"https://{url_dom}.bit-erp.ru/v2/s3/put/{policy}/{zip_file_name}"
            amount_of_parts = json.dumps({"amount": len(ls_of_zip_parts)})
            headers_ls = {"Authorization": "Bearer " + token}
            response = requests.post(yc_url, data=amount_of_parts, headers=headers_ls)
            parts_url = response.json()["partUrls"]
            abort_url = response.json()["abort"]
            complete_url = response.json()["complete"]
            break
        except:
            log_data = f"Presigned link is not taken for file {zip_file_name}"
            wr_log(log_data)
            attempts -= 1
    if attempts == 0:
        successfully_uploaded = 0
        return successfully_uploaded
    else:
        attempts = number_of_attempts
    counter = 1
    for file_name, presigned_link in zip(sorted(ls_of_zip_parts), parts_url):
        parts = len(ls_of_zip_parts)
        while attempts > 0:
            try:
                file_size = os.stat(file_name).st_size
                print("-------------------------------------------")
                log_data = f"File {file_name} is uploading to s3 ({counter}/{parts}):"
                print(log_data)
                wr_log(log_data)
                with open(file_name, "rb") as binary_data:
                    with tqdm(
                        total=file_size, unit="B", unit_scale=True, unit_divisor=1024
                    ) as pr_bar:
                        wrapped_file = CallbackIOWrapper(
                            pr_bar.update, binary_data, "read"
                        )
                        requests.put(presigned_link, data=wrapped_file)
                log_data = (
                    f"File {file_name} is successfully upload to s3 ({counter}/{parts})"
                )
                print(log_data)
                wr_log(log_data)
                successfully_uploaded = 1
                counter += 1
                break
            except Exception as exc:
                log_data = f"File {file_name} is not upload to s3 from attempt {attempts} because of exception {exc}"
                print(log_data)
                wr_log(log_data)
                attempts -= 1
        else:
            try:
                requests.get(abort_url, headers=headers_ls)
                log_data = f"File {file_name} is not upload to s3 all attempts are over abort upload"
                print(log_data)
                wr_log(log_data)
                successfully_uploaded = 0
                return successfully_uploaded
            except Exception as exc:
                log_data = f"File {file_name} is not upload to s3 and abort upload does not work because of exception {exc}"
                print(log_data)
                wr_log(log_data)
                successfully_uploaded = 0
                return successfully_uploaded
    if successfully_uploaded:
        try:
            resp = requests.get(complete_url, headers=headers_ls)
            if resp.status_code == 200:
                log_data = (
                    f"File {zip_file_name} is successfully upload to s3 and assembled"
                )
                print(log_data)
                wr_log(log_data)
        except Exception as exc:
            log_data = f"File {zip_file_name} successfully upload to s3 but did not assembled because of exception {exc}"
            print(log_data)
            wr_log(log_data)
    return successfully_uploaded


# записывает последний отправленный файл в лог
def wr_ls_of_last_bak_files(launch_period, ls_bak_file_names=[]):
    log_file_path = rd_log_files_path()
    log_file_name = f"last_bak_files_{launch_period}.log"
    last_bak_log_file = os.path.join(log_file_path, log_file_name)
    if ls_bak_file_names:
        try:
            with open(last_bak_log_file, "w+") as last_bak_log_file:
                for bak_file_name in ls_bak_file_names:
                    last_bak_log_file.write(bak_file_name + "\n")
            log_data = f"File last_bak_files_{launch_period}.log is successfully wrote"
            wr_log(log_data)
        except Exception as exc:
            log_data = f"Error occurred when write data in file {last_bak_log_file} because of exception {exc}"
            wr_log(log_data)


# удаляет тома архива для очистки места
def del_zip_parts(zip_files_path):
    if os.listdir(zip_files_path):
        for file_name in os.listdir(zip_files_path):
            os.remove(os.path.join(zip_files_path, file_name))
            log_data = f"File {file_name} delete from folder {zip_files_path}"
            wr_log(log_data)
    else:
        log_data = f"Folder {zip_files_path} is empty nothing to delete"
        wr_log(log_data)


# формирует метрики для отправки:
# имя проекта, имя базы, бакет и размер файла,
# для отправки в мониторинг, в случае неудачной отправки
# размер файла = -1
def mk_monitoring_data(last_bak_file_name, successfully_uploaded, launch_period):
    project_name = rd_project_name()
    if rd_db_name():
        db_name = rd_db_name()
    else:
        dir_name = os.path.dirname(last_bak_file_name)
        db_name = os.path.basename(dir_name)
    if successfully_uploaded:
        file_size_bytes = bak_file_size(last_bak_file_name)
        file_size_mb = round(file_size_bytes / 1024 / 1024, 2)
    else:
        file_size_mb = -1
    upload_metrics = [
        {
            "name": "s3_upload",
            "labels": {
                "project_name": project_name,
                "server_name": rd_server_name(),
                "base_name": db_name,
                "launch_period": launch_period,
            },
            "value": file_size_mb,
        }
    ]
    monitoring_data = {"metrics": upload_metrics}
    return monitoring_data


# отправляет метрики в мониторинг для отслеживания процесса
# загрузки бэкапов
def send_monitoring_data(token, url_dom, monitoring_data, number_of_attempts=10):
    attempts = number_of_attempts
    while attempts >= 0:
        try:
            yc_url = f"https://{url_dom}.bit-erp.ru/iam/monitor_token"
            headers = {"Authorization": "Bearer " + token}
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
            break
        except Exception as exc:
            log_data = f"Error occurred when form monitoring url: {exc}"
            wr_log(log_data)
            attempts -= 1
            time.sleep(10)
    if attempts == 0:
        log_data = (
            f"Monitoring for file is not send:"
            + "Error occurred when form monitoring url"
        )
        wr_log(log_data)
        return
    else:
        attempts = number_of_attempts
    while attempts > 0:
        if monitoring_data:
            try:
                resp = requests.post(
                    yc_url, data=json.dumps(monitoring_data), headers=headers
                )
                if resp.status_code == 200:
                    log_data = f"Monitoring for file is successfully send"
                    wr_log(log_data)
                    break
                else:
                    log_data = f"Monitoring for file is not send: {resp}"
                    wr_log(log_data)
                    attempts -= 1
                    time.sleep(10)
            except Exception as exc:
                log_data = f"Error occurred when send monitoring: {exc}"
                wr_log(log_data)
                attempts -= 1
                time.sleep(10)
        else:
            log_data = f"Monitoring data are empty, nothing to send for file"
            wr_log(log_data)
            break


# удаляет файлы бэкаопв старше параметра backup_lifetime
def del_bak_files(files_path):
    backup_lifetime = int(rd_backup_lifetime())
    if backup_lifetime > 0:
        now_time = time.time()
        if os.path.exists(files_path):
            for file_name in os.listdir(files_path):
                if (
                    os.path.getmtime(os.path.join(files_path, file_name))
                    < now_time - backup_lifetime * 86400
                ):
                    if os.path.isfile(os.path.join(files_path, file_name)):
                        try: 
                            os.remove(os.path.join(files_path, file_name))
                            log_data = f"File {file_name} deleted from folder {files_path} because it is older than {backup_lifetime} days"
                            wr_log(log_data)
                        except OSError as err:
                            log_data = f"Error occurred {err} when delete file {file_name} deleted from folder {files_path}"
                            wr_log(log_data)
                    elif os.path.isdir(os.path.join(files_path, file_name)):
                        try: 
                            shutil.rmtree(os.path.join(files_path, file_name))
                            log_data = f"Cluster folder {file_name} deleted from folder {files_path} because it is older than {backup_lifetime} days"
                            wr_log(log_data)
                        except OSError as err:
                            log_data = f"Error occurred {err} when delete cluster folder {file_name} deleted from folder {files_path}"
                            wr_log(log_data)  
                    else:
                        log_data = f"Folder {files_path} is empty, nothing to delete"
                        wr_log(log_data)
                else:
                    log_data = f"File {file_name} is younger than {backup_lifetime} days, and not be deleted"
                    wr_log(log_data)
    else:
        log_data = "backup_lifetime is 0 and files not be deleted"
        wr_log(log_data)


# для каждого файла из списка бэкапов
# запускает архивировани, загрузку на S3, отправку мониторига,
# удаление томов архива и устаревших бэкапов, логгирует процесс
def main():
    launch_period = get_args().get("launch_period")
    log_file_path = rd_log_files_path() + f"s3_upload_{launch_period}.log"
    logging.basicConfig(
        handlers=[RotatingFileHandler(log_file_path, maxBytes=300000, backupCount=5)],
        level=logging.DEBUG,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    start_time = datetime.now()
    try:
        token = rd_token_env()
    except Exception as exc:
        logging.exception(f"Error when get token: {exc}")
    url_dom = mk_url_dom()
    bak_files_path = rd_bak_files_path()
    zip_files_path = rd_zip_files_path()
    last_bak_files = mk_ls_of_last_bak_files(launch_period)
    ls_bak_file_names = []
    del_zip_parts(zip_files_path)
    for last_bak_file in last_bak_files:
        if last_bak_file:
            successfully_zipped, bak_file_name = zip_last_bak_file(
                token, last_bak_file, zip_files_path
            )
            if successfully_zipped:
                ls_of_zip_parts = rd_ls_of_zip_files(zip_files_path, bak_file_name)
                successfully_uploaded = s3_upload(
                    token, launch_period, url_dom, ls_of_zip_parts
                )
                if successfully_uploaded:
                    monitoring_data = mk_monitoring_data(
                        last_bak_file, successfully_uploaded, launch_period
                    )
                    send_monitoring_data(token, url_dom, monitoring_data)
                    ls_bak_file_names.append(bak_file_name)
                    del_zip_parts(zip_files_path)
                    del_bak_files(os.path.dirname(last_bak_file))
                else:
                    del_zip_parts(zip_files_path)
                    monitoring_data = mk_monitoring_data(
                        last_bak_file, successfully_uploaded, launch_period
                    )
                    send_monitoring_data(token, url_dom, monitoring_data)
            else:
                log_data = (
                    f"Nothing to upload to s3 because folder {zip_files_path} is empty"
                )
                wr_log(log_data)
                del_zip_parts(zip_files_path)
        else:
            log_data = f"Nothing to upload to s3 because folder {bak_files_path} dose not have new backup files"
            wr_log(log_data)
    wr_ls_of_last_bak_files(launch_period, ls_bak_file_names)
    exec_time = datetime.now() - start_time
    log_data = f"Script execution time is {exec_time}"
    wr_log(log_data)


if __name__ == "__main__":

    main()