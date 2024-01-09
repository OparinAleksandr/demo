#!/usr/bin/env python3

import os
import json
import getpass
import argparse
import platform
import subprocess
from modules.log_config import logging_config


CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(CURRENT_DIR, "conf.yml")
logger = logging_config(__file__, main_module=True)


def get_args():
    parser = argparse.ArgumentParser(
        description="Создаёт конфиг для: "
        + "отправки метрик аппаратного мониторинга в Яндекс-Мониторинг," 
        + "PostgreSQL: запуск скриптов обслуживания и бэкапа, "
        + "sonar - метрики в мониторинг и бэкап, "
        + "проверки статуса служб systemctl"
        + "бэкапа файлов в ZIP-архиве"
        + "и делает ссылки на них в файле /etc/cron.d/bit_svc.cron"
    )
    parser.add_argument(
        "--config_type",
        default="hardware",
        type=str,
        help="Тип конфига: " 
        + "По умолчанию hardware - только для аппаратного мониторинга,\n"
        + "sonar - конфиг для ВМ с sonar, \n"
        + "service_status - конфиг для проверки статуса служб systemctl, \n"
        + "postgres_base - конфиг для работы с отдельной базой PostgreSQL и аппаратного мониторинга, \n"
        + "postgres_cluster - конфиг для работы с кластером PostgreSQL и аппаратного мониторинга, \n"
        + "files_backup - конфиг для бэкапа файлов в ZIP-архиве."
    )
    parser.add_argument(
        "--token",
        default="",
        type=str,
        help="Токен клиента. Обязательная опция",
    )
    parser.add_argument(
        "--token_env",
        default="YCT",
        type=str,
        help="Имя переменной окружения для токена. По умолчанию YCT",
    )
    parser.add_argument(
        "--project_name",
        default="",
        type=str,
        help="Имя проекта(клиента) \n"
        + "Если не введено, то будет сгенерировано я-функцией getcurrentclientinfo",
    )
    parser.add_argument(
        "--server_name",
        default="",
        type=str,
        help="Имя ПК. Если не введено, то используется hostname",
    )
    parser.add_argument(
        "--service_directory",
        default="",
        type=str,
        help="Путь до файлов с бэкапами. По умолчанию текущая директория со скриптами",
    )
    parser.add_argument(
        "--db_backup_lifetime",
        default="3",
        type=str,
        help="Время жизни локального бэкапа базы. По умолчанию 3 дня",
    )
    parser.add_argument(
        "--db_name",
        default="",
        type=str,
        help="Имя базы PostgreSQL.",
    )
    parser.add_argument(
        "--postgresql_host",
        default="",
        type=str,
        help="Адрес хоста PostgreSQL.",
    )
    parser.add_argument(
        "--postgresql_version",
        default="",
        type=str,
        help="Версия PostgreSQL. Обязательная опция для Windows",
    )
    parser.add_argument(
        "--postgresql_port",
        default="5432",
        type=str,
        help="Порт хоста PostgreSQL. По умолчанию 5432",
    )
    parser.add_argument(
        "--postgresql_user",
        default="postgres",
        type=str,
        help="Пользователь PostgreSQL.",
    )
    parser.add_argument(
        "--postgresql_env_pass",
        default="PG_PSW",
        type=str,
        help="Имя переменной с паролем PostgreSQL. По умолчанию PG_PSW",
    )
    parser.add_argument(
        "--postgresql_pass",
        default="",
        type=str,
        help="Пароль PostgreSQL.",
    )
    parser.add_argument(
        "--local_db_backup_cron",
        default="0 */6 * * *",
        type=str,
        help="Задание в cron для локального бэкапа \n"
        + "По умолчанию каждые 6 часов \n",
    )
    parser.add_argument(
        "--db_service_cron",
        default="30 */12 * * *",
        type=str,
        help="Задание в cron для сервиса БД \n" + 
        "По умолчанию каждые 12 с половиной часов \n",
    )
    parser.add_argument(
        "--daily_s3_db_backup_cron",
        default="0 19 */1 * *",
        type=str,
        help="Задание в cron для ежедневного бэкапа базы в s3 \n"
        + "По умолчанию: '0 19 */1 * *' \n",
    )
    parser.add_argument(
        "--daily_s3_files_backup_cron",
        default="0 17 */1 * *",
        type=str,
        help="Задание в cron для ежедневного бэкапа файлов в s3 \n"
        + "По умолчанию: '0 19 */1 * *' \n",
    )
    parser.add_argument(
        "--weekly_s3_db_backup_cron",
        default="0 20 * * */6",
        type=str,
        help="Задание в cron для еженедельного бэкапа базы в s3 \n"
        + "По умолчанию: '0 20 * * */6' \n",
    )
    parser.add_argument(
        "--weekly_s3_files_backup_cron",
        default="0 23 * * */6",
        type=str,
        help="Задание в cron для еженедельного бэкапа файлов в s3 \n"
        + "По умолчанию: '0 23 * * */6' \n",
    )
    parser.add_argument(
        "--hardware_monitoring_cron",
        default="*/5 * * * *",
        type=str,
        help="Задание в cron для аппаратного мониторинга \n"
        + "По умолчанию: '*/5 * * * *' \n",
    )
    parser.add_argument(
        "--sonar_backup_cron",
        default="0 17 */1 * *",
        type=str,
        help="Задание в cron бэкапа sonar \n"
        + "По умолчанию: '0 17 */1 * *' \n",
    )
    parser.add_argument(
        "--sonar_backup_folder",
        default="/opt/sonarqube/postgres_sonar",
        type=str,
        help="Директория файлов sonar \n"
        + "По умолчанию: '/opt/sonarqube/postgres_sonar' \n",
    )
    parser.add_argument(
        "--sonar_backup_lifetime",
        default="3",
        type=str,
        help="Время жизни локального бэкапа файлов. По умолчанию 3 дня",
    )
    parser.add_argument(
        "--services_names",
        type=str,
        help="Имена служб для мониторинга \n"
        + "для отслеживания нескольких служб, перечислить через запятую \n",
    )
    parser.add_argument(
        "--files_backup_folder",
        type=str,
        help="Директория с файлами для бэкапа\n"
    )
    parser.add_argument(
        "--files_backup_cron",
        default="0 17 */1 * *",
        type=str,
        help="Задание в cron бэкапа файлов \n"
        + "По умолчанию: '0 17 */1 * *' \n",
    )
    parser.add_argument(
        "--files_backup_lifetime",
        default="3",
        type=str,
        help="Время жизни локального бэкапа файлов. По умолчанию 3 дня",
    )
    parser.add_argument(
        "--files_exclude_mask",
        default="snapshot",
        type=str,
        help="Маска для исключения файлов из бэкапа. По умолчанию: snapshot",
    )
    parser.add_argument(
        "--files_exclude_lifetime",
        default="3",
        type=str,
        help="Время жизни исключенных файлов. По умолчанию 3 дня",
    )
    args = parser.parse_args()

    return vars(args)


def install_requirements(config_type):
    """
    установка зависимостей
    """
    
    requirements_path = os.path.join(CURRENT_DIR, "requirements.txt")
    if platform.system() != "Windows":
        if getpass.getuser() != "root":
            logger.debug("Please, start as root!")
            exit(1)
        if config_type.startswith('postgres'):
            try:
                subprocess.call(f"sudo -n apt update", shell=True)
                subprocess.call(f"sudo -n apt install pip -y", shell=True)
                subprocess.call(f"sudo -n apt install p7zip-full -y", shell=True)
                subprocess.call(f"sudo -n pip install --default-timeout=1000 -r {requirements_path}", shell=True)
                logger.debug(
                    f"PostgreSQL-client, pip and requirement libraries successfully installed"
                )
            except Exception as exc:
                logger.error(f"Error install pip and requirement libraries: {exc}")

        elif config_type == "hardware" or config_type == "sonar":
            try:
                subprocess.call(f"sudo -n apt update", shell=True)
                subprocess.call(f"sudo -n apt install p7zip-full -y", shell=True)
                subprocess.call(f"sudo -n apt install pip -y", shell=True)
                subprocess.call(f"sudo -n pip install --default-timeout=1000 -r {requirements_path}", shell=True)
                logger.debug(f"7zip, pip and requirement libraries successfully installed")
            except Exception as exc:
                logger.error(f"Error install pip and requirement libraries: {exc}")
    else:
        try:
            subprocess.call(f"pip install --default-timeout=1000 -r {requirements_path}", shell=True)
            logger.debug(
                    f"Requirement libraries successfully installed, please install PostgreSQL-client and 7zip"
                )
        except Exception as exc:
                logger.error(f"Error install requirement libraries: {exc}") 


config_type = get_args().get("config_type")
install_requirements(config_type)


import yaml
import requests


def rd_config():
    """
    читает файл конфига и возвращает словарь с параметрами
    """
    
    conf_dict = {}
    try:
        with open(CONFIG_PATH, encoding="utf-8") as conf_file:
            conf_dict = yaml.safe_load(conf_file)
            return conf_dict
    except FileNotFoundError:
        return conf_dict


def wr_env(env_name, env_value):
    """
    записывает переменную в файл /etc/environment
    """

    wr_token = False
    if platform.system() != "Windows":
        try:
            if os.environ.get(env_name) == None:
                subprocess.check_output(
                    f"echo {env_name}={env_value} >> /etc/environment", shell=True
                )
                logger.debug(
                    f"Переменная {env_name} успешно записана в файл /etc/environment"
                )
                wr_token = True
                return wr_token
            else:
                logger.debug(
                    f"Переменная {env_name} уже есть в файле /etc/environment и не будет заменена"
                )
                wr_token = True
                return wr_token
        except Exception as exc:
            logger.debug(f"Ошибка записи переменной {env_name}: {exc}")
            wr_token = False
            return wr_token
    else:
        import winreg
        try:
            if os.environ.get(env_name) == None:
                os.environ[env_name] = env_value
                env_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment', 0, winreg.KEY_ALL_ACCESS)
                winreg.SetValueEx(env_key, env_name, 0, winreg.REG_SZ, env_value)
                winreg.CloseKey(env_key)
                logger.debug(f"Переменная {env_name} успешно записана в реестр Windows")
                wr_token = True
                return wr_token
            else:
                logger.debug(
                    f"Переменная {env_name} уже есть в реестре Windows и не будет заменена"
                )
                wr_token = True
                return wr_token
        except Exception as exc:
            logger.debug(f"Ошибка записи переменной {env_name}: {exc}")
            wr_token = False
            return wr_token


def get_current_client_info(token):
    """
    получает информацию о текущем клиенте
    """

    attempts = 5
    prod_url = "https://apigwpriv.bit-erp.ru/"
    test_url = "https://devapigwpriv.bit-erp.ru/"

    def get_response(attempts, url):
        while attempts > 0:
            response = requests.request(
                "GET", url, headers={"Authorization": "Bearer " + token}
            )
            if response.status_code == 403:
                break
            elif response.status_code == 200:
                return response.text
            else:
                attempts -= 1

    client_info = get_response(attempts, f"{test_url}/getcurrentclientinfo")
    if client_info:
        cloud = "test"
        return client_info, cloud
    else:
        client_info = get_response(attempts, f"{prod_url}/getcurrentclientinfo")
        cloud = "prod"
        return client_info, cloud


def wr_cron(scripts_name_expressions_dict, script_arguments="", cron_file_path="/etc/cron.d/bit_svc"):
    """
    записывает в файл cron задания для скриптов
    """
    
    if platform.system() != "Windows":
        current_crone_lines = []
        if os.path.exists(cron_file_path):
            current_crone = subprocess.check_output(f"cat {cron_file_path}", 
                                                          shell=True, text=True, 
                                                          encoding='utf-8')
            current_crone_lines = current_crone.split("\n")
        
        for script_name, expression in scripts_name_expressions_dict.items():
            if '.py' in script_name:
                program = "python3"
            else:
                logger.error(f"Script {script_name} is not a python script")
            if script_name in current_crone_lines:
                logger.debug(f"Cron expression {expression} for {script_name} already exists")
                continue
            else:
                script_path = os.path.join(CURRENT_DIR, script_name)
                subprocess.call(f"sudo echo '{expression} root {program} {script_path} {script_arguments} >/dev/null 2>&1' >> {cron_file_path}", shell=True)
                logger.debug(f"Cron expression is successfully write to {cron_file_path}")
    else:
        for script_name, expression in scripts_name_expressions_dict.items():
            script_path = os.path.join(CURRENT_DIR, script_name)
            if '.py' in script_name:
                program = 'C:\python\python.exe'
            else:
                logger.error(f"Script {script_name} is not a python script")
            subprocess.call(f'SCHTASKS /CREATE /SC MINUTE /MO 5 /TN "{script_name}" /TR "{program} {script_path} {script_arguments}" /RU SYSTEM', shell=True)
            logger.debug(f"Cron expression is successfully write to Windows registry")


def mk_config(
    config_type,
    client_info,
    cloud,
    project_name,
    server_name,
    token_env,
    db_name,
    postgresql_version,
    postgresql_host,
    postgresql_port,
    postgresql_user,
    postgresql_env_pass,
    service_directory,
    db_backup_lifetime,
    services_names,
    files_backup_folder,
    files_backup_lifetime,
    files_exclude_mask,
    files_exclude_lifetime,
    sonar_backup_folder,
    sonar_backup_lifetime,
):
    """
    создаёт файл конфига
    """
    if platform.system() != "Windows":
        slash_type = "/"
    else:
        slash_type = "\\"
    if config_type.startswith('postgres'):
        config = {
            "client": {"project_name": "", "server_name": ""},
            "cloud": "",
            "token_env": "",
            "postgresql_conf": {
                "db_name": "",
                "version": "",
                "host": "",
                "port": "",
                "user": "",
                "passwd_env": "",
            },
            "db_backup_conf": {
                "backup_lifetime": "",
                "backup_path": "",
                "backup_zip": "",
            },
        }
        client_info = json.loads(client_info)
        if project_name == "" or "null":
            config["client"]["project_name"] = client_info["ClientName"]
        else:
            config["client"]["project_name"] = project_name
        if server_name == "" or "null":
            server_name = platform.node()
        config["client"]["server_name"] = server_name
        config["cloud"] = cloud
        config["token_env"] = token_env
        if config_type.endswith('base'):
            config["postgresql_conf"]["db_name"] = db_name
        elif config_type.endswith('cluster'):
            config["postgresql_conf"]["db_name"] = f"{platform.node()}_pg_cluster"
            if postgresql_host == "" or "null":
                postgresql_host = "localhost"
        config["postgresql_conf"]["host"] = postgresql_host
        config["postgresql_conf"]["version"] = postgresql_version
        config["postgresql_conf"]["port"] = postgresql_port
        config["postgresql_conf"]["user"] = postgresql_user
        config["postgresql_conf"]["passwd_env"] = postgresql_env_pass
        if service_directory == "" or "null":
            service_directory = CURRENT_DIR
        config["db_backup_conf"]["backup_path"] = os.path.join(
            service_directory, f"db_backup{slash_type}backup{slash_type}"
        )
        config["db_backup_conf"]["backup_zip"] = os.path.join(
            service_directory, f"db_backup{slash_type}zip{slash_type}"
        )
        config["db_backup_conf"]["backup_lifetime"] = db_backup_lifetime
        logger.debug(f"Config: {config}")
    elif config_type == "files_backup":
        config = {
            "client": {"project_name": "", "server_name": ""},
            "cloud": "",
            "token_env": "",
            "files_backup_conf": {
                "backup_folder": "",
                "backup_lifetime": "",
                "backup_zip": "",
                "backup_path": "",
                "exclude_mask": "",
                "exclude_lifetime": "",
            },
        }
        client_info = json.loads(client_info)
        if project_name == "" or "null":
            config["client"]["project_name"] = client_info["ClientName"]
        else:
            config["client"]["project_name"] = project_name
        if server_name == "" or "null":
            server_name = platform.node()
        config["client"]["server_name"] = server_name
        config["cloud"] = cloud
        config["token_env"] = token_env
        config["files_backup_conf"]["backup_folder"] = files_backup_folder
        if service_directory == "" or "null":
            service_directory = CURRENT_DIR
        config["files_backup_conf"]["backup_path"] = os.path.join(
            service_directory, f"files_backup{slash_type}backup{slash_type}"
        )
        config["files_backup_conf"]["backup_zip"] = os.path.join(
            service_directory, f"files_backup{slash_type}zip{slash_type}"
        )
        config["files_backup_conf"]["backup_lifetime"] = files_backup_lifetime
        config["files_backup_conf"]["exclude_mask"] = files_exclude_mask
        config["files_backup_conf"]["exclude_lifetime"] = files_exclude_lifetime
        logger.debug(f"Config: {config}")
    elif config_type == "sonar":
        config = {
            "client": {"project_name": "", "server_name": ""},
            "cloud": "",
            "token_env": "",
            "sonar_backup_conf": {
                "backup_folder": "",
                "backup_lifetime": "",
                "backup_zip": "",
                "backup_path": "",
            },
        }
        client_info = json.loads(client_info)
        if project_name == "" or "null":
            config["client"]["project_name"] = client_info["ClientName"]
        else:
            config["client"]["project_name"] = project_name
        if service_directory == "" or "null":
            service_directory = CURRENT_DIR
        config["client"]["server_name"] = server_name
        config["cloud"] = cloud
        config["token_env"] = token_env
        if service_directory == "" or "null":
            service_directory = CURRENT_DIR
        config["sonar_backup_conf"]["backup_folder"] = sonar_backup_folder 
        config["sonar_backup_conf"]["backup_zip"] = os.path.join(
            service_directory, f"sonar{slash_type}zip{slash_type}"
        )
        config["sonar_backup_conf"]["backup_lifetime"] = sonar_backup_lifetime
        logger.debug(f"Config: {config}")
    elif config_type == "hardware":
        client_info = json.loads(client_info)
        config = {
            "client": {"project_name": "", "server_name": ""},
            "cloud": "",
            "token_env": "",
        }
        if project_name == "":
            config["client"]["project_name"] = client_info["ClientName"]
        else:
            config["client"]["project_name"] = project_name
        if server_name == "":
            server_name = platform.node()
        config["client"]["server_name"] = server_name
        config["cloud"] = cloud
        config["token_env"] = token_env
        logger.debug(f"Config: {config}")
    elif config_type == "service_status":
        client_info = json.loads(client_info)
        config = {
            "client": {"project_name": "", "server_name": ""},
            "cloud": "",
            "token_env": "",
        }
        if project_name == "":
            config["client"]["project_name"] = client_info["ClientName"]
        else:
            config["client"]["project_name"] = project_name
        if server_name == "":
            server_name = platform.node()
        config["client"]["server_name"] = server_name
        config["cloud"] = cloud
        config["token_env"] = token_env
        config["services_names"] = services_names
        logger.debug(f"Config: {config}")
    return config


def wr_conf(file_conf, conf):
    """
    записывает файл конфига
    """

    wr_conf = {}

    def merg_dict(dict_one, dict_two):
        for k, v in dict_two.items():
            dict_one[k] = v
        return dict_one

    if file_conf:
        wr_conf = merg_dict(wr_conf, file_conf)
        wr_conf = merg_dict(wr_conf, conf)
    else:
        wr_conf = merg_dict(wr_conf, conf)
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as conf_file:
            yaml.dump(wr_conf, conf_file, sort_keys=True, allow_unicode=True)
        logger.debug(f"Config was written to the file: {wr_conf}")
    except Exception as exc:
        logger.debug(f"Config was not written to the file: {exc}")


def main():
    scripts_expressions_dict = {}
    
    args = get_args()
    config_type = args.get("config_type")
    service_directory = args.get("service_directory")
    token = args.get("token")
    token_env = args.get("token_env")
    project_name = args.get("project_name")
    server_name = args.get("server_name")
    
    db_backup_lifetime = args.get("db_backup_lifetime")
    db_name = args.get("db_name")
    postgresql_version = args.get("postgresql_version")
    postgresql_host = args.get("postgresql_host")
    postgresql_port = args.get("postgresql_port")
    postgresql_user = args.get("postgresql_user")
    postgresql_env_pass = args.get("postgresql_env_pass")
    postgresql_pass = args.get("postgresql_pass")
    local_db_backup_cron = args.get("local_db_backup_cron")
    db_service_cron = args.get("db_service_cron")
    
    files_backup_folder = args.get("files_backup_folder")
    files_backup_cron = args.get("files_backup_cron")
    files_backup_lifetime = args.get("files_backup_lifetime")
    files_exclude_mask = args.get("files_exclude_mask")
    files_exclude_lifetime = args.get("files_exclude_lifetime")
        
    daily_s3_db_backup_cron = args.get("daily_s3_db_backup_cron")
    weekly_s3_db_backup_cron = args.get("weekly_s3_db_backup_cron")
    daily_s3_files_backup_cron = args.get("daily_s3_files_backup_cron")
    weekly_s3_files_backup_cron = args.get("weekly_s3_files_backup_cron")
    
    sonar_backup_cron = args.get("sonar_backup_cron")
    sonar_backup_folder = args.get("sonar_backup_folder")
    sonar_backup_lifetime = args.get("sonar_backup_lifetime")
    
    hardware_monitoring_cron = args.get("hardware_monitoring_cron")
    
    services_names = args.get("services_names")

    file_conf = rd_config()

    if token == "":
        logger.debug("Missing token")
        token = input("Пожалуйста введи токен: ")
    if config_type.startswith('postgres'):
        if not postgresql_version:
            logger.debug("Missing version PG")
            postgresql_version = input("Пожалуйста введи версию PostgreSQL: ")
        if not postgresql_host:
            logger.debug("Missing postgresql_host")
            postgresql_host = input("Пожалуйста введи PostgreSQL хост: ")
        if not postgresql_user:
            logger.debug("Missing postgresql_user")
            postgresql_user = input("Пожалуйста введи PostgreSQL пользователя: ")
        if not postgresql_pass:
            logger.debug("Missing postgresql_pass")
            postgresql_pass = input("Пожалуйста введи PostgreSQL пароль: ")
        if config_type.endswith('base') and not db_name:
            logger.debug("Missing db_name")
            db_name = input("Пожалуйста введи имя базы: ")
    elif config_type == "sonar":
        logger.debug("Make config for sonar")
    elif config_type == "hardware":
        logger.debug("Make config for hardware only")
    elif config_type == "service_status":
        logger.debug("Make config for service status only")
    elif config_type == "files_backup":
        if not files_backup_folder:
            logger.debug("Missing files_backup_folder")
            files_backup_folder = input("Пожалуйста введи директорию с файлами для бэкапа: ")
        logger.debug("Make config for files backup only")
    else:
        logger.debug("Enter correct type of config")
        config_type = input(
            "Пожалуйста введи правильный тип конфига: "
            + "sonar - конфиг для ВМ с sonar, "
            + "postgres_base - конфиг для работы с отдельной базой PostgreSQL и аппаратного мониторинга, "
            + "postgres_cluster - конфиг для работы с кластером PostgreSQL и аппаратного мониторинга, "
            + "files_backup - конфиг для бэкапа файлов в ZIP-архиве, "
            + "hardware - только для аппаратного мониторинга: "
        )

    if wr_env(token_env, token):
        if config_type.startswith('postgres'):
            if wr_env(postgresql_env_pass, postgresql_pass):
                if config_type.endswith('base'):
                    scripts_expressions_dict[
                        "pg_backup_service.py --launch_type=backup --backup_type=single_base"
                        ] = local_db_backup_cron
                elif config_type.endswith('cluster'):
                    scripts_expressions_dict[
                        "pg_backup_service.py --launch_type=backup --backup_type=full_cluster"
                        ] = local_db_backup_cron
                scripts_expressions_dict["pg_backup_service.py --launch_type=service"] = db_service_cron
                scripts_expressions_dict[
                    "s3_upload.py --launch_period=daily --backup_type=db"
                ] = daily_s3_db_backup_cron
                scripts_expressions_dict[
                    "s3_upload.py --launch_period=weekly --backup_type=db"
                ] = weekly_s3_db_backup_cron
            else:
                logger.debug("Does not get environment var for postgresql")
        elif config_type == "sonar":
            scripts_expressions_dict[
                "files_backup.py --backup_type=sonar"
            ] = sonar_backup_cron
            scripts_expressions_dict[
                "s3_upload.py --launch_period=daily --backup_type=sonar"
            ] = daily_s3_db_backup_cron
            scripts_expressions_dict[
                "s3_upload.py --launch_period=weekly --backup_type=sonar"
            ] = weekly_s3_db_backup_cron
        elif config_type == "files_backup":
            scripts_expressions_dict[
                "files_backup.py"
            ] = files_backup_cron
            scripts_expressions_dict[
                "s3_upload.py --launch_period=daily --backup_type=files"
            ] = daily_s3_files_backup_cron
            scripts_expressions_dict[
                "s3_upload.py --launch_period=weekly --backup_type=files"
            ] = weekly_s3_files_backup_cron
        elif config_type == "hardware":
            scripts_expressions_dict["hardware_monitoring.py"] = hardware_monitoring_cron
        elif config_type == "service_status":
            scripts_expressions_dict["service_monitoring.py"] = hardware_monitoring_cron
        wr_cron(scripts_expressions_dict)
        client_info, cloud = get_current_client_info(token)
        if not client_info:
            logger.error("Client info is empty")
            exit(1)
        conf = mk_config(
            config_type,
            client_info,
            cloud,
            project_name,
            server_name,
            token_env,
            db_name,
            postgresql_version,
            postgresql_host,
            postgresql_port,
            postgresql_user,
            postgresql_env_pass,
            service_directory,
            db_backup_lifetime,
            services_names,
            files_backup_folder,
            files_backup_lifetime,
            files_exclude_mask,
            files_exclude_lifetime,
            sonar_backup_folder,
            sonar_backup_lifetime,
        )
        wr_conf(file_conf, conf)
    else:
        logger.debug("Does not get environment var for yandex cloud token")


if __name__ == "__main__":
    main()
