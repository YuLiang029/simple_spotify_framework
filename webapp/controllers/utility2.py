from webapp import spotify
from flask import session


def generate_playlist(name="demo", description="for demo use", public=False):
    """
    generate a playlist to spotify
    :param name: string, default: "demo"
    :param description: string, default: "for demo use"
    :param public: Boolean, default: False
    :return: playlist_id: string, playlist_url: string
    """
    url = '/v1/users/' + session["userid"] + '/playlists'
    data = {"name": name, "description": description, "public": public}
    try:
        playlist = spotify.post(url, data=data, format='json')
        if playlist.status == 200 or playlist.status == 201:
            playlist_id = playlist.data['id']
            playlist_url = playlist.data['external_urls']['spotify']
            return playlist_id, playlist_url
        else:
            return 'failure in creating new playlist on spotify, error ' + str(playlist.status), 400
    except Exception as e:
        print(e.args)
        return "error", 400


def save_tracks_to_playlist(playlist_id, playlist_url, track_list):
    """
    save a list of tracks to playlist
    :param playlist_id: string
    :param playlist_url: string
    :param track_list: a list of track ids to be added
    :return: playlist_url: string
    """
    url = '/v1/users/' + session["userid"] + '/playlists/' + playlist_id + '/tracks?position=0'
    prefix = "spotify:track:"
    new_track_list = []

    for track in track_list:
        new_track_list.append(prefix + track)
    data = {"uris": new_track_list}
    try:
        new_playlist = spotify.post(url, data=data, format='json')
        if new_playlist.status == 201:
            return playlist_url
        else:
            return 'failure in saving tracks to the new playlist, error ' + str(new_playlist.status), 400
    except Exception as e:
        print(e.args)
        return "error", 400

