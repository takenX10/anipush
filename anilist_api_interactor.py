import json
import time
import requests
from custom_logging import set_logger

log = set_logger("API_INTERACTOR")

API_URL = "https://graphql.anilist.co"

def send_request_to_anilist(query:str, variables:dict, title:str)-> dict|None:
    data = None
    log.info(f"[.] Sending request to anilist: {title}")
    for i in range(3):
        try:
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


