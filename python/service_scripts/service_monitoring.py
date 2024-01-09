#!/usr/bin/python3

import copy
import subprocess
from modules.config import config
from modules.log_config import logging_config
from modules.monitoring import send_monitoring_metrics

logger = logging_config(__file__, main_module=True)


def service_status(service_name):
    """
    Возвращает статус службы.
    """

    service_status = subprocess.run(['systemctl', 'is-active', service_name], 
                            capture_output=True, 
                            text=True).stdout.strip()
    logger.debug(f"Service {service_name} is {service_status}")
    if service_status == 'active':
        return True
    else:
        return False   


def metrics():
    """
    Возвращает список метрик.
    """
    
    conf = config()
    srv_name = conf["client"]["server_name"]
    prj_name = conf["client"]["project_name"]
    services_names = conf["client"]["services_names"]
    metrics_array = []
    metrics_data = {
        "name": "service_monitoring",
        "labels": {
            "project_name": prj_name,
            "server_name": srv_name,
        },
        "value": "",
    }
    for service_name in services_names.split(','):
        service_metrics = copy.deepcopy(metrics_data) 
        service_metrics["labels"]["service_name"] = service_name
        if service_status(service_name):
            service_metrics["value"] = 1
        else:
            service_metrics["value"] = -1
        metrics_array.append(service_metrics) 

    service_metrics = {"metrics": metrics_array}
    return service_metrics


def main():
    send_monitoring_metrics(__file__, metrics())


if __name__ == "__main__":
    main()