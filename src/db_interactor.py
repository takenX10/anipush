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
    log.info(f"\t[.] Running migrations commands")
    #add_column("users", "is_admin", "INTEGER DEFAULT 0")
    log.info(f"\t[-] Done running migrations")
    pass

def init_db():
    log.info("[.] Initializing database")
    log.info(f"\t[.] Checking and adding tables")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            telegram_handle TEXT,
            anilist_id INTEGER,
            last_activity_checked INTEGER DEFAULT 0
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
            anilist_user_id INTEGER,
            anime_id INTEGER,
            notified_episode INTEGER DEFAULT 0,
            UNIQUE(anilist_user_id, anime_id)
        );
    """)    
    conn.commit()
    conn.close()
    log.info(f"\t[-] Done checking and adding tables")
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
            INSERT OR ignore wINTO user_anime (
                anilist_user_id, anime_id
            ) VALUES (?, ?)
            """,
            [
                (
                    user_id,
                    anime_id
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
    

def get_last_user_activity(user_id:int)->int:
    log.info(f"[.] Getting last user activity (userid: {user_id})")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT last_activity_checked FROM users WHERE anilist_id = ?""",
        (user_id,),
    )
    res = cursor.fetchall()
    conn.close()
    if len(res) != 1 or len(res[0]) != 1:
        log.info(f"[+] Activity date not found, returning 0")
        return 0
    log.info(f"[+] Found activity date: {res[0][0]}")
    return res[0][0]
    

def check_anime_in_db(anime_id:int)->bool:
    log.info(f"[.] Checking if anime is already in db {anime_id}")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id FROM anime WHERE id = ?""",
        (anime_id,),
    )
    res = cursor.fetchall()
    conn.close()
    if len(res) != 1 or len(res[0]) != 1:
        log.info(f"[-] Anime not in db")
        return False
    log.info(f"[+] Anime is in db")
    return True

def get_user_id_list()->list[int]:
    log.info(f"[.] Getting user id list")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT anilist_id FROM users""",
    )
    res = cursor.fetchall()
    conn.close()
    return [r[0] for r in res] or []

def update_last_user_activity(user_id:int, last_activity:int):
    log.info(f"[.] Updating last user activity for user_id {user_id} and new activity {last_activity}")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """update users set last_activity_checked=? where id=?""",
        (last_activity, user_id, ),
    )
    conn.commit()
    conn.close()
    return