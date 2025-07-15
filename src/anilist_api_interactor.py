import json, time, datetime, logging
import requests
from custom_dataclasses import AnimeData
from custom_logging import set_logger

log = set_logger("API_INTERACTOR", logging.INFO)

WRITTEN_DATA_FORMAT = ["MANGA", "NOVEL", "ONE_SHOT"]
MAX_ANIME_PER_QUERY = 25

API_URL = "https://graphql.anilist.co"

def send_request_to_anilist(query:str, variables:dict, title:str)-> dict|None:
    data = None
    log.info(f"[.] Sending request to anilist: {title}")
    for i in range(3):
        try:
            time.sleep(2.2)
            response = requests.post(API_URL, json={"query": query, "variables": variables})
            if response.status_code == 403:
                log.warning("\t[!] The anilist api seems unavailiable, returned status code 403.")
                if i<2:
                    log.info("\t[i] Retrying in 15 seconds")
                    time.sleep(15)
                continue
            if response.status_code == 429:
                log.warning("\t[!] Rate limit has been exceeded, waiting")
                retry_after = response.headers.get("Retry-After")
                if retry_after and isinstance(retry_after, int):
                    time_after_retry = int(retry_after)+1
                    log.info(f"\t[i] Retrying in {time_after_retry} seconds (retry-after time)")
                    time.sleep(time_after_retry)
                else:
                    log.info("\t[i] Retrying in 31 seconds")
                    time.sleep(31)
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

def get_watched_anime(username:str)->list[int]|None:
    query = '''
query ($userName: String) {
  MediaListCollection(userName: $userName, type: ANIME) {
    lists {
      entries {
        media {
          id
        }
      }
    }
  }
}
    '''
    variables = {
        "userName": username
    }
    data = send_request_to_anilist(query, variables, "get_watched_anime")
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
            if 'media' not in entry or 'id' not in entry['media']:
                continue
            anime_list.append(entry['media']['id'])
    return anime_list

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
    
def get_anime_data_from_id(anime_id_list:list[int])->list[AnimeData]|None:
    log.info("\t\t[+] Getting anime data from id list")
    query = '''
query AnimeData($mediaId: [Int], $page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    media(id_in: $mediaId) {
        id
        type
        status
        episodes
        updatedAt
        title {
            romaji
            english
        }
        nextAiringEpisode {
            episode
        }
        coverImage {
            extraLarge
        }
        startDate {
            year
            month
            day
        }
        nextAiringEpisode {
            episode
            airingAt
        }
    }
  }
}   '''
    anime_data_list : list[AnimeData] = []
    print("ANIME ID LIST")
    print(anime_id_list)
    for i in range((len(anime_id_list)//MAX_ANIME_PER_QUERY)+1):
        anime_portion = anime_id_list[
            i*MAX_ANIME_PER_QUERY: min((i+1)*MAX_ANIME_PER_QUERY, len(anime_id_list))
        ]
        print("ANIME PORTION")
        print("IDS: ", i*MAX_ANIME_PER_QUERY, min((i+1)*MAX_ANIME_PER_QUERY, len(anime_id_list), len(anime_portion)))
        print(anime_portion)
        variables = {
            "page":1,
            "perPage":MAX_ANIME_PER_QUERY,
            "mediaId":anime_portion
        }
        data = send_request_to_anilist(query, variables, "get_anime_data")
        if data is None or 'data' not in data or \
            'Page' not in data['data'] or \
            'media' not in data['data']['Page']:
                log.error("\t\t[!] The json structure returned by anilist is wrong!")
                return None
        print("DATA DUMP")
        print(json.dumps(data))
        media_list = data['data']['Page']['media']
        print("LENGTHS")
        print(not media_list, len(media_list), len(anime_portion))
        if not media_list or len(media_list) != len(anime_portion):
            log.error("\t\t[!] The returned anilist data is wrong, length does not match!")
            return None

        for m in media_list:
            if ("romaji" not in m["title"] and "english" not in m["title"]) or \
                 ("nextAiringEpisode" in m and m["nextAiringEpisode"] is not None and "episode" not in m["nextAiringEpisode"]) or \
                 "startDate" not in m or \
                 "day" not in m["startDate"] or \
                 "month" not in m["startDate"] or \
                 "year" not in m["startDate"] or \
                 "coverImage" not in m or \
                 "extraLarge" not in m["coverImage"] or \
                 "id" not in m or \
                 "title" not in m or \
                 "episodes" not in m or \
                 "type" not in m or \
                 "status" not in m:
                log.error("\t\t[!] The anime data returned by anilist is broken, returning empty response")
                return None

            title = m["title"]["romaji"]
            if "english" in m["title"] and m["title"]["english"] and len(m["title"]["english"]) > 0:
                title = m["title"]["english"]
            next :int= 0
            if "nextAiringEpisode" in m and m["nextAiringEpisode"] is not None and "episode" in m["nextAiringEpisode"]:
                next = m["nextAiringEpisode"]["episode"]
            elif "episodes" in m and m["episodes"] is not None:
                next = m["episodes"]
            date = datetime.datetime(year=3099, month=1, day=1)
            if m["status"] != "NOT_YET_RELEASED" and \
                m["startDate"]["year"] is not None and \
                m["startDate"]["month"] is not None and \
                m["startDate"]["day"] is not None:
                date = datetime.datetime(year=m["startDate"]["year"], month=m["startDate"]["month"], day=m["startDate"]["day"])
            date = time.mktime(date.timetuple())
            anime_data_list.append(
                AnimeData(
                    id=m["id"],
                    type=m["type"],
                    status=m["status"],
                    cover=m["coverImage"]["extraLarge"],
                    episodes=m["episodes"],
                    latest_aired_episode=next,
                    title=title,
                    date=date
                )
            )

    return anime_data_list

    
def get_new_user_activity(user_id:int, last_activity:int)->tuple[list[int], int]:
    log.info(f"\t[.] Getting new user activities user_id:{user_id}, last_activity:{last_activity}")
    query = '''
query ($id: Int, $page: Int, $createdAtGreater: Int) {
  Page(page: $page, perPage: 25) {
    pageInfo {
      hasNextPage
    }
    activities(userId: $id, type: ANIME_LIST, sort: [ID_DESC], createdAt_greater: $createdAtGreater) {
      ... on ListActivity {
        status
        createdAt
        media {
          id
        }
      }
    }
  }
}

    '''
    current_page = 1
    max_date = last_activity
    new_anime :list[int] = []
    while True:
        variables = {
            "id": user_id,
            "createdAtGreater": last_activity,
            "page":current_page
        }
        data = send_request_to_anilist(query, variables, "get_new_user_activity")
        if data is None or 'data' not in data or \
            'Page' not in data['data'] or \
            'pageInfo' not in data['data']['Page'] or \
            'hasNextPage' not in data['data']['Page']['pageInfo'] or \
            'activities' not in data['data']['Page']:
                log.error("The json structure returned by anilist is wrong!")
                return None, last_activity
        
        activities = data['data']['Page']['activities']
        for a in activities:
            if 'status' not in a or \
                a['status'] != 'completed' or \
                'createdAt' not in a or \
                'media' not in a or \
                'id' not in a['media']:
                log.debug(f"The json structure of activity {a} returned by anilist is wrong!")
                continue
            if a["createdAt"] > max_date:
                max_date = a["createdAt"]
            new_anime.append(a['media']['id'])
        if not data['data']['Page']['pageInfo']['hasNextPage']:
            break
        current_page += 1
    return new_anime, max_date