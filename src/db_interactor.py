import sqlite3
import custom_config
from custom_dataclasses import AnimeData
from custom_logging import set_logger

log = set_logger("DATABASE_INTERACTOR")


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


def add_anime_bulk(anime_list: list[AnimeData], related_to:int) -> bool:
    log.info(f"[.] Adding bulk anime list to db (length: {len(anime_list)})")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.executemany(
            """
            INSERT OR REPLACE INTO anime (
                id, title, type, status, cover, episodes, latest_aired_episode, related_to
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    anime.id,
                    anime.title,
                    anime.type,
                    anime.status,
                    anime.cover,
                    anime.episodes,
                    anime.latest_aired_episode,
                    related_to
                )
                for anime in anime_list
            ]
        )
        conn.commit()
        log.info(f"[+] Bulk insert successful")
        return True
    except Exception as e:
        log.error(f"[!] Error during bulk insert: {e}")
        return False
    finally:
        conn.close()
        return True


def add_user_anime_bulk(anime_ids: list[int], user_id: int) -> bool:
    log.info(f"[.] Adding bulk user_anime (user_id: {user_id}, len anime_ids: {len(anime_ids)})")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    try:
        cursor.executemany(
            """
            INSERT OR REPLACE INTO user_anime (
                user_id, anime_id, notified_episode
            ) VALUES (?, ?, ?)
            """,
            [
                (
                    user_id,
                    anime_id,
                    0  # notified_episode default a 0
                )
                for anime_id in anime_ids
            ]
        )
        conn.commit()
        log.info(f"[+] Bulk insert into user_anime successful")
        return True
    except Exception as e:
        log.error(f"[!] Error during bulk insert into user_anime: {e}")
        return False
    finally:
        conn.close()
        return True