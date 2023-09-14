import os
import sys
import yaml
import json
import logging
import argparse
import requests
import platform
import subprocess

CURRENTDIR = os.path.dirname(os.path.abspath(__file__))
CONFIGNAME = os.path.join(CURRENTDIR, "conf.yaml")


def get_args():
    parser = argparse.ArgumentParser(
        description="Создаёт конфиг для работы с PostgreSQL, sonar и отправки метрик аппаратного мониторинга в Яндекс-Мониторинг."
    )
    parser.add_argument(
        "--config_type",
        default="hardware",
        type=str,
        help="Тип конфига: " 
        + "По умолчанию hardware - только для аппаратного мониторинга,"
        + "sonar - конфиг для ВМ с sonar, "
        + "service_status - конфиг для проверки статуса служб systemctl"
        + "postgres_base - конфиг для работы с отдельной базой PostgreSQL и аппаратного мониторинга, "
        + "postgres_cluster - конфиг для работы с кластером PostgreSQL и аппаратного мониторинга. ",
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
        "--backup_lifetime",
        default="3",
        type=str,
        help="Время жизни локального бэкапа. По умолчанию 3 дня",
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
        default="",
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
        default="0 18 */1 * *",
        type=str,
        help="Задание в cron для локального бэкапа \n"
        + "По умолчанию: '0 18 */1 * *' \n",
    )
    parser.add_argument(
        "--db_service_cron",
        default="30 18 */1 * *",
        type=str,
        help="Задание в cron для сервиса БД \n" + "По умолчанию: '30 18 */1 * *' \n",
    )
    parser.add_argument(
        "--daily_s3_db_backup_cron",
        default="0 19 */1 * *",
        type=str,
        help="Задание в cron для ежедневного бэкапа в s3 \n"
        + "По умолчанию: '0 19 */1 * *' \n",
    )
    parser.add_argument(
        "--weekly_s3_db_backup_cron",
        default="0 20 * * */6",
        type=str,
        help="Задание в cron для еженедельного бэкапа в s3 \n"
        + "По умолчанию: '0 20 * * */6' \n",
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
        "--services_names",
        type=str,
        help="Имена служб для мониторинга \n"
        + "для отслеживания нескольких служб, перечислить через запятую \n",
    )
    args = parser.parse_args()

    return vars(args)


def wr_env(env_name, env_value):
    wr_token = 0
    try:
        if os.environ.get(env_name) == None:
            subprocess.check_output(
                f"echo {env_name}={env_value} >> /etc/environment", shell=True
            )
            logging.info(
                f"Переменная {env_name} успешно записана в файл /etc/environment"
            )
            wr_token = 1
            return wr_token
        else:
            logging.info(
                f"Переменная {env_name} уже есть в файле /etc/environment и не будет заменена"
            )
            wr_token = 1
            return wr_token
    except Exception as exc:
        logging.error(f"Ошибка записи переменной {env_name}: {exc}")
        wr_token = 0
        return wr_token


def get_current_client_info(token):
    attempts = 5
    prod_url = "https://apigwpriv.bit-erp.ru/getcurrentclientinfo"
    test_url = "https://devapigwpriv.bit-erp.ru/getcurrentclientinfo"

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

    client_info = get_response(attempts, test_url)
    if client_info:
        cloud = "test"
        logging.debug(f"Client info: {client_info}")
        return client_info, cloud
    else:
        client_info = get_response(attempts, prod_url)
        logging.debug(f"Client info: {client_info}")
        cloud = "prod"
        return client_info, cloud


def wr_cron(scripts_name_expressions_dict, script_arguments=""):
    for script_name, expression in scripts_name_expressions_dict.items():
        script_path = os.path.join(CURRENTDIR, script_name)
        if '.py' in script_name:
            program = 'python3'
        elif '.sh' in script_name:
            program = 'bash'
        else:
            logging.error("Error write cron expression unknown type of script")     
        try:
            subprocess.check_output(
                f"echo '{expression} root {program} {script_path} {script_arguments} >/dev/null 2>&1' >> /etc/cron.d/bit_svc",
                shell=True,
            )
            logging.info("Cron expression is successfully write to /etc/cron.d/bit_svc")
        except Exception as exc:
            logging.error(f"Error write cron expression: {exc}")


def rd_config():
    conf_dict = {}
    try:
        with open(CONFIGNAME, encoding="utf-8") as conf_file:
            conf_dict = yaml.safe_load(conf_file)
            return conf_dict
    except FileNotFoundError:
        return conf_dict


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
    backup_lifetime,
    services_names,
):
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
            "backup_conf": {
                "backup_lifetime": "",
                "bak_files_path": "",
                "zip_files_path": "",
                "log_files_path": "",
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
            service_directory = CURRENTDIR
        print(service_directory)
        config["backup_conf"]["bak_files_path"] = os.path.join(
            service_directory, "pg_backup/backup/"
        )
        config["backup_conf"]["zip_files_path"] = os.path.join(
            service_directory, "pg_backup/zip/"
        )
        config["backup_conf"]["log_files_path"] = os.path.join(
            service_directory, "pg_backup/log/"
        )
        config["backup_conf"]["backup_lifetime"] = backup_lifetime
        logging.info(f"Config: {config}")
    elif config_type == "sonar":
        config = {
            "client": {"project_name": "", "server_name": ""},
            "cloud": "",
            "token_env": "",
            "postgresql_conf": {
                "db_name": "",
            },
            "backup_conf": {
                "backup_lifetime": "",
                "bak_files_path": "",
                "zip_files_path": "",
                "log_files_path": "",
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
        if db_name == "" or "null":
            db_name = platform.node()
        config["postgresql_conf"]["db_name"] = db_name
        if service_directory == "" or "null":
            service_directory = "/opt/sonarqube"
        config["backup_conf"]["bak_files_path"] = os.path.join(
            service_directory, "backup/"
        )
        config["backup_conf"]["zip_files_path"] = os.path.join(
            service_directory, "zip/"
        )
        config["backup_conf"]["log_files_path"] = os.path.join(
            service_directory, "log/"
        )
        if backup_lifetime == "" or "null":
            backup_lifetime = "1"
        config["backup_conf"]["backup_lifetime"] = backup_lifetime
        logging.info(f"Config: {config}")
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
        logging.info(f"Config: {config}")
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
        logging.info(f"Config: {config}")
    return config


def wr_conf(file_conf, conf):
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
        with open(CONFIGNAME, "w", encoding="utf-8") as conf_file:
            yaml.dump(wr_conf, conf_file, sort_keys=True, allow_unicode=True)
        logging.info(f"Config was written to the file: {wr_conf}")
    except Exception as exc:
        logging.error(f"Config was not written to the file: {exc}")


def install_requirements(config_type):
    requirements_path = os.path.join(CURRENTDIR, "requirements.txt")
    if config_type.startswith('postgres'):
        try:
            subprocess.call(f"sudo -n apt update", shell=True)
            subprocess.call(f"sudo -n apt install pip -y", shell=True)
            subprocess.call(f"sudo -n apt install postgresql-client -y", shell=True)
            subprocess.call(f"sudo -n apt install p7zip-full -y", shell=True)
            subprocess.call(f"sudo -n pip install --default-timeout=1000 -r {requirements_path}", shell=True)
            logging.info(
                f"PostgreSQL-client, pip and requirement libraries successfully installed"
            )
        except Exception as exc:
            logging.error(f"Error install pip and requirement libraries: {exc}")

    elif config_type == "hardware" or config_type == "sonar":
        try:
            subprocess.call(f"sudo -n apt update", shell=True)
            subprocess.call(f"sudo -n apt install p7zip-full -y", shell=True)
            subprocess.call(f"sudo -n apt install pip -y", shell=True)
            subprocess.call(f"sudo -n pip install --default-timeout=1000 -r {requirements_path}", shell=True)
            logging.info(f"7zip, pip and requirement libraries successfully installed")
        except Exception as exc:
            logging.error(f"Error install pip and requirement libraries: {exc}")


def main():
    name = os.path.basename(sys.argv[0]).split(".")[0]
    log_dir_path = os.path.join(CURRENTDIR, name)
    if not os.path.exists(log_dir_path):
        os.makedirs(log_dir_path)
    log_file_path = os.path.join(log_dir_path, f"{name}.log")
    logging.basicConfig(
        handlers=[logging.StreamHandler(), logging.FileHandler(log_file_path)],
        level=logging.DEBUG,
        format="[%(asctime)s] {%(levelname)s} %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    scripts_expressions_dict = {}
    args = get_args()
    config_type = args.get("config_type")
    token = args.get("token")
    token_env = args.get("token_env")
    project_name = args.get("project_name")
    server_name = args.get("server_name")
    service_directory = args.get("service_directory")
    backup_lifetime = args.get("backup_lifetime")
    db_name = args.get("db_name")
    postgresql_version = args.get("postgresql_version")
    postgresql_host = args.get("postgresql_host")
    postgresql_port = args.get("postgresql_port")
    postgresql_user = args.get("postgresql_user")
    postgresql_env_pass = args.get("postgresql_env_pass")
    postgresql_pass = args.get("postgresql_pass")
    local_db_backup_cron = args.get("local_db_backup_cron")
    db_service_cron = args.get("db_service_cron")
    daily_s3_db_backup_cron = args.get("daily_s3_db_backup_cron")
    weekly_s3_db_backup_cron = args.get("weekly_s3_db_backup_cron")
    sonar_backup_cron = args.get("sonar_backup_cron")
    hardware_monitoring_cron = args.get("hardware_monitoring_cron")
    services_names = args.get("services_names")

    install_requirements(config_type)

    file_conf = rd_config()

    if token == "":
        logging.error("Missing token")
        token = input("Пожалуйста введи токен: ")
    if config_type.startswith('postgres'):
        if platform.system() == "Windows" and postgresql_version == "":
            logging.error("Missing version PG")
            postgresql_version = input("Пожалуйста введи версию PostgreSQL: ")
        if postgresql_host == "":
            logging.error("Missing postgresql_host")
            postgresql_host = input("Пожалуйста введи PostgreSQL хост: ")
        if postgresql_user == "":
            logging.error("Missing postgresql_user")
            postgresql_user = input("Пожалуйста введи PostgreSQL пользователя: ")
        if postgresql_pass == "":
            logging.error("Missing postgresql_pass")
            postgresql_pass = input("Пожалуйста введи PostgreSQL пароль: ")
        if config_type.endswith('base') and db_name == "":
            logging.error("Missing db_name")
            db_name = input("Пожалуйста введи имя базы: ")
    elif config_type == "sonar":
        logging.info("Make config for sonar")
    elif config_type == "hardware":
        logging.info("Make config for hardware only")
    elif config_type == "service_status":
        logging.info("Make config for service status only")
    else:
        logging.error("Enter correct type of config")
        config_type = input(
            "Пожалуйста введи правильный тип мониторинга "
            + "sonar - конфиг для ВМ с sonar, "
            + "postgres_base - конфиг для работы с отдельной базой PostgreSQL и аппаратного мониторинга, "
            + "postgres_cluster - конфиг для работы с кластером PostgreSQL и аппаратного мониторинга, "
            + "hardware - только для аппаратного мониторинга: "
        )

    if wr_env(token_env, token) and wr_env(postgresql_env_pass, postgresql_pass):
        if config_type.startswith('postgres'):
            if config_type.endswith('base'):
                scripts_expressions_dict["pg_backup.py --backup_type=single_base"] = local_db_backup_cron
            elif config_type.endswith('cluster'):
                scripts_expressions_dict["pg_backup.py --backup_type=full_cluster"] = local_db_backup_cron
            scripts_expressions_dict["pg_service.py"] = db_service_cron
            scripts_expressions_dict[
                "s3_upload.py --launch_period=daily"
            ] = daily_s3_db_backup_cron
            scripts_expressions_dict[
                "s3_upload.py --launch_period=weekly"
            ] = weekly_s3_db_backup_cron
            scripts_expressions_dict["send_hw_mon.py"] = hardware_monitoring_cron
        elif config_type == "sonar":
            scripts_expressions_dict[
                "backup_postgres_sonar.sh"
            ] = sonar_backup_cron
            scripts_expressions_dict[
                "s3_upload.py --launch_period=daily"
            ] = daily_s3_db_backup_cron
            scripts_expressions_dict[
                "s3_upload.py --launch_period=weekly"
            ] = weekly_s3_db_backup_cron
            scripts_expressions_dict["send_hw_mon.py"] = hardware_monitoring_cron
        elif config_type == "hardware":
            scripts_expressions_dict["send_hw_mon.py"] = hardware_monitoring_cron
        elif config_type == "service_status":
            scripts_expressions_dict["service_monitoring.py"] = hardware_monitoring_cron
        wr_cron(scripts_expressions_dict)
        client_info, cloud = get_current_client_info(token)
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
            backup_lifetime,
            services_names,
        )
        wr_conf(file_conf, conf)
    else:
        logging.error("Does not get environment var, nothing to do")


if __name__ == "__main__":
    main()
