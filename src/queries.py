GET_ANIME_DATA_FROM_ID = '''
query AnimeDataFromId($mediaId: [Int], $page: Int, $perPage: Int) {
    Page(page: $page, perPage: $perPage) {
        media(id_in: $mediaId) {
            id
            type
            format
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
            relations {
                edges {
                    relationType
                    node {
                        id
                        format
                    }
                }
            }
        }
    }
}
'''

GET_WATCHED_ANIME = '''
query ($userName: String) {
  MediaListCollection(userName: $userName, type: ANIME) {
    lists {
      entries {
        status
        media {
          id
        }
      }
    }
  }
}
'''

GET_NEW_USER_ACTIVITIES = '''
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

GET_NEW_UPDATES = '''
query AnimeData($page: Int, $perPage: Int) {
  Page(page: $page, perPage: $perPage) {
    pageInfo {
      perPage
      hasNextPage
    }
    media(sort: UPDATED_AT_DESC, type: ANIME, format_in: [TV, TV_SHORT, MOVIE, SPECIAL, OVA, ONA, MUSIC]) {
      id
      type
      format
      status
      episodes
      updatedAt
      nextAiringEpisode {
        episode
      }
      coverImage {
        extraLarge
      }
      title {
        romaji
        english
      }
      startDate {
        year
        month
        day
      }
      relations {
        edges {
          relationType
          node {
            id
            format
          }
        }
      }
    }
  }
}
'''