import sqlite3
import custom_config
from custom_logging import set_logger
import logging

log = set_logger("DATABASE_INTERACTOR", logging.DEBUG)


def add_column(table_name, column_name, column_type):
    log.info(f"\t\t[.] Adding column {column_name} on table {table_name}")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name});")
    columns = [row[1] for row in cur.fetchall()]

    if column_name not in columns:
        cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type};")
        conn.commit()
        log.info(f"\t\t[+] Column {column_name} on table {table_name} added successfully")
    else:
        log.info(f"\t\t[-] Column {column_name} on table {table_name} was already present")

    conn.close()

def run_migrations():
    """Run all database migrations in order"""
    log.info("\t[.] Running migrations commands")
    #add_column("users", "is_admin", "INTEGER DEFAULT 0")
    log.info("\t[-] Done running migrations")
    pass

def init_db():
    log.info("[.] Initializing database")
    log.info("\t[.] Checking and adding tables")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            telegram_handle TEXT,
            anilist_handle TEXT
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            type TEXT,
            status TEXT,
            cover TEXT,
            episodes INTEGER,
            latest_aired_episode INTEGER,
            related_to INTEGER
        );
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_anime (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            anime_id INTEGER,
            notified_episode INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(anime_id) REFERENCES anime(id)
        );
    """)    
    conn.commit()
    conn.close()
    log.info("\t[-] Done checking and adding tables")
    run_migrations()
    log.info("[-] Done initializing database")
