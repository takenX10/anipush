import sqlite3
import json, time, datetime, logging
import requests
import custom_config
from custom_dataclasses import AnimeData, AnimeRelation
from custom_logging import set_logger
from db_interactor import add_anime_bulk, add_relations_bulk
from queries import GET_ANIME_DATA_FROM_ID, GET_NEW_UPDATES, GET_NEW_USER_ACTIVITIES, GET_WATCHED_ANIME

log = set_logger("API_INTERACTOR", logging.INFO)

WRITTEN_DATA_FORMAT = ["MANGA", "NOVEL", "ONE_SHOT"]
MAX_ANIME_PER_QUERY = 25
MAX_TRIES = 4
MAX_DATE=int(datetime.datetime(year=3099, month=1, day=1).timestamp())

API_URL = "https://graphql.anilist.co"

def send_request_to_anilist(query:str, variables:dict, title:str)-> dict|None:
    data = None
    log.info(f"[.] Sending request to anilist: {title}")
    for i in range(3):
        try:
            time.sleep(4)
            response = requests.post(API_URL, json={"query": query, "variables": variables})
            if response.status_code == 403:
                log.warning("\t[!] The anilist api seems unavailiable, returned status code 403.")
                if i<2:
                    log.info("\t[i] Retrying in 1 hour")
                    time.sleep(3600)
                continue
            if response.status_code == 429:
                log.warning("\t[!] Rate limit has been exceeded, waiting")
                retry_after = response.headers.get("Retry-After")
                if retry_after and isinstance(retry_after, int):
                    time_after_retry = int(retry_after)+1
                    log.info(f"\t[i] Retrying in {time_after_retry} seconds (retry-after time)")
                    time.sleep(time_after_retry)
                else:
                    log.info("\t[i] Retrying in 61 seconds")
                    time.sleep(61)
                continue
            if response.status_code != 200:
                response.raise_for_status()
            j = response.json()
            if "errors" in j:
                log.error(f"\t[!] The anilist api returned error(s) in the response")
                for e in j['errors']:
                    log.error("\t[!] "+json.dumps(e))
                log.info("\t[i] Retrying in 15 seconds")
                time.sleep(15)
                continue
            data = j
            break
        except Exception as e:
            log.error(f"\t[!] Something went wrong when fetching anime list: {e}")
            if i<2:
                log.info("\t[i] Retrying in 15 seconds")
                time.sleep(15)
    if data is None:
        log.info(f"[!] Could not get the correct data for request {title}")
    else:
        log.info(f"[+] Done sending request: {title}")
    return data

def parse_media(m:dict)->tuple[AnimeData, list[AnimeRelation]] | None:
    relations : list[AnimeRelation] = []
    if 'id' not in m or \
        m['id'] is None or \
        'type' not in m or \
        'format' not in m or \
        'status' not in m or \
        'episodes' not in m or \
        'relations' not in m or \
        'edges' not in m['relations'] or \
        'title' not in m or \
        ("romaji" not in m["title"] and "english" not in m["title"]) or \
        'coverImage' not in m or m['coverImage'] is None or \
        'extraLarge' not in m['coverImage'] or \
        'nextAiringEpisode' not in m or \
        (m['nextAiringEpisode'] is not None and 'episode' not in m['nextAiringEpisode']) or \
        'startDate' not in m or \
        (m['startDate'] is not None and ('year' not in m['startDate'] or 'month' not in m['startDate'] or 'day' not in m['startDate'])):
        log.debug(f"The json structure of media \n{json.dumps(m)}\n returned by anilist is broken!")
        return None

    title = m['title']['romaji']
    if m['title']['english'] is not None and len(m['title']['english']) > 0:
        title = m['title']['english']
    latest_episode = m['episodes']
    if m['nextAiringEpisode'] is not None:
        latest_episode = m['nextAiringEpisode']['episode'] or m['episodes']
    start_date = MAX_DATE
    if m['startDate']['year'] is not None and m['startDate']['month'] is not None and m['startDate']['day'] is not None:
        start_date = int(datetime.datetime(year=m['startDate']['year'], month=m['startDate']['month'], day=m['startDate']['day']).timestamp())
    anime = AnimeData(
        id = m['id'],
        title=title,
        type=m['format'],
        status=m['status'],
        cover=m['coverImage']['extraLarge'] or "",
        episodes=m['episodes'],
        latest_aired_episode=latest_episode,
        startDate=start_date,
        updatedDate=m['updatedAt']
    )
    log.debug(f"\t\t[+] Added anime {m['id']} to list")
    if m['relations']['edges'] is None:
        return (anime, [])
    log.debug(f"\t\t[+] Found {len(m['relations']['edges'])} relations to add for anime {m['id']}")
    for r in m['relations']['edges']:
        if r['node']['format'] in WRITTEN_DATA_FORMAT or r["relationType"] == "CHARACTER":
            continue
        relations.append(AnimeRelation(
            primary_anilist_id=m['id'],
            related_anilist_id=r['node']['id'],
            relation_type=r['relationType'],
            date_update_found=m['updatedAt']
        ))
    return (anime, relations)

def get_watched_anime(username:str)->list[int]|None:
    variables = {
        "userName": username
    }
    data = send_request_to_anilist(GET_WATCHED_ANIME, variables, "get_watched_anime")
    if data is None or 'data' not in data or \
        'MediaListCollection' not in data['data'] or \
        'lists' not in data['data']['MediaListCollection']:
            log.error("The json structure returned by anilist is wrong!")
            return None
    
    lists = data['data']['MediaListCollection']['lists']
    
    anime_list = []

    for l in lists:
        if 'entries' not in l:
            continue
        for entry in l['entries']:
            if 'media' not in entry or 'id' not in entry['media'] or 'status' not in entry:
                continue
            if entry['status'] == "DROPPED":
                continue
            anime_list.append(entry['media']['id'])
    return anime_list

def get_anime_data_from_id(anime_id_list:list[int])->list[tuple[AnimeData, list[AnimeRelation]]]|None:
    log.info("\t\t[+] Getting anime data from id")
    anime_data_list : list[tuple[AnimeData, list[AnimeRelation]]] = []
    for i in range((len(anime_id_list)//MAX_ANIME_PER_QUERY)+1):
        anime_portion = anime_id_list[
            i*MAX_ANIME_PER_QUERY: min((i+1)*MAX_ANIME_PER_QUERY, len(anime_id_list))
        ]
        variables = {
            "page":1,
            "perPage":MAX_ANIME_PER_QUERY,
            "mediaId":anime_portion
        }
        data = send_request_to_anilist(GET_ANIME_DATA_FROM_ID, variables, "get_anime_data_from_id")
        if data is None or 'data' not in data or \
            'Page' not in data['data'] or \
            'media' not in data['data']['Page']:
                log.error("\t\t[!] The json structure returned by anilist is wrong!")
                return None
        media_list = data['data']['Page']['media']
        if not media_list or len(media_list) != len(anime_portion):
            log.error("\t\t[!] The returned anilist data is wrong, length does not match!")
            return None

        for m in media_list:
            res = parse_media(m)
            if res is None:
                if "id" in m:
                    log.error(f"[!] Something went wrong while getting anime data {m['id']}!")
                else:
                    log.error(f"[!] Something went wrong while getting anime data (Unkwnown id)!")
                continue
            anime_data_list.append(res)

    return anime_data_list
    
def get_new_user_activity(user_id:int, last_activity:int)->tuple[list[int], int]:
    log.info(f"\t[.] Getting new user activities user_id:{user_id}, last_activity:{last_activity}")
    current_page = 1
    max_date = last_activity
    new_anime :list[int] = []
    while True:
        variables = {
            "id": user_id,
            "createdAtGreater": last_activity,
            "page":current_page
        }
        data = send_request_to_anilist(GET_NEW_USER_ACTIVITIES, variables, "get_new_user_activity")
        if data is None or 'data' not in data or \
            'Page' not in data['data'] or \
            'pageInfo' not in data['data']['Page'] or \
            'hasNextPage' not in data['data']['Page']['pageInfo'] or \
            'activities' not in data['data']['Page']:
                log.error("The json structure returned by anilist is wrong!")
                return [], last_activity
        
        activities = data['data']['Page']['activities']
        for a in activities:
            if 'status' not in a or \
                'createdAt' not in a or \
                'media' not in a or \
                'id' not in a['media']:
                log.debug(f"The json structure of activity {a} returned by anilist is wrong!")
                continue
            if a['status'] != 'completed':
                continue
            if a["createdAt"] > max_date:
                max_date = a["createdAt"]
            new_anime.append(a['media']['id'])
        if not data['data']['Page']['pageInfo']['hasNextPage']:
            break
        current_page += 1
    return new_anime, max_date

def get_new_updates(last_update_time:int, add_each_page:bool)->tuple[list[AnimeData], list[AnimeRelation]]:
    anime_updates_list : dict[int, AnimeData] = {}
    relations_list :list[AnimeRelation]= []
    current_page = 1
    current_tries = 1
    while True:
        if add_each_page:
            anime_updates_list : dict[int, AnimeData] = {}
            relations_list :list[AnimeRelation]= []
        variables = {
            "perPage": 50,
            "page":current_page
        }
        log.debug(f"\t\t[.] Fetching updates for page {current_page}")
        data = send_request_to_anilist(GET_NEW_UPDATES, variables, "get_new_anime_updates")
        if data is None or 'data' not in data or \
            'Page' not in data['data'] or \
            'pageInfo' not in data['data']['Page'] or \
            'hasNextPage' not in data['data']['Page']['pageInfo'] or \
            'media' not in data['data']['Page']:
                log.error("\t\t[!] The json structure returned by anilist is wrong!")
                return [], []
        
        media_list = data['data']['Page']['media']
        log.debug(f"\t\t[+] Found {len(media_list)} updates to add on page {current_page}")
        if (len(media_list) == 0 or (len(media_list) != 50 and data['data']['Page']['pageInfo']['hasNextPage']))and current_tries <= MAX_TRIES:
                log.info(f"\t\t[i] Trying to fetch updates for this page a couple more times just to be sure! try {current_tries}/{MAX_TRIES}")
                current_tries += 1
                continue
        else:
            current_tries = 1

        for m in media_list:
            if 'updatedAt' not in m:
                log.debug(f"The json structure of media {json.dumps(m)} returned by anilist is wrong!")
                continue
            if m['updatedAt'] < last_update_time:
                log.debug(f"\t\t[!] The time {m['updatedAt']} is less than the last updated time {last_update_time}!")
                data['data']['Page']['pageInfo']['hasNextPage'] = False
                break
            res = parse_media(m)
            if res is None:
                continue
            anime_updates_list[res[0].id] = res[0]
            relations_list += res[1]
        if add_each_page:
            add_relations_bulk(relations_list)
            add_anime_bulk(list(anime_updates_list.values()))
            

        if not data['data']['Page']['pageInfo']['hasNextPage']:
            break
        current_page += 1
    return list(anime_updates_list.values()), relations_list


"""
def get_anime_relations_from_anime_id(anime_id:int)->tuple[list[int],list[int]]:
    query = '''
query Media($mediaId: Int) {
  Media(id: $mediaId) {
    format
    relations {
      edges {
        relationType
        node {
          format
          id
          relations {
            edges {
              relationType
              node {
                format
                id
              }
            }
          }
        }
      }
    }
  }
}
    '''
    anime_to_check:list[int]= [anime_id]
    anime_checked :dict[int,bool]= {}
    main_story_anime:list[int] = []
    spinoff_anime:list[int] = []

    while len(anime_to_check) > 0:
        current_id = anime_to_check.pop()
        if current_id in anime_checked and anime_checked[current_id] == True:
            continue
        variables = {
            "mediaId": current_id
        }
        data = send_request_to_anilist(query, variables, f"get_anime_struct - {current_id}")
        anime_checked[current_id] = True
        if data is None or 'data' not in data or \
            'Media' not in data['data'] or \
            'relations' not in data['data']['Media']:
                log.error("The json structure returned by anilist is wrong!")
                continue
        
        if data["data"]["Media"]["format"] in WRITTEN_DATA_FORMAT:
            continue

        relations = data["data"]["Media"]["relations"]["edges"]

        has_parents = False
        for rel in relations:
            if rel["node"]["format"] in WRITTEN_DATA_FORMAT or rel["relationType"] == "CHARACTER":
                continue
            if rel["relationType"] == "PARENT":
                has_parents = True
            if rel["node"]["id"] in anime_checked:
                continue
            anime_checked[rel["node"]["id"]] = True

            has_parents2 = False
            for rel2 in rel["node"]["relations"]["edges"]:
                if rel2["node"]["format"] in WRITTEN_DATA_FORMAT or rel2["relationType"] == "CHARACTER":
                    continue
                if rel2["relationType"] == "PARENT":
                    has_parents2 = True
                if rel2["node"]["id"] in anime_checked or rel2["node"]["id"] in anime_to_check:
                    continue
                anime_to_check.append(rel2["node"]["id"])
            if has_parents2:
                if rel["node"]["id"] not in spinoff_anime:
                    spinoff_anime.append(rel["node"]["id"])
            else:
                if rel["node"]["id"] not in main_story_anime:
                    main_story_anime.append(rel["node"]["id"])    

        if has_parents:
            if current_id not in spinoff_anime:
                spinoff_anime.append(current_id)
        else:
            if current_id not in main_story_anime:
                main_story_anime.append(current_id)
    return main_story_anime, spinoff_anime

"""


def get_anilist_id_from_username(username: str) -> int | None:
    query = '''
    query ($name: String) {
      User(name: $name) {
        id
      }
    }
    '''
    variables = {"name": username}
    data = send_request_to_anilist(query, variables, f"get_anilist_id_from_username {username}")
    if data and 'data' in data and 'User' in data['data'] and data['data']['User'] and 'id' in data['data']['User']:
        return data['data']['User']['id']
    return None