import logging
from custom_logging import set_logger
log = set_logger("ANIPUSH", logging.INFO)

from anilist_api_interactor import get_anime_data_from_id, get_anime_relations_from_anime_id, get_new_user_activity
from db_interactor import add_anime_bulk, add_user_anime_bulk, check_anime_in_db, get_last_user_activity, get_user_id_list, init_db, update_last_user_activity


def add_new_user():
    pass

def check_new_user_activity():
    log.info("[.] Checking new user activity")
    for user_id in get_user_id_list():
        log.info(f"\t[.] Starting check for user {user_id}")
        last_activity = get_last_user_activity(user_id)
        log.info(f"\t[o] Previous last activity found {last_activity}")
        activities, max_activity_date = get_new_user_activity(user_id, last_activity)
        log.info(f"\t[o] Found {len(activities)} new user activities")
        for a in activities:
            if check_anime_in_db(a):
                continue
            log.info(f"\t\t[.] Anime {a} is new, adding it to the db...")
            official, spinoffs = get_anime_relations_from_anime_id(a)
            anime_data_list = get_anime_data_from_id(official+spinoffs)
            if anime_data_list is None:
                log.error(f"[!] Something went wrong while getting anime data for activity {a}")
                continue
            min_date= anime_data_list[0].date
            min_id = anime_data_list[0].id
            for d in anime_data_list:
                if d.date < min_date:
                    min_date = d.date
                    min_id = d.id
            add_anime_bulk(anime_data_list, min_id)
            log.info(f"\t\t[+] Done adding anime {a} and all his parents to the db")
        add_user_anime_bulk(activities, user_id)
        update_last_user_activity(user_id, max_activity_date)
        log.info(f"\t[.] Done new activity check for user {user_id}")
    log.info("[+] Done checking new user activity")
        

def check_new_episodes():
    pass

def check_new_anime():
    pass


def main():
    init_db()
    print(check_new_user_activity())
if __name__ == "__main__":
    main()