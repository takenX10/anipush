
import datetime
import time
import requests

import custom_config
from custom_dataclasses import AnimeData
from custom_logging import set_logger

log = set_logger("UTILS")


def format_date(ts):
    try:
        ts = int(ts)
        if ts > 0:
            return datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
    except Exception as e:
        log.error(e)
    return "-"


def format_status_plain(status: str):
    status = (status or '').upper()
    if status == 'FINISHED':
        return 'Finished'
    elif status == 'RELEASING':
        return 'Releasing'
    elif status == 'NOT_YET_RELEASED':
        return 'Not yet released'
    elif status == 'CANCELLED':
        return 'Cancelled'
    elif status == 'HIATUS':
        return 'Hiatus (on hold)'
    return status.title()


def format_type(type_str: str):
    if type_str is None:
        return ''
    t = (type_str or '').upper()
    if t == 'TV':
        return 'TV Series'
    elif t == 'TV_SHORT':
        return 'TV Short'
    elif t == 'MOVIE':
        return 'Movie'
    elif t == 'SPECIAL':
        return 'Special Episode'
    elif t == 'OVA':
        return 'OVA - Original Video Animation'
    elif t == 'ONA':
        return 'ONA - Original Net Animation'
    elif t == 'MUSIC':
        return 'Music Video'
    elif t == 'MANGA':
        return 'Manga'
    elif t == 'NOVEL':
        return 'Novel'
    elif t == 'ONE_SHOT':
        return 'One-shot'
    return t.replace('_', ' ').title()


def send_telegram_notification(telegram_id: int, anime: AnimeData, notification_type: str):
    try:
        url = f"https://api.telegram.org/bot{custom_config.BOT_TOKEN}/sendPhoto"
        custom_text = ""
        sub_text = ""
        if notification_type == "new":
            custom_text = "New anime found!"
            sub_text = f"Found anime <b>{anime.title}</b> ({format_type(anime.type)})"
        elif notification_type == "status_change":
            custom_text = "Anime status changed!"
            sub_text = f"The anime {anime.title} ({format_type(anime.type)}) has changed status to <b>{format_status_plain(anime.status)}</b>"
        elif notification_type == "episode_update":
            custom_text = "New episode out!"
            sub_text = f"The <b>episode {anime.latest_aired_episode or anime.episodes}</b> of {anime.title} is out!"
        caption = (
            f"<b>🔔 {custom_text}!</b>\n"
            f"\n{sub_text}\n\n"
            f"<b>Title:</b> {anime.title}\n"
            f"<b>Type:</b> {format_type(anime.type)}\n"
            f"<b>Status:</b> {format_status_plain(anime.status)}\n"
            f"<b>Episodes:</b> {anime.episodes}\n"
            f"<b>Latest aired episode:</b> {anime.latest_aired_episode}\n" if anime.latest_aired_episode else ""
            f"<b>Start date:</b> {format_date(anime.start_date)}\n" if anime.start_date else ""
            f"<b>Updated at:</b> {format_date(anime.updated_date)}" if anime.updated_date else ""
        )
        data = {
            'chat_id': str(telegram_id),
            'caption': caption,
            'photo': anime.cover,
            'parse_mode': 'HTML'
        }
        requests.post(url, data=data, timeout=10)
        time.sleep(5)
    except Exception as e:
        log.error(
            f"[!] Failed to send Telegram notification to {telegram_id}: {e}")
