import os
import sys
from dotenv import load_dotenv

def check_env(key: str) -> str:
    v = os.getenv(key)
    if v is None or len(v) == 0:
        print(f"ERROR: Missing environment variable: {key}")
        sys.exit()
    return v

def get_int(value:str)->int:
    if not value.isdigit():
        print(f"ERROR: {value} can't be converted as int")
        sys.exit()
    return int(value)

dotenvpath = os.path.dirname(os.path.abspath(__file__)) + "/../.env"
if os.path.exists(dotenvpath) and os.path.isfile(dotenvpath):
    load_dotenv(dotenvpath)


SAVE_LOGS_TO_FILE = check_env("SAVE_LOGS_TO_FILE") == "true"
LOG_FOLDER = check_env("LOG_FOLDER")
INFO_LOG_MAX_BYTES_SIZE = get_int(check_env("INFO_LOG_MAX_BYTES_SIZE"))
ERROR_LOG_MAX_BYTES_SIZE = get_int(check_env("ERROR_LOG_MAX_BYTES_SIZE"))
BOT_TOKEN= check_env("BOT_TOKEN")