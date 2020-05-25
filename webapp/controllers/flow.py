import os
import json

from flask import session, url_for, request, redirect, render_template
from flask_oauthlib.client import OAuthException
from webapp import app, spotify, User, db, Track, TopArtists, TopTracks, SurveyResponse, SurveyBehaviorLog
from webapp.controllers.utility import combine_track_features, tracklist2object

import six
import base64
import requests
import re
import time
import uuid


# Sample HTTP error handling
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login')
def login():
    """
    Controller for login:
    Set authorization scopes: https://developer.spotify.com/documentation/general/guides/scopes/
    Available scopes
        user-read-private user-read-birthdate user-read-email
        playlist-modify-private playlist-read-private playlist-read-collaborative playlist-modify-public
        user-follow-modify user-follow-read
        app-remote-control streaming
        user-read-currently-playing user-modify-playback-state user-read-playback-state
        user-library-modify user-library-read
        user-read-recently-played user-top-read
        user-read-recently-played user-top-read
    :return:
    """
    if "oauth_token" in session:
        del session["oauth_token"]
    if "userid" in session:
        del session["userid"]
    print("DEBUG: LOGIN")
    session["redirecturl"] = request.args.get("redirecturl")
    session["consent_to_share"] = request.args.get("consent_to_share")
    print("oauth_token" in session)
    if "oauth_token" not in session:
        print("DEBUG: NO TOKEN IN SESSION, REDIRECTING")
        callback = url_for(
            'authorized',
            _external=True
        )
        # define authorization scope
        scope = "user-top-read"
        return spotify.authorize(callback=callback, scope=scope, show_dialog=True)
    else:
        print("TOKEN IN SESSION: REDIRECTING")
        redirect_url = session["redirecturl"]
        print(redirect_url)
        return redirect(redirect_url)


@app.route('/login/authorized')
def authorized():
    #   retrieve basic user information
    print("Redirect from Spotify")
    try:
        resp = spotify.authorized_response()
        if resp is None:
            return 'Access denied: reason={0} error={1}'.format(
                request.args['error_reason'],
                request.args['error_description']
            )
        else:
            session['oauth_token'] = {"access_token": resp['access_token'], "refresh_token": resp['refresh_token'],
                                      "expires_in": resp['expires_in'],
                                      "expires_at": int(time.time()) + resp['expires_in']}
            me = spotify.request('/v1/me/')
            if me.status != 200:
                return 'HTTP Status Error: {0}'.format(resp.data)
            else:
                print(me.data)
                if me.data["display_name"] is None:
                    display_name = ""
                else:
                    display_name = me.data["display_name"]

                user = User.query.filter_by(id=me.data["id"]).first()

                if user is None:
                    userhash = str(uuid.uuid4())
                    user = User(id=me.data["id"], username=display_name,
                                userhash=userhash,
                                consent_to_share=False)

                    db.session.add(user)
                    db.session.commit()

                # Whether user is set or not, always update the consent_to_share
                user.consent_to_share = True if session["consent_to_share"] == "True" else False
                db.session.commit()
                session["userid"] = user.id
                scrape()
                print(session["redirecturl"])
                return redirect("/personality_survey")
    except OAuthException:
        print 'Access denied'


@app.route('/form_consent')
def form_consent():
    """
    Controller for form consent
    :return: consent_form.html
    """
    return render_template('consent_form.html')


@app.route('/msi_survey', methods=["GET", "POST"])
def msi_survey():
    if request.method == "GET":
        responses = User.query.filter_by(id=session["userid"]).first().surveyresponses
        surveydata = {}

        for responseitem in responses:
            m = re.match(r"^([^\[]*)\[([0-9]+)\]$", responseitem.itemid)
            if m:
                print(responseitem.itemid + " " + m.group(1))
                print(m.group(1))
                if m.group(1) in surveydata:
                    surveydata[m.group(1)][m.group(2)] = responseitem.value
                else:
                    surveydata[m.group(1)] = {}
                    surveydata[m.group(1)][m.group(2)] = responseitem.value
            else:
                surveydata[responseitem.itemid] = responseitem.value
        survey = {
            "showProgressBar": "top",
            "pages": [{
                "questions": [{
                    "name": "email",
                    "type": "text",
                    "inputType": "email",
                    "title": "Your contact email:",
                    "isRequired": "true",
                    "validators": [{
                        "type": "email"
                    }]
                }, {
                    "name": "age",
                    "type": "text",
                    "title": "Your age (years):",
                    "isRequired": "true"
                }, {
                    "name": "gender",
                    "type": "dropdown",
                    "title": "Your gender:",
                    "isRequired": "true",
                    "colCount": 0,
                    "choices": [
                        "male",
                        "female",
                        "other"
                    ]
                }]
            }, {
                "questions": [{
                    "type": "matrix",
                    "name": "Active Engagement",
                    "title": "Below some questions how you relate to music. "
                             "Please indicate to what extent you agree or disagree with each statement.",
                    "isAllRowRequired": "true",
                    "columns": [
                        {"value": 1, "text": "Completely Disagree"},
                        {"value": 2, "text": "Strongly Disagree"},
                        {"value": 3, "text": "Disagree"},
                        {"value": 4, "text": "Neither Agree nor Disagree"},
                        {"value": 5, "text": "Agree"},
                        {"value": 6, "text": "Strongly Agree"},
                        {"value": 7, "text": "Completely Agree"}
                    ],
                    "rows": [
                        {"value": "1", "text": "I spend a lot of my free time doing music-related activities."},
                        {"value": "2", "text": "I enjoy writing about music, for example on blogs and forums."},
                        {"value": "3", "text": "I'm intrigued by musical styles I'm not familiar with and want "
                                               "to find out more."},
                        {"value": "4", "text": "I often read or search the internet for things related to music."},
                        {"value": "5", "text": "I don't spend much of my disposable income on music."},
                        {"value": "6", "text": "Music is kind of an addiction for me - I couldn't live without it."},
                        {"value": "7", "text": "I keep track of new of music that I come across (e.g. new artists "
                                               "or recordings)."}
                    ]
                }, {
                    "type": "dropdown",
                    "name": "8",
                    "title": "I have attended _ live music events as an audience member in the past twelve months.",
                    "isRequired": "true",
                    "colCount": 0,
                    "choices": [
                        "0",
                        "1",
                        "2",
                        "3",
                        "4-6",
                        "7-10",
                        "11 or more"
                    ]
                }, {
                    "type": "dropdown",
                    "name": "9",
                    "title": "I listen attentively to music for __ per day.",
                    "isRequired": "true",
                    "colCount": 0,
                    "choices": [
                        "0-15 minutes",
                        "15-30 minutes",
                        "30-60 minutes",
                        "60-90 minutes",
                        "2 hours",
                        "2-3 hours",
                        "4 hours or more"
                    ]
                }]
            }, {
                "questions": [{
                    "type": "matrix",
                    "name": "Emotions",
                    "title": "Please indicate to what extent you agree or disagree with the following statements",
                    "isAllRowRequired": "true",
                    "columns": [
                        {"value": 1, "text": "Completely Disagree"},
                        {"value": 2, "text": "Strongly Disagree"},
                        {"value": 3, "text": "Disagree"},
                        {"value": 4, "text": "Neither Agree nor Disagree"},
                        {"value": 5, "text": "Agree"},
                        {"value": 6, "text": "Strongly Agree"},
                        {"value": 7, "text": "Completely Agree"}
                    ],
                    "rows": [
                        {"value": "10",
                         "text": "I sometimes choose music that can trigger shivers down my spine."},
                        {"value": "11", "text": "Pieces of music rarely evoke emotions for me."},
                        {"value": "12", "text": "I often pick certain music to motivate or excite me."},
                        {"value": "13",
                         "text": "I am able to identify what is special about a given musical piece."},
                        {"value": "14",
                         "text": "I am able to talk about the emotions that a piece of music evokes for me."},
                        {"value": "15", "text": "Music can evoke my memories of past people and places."}
                    ]
                }]
            }],
            "completedHtml": "Redirecting to the next page..."
        }

        survey_config = {
            'title': 'Musical sophistication survey',
            'description': 'The music sophistication survey makes us know your music expertise better.',
            'log_url': '/log_mis_behavior',
            'next_url': url_for('last_step')
        }
        print (surveydata)
        return render_template('survey.html', survey=survey, surveydata=surveydata, survey_config=survey_config)
    if request.method == "POST":
        user = User.query.filter_by(id=session["userid"]).first()
        user.surveyresponses[:] = [
            SurveyResponse(userid=user.id, user=user,
                           itemid=item, value=request.form[item], timestamp=time.time()) for item in
            request.form]
        db.session.commit()
        return "done"


@app.route('/personality_survey', methods=["GET", "POST"])
def personality_survey():
    if request.method == "GET":
        responses = User.query.filter_by(id=session["userid"]).first().surveyresponses
        surveydata = {}

        for responseitem in responses:
            m = re.match(r"^([^\[]*)\[([0-9]+)\]$", responseitem.itemid)
            if m:
                print(responseitem.itemid + " " + m.group(1))
                print(m.group(1))
                if m.group(1) in surveydata:
                    surveydata[m.group(1)][m.group(2)] = responseitem.value
                else:
                    surveydata[m.group(1)] = {}
                    surveydata[m.group(1)][m.group(2)] = responseitem.value
            else:
                surveydata[responseitem.itemid] = responseitem.value
        survey = {
            "showProgressBar": "top",
            "pages": [{
                "questions": [{
                    "type": "matrix",
                    "name": "Big Five Inventory",
                    "title": "Below some questions about personality. "
                             "Please indicate to what extent you agree or disagree with each statement.",
                    "isAllRowRequired": "true",
                    "columns": [
                        {"value": 1, "text": "Strongly Disagree"},
                        {"value": 2, "text": "Disagree"},
                        {"value": 3, "text": "Neutral"},
                        {"value": 4, "text": "Agree"},
                        {"value": 5, "text": "Strongly Agree"}
                    ],
                    "rows": [
                        {"value": "1", "text": "I see myself as someone who is talkative ."},
                        {"value": "2", "text": "I see myself as someone who tends to find fault with others ."},
                        {"value": "3", "text": "I see myself as someone who does a thorough job."},
                        {"value": "4", "text": "I see myself as someone who is depressed, blue."},
                        {"value": "5", "text": "I see myself as someone who is original, comes up with new ideas."},
                        {"value": "6", "text": "I see myself as someone who is reserved ."},
                        {"value": "7", "text": "I see myself as someone who is helpful and unselfish with others."},
                        {"value": "8", "text": "I see myself as someone who can be somewhat careless."},
                        {"value": "9", "text": "I see myself as someone who is relaxed, handles stress well ."},
                        {"value": "10", "text": "I see myself as someone who is curious about many different things."},
                    ]
                }]
            }, {
                "questions": [{
                    "type": "matrix",
                    "name": "Big Five Inventory",
                    "title": "Below some questions about personality. "
                             "Please indicate to what extent you agree or disagree with each statement.",
                    "isAllRowRequired": "true",
                    "columns": [
                        {"value": 1, "text": "Strongly Disagree"},
                        {"value": 2, "text": "Disagree"},
                        {"value": 3, "text": "Neutral"},
                        {"value": 4, "text": "Agree"},
                        {"value": 5, "text": "Strongly Agree"}
                    ],
                    "rows": [
                        {"value": "11", "text": "I see myself as someone who is full of energy."},
                        {"value": "12", "text": "I see myself as someone who starts quarrels with others ."},
                        {"value": "13", "text": "I see myself as someone who is a reliable worker ."},
                        {"value": "14", "text": "I see myself as someone who can be tense ."},
                        {"value": "15", "text": "I see myself as someone who is ingenious, a deep thinker."},
                        {"value": "16", "text": "I see myself as someone who generates a lot of enthusiasm."},
                        {"value": "17", "text": "I see myself as someone who has a forgiving nature ."},
                        {"value": "18", "text": "I see myself as someone who tends to be disorganized ."},
                        {"value": "19", "text": "I see myself as someone who worries a lot ."},
                        {"value": "20", "text": "I see myself as someone who has an active imagination."},
                    ]
                }]
            }, {
                "questions": [{
                    "type": "matrix",
                    "name": "Big Five Inventory",
                    "title": "Below some questions about personality. "
                             "Please indicate to what extent you agree or disagree with each statement.",
                    "isAllRowRequired": "true",
                    "columns": [
                        {"value": 1, "text": "Strongly Disagree"},
                        {"value": 2, "text": "Disagree"},
                        {"value": 3, "text": "Neutral"},
                        {"value": 4, "text": "Agree"},
                        {"value": 5, "text": "Strongly Agree"}
                    ],
                    "rows": [
                        {"value": "21", "text": "I see myself as someone who tends to be quiet."},
                        {"value": "22", "text": "I see myself as someone who is generally trusting ."},
                        {"value": "23", "text": "I see myself as someone who tends to be lazy ."},
                        {"value": "24", "text": "I see myself as someone who is emotionally stable, not easily upset."},
                        {"value": "25", "text": "I see myself as someone who is inventive ."},
                        {"value": "26", "text": "I see myself as someone who has an assertive personality."},
                        {"value": "27", "text": "I see myself as someone who can be cold and aloof."},
                        {"value": "28", "text": "I see myself as someone who perseveres until the task is finished ."},
                        {"value": "29", "text": "I see myself as someone who can be moody."},
                        {"value": "30", "text": "I see myself as someone who values artistic, aesthetic experiences ."},
                    ]
                }]
            }, {
                "questions": [{
                    "type": "matrix",
                    "name": "Big Five Inventory",
                    "title": "Below some questions about personality. "
                             "Please indicate to what extent you agree or disagree with each statement.",
                    "isAllRowRequired": "true",
                    "columns": [
                        {"value": 1, "text": "Strongly Disagree"},
                        {"value": 2, "text": "Disagree"},
                        {"value": 3, "text": "Neutral"},
                        {"value": 4, "text": "Agree"},
                        {"value": 5, "text": "Strongly Agree"}
                    ],
                    "rows": [
                        {"value": "31", "text": "I see myself as someone who is sometimes shy, inhibited ."},
                        {"value": "32",
                         "text": "I see myself as someone who is considerate and kind to almost everyone ."},
                        {"value": "33", "text": "I see myself as someone who does things efficiently ."},
                        {"value": "34", "text": "I see myself as someone who remains calm in tense situations ."},
                        {"value": "35", "text": "I see myself as someone who prefers work that is routine ."},
                        {"value": "36", "text": "I see myself as someone who is outgoing, sociable."},
                        {"value": "37", "text": "I see myself as someone who is sometimes rude to others ."},
                        {"value": "38",
                         "text": "I see myself as someone who makes plans and follows through with them."},
                        {"value": "39", "text": "I see myself as someone who gets nervous easily ."},
                        {"value": "40", "text": "I see myself as someone who likes to reflect, play with ideas."},
                    ]
                }]
            }, {
                "questions": [{
                    "type": "matrix",
                    "name": "Big Five Inventory",
                    "title": "Below some questions about personality. "
                             "Please indicate to what extent you agree or disagree with each statement.",
                    "isAllRowRequired": "true",
                    "columns": [
                        {"value": 1, "text": "Strongly Disagree"},
                        {"value": 2, "text": "Disagree"},
                        {"value": 3, "text": "Neutral"},
                        {"value": 4, "text": "Agree"},
                        {"value": 5, "text": "Strongly Agree"}
                    ],
                    "rows": [
                        {"value": "41", "text": "I see myself as someone who has few artistic interests."},
                        {"value": "42", "text": "I see myself as someone who likes to cooperate with others ."},
                        {"value": "43", "text": "I see myself as someone who is easily distracted."},
                        {"value": "44", "text": "I see myself as someone who is sophisticated "
                                                "in art, music, or literature."},
                    ]
                }]
            }],
            "completedHtml": "Redirecting to the next page..."
        }

        survey_config = {
            'title': 'Personality survey',
            'description': '',
            'log_url': '/log_survey_behavior',
            'next_url': url_for('music_preference_survey')
        }
        print (surveydata)
        return render_template('survey.html', survey=survey, surveydata=surveydata, survey_config=survey_config)
    if request.method == "POST":
        user = User.query.filter_by(id=session["userid"]).first()
        user.surveyresponses[:] = [
            SurveyResponse(userid=user.id, user=user,
                           itemid=item, value=request.form[item], timestamp=time.time()) for item in
            request.form]
        db.session.commit()
        return "done"


@app.route('/music_preference_survey', methods=["GET", "POST"])
def music_preference_survey():
    if request.method == "GET":
        responses = User.query.filter_by(id=session["userid"]).first().surveyresponses
        surveydata = {}

        for responseitem in responses:
            m = re.match(r"^([^\[]*)\[([0-9]+)\]$", responseitem.itemid)
            if m:
                print(responseitem.itemid + " " + m.group(1))
                print(m.group(1))
                if m.group(1) in surveydata:
                    surveydata[m.group(1)][m.group(2)] = responseitem.value
                else:
                    surveydata[m.group(1)] = {}
                    surveydata[m.group(1)][m.group(2)] = responseitem.value
            else:
                surveydata[responseitem.itemid] = responseitem.value
        survey = {
            "showProgressBar": "top",
            "pages": [{
                "questions": [{
                    "type": "matrix",
                    "name": "Music genre preferences",
                    "title": "Below some music genres are displayed "
                             "Please indicate to what extent your music taste matches with the genre. "
                             "You can indicate also that you do not know a genre.",
                    "isAllRowRequired": "true",
                    "columns": [
                        {"value":0, "text": "Not familiar with this genre"},
                        {"value": 1, "text": "Not a match with my preference, listen never"},
                        {"value": 2, "text": ""},
                        {"value": 3, "text": "Not a great match with my preference, Listen rarely"},
                        {"value": 4, "text": ""},
                        {"value": 5, "text": "Neutral, Listen regularly"},
                        {"value": 6, "text": ""},
                        {"value": 7, "text": "Close to my preference, Listen frequently "},
                        {"value": 8, "text": ""},
                        {"value": 9, "text": "Very good match to my preference, listen often"}
                    ],

                    "rows": [
                        {"value": "1", "text": "Soft rock"},
                        {"value": "2", "text": "RnB"},
                        {"value": "3", "text": "Country"},
                        {"value": "4", "text": "Rocknrol"},
                        {"value": "5", "text": "Classical"},
                        {"value": "6", "text": "Avantgarde"},
                        {"value": "7", "text": "Punk"},
                        {"value": "8", "text": "Heavy metal"},
                        {"value": "9", "text": "Rap"},
                        {"value": "10", "text": "Electronica"},
                    ]
                }]
            }],
            "completedHtml": "Redirecting to the next page..."
        }

        survey_config = {
            'title': 'Music preference survey',
            'description': '',
            'log_url': '/log_survey_behavior',
            'next_url': url_for('last_step')
        }
        print (surveydata)
        return render_template('survey.html', survey=survey, surveydata=surveydata, survey_config=survey_config)
    if request.method == "POST":
        user = User.query.filter_by(id=session["userid"]).first()
        user.surveyresponses[:] = [
            SurveyResponse(userid=user.id, user=user,
                           itemid=item, value=request.form[item], timestamp=time.time()) for item in
            request.form]
        db.session.commit()
        return "done"


@app.route('/last_step')
def last_step():
    return render_template('last_page.html')


def is_token_expired():
    """
    check if token is expired
    :return: Boolean
    """
    if session["oauth_token"]["expires_at"] - int(time.time()) < 60:
        return True
    return False


def make_refresh_token_headers(client_id, client_secret):
    """
    make refresh token headers
    :param client_id:
    :param client_secret:
    :return: headers for requesting refresh tokens
    """
    auth_header = base64.b64encode(
        six.text_type(client_id + ':' + client_secret).encode('ascii'))
    headers = {'Authorization': 'Basic %s' % auth_header.decode('ascii')}
    return headers


def get_refresh_token(refresh_token):
    """
    get refresh token
    :param refresh_token:
    :return: update oauth_token
    """
    payload = {'refresh_token': refresh_token, 'grant_type': 'refresh_token'}

    if os.path.exists('keys.json'):
        keys = json.load(open('keys.json', 'r'))

    headers = make_refresh_token_headers(keys["CLIENT_ID"], keys["CLIENT_SECRET_ID"])
    resp = requests.post(spotify.access_token_url, data=payload, headers=headers)

    if resp.status_code != 200:
        # if False:  # debugging code
        print('debugging')
        print('headers', headers)
    else:
        token_info = resp.json()
        if 'refresh_token' not in token_info:
            session['oauth_token'] = {"access_token": token_info['access_token'], "refresh_token": refresh_token,
                                      "expires_in": token_info['expires_in'],
                                      "expires_at": int(time.time()) + token_info['expires_in']}
        else:
            session['oauth_token'] = {"access_token": token_info['access_token'],
                                      "refresh_token": token_info['refresh_token'],
                                      "expires_in": token_info['expires_in'],
                                      "expires_at": int(time.time()) + token_info['expires_in']}


@app.route('/scrape')
def scrape(limit=50):
    """
    Scrape user top tracks
    https://developer.spotify.com/console/get-current-user-top-artists-and-tracks/
    authorization scopes: user-top-read
    :param limit:
    :return:
    """

    terms = ['short', 'medium', 'long']
    ts = time.time()

    def check_token():
        if "oauth_token" not in session:
            print("authorizing")
            session["redirecturl"] = url_for("scrape")
            return spotify.authorize(url_for("authorized", _external=True))

        if is_token_expired():
            refresh_token = session["oauth_token"]["refresh_token"]
            get_refresh_token(refresh_token)

    for term in terms:
        check_token()
        url = '/v1/me/top/tracks?limit=' + str(limit) + '&time_range=' + term + '_term'
        print("url: " + url)
        try:
            toptracksrequest = spotify.request(url)

            if toptracksrequest.status != 200:
                return "toptracksrequest status: " + str(toptracksrequest.status), 400
            else:
                toptracks = toptracksrequest.data["items"]
                url = "https://api.spotify.com/v1/audio-features?ids=" + ",".join([x["id"] for x in toptracks])
                audiofeaturesrequest = spotify.request(url)
                featuredata = audiofeaturesrequest.data["audio_features"]
                tracklist = combine_track_features(toptracks, featuredata)
                libraryobjects = tracklist2object(tracklist)
                for x in libraryobjects:
                    track = Track.query.filter_by(id=x.id).first()
                    if track:
                        entry = TopTracks.query.filter_by(userid=session["userid"],
                                                          trackid=x.id, timeperiod=term).first()
                        if entry:
                            pass
                        else:
                            new_toptrack_obj = TopTracks(userid=session["userid"],
                                                         trackid=x.id, timeperiod=term, timestamp=str(ts), track=track)
                            db.session.add(new_toptrack_obj)
                    else:
                        new_track_obj = Track(
                            id=x.id, trackname=x.trackname, popularity=x.popularity, preview_url=x.preview_url,
                            track_number=x.track_number, firstartist=x.firstartist, imageurl=x.imageurl,
                            spotifyurl=x.spotifyurl, acousticness=x.acousticness, danceability=x.danceability,
                            duration_ms=x.duration_ms, energy=x.energy, instrumentalness=x.instrumentalness,
                            key=x.key, liveness=x.liveness, loudness=x.loudness,
                            speechiness=x.speechiness, tempo=x.tempo, time_signature=x.time_signature,
                            valence=x.valence
                        )
                        new_toptrack_obj = TopTracks(userid=session["userid"],
                                                     trackid=x.id, timeperiod=term,
                                                     timestamp=str(ts), track=new_track_obj)
                        db.session.add(new_toptrack_obj)
                db.session.commit()
        except Exception as e:
            print(e.args)
            return "error", 400

    # for term in terms:
    #     check_token()
    #     url = '/v1/me/top/artists?limit=' + str(limit) + '&time_range=' + term + '_term'
    #     print("url: " + url)
    #     try:
    #         topartistsrequest = spotify.request(url)
    #
    #         if topartistsrequest.status != 200:
    #             return "topartistsrequest status: " + str(topartistsrequest.status), 400
    #         else:
    #             topartists = topartistsrequest.data["items"]
    #             for artist in topartists:
    #                 entry = TopArtists.query.filter_by(userid=session["userid"],
    #                                                    artistid=artist["id"], timeperiod=term).first()
    #                 if entry:
    #                     pass
    #                 else:
    #                     new_topartist_obj = TopArtists(userid=session["userid"],
    #                                                    artistid=artist["id"], timeperiod=term, timestamp=ts)
    #                     db.session.add(new_topartist_obj)
    #         db.session.commit()
    #     except Exception as e:
    #         print(e.args)
    #         return "error", 400
    return "done"


@app.route('/log_survey_behavior', methods=['POST'])
def log_survey_behavior():
    if request.method == 'POST':
        print request.form
        bahavior_log = SurveyBehaviorLog(
            userid=session["userid"],
            timestamp=time.time(),
            question=request.form["question"],
            answer=request.form["answer"]
        )
        db.session.add(bahavior_log)
        db.session.commit()
        return "done"
