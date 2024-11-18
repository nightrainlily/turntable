from flask import Flask, session, redirect, request, url_for, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql.sqltypes import ARRAY
from sqlalchemy import desc, cast, func
import requests
import os
from dotenv import load_dotenv
from urllib.parse import urlencode, quote
from apscheduler.schedulers.background import BackgroundScheduler
import re
import time
import model

load_dotenv()

client_secret = os.getenv('CLIENT_SECRET')
client_id = os.getenv('CLIENT_ID')
redirect_uri=os.getenv('REDIRECT_URI')
scope = os.getenv('SCOPE')
secret_key = 'aaaaaaaaaaaaaaaa'

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///playlists.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = secret_key
db = SQLAlchemy(app)

# app.config.update(SESSION_COOKIE_SAMESITE="None", SESSION_COOKIE_SECURE=True)

class Playlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String, nullable=False)
    url = db.Column(db.String)
    image = db.Column(db.String)

    def __repr__(self):
        return f"<{self.name}>"

class Track(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    track_id = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    artist = db.Column(db.String(100), nullable=False)
    danceability = db.Column(db.Float)
    energy = db.Column(db.Float)
    key = db.Column(db.Float)
    loudness = db.Column(db.Float)
    mode = db.Column(db.Float)
    speechiness = db.Column(db.Float)
    acousticness = db.Column(db.Float)
    instrumentalness = db.Column(db.Float)
    liveness = db.Column(db.Float)
    valence = db.Column(db.Float)
    tempo = db.Column(db.Float)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlist.playlist_id'), nullable=False)
    artist_id = db.Column(db.String, db.ForeignKey('artist.artist_id'))

    playlist = db.relationship('Playlist', backref='playlist.playlist_id')

    def __repr__(self):
        return f"<{self.name}>"

class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    artist_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    genres = db.Column(db.String, default='')

    artist_tracks = db.relationship('Track', backref='track')

    def __repr__(self):
        return f"<{self.name}"

scheduler = BackgroundScheduler()

with app.app_context():
    # db.drop_all()
    db.create_all()
    db.session.commit()
    print('dbs created')

def flatten(lst):
    return [item for sublist in lst for item in sublist]

def playlist_tracks(playlist_id):
    tracks = db.session.query(Track.name).filter_by(playlist_id=playlist_id).all()
    return [track.name for track in tracks]

def playlist_genres(playlist_id):
    playlist_artists = db.session.query(Track.artist_id).filter_by(playlist_id=playlist_id).all()
    genres = []
    for artist in playlist_artists:
        genre_list = db.session.query(Artist.genres).filter_by(artist_id=artist.artist_id).first().genres
        genres.append((genre_list))
    return flatten(genres)

@app.route('/')
def index():
    playlists = Playlist.query.order_by(desc(cast(Playlist.name, db.Integer))).all()
    tracks = Track.query.all()

    if playlists:
        return render_template('index.html', playlist_tracks=playlist_tracks, playlist_genres=playlist_genres, playlists=playlists, tracks=tracks)
    else:
        return render_template('index.html', playlists=None, tracks=None)
    
@app.route('/playlist/<string:playlist_id>')
def playlist_details(playlist_id):
    playlist = Playlist.query.filter_by(playlist_id=playlist_id).first_or_404()
    playlist_tracks = Track.query.filter_by(playlist_id=playlist_id).all()
    return render_template('playlist.html', playlist=playlist, playlist_tracks=playlist_tracks)

@app.route('/artist/<string:artist_id>')
def artist_playlists(artist_id):
    artist_name = db.session.query(Artist.name).filter_by(artist_id=artist_id).first().name
    tracks = db.session.query(Track).filter_by(artist_id=artist_id).all()
    artist_playlists = []
    for track in tracks:
        playlists = Playlist.query.filter_by(playlist_id=track.playlist_id).all()
        artist_playlists.append(playlists)
    sorted_playlists = sorted(
        artist_playlists,
        key=lambda p: int(p[0].name.split(' ')[0]) if p[0].name.split(' ')[0].isdigit() else 0,
        reverse=True
    )
    return render_template('artist.html', artist_playlists=sorted_playlists, artist_name=artist_name)

@app.route('/recommendations/<string:playlist_id>')
def model_playlists(playlist_id):
    recs = model.get_recs(playlist_id=playlist_id)
    model_playlists=[]
    for playlist_name in recs:
        playlist = Playlist.query.filter_by(name=playlist_name).first()
        model_playlists.append(playlist)
    sorted_playlists = sorted(model_playlists, key=lambda p: int(p.name.split()[0]), reverse=True)

    return render_template('model.html', model_playlists=sorted_playlists, playlist_name=db.session.query(Playlist.name).filter(Playlist.playlist_id == playlist_id).scalar())

@app.route('/authorize')
def authorize():
    auth_url = "https://accounts.spotify.com/authorize/"
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': scope,
        'show_dialog': True,
    }
    return redirect(f"{auth_url}?{urlencode(params)}")

@app.route('/callback')
def callback():
    auth_code = request.args.get('code')
    if auth_code:
        token_url = 'https://accounts.spotify.com/api/token'
        token_data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret,
        }
        response = requests.post(token_url, data=token_data)
        tokens = response.json()
        access_token = tokens['access_token']
        refresh_token = tokens['refresh_token']

        session['access_token'] = access_token
        session['refresh_token'] = refresh_token
        session.modified = True

        updated = update(1100)

        if updated:
            print('loaded dbs')
            return redirect(url_for('index'))
        return redirect(url_for('/authorize'))       

#refresh
def refresh_access_token():
    url = "https://api.spotify.com/v1/me"
    access_token = session.get('access_token')
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 401:
        refresh_token = session.get('refresh_token')
        if refresh_token:
            token_url = "https://accounts.spotify.com/api/token"
            token_data = {
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': client_id,
                'client_secret': client_secret,
            }
            response = requests.post(token_url, data=token_data)
            access_token = response.json().get('access_token')
            return access_token
        return None
    return access_token

def batch(lst, n):
    for i in range(0, len(lst), n):
        if len(lst) >= (i+n):
            yield lst[i:i + n]
        else:
            yield lst[i:]

def get_playlists(num_playlists, limit=50):
    access_token = refresh_access_token()
    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        results = []
        offset = 0
        while offset < num_playlists:
            playlists_url = f"https://api.spotify.com/v1/me/playlists?offset={offset}&limit={limit}"
            response = requests.get(playlists_url, headers=headers)
            playlists_data = response.json()
            results.append(playlists_data['items'])
            offset += 50
            time.sleep(1)
        playlists_data = [playlist for result in results for playlist in result]

        new_playlist_count=0
        for playlist in playlists_data:
            reg = "^([0-9])+\s([a-z]+(\s?)([a-z]?))"
            zero_reg = "^00"
            if re.search(reg, playlist['name']) != None and playlist['public'] == True and playlist['collaborative'] == False and re.match(zero_reg, playlist['name']) == None:
                name = playlist['name']
                playlist_id = playlist['id']
                url = playlist['external_urls']['spotify']
                image = playlist['images'][0]['url']

                existing_playlist = db.session.query(Playlist.playlist_id).filter_by(playlist_id=playlist_id).first()
                image_reg = "^https:\/\/image-cdn-ak"
                if not existing_playlist and re.match(image_reg, image) != None:
                    new_playlist = Playlist(
                        name=name,
                        playlist_id=playlist_id,
                        url=url,
                        image=image
                    )
                    get_tracks(playlist_id)
                    db.session.add(new_playlist)
                    new_playlist_count+=1
        db.session.commit()
        return new_playlist_count
    return False

def get_tracks(playlist_id):
    access_token = refresh_access_token()
    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        tracks_url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?fields=items%28track%28name%2C+artists%28id%2C+name%29%2C+id%29"
        tracks_response = requests.get(tracks_url, headers=headers)
        tracks_data = tracks_response.json().get('items', [])

        for track_info in tracks_data:
            track = track_info['track']
            track_id = track['id']
            track_name = track['name']
            artist_name = track['artists'][0]['name']
            artist_id = track['artists'][0]['id']

            existing_track = db.session.query(Track.track_id).filter_by(track_id=track_id).first()
            if not existing_track and all([track, track_id, track_name, artist_name, artist_id]):
                new_track = Track(
                    track_id=track_id,
                    name=track_name,
                    artist=artist_name,
                    playlist_id=playlist_id,
                    artist_id=artist_id
                )
                print(track_name)
                get_artists(artist_id)
                db.session.add(new_track)
        db.session.commit()
    return


def get_audio_features(num_tracks):
    track_ids = db.session.query(Track.track_id).limit(-num_tracks).all()
    print(track_ids)
    access_token = refresh_access_token()
    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        batched = batch(track_ids, 100)
        for each in batched:
            track_ids_string = ','.join([item[0] for item in each])
            af_url = f"https://api.spotify.com/v1/audio-features?ids={quote(track_ids_string)}"
            af_response = requests.get(af_url, headers=headers)
            af_data = af_response.json()['audio_features']

            for each_track in af_data:
                reg = '(?<=track:).*'
                spotify_id = re.findall(reg, each_track['uri'])[0]
                track = db.session.query(Track).filter_by(track_id=spotify_id).first()

                track.danceability = each_track['danceability']
                track.energy = each_track['energy']
                track.key = each_track['key']
                track.loudness = each_track['loudness']
                track.mode = each_track['mode']
                track.speechiness = each_track['speechiness']
                track.acousticness = each_track['acousticness']
                track.instrumentalness = each_track['instrumentalness']
                track.liveness = each_track['liveness']
                track.valence = each_track['valence']
                track.tempo = each_track['tempo']
        db.session.commit()
    return

def get_artists(artist_id):
    access_token = refresh_access_token()
    if access_token:
        headers = {
            'Authorization': f'Bearer {access_token}',
        }

        existing_artist = db.session.query(Artist.artist_id).filter_by(artist_id=artist_id).first()
        if not existing_artist:
            artist_url = f"https://api.spotify.com/v1/artists/{artist_id}"
            artist_response = requests.get(artist_url, headers=headers)
            artist_data = artist_response.json()

            new_artist = Artist(
                artist_id=artist_id,
                name=artist_data['name'],
                genres=", ".join(artist_data['genres'])
            )
            db.session.add(new_artist)
        db.session.commit()
    return

@app.route('/update')
def update():
    num_playlists = get_playlists(10, 10)
    get_audio_features(num_playlists)
    print('updated!', num_playlists)
    if num_playlists:
        return redirect(url_for('index'))

scheduler = BackgroundScheduler()
scheduler.add_job(update, 'interval', days=1)
scheduler.start()

if __name__ == "__main__":
    app.run(debug=True, port=5000)

