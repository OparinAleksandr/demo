#!/usr/bin/env python3

import os
import time
import shutil
import platform
from datetime import datetime
from .config import config
from .log_config import logging_config


logger = logging_config(__name__, main_module=False)
CONFIG = config()

def mk_dir(dir_path):
    """
    создаёт папку если она не существует
    """
    
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def mk_backup_file_name(backup_name, backup_type):
    """
    формирует имя бэкапа
    имябэкапа_датавремя.backup
    """

    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M")
    bak_files_path = CONFIG[f"{backup_type}_backup_conf"]["backup_path"]
    mk_dir(bak_files_path)
    bak_file_name = f"{backup_name}-{date_time}.backup"
    full_bak_file_name = os.path.join(bak_files_path, bak_file_name)
    return full_bak_file_name


def zip_prog_path():
    """
    определяет путь до программы 7z
    """

    if platform.system() == "Windows":
        zip_prog_path = "C:\\Program Files\\7-Zip\\7z.exe"
    else:
        zip_prog_path = "7z"
    return zip_prog_path


def delete_single_file(file_path):
    """
    удаляет файл из папки
    """

    try: 
        os.remove(file_path)
        result = "Success"
    except OSError as err:
        result = "Error"
    return result


def delete_directory(dir_path):
    """
    удаляет папку и её содержимое
    """

    try: 
        shutil.rmtree(dir_path)
        result = "Success"
    except OSError as err:
        result = "Error"
    return result


def delete(files_path, file_name, file_lifetime):
    """
    удаляет файл или директорию старше file_lifetime из каталога
    """

    now_time = time.time()
    file_path = os.path.join(files_path, file_name)
    if os.path.getmtime(file_path) < now_time - int(file_lifetime) * 86400:
        if os.path.isfile(file_path):
            logger.debug(f"""{delete_single_file(file_path)} delete file 
                         {file_name} from folder {files_path}""")
        elif os.path.isdir(file_path):
            logger.debug(f"""{delete_directory(file_path)} delete directory 
                         {file_name} from folder {files_path}""")
        else:
            logger.debug(f"Folder {files_path} is empty, nothing to delete")
    else:
        logger.debug(f"File {file_name} is younger than {file_lifetime} days and will not be deleted")


def del_backup_files(files_path, backup_type):
    """
    удаляет файлы бэкапов старше backup_lifetime
    """

    backup_lifetime = CONFIG[f"{backup_type}_backup_conf"]["backup_lifetime"]
    if not backup_lifetime:
        logger.debug("backup_lifetime not set and files not be deleted")
        return
    if os.path.exists(files_path):
        for file_name in os.listdir(files_path):
            delete(files_path, file_name, backup_lifetime)


def del_files_by_mask(mask, files_path, file_lifetime):
    """
    удаляет файлы по маске старше file_lifetime
    """
    
    if not file_lifetime:
        logger.debug("lifetime not set and files not be deleted")
        return
    if os.path.exists(files_path):
        for root, dirs, files in os.walk(files_path):
            for file in files:
                if file.startswith(mask):
                    delete(root, file, file_lifetime)