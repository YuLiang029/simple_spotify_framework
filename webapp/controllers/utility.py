from webapp import Track


def tracklist2object(tracklist):
    """
    tracklist to track object
    :param tracklist: a list if tracks
    :return: Track object
    """
    libraryobjects = []
    for track in tracklist:
        try:
            libraryobjects.append(
                Track(
                    trackname=track["name"],
                    popularity=track["popularity"],
                    preview_url=track["preview_url"],
                    track_number=track["track_number"],
                    id=track["id"],
                    firstartist=track["artists"][0]["name"],
                    imageurl=None if len(track["album"]["images"]) == 0 else track["album"]["images"][1]["url"],
                    spotifyurl=track["external_urls"]["spotify"],
                    acousticness=track["acousticness"],
                    danceability=track["danceability"],
                    duration_ms=track["duration_ms"],
                    energy=track["energy"],
                    instrumentalness=track["instrumentalness"],
                    key=track["key"],
                    liveness=track["liveness"],
                    loudness=track["loudness"],
                    speechiness=track["speechiness"],
                    tempo=track["tempo"],
                    time_signature=track["time_signature"],
                    valence=track["valence"]
                )
            )
        except Exception as e:
            print (e)
            pass
    return libraryobjects


def combine_track_features(track_recommendations, featuredata):
    """
    combine track features: basic track feature + audio features
    :param track_recommendations:
    :param featuredata:
    :return:
    """
    tracks = {}
    for item in featuredata + track_recommendations:
        if item is not None and "id" in item:
            if item["id"] in tracks:
                tracks[item["id"]].update(item)
            else:
                tracks[item["id"]] = item
    tracklist = [val for (_, val) in tracks.items()]
    return tracklist

