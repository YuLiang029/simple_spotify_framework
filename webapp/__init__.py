from flask import Flask, session
from flask_oauthlib.client import OAuth
import os
import json
from flask_sqlalchemy import SQLAlchemy

from rq import Queue
from worker import conn

q = Queue('high', connection=conn)

app = Flask(__name__)
app.config.from_object('config')


db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.VARCHAR, primary_key=True)
    username = db.Column(db.VARCHAR)
    userhash = db.Column(db.VARCHAR)
    consent_to_share = db.Column(db.Boolean)

    surveyresponses = db.relationship('SurveyResponse',
                                      cascade='delete-orphan, delete, save-update, merge, expunge')

    def __repr__(self):
        return '<User %r>' % self.id


class TopArtists(db.Model):
    __tablename__ = 'top_artists'
    userid = db.Column(db.VARCHAR, db.ForeignKey('user.id'), primary_key=True)
    artistid = db.Column(db.VARCHAR, primary_key=True)
    timeperiod = db.Column(db.VARCHAR, primary_key=True)
    timestamp = db.Column(db.FLOAT)

    def __repr__(self):
        return '<TopArtists %r-%r>' % (self.userid, self.artistid)


class TopTracks(db.Model):
    __tablename__ = 'top_tracks'
    userid = db.Column(db.VARCHAR, db.ForeignKey('user.id'), primary_key=True)
    trackid = db.Column(db.VARCHAR, db.ForeignKey('track.id'), primary_key=True)
    timeperiod = db.Column(db.VARCHAR, primary_key=True)
    timestamp = db.Column(db.VARCHAR)
    track = db.relationship('Track')

    def __repr__(self):
        return '<TopTracks %r-%r>' % (self.userid, self.trackid)


class SurveyResponse(db.Model):
    __tablename__ = 'survey_responses'
    userid = db.Column(db.VARCHAR, db.ForeignKey('user.id'), primary_key=True)
    user = db.relationship('User')
    itemid = db.Column(db.VARCHAR, primary_key=True)
    value = db.Column(db.VARCHAR)
    timestamp = db.Column(db.FLOAT)

    def __repr__(self):
        return '<SurveyResponse %r-%r>' % (self.userid, self.itemid)


class SurveyBehaviorLog(db.Model):
    __tablename__ = 'survey_behavior_log'
    userid = db.Column(db.VARCHAR, db.ForeignKey('user.id'), primary_key=True)
    timestamp = db.Column(db.FLOAT, primary_key=True)
    question = db.Column(db.VARCHAR, primary_key=True)
    answer = db.Column(db.VARCHAR, primary_key=True)


class Track(db.Model):
    __tablename__ = 'track'
    id = db.Column(db.VARCHAR, primary_key=True)
    trackname = db.Column(db.VARCHAR)
    popularity = db.Column(db.INTEGER)
    preview_url = db.Column(db.VARCHAR)
    track_number = db.Column(db.INTEGER)
    firstartist = db.Column(db.VARCHAR)
    imageurl = db.Column(db.VARCHAR)
    spotifyurl = db.Column(db.VARCHAR)
    acousticness = db.Column(db.FLOAT)
    danceability = db.Column(db.FLOAT)
    duration_ms = db.Column(db.INTEGER)
    energy = db.Column(db.FLOAT)
    instrumentalness = db.Column(db.FLOAT)
    key = db.Column(db.VARCHAR)
    liveness = db.Column(db.FLOAT)
    loudness = db.Column(db.FLOAT)
    speechiness = db.Column(db.FLOAT)
    tempo = db.Column(db.INTEGER)
    time_signature = db.Column(db.INTEGER)
    valence = db.Column(db.FLOAT)

    def to_json(self):
        return dict(
            id=self.id,
            trackname=self.trackname,
            popularity=self.popularity,
            preview_url=self.preview_url,
            track_number=self.track_number,
            firstartist=self.firstartist,
            imageurl=self.imageurl,
            spotifyurl=self.spotifyurl,
            acousticness=self.acousticness,
            danceability=self.danceability,
            duration_ms=self.duration_ms,
            energy=self.energy,
            instrumentalness=self.instrumentalness,
            key=self.key,
            liveness=self.liveness,
            loudness=self.loudness,
            speechiness=self.speechiness,
            tempo=self.tempo,
            time_signature=self.time_signature,
            valence=self.valence)

    def __repr__(self):
        return '<Track %r-%r>' % (self.firstartist, self.trackname)


if os.path.exists('keys.json'):
    keys = json.load(open('keys.json', 'r'))

oauth = OAuth(app)

spotify = oauth.remote_app(
    'spotify',
    consumer_key=os.environ.get('SPOTIFY_CLIENT_ID', keys["CLIENT_ID"]),
    consumer_secret=os.environ.get('SPOTIFY_CLIENT_SECRET', keys["CLIENT_SECRET_ID"]),
    base_url='https://api.spotify.com/',
    request_token_url=None,
    access_token_url='https://accounts.spotify.com/api/token',
    authorize_url='https://accounts.spotify.com/authorize'
)


@spotify.tokengetter
def get_spotify_oauth_token():
    return session.get('oauth_token')


@app.after_request
def add_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    return response


from webapp.controllers import flow, utility, utility2


db.create_all()

