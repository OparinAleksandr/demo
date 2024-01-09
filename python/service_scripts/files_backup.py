#!/usr/bin/env python3

import os
import argparse
from modules.files import *
from modules.config import config
from modules.log_config import logging_config


def get_args():
    parser = argparse.ArgumentParser(description="Формирует локальные бэкапы файлов.")
    parser.add_argument(
        "--backup_type",
        default="files",
        type=str,
        help="Тип бэкапа: files - файлов, sonar - для ВМ с сонаром",
    )
    args = parser.parse_args()
    return vars(args)


backup_type = get_args().get("backup_type")
logger = logging_config(f"{backup_type}_backup.log", main_module=True)


def main():
    conf = config()
    backup_name = f"{backup_type}_{conf['client']['server_name']}"
    backup_file_name = mk_backup_file_name(backup_name, backup_type)
    zip_prog = zip_prog_path()
    source_path = conf[f"{backup_type}_backup_conf"][f"backup_folder"]
    destination_file_name = os.path.splitext(os.path.basename(backup_file_name))[0]
    destination_dir = conf[f"{backup_type}_backup_conf"]["backup_path"]
    mk_dir(destination_dir)
    destination_file = os.path.join(destination_dir, 
                                    destination_file_name + ".backup")
    if backup_type == "files":
        exclude_mask = conf[f"{backup_type}_backup_conf"][f"exclude_mask"]
        exclude_lifetime = conf[f"{backup_type}_backup_conf"][f"exclude_lifetime"]
        zip_command = f""""{zip_prog}" a -ssw -mx0 -mmt=2 -r0 -x!{exclude_mask}* {destination_file} {source_path}"""
    elif backup_type == "sonar":
        zip_command = f""""{zip_prog}" a -ssw -mx0 -mmt=2 -r0 {destination_file} {source_path}"""
    else:
        logger.debug(f"Fail {backup_type} is not supported")
        return
    zip_result = os.system(f"{zip_command}")
    if zip_result == 0:
        if backup_type == "files":
            del_files_by_mask(exclude_mask, source_path, exclude_lifetime)
        logger.debug(f"Success {source_path} is successfully zipped in file {destination_file}")
    else:
        logger.debug(f"Fail {source_path} is not zipped")


if __name__ == "__main__":
    main()
