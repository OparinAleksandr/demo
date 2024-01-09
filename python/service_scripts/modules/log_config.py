#!/usr/bin/env python3

import os
import logging
from logging.handlers import RotatingFileHandler


def logging_config(module_name, main_module):
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logs_dir = os.path.join(parent_dir, "logs")
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    
    log_filename = os.path.basename(module_name).replace("py", "log") 
    if not main_module:
        log_filename = f"{log_filename.replace('.', '_')}.log"
    log_path = os.path.join(logs_dir, log_filename)
    
    logger = logging.getLogger(module_name)    

    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        try:
            log_handler = RotatingFileHandler(log_path, maxBytes=300000, backupCount=5)
            log_handler.setLevel(logging.DEBUG)
        except PermissionError:
            log_path = os.path.join(logs_dir, f"user_{log_filename}")
            log_handler = RotatingFileHandler(log_path, maxBytes=300000, backupCount=5)
            log_handler.setLevel(logging.DEBUG)
        
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        
        if main_module:
            formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] > %(message)s", "%Y-%m-%dT%H:%M:%S")
        else:
            formatter = logging.Formatter("[%(asctime)s] [%(name)s] [%(levelname)s] >  %(message)s", "%Y-%m-%dT%H:%M:%S")
        log_handler.setFormatter(formatter)
        stream_handler.setFormatter(formatter)
        
        logger.addHandler(log_handler)
        logger.addHandler(stream_handler)
    
    return logger


