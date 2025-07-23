from custom_logging import set_logger
from anilist_api_interactor import get_anilist_id_from_username, get_anime_data_from_id, get_new_updates, get_new_user_activity, get_watched_anime
from custom_dataclasses import AnimeData, AnimeRelation
from db_interactor import add_anime_bulk, add_relations_bulk, add_user_anime_bulk, check_anime_in_db, find_next_unrelated_anime, get_anime_data, get_anime_relations, get_last_updated_at, get_last_user_activity, get_user_id_list, get_users_with_missing_anilist_id, update_anime_related_to, update_last_user_activity, update_user_anilist_id
log = set_logger("DAEMON_CONNECTORS")


ANIME_TO_SEARCH:list[int] = []

def check_new_user_activity():
    log.info("[.] Checking new user activity")
    for user_id in get_user_id_list():
        log.info(f"\t[.] Starting check for user {user_id}")
        last_activity = get_last_user_activity(user_id)
        log.info(f"\t[o] Previous last activity found {last_activity}")
        activities, max_activity_date = get_new_user_activity(user_id, last_activity)
        log.info(f"\t[o] Found {len(activities)} new user activities")
        add_user_anime_bulk(activities, user_id)
        update_last_user_activity(user_id, max_activity_date)
        log.info(f"\t[.] Done new activity check for user {user_id}")
    log.info("[+] Done checking new user activity")

def get_anime(id:int, update_anime=True)->tuple[AnimeData, list[AnimeRelation]]|None:
    global ANIME_TO_SEARCH
    anime : AnimeData|None = get_anime_data(id)
    relations : list[AnimeRelation]|None = get_anime_relations(id)
    if anime is None or relations is None:
        if id not in ANIME_TO_SEARCH:
            ANIME_TO_SEARCH.append(id)
        if not update_anime:
            return None
        datas = get_anime_data_from_id([id])
        if datas is None or len(datas) != 1:
            log.error(f"[!] Unable to find anime data! {id}")
            return None
        if not add_anime_bulk([datas[0][0]]):
            log.error(f"[!] Error identifying anime {id}")
            return None
        if not add_relations_bulk(datas[0][1]):
            log.error(f"[!] Error identifying anime relations {id}")
        return datas[0]
    
    return (anime, relations)

def update_database_relations(anime_id:int)->bool:
    anime_to_check:list[int]= [anime_id]
    anime_checked :dict[int,bool]= {}
    main_story_anime:list[AnimeData] = []
    spinoff_anime:list[AnimeData] = []

    while len(anime_to_check) > 0:
        current_id = anime_to_check.pop()
        if current_id in anime_checked and anime_checked[current_id] == True:
            continue
        res = get_anime(current_id, False)
        if res is None:
            log.error("[!] Could not update anime database, can't find anime!")
            return False
        has_parents = False
        for rel in res[1]:
            if rel.relation_type == "CHARACTER":
                continue
            if rel.relation_type == "PARENT":
                has_parents = True
                break
        if not has_parents:
            for rel in res[1]:
                if rel.relation_type == "CHARACTER":
                    continue
                if rel.related_anilist_id in anime_checked and anime_checked[rel.related_anilist_id]:
                    continue
                anime_to_check.append(rel.related_anilist_id)

        if has_parents:
            if current_id not in spinoff_anime:
                spinoff_anime.append(res[0])
        else:
            if current_id not in main_story_anime:
                main_story_anime.append(res[0])
        anime_checked[res[0].id] = True
    anime_data_list = main_story_anime+spinoff_anime
    search_min_list = main_story_anime if len(main_story_anime) > 0 else spinoff_anime
    min_date= search_min_list[0].startDate
    min_id = search_min_list[0].id
    for d in search_min_list:
        if d.startDate < min_date:
            min_date = d.startDate
            min_id = d.id
    
    for a in anime_data_list:
        update_anime_related_to(a.id, min_id)
    return True

def update_anime_database():
    global ANIME_TO_SEARCH
    get_new_updates(get_last_updated_at(), True)
    offset = 0
    while True:
        related_id = find_next_unrelated_anime(offset)
        if related_id is None:
            if len(ANIME_TO_SEARCH) ==0:
                return
            datas = get_anime_data_from_id(ANIME_TO_SEARCH)
            if datas is None:
                log.error(f"[!] Unable to find anime data! {id}")
                return None
            anime_list :list[AnimeData]= []
            relations:list[AnimeRelation] = []
            for v in datas:
                anime_list.append(v[0])
                relations += v[1]
            if not add_anime_bulk(anime_list):
                log.error(f"[!] Error identifying anime {id}")
                return None
            if not add_relations_bulk(relations):
                log.error(f"[!] Error identifying anime relations {id}")
            ANIME_TO_SEARCH = []
            offset = 0
            continue
        success = update_database_relations(related_id)
        if not success:
            offset += 1

def process_users_with_missing_anilist_id():
    users = get_users_with_missing_anilist_id()
    for telegram_id, anilist_username in users:
        anilist_id = get_anilist_id_from_username(anilist_username)
        if not anilist_id:
            log.error(f"[!] Could not find anilist_id for username {anilist_username}")
            continue
        
        anime_ids = get_watched_anime(anilist_username)
        if not anime_ids:
            log.warning(f"[!] No watched anime found for user {anilist_username}")
            continue
        anime_to_get:list[int] = []
        for anime_id in anime_ids:
            if not check_anime_in_db(anime_id):
                anime_to_get.append(anime_id)
        if len(anime_to_get) > 0:
            anime_data = get_anime_data_from_id(anime_to_get)
            if anime_data and len(anime_data) > 0:
                anime_list:list[AnimeData] = []
                relations_list :list[AnimeRelation]= []
                for v in anime_data:
                    anime_list.append(v[0])
                    relations_list += v[1]
                add_anime_bulk(anime_list)
                add_relations_bulk(relations_list)
        update_user_anilist_id(telegram_id, anilist_id)
        add_user_anime_bulk(anime_ids, anilist_id)
        log.info(f"[+] Processed user {anilist_username} (anilist_id={anilist_id})")

def main_daemon_job():
    update_anime_database()
    #check_new_user_activity()
    process_users_with_missing_anilist_id()