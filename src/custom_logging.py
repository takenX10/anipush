import os, sys, logging
from logging.handlers import RotatingFileHandler
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

import custom_config

MODULE_NAME = "ANIPUSH"
LOGGER : None|logging.Logger = None

disable_warnings(InsecureRequestWarning)
logger: logging.Logger = logging.getLogger(__name__)

def format_error(_):
    return "\033[41m\033[1m[ ERROR ]\033[00m"

def format_warning(_):
    return "\033[43m\033[1m[WARNING]\033[00m"

def format_info(_):
    return "\033[44m\033[1m[ INFO  ]\033[00m"

def format_debug(_):
    return "\033[46m\033[1m[ DEBUG ]\033[00m"

def print_function_name(x:str):
    return x + (" "*(26-len(x)))

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        record.orig = record.msg
        timestamp = self.formatTime(record, self.datefmt)
        if record.levelno == logging.WARNING:
            record.msg = f"{format_warning('['+record.levelname+']')} {timestamp} {'{'}{MODULE_NAME}-{print_function_name(record.funcName)}{'}'} {record.msg}"
        elif record.levelno == logging.ERROR:
            record.msg = f"{format_error('['+record.levelname+']')} {timestamp} {'{'}{MODULE_NAME}-{print_function_name(record.funcName)}{'}'} {record.msg}"
        elif record.levelno == logging.INFO:
            record.msg = f"{format_info('['+record.levelname+']')} {timestamp} {'{'}{MODULE_NAME}-{print_function_name(record.funcName)}{'}'} {record.msg}"
        elif record.levelno == logging.DEBUG:
            record.msg = f"{format_debug('['+record.levelname+']')} {timestamp} {'{'}{MODULE_NAME}-{print_function_name(record.funcName)}{'}'} {record.msg}"
        return logging.Formatter.format(self, record)

class BaseFormatter(logging.Formatter):
    def format(self, record):
        record.msg = record.orig # type: ignore
        timestamp = self.formatTime(record, self.datefmt)
        if record.levelno == logging.WARNING:
            record.msg = f"[{record.levelname}] {timestamp} {'{'}{MODULE_NAME}-{print_function_name(record.funcName)}{'}'} {record.msg}"
        elif record.levelno == logging.ERROR:
            record.msg = f"[ {record.levelname} ] {timestamp} {'{'}{MODULE_NAME}-{print_function_name(record.funcName)}{'}'} {record.msg}"
        elif record.levelno == logging.INFO:
            record.msg = f"[ {record.levelname}  ] {timestamp} {'{'}{MODULE_NAME}-{print_function_name(record.funcName)}{'}'} {record.msg}"
        elif record.levelno == logging.DEBUG:
            record.msg = f"[ {record.levelname} ] {timestamp} {'{'}{MODULE_NAME}-{print_function_name(record.funcName)}{'}'} {record.msg}"
        return logging.Formatter.format(self, record)


def set_logger(module_name, logger_level=logging.DEBUG):
    global MODULE_NAME, LOGGER
    if LOGGER:
        return LOGGER
    MODULE_NAME = module_name
    LOGGER = logging.getLogger(module_name)
    LOGGER.setLevel(logger_level)

    console_formatter: ColoredFormatter = ColoredFormatter(datefmt='%Y-%m-%d %H:%M:%S')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logger_level)
    console_handler.setFormatter(console_formatter)
    LOGGER.addHandler(console_handler)

    if custom_config.SAVE_LOGS_TO_FILE:
        base_formatter: BaseFormatter = BaseFormatter(datefmt='%Y-%m-%d %H:%M:%S')
        debug_handler = RotatingFileHandler(f"{os.path.join(custom_config.LOG_FOLDER, 'debug.log')}", maxBytes=custom_config.INFO_LOG_MAX_BYTES_SIZE, backupCount=5)
        debug_handler.setFormatter(base_formatter)
        debug_handler.setLevel(logging.DEBUG)
        LOGGER.addHandler(debug_handler)

        error_handler = RotatingFileHandler(f"{os.path.join(custom_config.LOG_FOLDER, 'error.log')}", maxBytes=custom_config.ERROR_LOG_MAX_BYTES_SIZE, backupCount=5)
        error_handler.setFormatter(base_formatter)
        error_handler.setLevel(logging.ERROR)
        LOGGER.addHandler(error_handler)
    return LOGGER
