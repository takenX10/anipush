from dataclasses import asdict, dataclass


@dataclass
class AnimeData:
    id: int
    title: str
    type: str
    status: str
    cover: str
    episodes: int
    latest_aired_episode: int
    startDate: int
    updatedDate: int

@dataclass
class AnimeRelation:
    primary_anilist_id: int
    related_anilist_id: int
    relation_type: str
    date_update_found: int