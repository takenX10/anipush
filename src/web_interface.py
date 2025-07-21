from flask import Flask, render_template_string, request, url_for, redirect
from db_interactor import get_anime_data, get_anime_relations
import sqlite3
import custom_config
from custom_logging import set_logger
import datetime
log = set_logger("WEB_INTERFACE")

app = Flask(__name__)

HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Anipush - User Anime Overview</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f7f7f7; }
        .anime-card { min-width: 200px; max-width: 220px; margin: 10px; box-shadow: 0 2px 8px #0001; border-radius: 10px; overflow: hidden; background: #fff; }
        .anime-cover { width: 100%; height: 320px; object-fit: cover; }
        .anime-title { font-weight: bold; font-size: 1.1em; margin: 8px 0 4px 0; }
        .anime-meta { color: #666; font-size: 0.95em; }
        .not-watched { color: #c00; font-weight: bold; }
        .watched { color: #090; font-weight: bold; }
        .anime-list { display: flex; flex-wrap: wrap; gap: 10px; }
        .correlated-list { display: flex; flex-wrap: wrap; gap: 10px; }
        .correlated-card { min-width: 180px; max-width: 200px; background: #f8f9fa; border-radius: 8px; box-shadow: 0 1px 4px #0001; padding: 8px; }
        .correlated-card .anime-title { font-size: 1em; }
    </style>
</head>
<body>
<div class="container mt-4">
    <h1 class="mb-4">Anipush - User Anime Overview</h1>
    <form method="get" class="mb-4">
        <div class="input-group">
            <input type="text" class="form-control" name="user" placeholder="Insert Anilist ID or Username" value="{{ user }}">
            <button class="btn btn-primary" type="submit">Show</button>
        </div>
    </form>
    {% if anime_list is not none %}
        <h4>Anime watched by user: <b>{{ user }}</b></h4>
        <div class="anime-list">
        {% for anime, not_watched, total_correlated, percent_not_watched, start_date_fmt, updated_date_fmt in anime_list %}
            <div class="anime-card">
                <a href="{{ url_for('anime_detail', anime_id=anime.id, user=user) }}" style="text-decoration:none;color:inherit;">
                    <img src="{{ anime.cover }}" class="anime-cover" alt="cover">
                    <div class="p-2">
                        <div class="anime-title">{{ anime.title }}</div>
                        <div class="anime-meta">Status: {{ anime.status }}<br>Episodes: {{ anime.episodes }}</div>
                        <div class="anime-meta"> Correlated not watched: <span class="not-watched"> {{ not_watched }}</span></div>
                        <div class="anime-meta"> Total correlated: <span class="not-watched"> {{ total_correlated }}</span></div>
                        <div class="anime-meta"> Percent not watched: <span class="not-watched"> {{ percent_not_watched|round(2) }}%</span></div>
                    </div>
                </a>
            </div>
        {% endfor %}
        </div>
    {% endif %}
</div>
</body>
</html>
'''

DETAIL_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Anipush - Anime Details</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: #f7f7f7; }
        .anime-card { min-width: 200px; max-width: 220px; margin: 10px; box-shadow: 0 2px 8px #0001; border-radius: 10px; overflow: hidden; background: #fff; }
        .anime-cover { width: 100%; height: 320px; object-fit: cover; }
        .anime-title { font-weight: bold; font-size: 1.1em; margin: 8px 0 4px 0; }
        .anime-meta { color: #666; font-size: 0.95em; }
        .not-watched { color: #c00; font-weight: bold; }
        .watched { color: #090; font-weight: bold; }
        .correlated-list { display: flex; flex-wrap: wrap; gap: 10px; }
        .correlated-card { min-width: 180px; max-width: 200px; background: #f8f9fa; border-radius: 8px; box-shadow: 0 1px 4px #0001; padding: 8px; }
        .correlated-card .anime-title { font-size: 1em; }
    </style>
</head>
<body>
<div class="container mt-4">
    <a href="{{ url_for('index', user=user) }}" class="btn btn-secondary mb-3">&larr; Back to list</a>
    <div class="row">
        <div class="col-md-4">
            <img src="{{ anime.cover }}" class="img-fluid rounded" alt="cover">
        </div>
        <div class="col-md-8">
            <h2>{{ anime.title }}</h2>
            <div>Status: <b>{{ anime.status }}</b></div>
            <div>Episodes: <b>{{ anime.episodes }}</b></div>
            <div>Type: <b>{{ anime.type }}</b></div>
            <div>Latest aired episode: <b>{{ anime.latest_aired_episode }}</b></div>
            <div>Start date: <b>{{ start_date_fmt }}</b></div>
            <div>Updated at: <b>{{ updated_date_fmt }}</b></div>
        </div>
    </div>
    <hr>
    <h4>Correlated Anime</h4>
    <div class="mb-2"><b>Completion:</b> <span class="watched">{{ watched_count }}</span>/<span class="not-watched">{{ total_correlated }}</span></div>
    <div class="correlated-list">
    {% for related, watched, rel_start_date_fmt, rel_updated_date_fmt in correlated %}
        <div class="correlated-card">
            <img src="{{ related.cover }}" class="anime-cover mb-2" style="height:180px;object-fit:cover;">
            <div class="anime-title">{{ related.title }}</div>
            <div class="anime-meta">Status: {{ related.status }}<br>Episodes: {{ related.episodes }}</div>
            {% if watched %}
                <div class="watched">Watched</div>
            {% else %}
                <div class="not-watched">Not watched</div>
            {% endif %}
        </div>
    {% endfor %}
    </div>
</div>
</body>
</html>
'''

def get_user_anime_ids(anilist_id:int):
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT anime_id, (SELECT related_to FROM anime WHERE id=anime_id) FROM user_anime WHERE anilist_user_id=?", (anilist_id,))
    res = cursor.fetchall()
    conn.close()
    return res  # list of (anime_id, related_to)

def get_anilist_id_from_username(username:str)->int|None:
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT anilist_id FROM users WHERE anilist_username=?", (username,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return res[0]
    return None

def format_date(ts):
    try:
        ts = int(ts)
        if ts > 0:
            return datetime.datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
    except Exception:
        pass
    return "-"

def get_related_anime(anime_id):
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT related_to FROM anime WHERE id=?", (anime_id,))
    res = cursor.fetchone()
    if not res or res[0] is None:
        conn.close()
        return [anime_id]  # solo se stesso se non ha related_to
    related_to = res[0]
    search_string = ''
    if related_to == '':
        search_string = f'id = {anime_id}'
    else:
        for v in related_to.split('|'):
            search_string += f"or '|'||related_to||'|' LIKE '%|{v}|%'"
        search_string = search_string[3:]
    cursor.execute(f"SELECT id FROM anime WHERE {search_string}")
    related = [r[0] for r in cursor.fetchall()]
    conn.close()
    return related

# Rimuovo la funzione get_main_anime_ids

@app.route('/', methods=['GET'])
def index():
    user = request.args.get('user', '').strip()
    log.debug(f"User: {user}")
    anime_list = None
    if user:
        anilist_id:str|int|None= None
        try:
            anilist_id = int(user)
        except ValueError:
            anilist_id = get_anilist_id_from_username(user)
        log.debug(f"Anilist id: {anilist_id}")
        if anilist_id:
            watched = get_user_anime_ids(anilist_id)  # list of (anime_id, related_to)
            watched_ids = set(aid for aid, _ in watched)
            # Filtra solo anime principali
            main_ids = set()
            for aid, related_to in watched:
                if related_to is None or len(related_to) == 0 or aid in related_to.split('|'):
                    main_ids.add(aid)
            anime_list = []
            for anime_id in main_ids:
                anime = get_anime_data(anime_id)
                if not anime:
                    continue
                start_date_fmt = format_date(anime.startDate)
                updated_date_fmt = format_date(anime.updatedDate)
                related_ids = set(get_related_anime(anime_id))
                related_ids.add(anime_id)  # include itself
                total_correlated = len(related_ids)
                not_watched = len([rid for rid in related_ids if rid not in watched_ids])
                percent_not_watched = (not_watched / total_correlated * 100) if total_correlated > 0 else 0
                anime_list.append((anime, not_watched, total_correlated, percent_not_watched, start_date_fmt, updated_date_fmt))
            anime_list.sort(key=lambda x: (-x[3], -x[1], x[0].title.lower()))
    return render_template_string(HTML, user=user, anime_list=anime_list)

@app.route('/anime/<int:anime_id>')
def anime_detail(anime_id):
    user = request.args.get('user', '').strip()
    anilist_id = None
    if user:
        try:
            anilist_id = int(user)
        except ValueError:
            anilist_id = get_anilist_id_from_username(user)
    anime = get_anime_data(anime_id)
    start_date_fmt = format_date(anime.startDate) if anime else "-"
    updated_date_fmt = format_date(anime.updatedDate) if anime else "-"
    related_ids = set(get_related_anime(anime_id))
    related_ids.add(anime_id)  # include itself
    # Qui prendo solo gli id degli anime visti
    watched_ids = set(aid for aid, _ in get_user_anime_ids(anilist_id)) if anilist_id else set()
    correlated = []
    watched_count = 0
    for rid in related_ids:
        related = get_anime_data(rid)
        if related:
            rel_start_date_fmt = format_date(related.startDate)
            rel_updated_date_fmt = format_date(related.updatedDate)
            is_watched = related.id in watched_ids
            if is_watched:
                watched_count += 1
            correlated.append((related, is_watched, rel_start_date_fmt, rel_updated_date_fmt))
    total_correlated = len(related_ids)
    return render_template_string(DETAIL_HTML, anime=anime, correlated=correlated, user=user, start_date_fmt=start_date_fmt, updated_date_fmt=updated_date_fmt, watched_count=watched_count, total_correlated=total_correlated)

if __name__ == '__main__':
    app.run(debug=True) 