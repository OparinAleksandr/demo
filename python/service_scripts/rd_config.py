import os
import sys
import yaml
import logging
import subprocess


def wr_log(log_data):
    logger = logging.getLogger()
    logger.debug(log_data)


def rd_config_file():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    conf_file_name = "conf.yaml"
    mk_config_file_name = "mk_config.py"
    conf_file_path = os.path.join(current_dir, conf_file_name)
    mk_config_file_path = os.path.join(current_dir, mk_config_file_name)

    def rd_config(conf_file_path):
        with open(conf_file_path, encoding="utf-8") as conf_file:
            conf_dict = yaml.safe_load(conf_file)
        return conf_dict

    try:
        conf_dict = rd_config(conf_file_path)
    except FileNotFoundError:
        subprocess.call(f"python3 {mk_config_file_path}", shell=True)
        print(
            ">> config.yaml does not exist and will be created, "
            + "run the script again to send the metrics"
        )
        sys.exit()
    return conf_dict


conf = rd_config_file()


def rd_cloud():
    return conf.get("cloud")


def rd_client():
    return conf.get("client")


def rd_project_name():
    return rd_client().get("project_name")


def rd_server_name():
    return rd_client().get("server_name")


def rd_backup_conf():
    return conf.get("backup_conf")


def rd_zip_files_path():
    zip_files_path = rd_backup_conf().get("zip_files_path")
    if not os.path.exists(zip_files_path):
        os.makedirs(zip_files_path)
    return zip_files_path


def rd_bak_files_path():
    bak_files_path = rd_backup_conf().get("bak_files_path")
    if not os.path.exists(bak_files_path):
        os.makedirs(bak_files_path)
    return bak_files_path


def rd_log_files_path():
    log_files_path = rd_backup_conf().get("log_files_path")
    if not os.path.exists(log_files_path):
        os.makedirs(log_files_path)
    return log_files_path


def rd_backup_lifetime():
    return rd_backup_conf().get("backup_lifetime")


def rd_token_env():
    return os.environ.get(conf.get("token_env"))


def rd_postgresql_conf():
    return conf.get("postgresql_conf")


def rd_db_name():
    return rd_postgresql_conf().get("db_name")


def rd_version():
    return rd_postgresql_conf().get("version")


def rd_host():
    return rd_postgresql_conf().get("host")


def rd_passwd_env():
    return rd_postgresql_conf().get("passwd_env")


def rd_port():
    return rd_postgresql_conf().get("port")


def rd_user():
    return rd_postgresql_conf().get("user")


def rd_services_names():
    return conf.get("services_names")


def mk_url_dom():
    cloud = rd_cloud()
    if cloud == "test":
        url_dom = "devapigwpriv"
    elif cloud == "prod":
        url_dom = "apigwpriv"
    return url_dom
