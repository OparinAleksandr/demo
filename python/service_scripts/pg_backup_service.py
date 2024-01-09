#!/usr/bin/env python3

import os
import argparse
import platform
import subprocess
from modules.config import config
from modules.log_config import logging_config
from modules.files import mk_backup_file_name


CONFIG = config()["postgresql_conf"]


def get_args():
    parser = argparse.ArgumentParser(description="Обслуживает PostgreSQL")
    parser.add_argument(
        "--backup_type",
        default="full_cluster",
        type=str,
        help="""Тип бэкапа, single_base - бэкап указанной базы, 
        full_cluster - бэкап кластера. По умолчанию - бэкап кластера""",
    )
    parser.add_argument(
        "--launch_type",
        default="backup",
        type=str,
        help="""Тип запуска, backup - для бэкапа, 
        service - для обслуживания. По умолчанию - backup""",
    )
    args = parser.parse_args()
    return vars(args)


launch_type = get_args().get("launch_type")
logger = logging_config(f"pg_backup_service_{launch_type}.log", main_module=True)


def service_utility_path():
    """
    возвращает путь к vacuumdb и reindexdb
    """

    version = CONFIG["version"]
    if platform.system() == "Windows":
        vacuumdb_path = f"C:\\Program Files\\PostgreSQL\\{version}\\bin\\vacuumdb.exe"
        reindexdb_path = f"C:\\Program Files\\PostgreSQL\\{version}\\bin\\reindexdb.exe"
    else:
        vacuumdb_path = f"/opt/pgpro/{version}/bin/vacuumdb"
        reindexdb_path = f"/opt/pgpro/{version}/bin/reindexdb"
    return vacuumdb_path, reindexdb_path


def backup_utility_path(backup_type):
    """
    возвращает путь к утилите бэкапа
    """

    version = CONFIG["version"]
    if backup_type == 'single_base':
        utility_name = 'pg_dump'
    elif backup_type == 'full_cluster':
        utility_name = 'pg_basebackup'
    if platform.system() == "Windows":
        utility_path = f"C:\\Program Files\\PostgreSQL\\{version}\\bin\\{utility_name}.exe"
    else:
        utility_path = f"/opt/pgpro/{version}/bin/{utility_name}"
    return utility_path



def get_passwd():
    """
    получает значение для пароля
    """

    return os.environ.get(f"{CONFIG.get('passwd_env', config()['token_env'])}")


def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        logger.debug(f"Command output: {result.stdout.strip()}")
        logger.debug(f"Command error: {result.stderr.strip()}")
        if result.returncode == 0:
            logger.debug(f"Command successfully completed")
        else:
            logger.debug("Command failed")
    except subprocess.CalledProcessError as e:
        logger.debug(f"Command error code: {e.returncode}")
        logger.debug(f"Command error: {e.stderr.strip()}")
        logger.debug("Command failed")


def pg_backup(backup_type):
    """
    формирует и выполняет
    комманду бэкапа
    """

    db = CONFIG["db_name"]
    host = CONFIG["host"]
    port = CONFIG["port"]
    user = CONFIG["user"]
    passwd = get_passwd()
    utility_path = backup_utility_path(backup_type)
    bak_file_name = mk_backup_file_name(db, "db")
    if platform.system() == "Windows":
        set_passwd = "SET PGPASSWORD="
        next_com = "&& CALL "
    else:
        set_passwd = "export PGPASSWORD="
        next_com = "&&"
    if backup_type == 'single_base':
        command = (
            f'{set_passwd}{passwd}{next_com} "{utility_path}" --dbname={db} --host={host} '
            + f'--port={port} --username={user} --no-password --file="{bak_file_name}" --format=custom'
        )
    elif backup_type == 'full_cluster':
        command = (
        f'{set_passwd}{passwd}{next_com} "{utility_path}" --checkpoint=fast -P -z -Ft --host={host} '
        + f'--port={port} --username={user} --no-password -D "{bak_file_name}"'
    )
    run_command(command)


def pg_srv():
    """
    формирует и выполянет
    команды vacuumdb и reindexdb
    """

    host = CONFIG["host"]
    port = CONFIG["port"]
    user = CONFIG["user"]
    passwd = get_passwd()
    for utility_path in service_utility_path():
        if platform.system() == "Windows":
            set_passwd = "SET PGPASSWORD="
            next_com = "&& CALL "
        else:
            set_passwd = "export PGPASSWORD="
            next_com = "&&"
        command = (
            f'{set_passwd}{passwd}{next_com}"{utility_path}" --all --host={host} '
            + f"--port={port} --username={user} --no-password"
        )
        run_command(command)


def main():
    launch_type = get_args().get("launch_type")
    if not launch_type:
        logger.debug("Missing launch_type")
        launch_type = input("Пожалуйста введи тип запуска(backup/service): ")
    if launch_type == "backup":
        backup_type = get_args().get("backup_type")
        if not launch_type:
            logger.debug("Missing backup_type")
            launch_type = input("Пожалуйста введи тип бэкапа(single_base/full_cluster): ")
        pg_backup(backup_type)
    elif launch_type == "service":
        pg_srv()


if __name__ == "__main__":

    main()
