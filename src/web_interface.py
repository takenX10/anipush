import time, sqlite3
from flask import Flask, render_template_string, request
import custom_config
from utils import format_date
from custom_logging import set_logger
from db_interactor import get_anime_data


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
        .anime-list {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }
        @media (max-width: 1200px) {
            .anime-list { grid-template-columns: repeat(3, 1fr); }
        }
        @media (max-width: 900px) {
            .anime-list { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 600px) {
            .anime-list { grid-template-columns: 1fr; }
        }
        .anime-card {
            min-width: 0;
            max-width: 100%;
            margin: 0;
            box-shadow: 0 2px 8px #0001;
            border-radius: 10px;
            overflow: hidden;
            background: #fff;
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        .anime-cover { width: 100%; height: 340px; object-fit: cover; }
        .anime-title {
            font-weight: bold;
            font-size: 1.1em;
            margin: 8px 0 4px 0;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: normal;
            cursor: pointer;
        }
        .anime-meta { color: #666; font-size: 0.95em; }
        .not-watched { color: #c00; font-weight: bold; }
        .watched { color: #090; font-weight: bold; }
    </style>
    <script>
    function updateVisibleCount() {
        var cards = document.querySelectorAll('.anime-card');
        var visibleCount = 0;
        for (var i = 0; i < cards.length; i++) {
            if (cards[i].style.display !== 'none') visibleCount++;
        }
        var countElement = document.getElementById('results-count');
        if (countElement) {
            countElement.textContent = visibleCount;
        }
    }

    function toggleCompleted() {
        var show = document.getElementById('show_completed').checked;
        var cards = document.querySelectorAll('.anime-card[data-completed="1"]');
        for (var i = 0; i < cards.length; i++) {
            cards[i].style.display = show ? '' : 'none';
        }
        filterByTitle();
    }

    function filterByTitle() {
        var input = document.getElementById('search_title');
        var filter = input ? input.value.toLowerCase() : '';
        var cards = document.querySelectorAll('.anime-card');
        for (var i = 0; i < cards.length; i++) {
            var titleElem = cards[i].querySelector('.anime-title');
            var matches = true;
            if (titleElem && filter.length > 0) {
                matches = titleElem.textContent.toLowerCase().indexOf(filter) !== -1;
            }
            var showCompleted = document.getElementById('show_completed').checked;
            var isCompleted = cards[i].getAttribute('data-completed') === '1';
            var show = (!isCompleted || showCompleted) && matches;
            cards[i].style.display = show ? '' : 'none';
        }
        updateVisibleCount();
    }

    window.addEventListener('DOMContentLoaded', function() {
        var showCompletedToggle = document.getElementById('show_completed');
        var searchInput = document.getElementById('search_title');
        if (showCompletedToggle) {
            showCompletedToggle.addEventListener('change', toggleCompleted);
        }
        if (searchInput) {
            searchInput.addEventListener('input', filterByTitle);
        }
        toggleCompleted();
    });
    </script>
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
    <div class="form-check form-switch mb-3">
        <input class="form-check-input" type="checkbox" id="show_completed" checked>
        <label class="form-check-label" for="show_completed">Show completed anime (100%)</label>
    </div>
    <div class="mb-3">
        <input type="text" class="form-control" id="search_title" placeholder="Search by title...">
    </div>
    {% if anime_list is not none %}
        <h4>Anime watched by user: <b>{{ user }}</b></h4>
        <div class="mb-2"><b>Results found:</b> <span id="results-count"></span></div>
        <div class="anime-list">
        {% for anime, not_watched, total_correlated, percent_not_watched, start_date_fmt, updated_date_fmt in anime_list %}
            <div class="anime-card flex-fill" data-completed="{{ 1 if percent_not_watched == 0 else 0 }}">
                <a href="{{ url_for('anime_detail', anime_id=anime.id, user=user) }}" style="text-decoration:none;color:inherit;">
                    <img src="{{ anime.cover }}" class="anime-cover" alt="cover">
                    <div class="p-3 pb-4">
                        <div class="anime-title" title="{{ anime.title }}">{{ anime.title }}</div>
                        <div class="anime-meta">Completion: {{ total_correlated - not_watched }}/{{ total_correlated }} ({{ (100 - percent_not_watched)|int }}%)</div>
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
        .anime-card { min-width: 200px; max-width: 320px; margin: 10px auto; box-shadow: 0 2px 8px #0001; border-radius: 10px; overflow: hidden; background: #fff; }
        .anime-cover { width: 100%; height: 340px; object-fit: cover; }
        .anime-title {
            font-weight: bold;
            font-size: 1.1em;
            margin: 8px 0 4px 0;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: normal;
            cursor: pointer;
        }
        .anime-meta { color: #666; font-size: 0.95em; }
        .not-watched { color: #c00; font-weight: bold; }
        .watched { color: #090; font-weight: bold; }
        .correlated-list { display: flex; flex-wrap: wrap; gap: 10px; }
        .correlated-card {
            min-width: 180px;
            max-width: 200px;
            width: 200px;
            height: 340px;
            background: #f8f9fa;
            border-radius: 8px;
            box-shadow: 0 1px 4px #0001;
            padding: 8px;
            transition: box-shadow 0.2s;
            cursor: pointer;
            display: flex;
            flex-direction: column;
            align-items: stretch;
        }
        .correlated-card:hover { box-shadow: 0 4px 16px #0002; background: #e9ecef; }
        .correlated-card .anime-title { font-size: 1em; }
        a.correlated-link { text-decoration: none; color: inherit; }
        .correlated-card .anime-cover {
            height: 180px;
            width: 100%;
            object-fit: cover;
            border-radius: 6px;
        }
        .correlated-card .correlated-content {
            flex: 1 1 auto;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
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
            <div>Status: <b>{{ format_status(anime.status)|safe }}</b></div>
            <div>Type: <b>{{ anime.type }}</b></div>
            <div>Episodes: <b>{{ anime.episodes if anime.episodes else '?' }}</b></div>
            <div>Latest aired episode: <b>{{ anime.latest_aired_episode if anime.latest_aired_episode else '?' }}</b></div>
            <div>Start date: <b>{{ start_date_fmt if start_date_fmt[:4] != '3098' else '?' }}</b></div>
            <div>Updated at: <b>{{ updated_date_fmt }}</b></div>
        </div>
    </div>
    <hr>
    <h4>Correlated Anime</h4>
    <div class="mb-2"><b>Completion:</b> <span class="watched">{{ watched_count }}</span>/<span class="not-watched">{{ total_correlated }}</span></div>
    <div class="correlated-list">
    {% for related, watched, rel_start_date_fmt, rel_updated_date_fmt in correlated %}
        <a href="{{ url_for('anime_detail', anime_id=related.id, user=user) }}" class="correlated-link">
        <div class="correlated-card">
            <img src="{{ related.cover }}" class="anime-cover mb-2">
            <div class="correlated-content">
                <div>
                    <div class="anime-title" title="{{ related.title }}">{{ related.title }}</div>
                    <div class="anime-meta">Status: {{ format_status(related.status)|safe }}<br>Episodes: {{ related.episodes if related.episodes else '?' }}</div>
                </div>
                <div>
                {% if watched %}
                    <div class="watched">Watched</div>
                {% else %}
                    <div class="not-watched">Not watched</div>
                {% endif %}
                </div>
            </div>
        </div>
        </a>
    {% endfor %}
    </div>
</div>
</body>
</html>
'''

def get_user_anime_ids(anilist_id:int)->list[tuple[int, str]]:
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT anime_id, a.related_to FROM user_anime ua join anime a on ua.anime_id=a.id WHERE ua.anilist_user_id=?", (anilist_id,))
    res = cursor.fetchall()
    conn.close()
    return res

def get_anilist_id_from_username(username:str)->int|None:
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT anilist_id FROM users WHERE anilist_username=?", (username,))
    res = cursor.fetchone()
    conn.close()
    if res:
        return res[0]
    return None

def get_related_anime(anime_id:int, related_to:str|None = None)->list[tuple[int, int]]:
    conn = sqlite3.connect(custom_config.DATABASE_PATH)
    cursor = conn.cursor()
    related_to_values = []
    if related_to is None:
        cursor.execute("SELECT related_to FROM anime WHERE id=?", (anime_id,))
        res = cursor.fetchone()
        if not res or res[0] is None or res[0] == '':
            conn.close()
            return [(anime_id, 0)]
        related_to_values = res[0].split('|')
    else:
        related_to_values = related_to.split('|')
    related_string = ''
    for v in related_to_values:
        related_string += f"or '|'||related_to||'|' like '%|{v}|%' "
    related_string = related_string[3:]
    query = f"SELECT id, start_date FROM anime WHERE {related_string}"
    cursor.execute(query)
    all_anime = cursor.fetchall()
    if not all_anime or len(all_anime) == 0:
        conn.close()
        return [(anime_id, 0)]
    conn.close()
    return [(aid[0], aid[1]) for aid in all_anime]

def format_status(status:str):
    status = (status or '').upper()
    if status == 'FINISHED':
        return '<span class="badge bg-success">Finished</span>'
    elif status == 'RELEASING':
        return '<span class="badge bg-primary">Releasing</span>'
    elif status == 'NOT_YET_RELEASED':
        return '<span class="badge bg-secondary">Not yet released</span>'
    elif status == 'CANCELLED':
        return '<span class="badge bg-danger">Cancelled</span>'
    elif status == 'HIATUS':
        return '<span class="badge bg-warning text-dark">Hiatus (on hold)</span>'
    return f'<span class="badge bg-light text-dark">{status.title()}</span>'

def format_status_plain(status:str):
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

app.jinja_env.globals.update(format_status_plain=format_status_plain)
app.jinja_env.globals.update(format_status=format_status)


@app.route('/', methods=['GET'])
def index():
    start = time.time()
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
            watched = get_user_anime_ids(anilist_id)
            anime_to_check: dict[int, str|None] = {}
            watched_ids:dict[int, bool] = {}
            for v in watched:
                anime_to_check[v[0]] = v[1]
                watched_ids[v[0]] = True
            anime_list = []
            for anime_id in anime_to_check.keys():
                if anime_to_check[anime_id] == None or '|' in (anime_to_check[anime_id] or ''):
                    continue
                group = get_related_anime(anime_id, anime_to_check[anime_id])
                main_id = int(anime_to_check[anime_id] or '0')
                for aid, _ in group:
                    if aid in anime_to_check:
                        anime_to_check[aid] = None
                
                main_anime = get_anime_data(main_id)
                if not main_anime:
                    continue
                start_date_fmt = format_date(main_anime.startDate)
                updated_date_fmt = format_date(main_anime.updatedDate)
                total_correlated = len(group)
                not_watched = 0
                for rid, _ in group:
                    not_watched += 0 if rid in watched_ids else 1
                percent_not_watched = (not_watched / total_correlated * 100) if total_correlated > 0 else 0
                anime_list.append((main_anime, not_watched, total_correlated, percent_not_watched, start_date_fmt, updated_date_fmt))
            anime_list.sort(key=lambda x: (-x[3], -x[1], x[0].title.lower()), reverse=True)
    log.info(f"Time taken: {time.time() - start}")
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
    related_ids = set([aid for aid, _ in get_related_anime(anime_id)])
    related_ids.add(anime_id)  # include itself
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
    correlated.sort(key=lambda x: (x[0].startDate if x[0].startDate else 0))
    total_correlated = len(related_ids)
    return render_template_string(DETAIL_HTML, anime=anime, correlated=correlated, user=user, start_date_fmt=start_date_fmt, updated_date_fmt=updated_date_fmt, watched_count=watched_count, total_correlated=total_correlated)

if __name__ == '__main__':
    app.run(debug=True) 