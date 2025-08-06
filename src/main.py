import logging
from custom_logging import set_logger
from db_interactor import init_db
from telegram_bot_interface import init_telegram_bot

log = set_logger("ANIPUSH", logging.DEBUG)


def main():
    init_db()
    init_telegram_bot()


if __name__ == "__main__":
    main()
