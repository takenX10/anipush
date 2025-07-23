import datetime


def format_date(ts):
    try:
        ts = int(ts)
        if ts > 0:
            return datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
    except Exception:
        pass
    return "-"