# выполняет сервисные комманды
# для PostgreSQL DB

import os
import logging
import platform
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
from rd_config import rd_log_files_path

# возвращает путь к vacuumdb и reindexdb
def srv_com_paths(version):
    if platform.system() == "Windows":
        vacuumdb_path = f"C:\\Program Files\\PostgreSQL\\{version}\\bin\\vacuumdb.exe"
        reindexdb_path = f"C:\\Program Files\\PostgreSQL\\{version}\\bin\\reindexdb.exe"
    else:
        vacuumdb_path = "vacuumdb"
        reindexdb_path = "reindexdb"
    return vacuumdb_path, reindexdb_path


# получает значение для пароля
def get_passwd():
    if rd_passwd_env():
        passwd_env = os.environ.get(rd_passwd_env())
    else:
        passwd_env = rd_token_env()
    return passwd_env


# формирует и выполянет
# команды vacuumdb и reindexdb
def pg_srv():
    db_name = rd_db_name()
    host = rd_host()
    port = rd_port()
    user = rd_user()
    passwd = get_passwd()
    version = rd_version()
    vacuumdb_path, reindexdb_path = srv_com_paths(version)
    if platform.system() == "Windows":
        set_passwd = "SET PGPASSWORD="
        next_com = "&& CALL "
    else:
        set_passwd = "export PGPASSWORD="
        next_com = "&&"
    command = (
        f'{set_passwd}{passwd}{next_com}"{vacuumdb_path}" --dbname={db_name} --host={host} '
        + f"--port={port} --username={user} --no-password"
    )
    vacuumdb_result = os.system(f"{command}")
    if vacuumdb_result == 0:
        log_data = f"In data base {db_name} vacuumdb is worked successfully"
        wr_log(log_data)
    else:
        log_data = f"In data base {db_name} vacuumdb did not worked"
        wr_log(log_data)
    command = (
        f'{set_passwd}{passwd}{next_com}"{reindexdb_path}" --dbname={db_name} --host={host} '
        + f"--port={port} --username={user} --no-password"
    )
    reindexdb_result = os.system(f"{command}")
    if reindexdb_result == 0:
        log_data = f"In data base {db_name} reindexdb is worked successfully"
        wr_log(log_data)
    else:
        log_data = f"In data base {db_name} reindexdb did not worked"
        wr_log(log_data)


def main():

    log_files_path = rd_log_files_path() + "pg_serv.log"
    logging.basicConfig(
        handlers=[RotatingFileHandler(log_files_path, maxBytes=300000, backupCount=5)],
        level=logging.DEBUG,
        format="[%(asctime)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    pg_srv()


if __name__ == "__main__":

    main()
