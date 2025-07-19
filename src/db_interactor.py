import sqlite3
import custom_config
from custom_dataclasses import AnimeData, AnimeRelation
from custom_logging import set_logger

log = set_logger("DATABASE_INTERACTOR")

NO_OLD_DATA_FOUND_STATUS = "NO_OLD_DATA_FOUND"

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
    add_column("anime", "updated_at", "INTEGER DEFAULT 0")
    add_column("anime_relations", "date_update_found", "INTEGER DEFAULT 0")
    add_column("users", "telegram_id", "INTEGER DEFAULT -1")
    add_column("anime", "start_date", "INTEGER DEFAULT 0")
    add_column("anime", "old_status", "TEXT")
    add_column("users", "anilist_username", "TEXT")
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anime_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            primary_anilist_id INTEGER,
            related_anilist_id INTEGER,
            relation_type TEXT,
            UNIQUE(primary_anilist_id, related_anilist_id)
        );
    """)    
    conn.commit()
    conn.close()
    log.info(f"\t[-] Done checking and adding tables")
    run_migrations()
    log.info("[-] Done initializing database")


def add_anime_bulk(anime_list: list[AnimeData]) -> bool:
    log.info(f"[.] Adding bulk anime list to db (length: {len(anime_list)})")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    try:
        for anime in anime_list:
            old_status = NO_OLD_DATA_FOUND_STATUS
            cursor.execute(
                """SELECT status, updated_at, related_to FROM anime WHERE id = ?""",
                (anime.id,anime.updatedDate),
            )
            res = cursor.fetchall()
            if len(res) > 0:
                if res[0][1] > anime.updatedDate:
                    log.debug(f"[?] Did not update anime {anime.id} because the update date {anime.updatedDate} was older than the current one ({res[0][0]})")
                    continue
                if res[0][2] != -1:
                    old_status = res[0][0]
                
            cursor.execute(
                """
                INSERT OR REPLACE INTO anime (
                    id, title, type, status, cover, episodes, latest_aired_episode, related_to, updated_at, start_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    anime.id,
                    anime.title,
                    anime.type,
                    anime.status,
                    anime.cover,
                    anime.episodes,
                    anime.latest_aired_episode,
                    -1,
                    anime.updatedDate,
                    anime.startDate,
                    old_status
                )
            )
        conn.commit()
        log.info(f"[+] Bulk insert successful")
    except Exception as e:
        log.error(f"[!] Error during bulk insert: {e}")
        return False
    finally:
        conn.close()
        return True

def add_relations_bulk(relations_list: list[AnimeRelation]) -> bool:
    log.info(f"[.] Adding bulk relations list to db (length: {len(relations_list)})")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    try:
        for relation in relations_list:
            cursor.execute(
                """SELECT date_update_found FROM anime_relations WHERE primary_anilist_id=? AND related_anilist_id = ? AND date_update_found >= ?""",
                (relation.primary_anilist_id,relation.related_anilist_id, relation.date_update_found),
            )
            res = cursor.fetchall()
            if len(res) > 0:
                log.debug(f"[?] Did not update relation {relation.primary_anilist_id}->{relation.related_anilist_id} because the update date {relation.date_update_found} was older than the current one ({res[0][0]})")
                continue
            cursor.execute(
                """
                INSERT OR REPLACE INTO anime_relations (
                    primary_anilist_id, related_anilist_id, relation_type, date_update_found
                ) VALUES (?, ?, ?, ?)
                """,
                (
                    relation.primary_anilist_id,
                    relation.related_anilist_id,
                    relation.relation_type,
                    relation.date_update_found
                )
            )
        conn.commit()
        log.info(f"[+] Bulk insert successful")
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
            INSERT OR ignore INTO user_anime (
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
        """UPDATE users SET last_activity_checked=? WHERE anilist_id=?""",
        (last_activity, user_id, ),
    )
    conn.commit()
    conn.close()
    return


def get_last_updated_at()->int:
    log.info(f"[.] Getting user id list")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT updated_at FROM anime ORDER BY updated_at DESC LIMIT 1 """,
    )
    res = cursor.fetchall()
    conn.close()
    if len(res) != 1 or len(res[0]) != 1:
        return 0
    return res[0][0]

def get_anime_data(anime_id:int)->AnimeData|None:
    log.debug(f"[.] Getting anime data for anime {anime_id}")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT title,type,status,cover,episodes,latest_aired_episode,start_date,updated_at FROM anime WHERE id=?""",
        (anime_id,)
    )
    res = cursor.fetchall()
    conn.close()
    anime :AnimeData|None= None
    if len(res) == 1 and len(res[0]) == 8:
        anime = AnimeData(
            id=anime_id,
            title=res[0][0],
            type=res[0][1],
            status=res[0][2],
            cover=res[0][3],
            episodes=res[0][4],
            latest_aired_episode=res[0][5],
            startDate=res[0][6],
            updatedDate=res[0][7]
        )
    log.debug(f"[i] Done getting data for anime {anime_id}")
    return anime

def get_anime_relations(anime_id:int)->list[AnimeRelation]|None:
    log.debug(f"\t\t\t[.] Getting anime relations for anime {anime_id}")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT related_anilist_id, relation_type, date_update_found FROM anime_relations WHERE primary_anilist_id=?""",
        (anime_id,)
    )
    res = cursor.fetchall()
    conn.close()
    relation_list : list[AnimeRelation] = []
    for v in res:
        if len(v) != 3:
            log.error("\t\t\t[!] Data returned from the get_relation query is broken!")
            return None
        relation_list.append(AnimeRelation(
            primary_anilist_id=anime_id,
            related_anilist_id=v[0],
            relation_type=v[1],
            date_update_found=v[2]
        ))
    log.debug(f"[i] Done getting relations for anime {anime_id}")
    return relation_list

def update_anime_related_to(anime_id, relation_id):
    log.debug(f"[.] Getting anime relations for anime {anime_id}")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT status, old_status, related_to FROM anime WHERE id = ?""",
        (anime_id),
    )
    res = cursor.fetchall()
    if not res or len(res) == 0:
        log.error(f"[!] Can't update anime relation because anime does not exists {anime_id} {relation_id}")
        return
    if len(res[0]) != 3:
        log.error(f"[!] Something went wrong while extracting anime information during relation {anime_id}->{relation_id} insertion")
        return
    cursor.execute(
        """UPDATE anime SET related_to = ? WHERE id=?""",
        (relation_id, anime_id)
    )
    if res[0][1] == NO_OLD_DATA_FOUND_STATUS:
        # TODO: notify that the new anime has been found
        pass
    elif res[0][0] != res[0][1]:
        # TODO: notify that the new anime might have changed status
        pass
    
    conn.commit()
    conn.close()
    log.debug(f"[i] Done getting relations for anime {anime_id}")
    return

def find_next_unrelated_anime(offset:int)->int|None:
    log.debug(f"[.] Getting unrelated anime")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id FROM anime WHERE related_to=-1 limit 1 offset ?""",
        (offset,)
    )
    res = cursor.fetchall()
    conn.close()
    if len(res) != 1:
        log.debug(f"[i] No unrelated anime found")
        return None
    if len(res[0]) != 1:
        log.error("[!] Could not find unrelated anime, error in the database result")
        return None
    log.debug(f"[i] Done getting unrelated anime (id: {res[0][0]})")
    return res[0][0]


def get_telegram_id_list() -> list[int]:
    log.info(f"[.] Getting telegram id list")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """SELECT telegram_id FROM users WHERE telegram_id != -1""",
    )
    res = cursor.fetchall()
    conn.close()
    return [r[0] for r in res] or []


def upsert_user_telegram_anilist(telegram_id: int, anilist_username: str):
    log.info(f"[.] Upsert user: telegram_id={telegram_id}, anilist_username={anilist_username}")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO users (telegram_id, anilist_username)
        VALUES (?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET anilist_username=excluded.anilist_username
        """,
        (telegram_id, anilist_username)
    )
    conn.commit()
    conn.close()
    log.info(f"[+] Upsert user done")


def get_user_info_by_telegram_id(telegram_id: int):
    log.info(f"[.] Getting user info for telegram_id={telegram_id}")
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT anilist_username, anilist_id, last_activity_checked
        FROM users WHERE telegram_id = ?
        """,
        (telegram_id,)
    )
    res = cursor.fetchone()
    conn.close()
    if res:
        return {
            "anilist_username": res[0],
            "anilist_id": res[1],
            "last_activity_checked": res[2]
        }
    return None