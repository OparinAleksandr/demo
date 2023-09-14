# бэкап базы из PostgreSQL
import os
import logging
import argparse
import platform
from datetime import datetime
from logging.handlers import RotatingFileHandler

from rd_config import wr_log
from rd_config import rd_version
from rd_config import rd_token_env
from rd_config import rd_db_name
from rd_config import rd_host
from rd_config import rd_port
from rd_config import rd_passwd_env
from rd_config import rd_user
from rd_config import rd_log_files_path
from rd_config import rd_bak_files_path


def get_args():
    parser = argparse.ArgumentParser(description="Делает бэкапы PostgreSQL")
    parser.add_argument(
        "--backup_type",
        default="",
        type=str,
        help="Тип бэкапа, single_base - бэкап указанной базы, full_cluster - бэкап кластера",
    )
    args = parser.parse_args()
    return vars(args)


# возвращает путь к утилите бэкапа
def backup_utility_path(version, backup_type):
    if backup_type == 'single_base':
        utility_name = 'pg_dump'
    elif backup_type == 'full_cluster':
        utility_name = 'pg_basebackup'
    if platform.system() == "Windows":
        utility_path = f"C:\\Program Files\\PostgreSQL\\{version}\\bin\\{utility_name}.exe"
    else:
        utility_path = f"{utility_name}"
    return utility_path


# формирует имя бэкапа
# имябэкапа_датавремя.backup
def mk_backup_file_name(backup_name):
    now = datetime.now()
    date_time = now.strftime("%Y-%m-%d_%H-%M")
    bak_files_path = rd_bak_files_path()
    bak_file_name = f"{backup_name}_{date_time}.backup"
    full_bak_file_name = os.path.join(bak_files_path, bak_file_name)
    return full_bak_file_name


# получает значение для пароля
def get_passwd():
    if rd_passwd_env():
        passwd_env = os.environ.get(rd_passwd_env())
    else:
        passwd_env = rd_token_env()
    return passwd_env


# формирует и выполняет
# комманду бэкапа
def pg_backup(backup_type):
    db_name = rd_db_name()
    host = rd_host()
    port = rd_port()
    user = rd_user()
    passwd = get_passwd()
    version = rd_version()
    utility_path = backup_utility_path(version, backup_type)
    bak_file_name = mk_backup_file_name(db_name)
    if platform.system() == "Windows":
        set_passwd = "SET PGPASSWORD="
        next_com = "&& CALL "
    else:
        set_passwd = "export PGPASSWORD="
        next_com = "&&"
    if backup_type == 'single_base':
        command = (
            f'{set_passwd}{passwd}{next_com} "{utility_path}" --dbname={db_name} --host={host} '
            + f'--port={port} --username={user} --no-password --file="{bak_file_name}" --format=custom'
        )
    elif backup_type == 'full_cluster':
        command = (
        f'{set_passwd}{passwd}{next_com} "{utility_path}" --checkpoint=fast -P -z -Ft --host={host} '
        + f'--port={port} --username={user} --no-password -D "{bak_file_name}"'
    )
    bak_result = os.system(f"{command}")
    if bak_result == 0:
        log_data = f"Backup is successfully complied in file {bak_file_name}"
        wr_log(log_data)
    else:
        log_data = f"Backup is failed"
        wr_log(log_data)


def main():
    log_files_path = rd_log_files_path() + "pg_bak.log"
    logging.basicConfig(
        handlers=[RotatingFileHandler(log_files_path, maxBytes=300000, backupCount=5)],
        level=logging.DEBUG,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    pg_backup(get_args().get("backup_type"))


if __name__ == "__main__":

    main()
