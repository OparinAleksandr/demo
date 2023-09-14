# устанавливает токен мониторинга
# в переменную окружения
import os
import platform
import pyautogui

from conf import rd_env
from conf import wr_log
from conf import log_conf


def main():
    log_conf("set_token.log")
    wr_log("test")
    yc_token = pyautogui.password(
        text="Токен", title="Set environment variable", default="", mask="*"
    )
    env_name = rd_env()
    if yc_token:
        try:
            if platform.system() == "Windows":
                command = f'setx {env_name} "{yc_token}" /M'
            else:
                command = f"export {env_name}={yc_token}"
            os.system(f"{command}")
        except Exception as exc:
            log_data = f"Error ocurred wen set env variabale {exc}"
            wr_log(log_data)


if __name__ == "__main__":
    main()
