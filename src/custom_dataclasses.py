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
    date: int