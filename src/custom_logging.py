import os, sys, logging
from logging.handlers import RotatingFileHandler
from urllib3.exceptions import InsecureRequestWarning
from urllib3 import disable_warnings

import custom_config

MODULE_NAME = "ANIPUSH"

disable_warnings(InsecureRequestWarning)
logger: logging.Logger = logging.getLogger(__name__)

class bcolors:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    
def format_error(x):
    return "\033[41m\033[1m" + x + "\033[00m"

def format_warning(x):
    return "\033[43m\033[1m" + x + "\033[00m"

def format_info(x):
    return "\033[44m\033[1m" + x + "\033[00m"

def format_debug(x):
    return "\033[47m\033[1m" + x + "\033[00m"

class ColoredFormatter(logging.Formatter):
    def format(self, record):
        record.orig = record.msg
        if record.levelno == logging.WARNING:
            record.msg = f"{format_warning('['+record.levelname+']')} {'{'}{MODULE_NAME}-{record.funcName}{'}'} {record.msg}"
        elif record.levelno == logging.ERROR:
            record.msg = f"{format_error('['+record.levelname+']')} {'{'}{MODULE_NAME}-{record.funcName}{'}'} {record.msg}"
        elif record.levelno == logging.INFO:
            record.msg = f"{format_info('['+record.levelname+']')} {'{'}{MODULE_NAME}-{record.funcName}{'}'} {record.msg}"
        elif record.levelno == logging.DEBUG:
            record.msg = f"{format_debug('['+record.levelname+']')} {'{'}{MODULE_NAME}-{record.funcName}{'}'} {record.msg}"
        return logging.Formatter.format(self, record)

class BaseFormatter(logging.Formatter):
    def format(self, record):
        record.orig = record.msg
        if record.levelno == logging.WARNING:
            record.msg = f"[{record.levelname}] {'{'}{MODULE_NAME}-{record.funcName}{'}'} {record.msg}"
        elif record.levelno == logging.ERROR:
            record.msg = f"[{record.levelname}] {'{'}{MODULE_NAME}-{record.funcName}{'}'} {record.msg}"
        elif record.levelno == logging.INFO:
            record.msg = f"[{record.levelname}] {'{'}{MODULE_NAME}-{record.funcName}{'}'} {record.msg}"
        elif record.levelno == logging.DEBUG:
            record.msg = f"[{record.levelname}] {'{'}{MODULE_NAME}-{record.funcName}{'}'} {record.msg}"
        return logging.Formatter.format(self, record)


def set_logger(module_name, logger_level: logging._Level):
    global MODULE_NAME
    MODULE_NAME = module_name
    
    # Prints to console when live executing
    console_formatter: ColoredFormatter = ColoredFormatter()
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logger_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Saves to files
    if custom_config.SAVE_LOGS_TO_FILE:
        base_formatter: BaseFormatter = BaseFormatter()
        debug_handler = RotatingFileHandler(f"{os.path.join(custom_config.LOG_FOLDER, 'debug.log')}", maxBytes=custom_config.INFO_LOG_MAX_BYTES_SIZE, backupCount=5)
        debug_handler.setFormatter(base_formatter)
        debug_handler.setLevel(logging.DEBUG)
        logger.addHandler(debug_handler)

        error_handler = RotatingFileHandler(f"{os.path.join(custom_config.LOG_FOLDER, 'error.log')}", maxBytes=custom_config.ERROR_LOG_MAX_BYTES_SIZE, backupCount=5)
        error_handler.setFormatter(base_formatter)
        error_handler.setLevel(logging.ERROR)
        logger.addHandler(error_handler)

    # Logger setup
    logger = logging.getLogger()
    logger.setLevel(logger_level)
    logger.addHandler(console_handler)