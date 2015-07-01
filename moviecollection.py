from flask import Flask, render_template, request, redirect, url_for, flash
from flask import session as login_session
from flask import make_response, jsonify
from flask.ext.seasurf import SeaSurf

import json
from dict2xml import dict2xml as xmlify
from werkzeug.contrib.atom import AtomFeed

from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Movie, Genre

import requests
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from oauth2client.client import OAuth2Credentials
import httplib2

from datetime import datetime
from functools import wraps

app = Flask(__name__)
# Use Flask-SeaSurf to include csrf_token for all POST requests
csrf = SeaSurf(app)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# Connect to Database and create database session
engine = create_engine('sqlite:///moviecollection.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# genres will be used to create left-side nav bar
genres = session.query(Genre)

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            flash('Please login to perform this operation')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function


# Show all movies ordered by their created time
@app.route('/')
@app.route('/movies/')
def showMovies():
    movies = session.query(Movie).order_by(desc(Movie.create_time)).all()
    # Login button will be available if user is not logged in
    if 'username' not in login_session:
        return render_template('public_movies.html', 
                               movies = movies, 
                               genres = genres, 
                               current_genre = 'Recently Added', 
                               CLIENT_ID = CLIENT_ID)
    # User logged in will be able to add new movies
    else:
        return render_template('movies.html', 
                               movies = movies, 
                               genres = genres, 
                               current_genre = 'Recently Added', 
                               username = login_session['username'], 
                               CLIENT_ID = CLIENT_ID)


# JSON API to list all movie information
@app.route('/movies/JSON')
def showMoviesJSON():
    movies = session.query(Movie).order_by(desc(Movie.create_time)).all()
    return jsonify(movies = [movie.serialize for movie in movies])


# XML API to list all movie information
@app.route('/movies/XML')
def showMoviesXML():
    movies = session.query(Movie).order_by(desc(Movie.create_time)).all()
    return xmlify({'movies': [movie.serialize for movie in movies]})

# ATOM API to list all movie information
@app.route('/movies/ATOM')
def showMoviesATOM():
    feed = AtomFeed('Recent Movies', 
                    feed_url = request.url, 
                    url = request.url_root)
    movies = (session.query(Movie)
                     .order_by(desc(Movie.create_time))
                     .limit(15)
                     .all())
    for movie in movies:
        content = render_template('movie_entry.atom', movie=movie)
        # Add feed entries
        feed.add(movie.title, 
                 content, 
                 content_type='html', 
                 url='/movie/%s'%movie.id, 
                 updated=movie.create_time)
    return feed.get_response()


# Show movies in a specific genre
@app.route('/genre/<int:genre_id>/')
def showGenre(genre_id):
    genre = (session.query(Genre)
                     .filter(Genre.id==genre_id)
                     .one())
    # Get movies of a genre with backref
    movies = genre.movies
    # Login button will be available if user is not logged in
    if 'username' not in login_session:
        return render_template('public_movies.html', 
                               movies = movies, 
                               genres = genres, 
                               current_genre = genre.genre, 
                               CLIENT_ID = CLIENT_ID)
    # User logged in will be able to add new movies
    else:
        return render_template('movies.html', 
                               movies = movies, 
                               genres = genres, 
                               current_genre = genre.genre, 
                               username = login_session['username'])


# Show details of a specific movie
@app.route('/movie/<int:movie_id>/')
def showMovieDetail(movie_id):
    movie = session.query(Movie).filter(Movie.id==movie_id).one()
    # Login button will be available if user is not logged in
    if 'username' not in login_session:
        return render_template('public_movie_detail.html', 
                               movie = movie, 
                               genres = genres, 
                               CLIENT_ID = CLIENT_ID)
    else:
        return render_template('movie_detail.html', 
                               movie = movie, 
                               genres = genres, 
                               username = login_session['username'], 
                               user_id = login_session['user_id'])


# Users logged in can create a new movie
@app.route('/movie/new/', methods=['GET', 'POST'])
# Only users logged in can add new movie
@login_required
def addMovie():
    # POST request, the user has submit the form
    if request.method == 'POST':
        # Get values for movie entry from the form
        title = request.form['title'] 
        tmdb_id = int(request.form['tmdbID'])
        imdb_id = request.form['imdbID']
        overview = request.form['overview']
        poster = request.form['poster']
        youtube_id = request.form['youtubeID']
        genre_ids = request.form.getlist('genres')
        release_date = request.form['releaseDate']
        release_date = (datetime.strptime(release_date, '%Y-%m-%d') 
                            if release_date else None)

        # ============================================================
        # TODO: 
        # Database should not be modified unless form is valid
        # Server-side form validation will go here
        # ============================================================

        current_genres = (session.query(Genre)
                                 .filter(Genre.id.in_(genre_ids))
                                 .all())

        # New movie entry with information from the form
        newMovie = Movie(
            tmdb_id = tmdb_id, 
            imdb_id = imdb_id, 
            title = title, 
            overview = overview, 
            poster = poster, 
            youtube_id = youtube_id, 
            release_date = release_date, 
            genres = current_genres, 
            user_id = login_session['user_id'])
        # Insert into database
        session.add(newMovie)
        session.commit()
        flash('Movie "%s" added'%newMovie.title)
        return redirect('/')
    # GET request, render the page with form
    else:
        return render_template('new_movie.html', 
                               genres = genres, 
                               username = login_session['username'])


# Users can edit movies that are created by them
@app.route('/movie/<int:movie_id>/edit/', methods=['GET', 'POST'])
# Only users logged in can edit movies
@login_required
def editMovie(movie_id):
    movie = session.query(Movie).filter(Movie.id==movie_id).one()
    # Only the user who created this movie can edit it
    if movie.user_id != login_session['user_id']:
        flash('You can only edit your own movie')
        return redirect('/')
    # POST request, the user has submit the form
    if request.method == 'POST':
        # ============================================================
        # TODO
        # Database should not be modified unless form is valid
        # Server-side form validation will go here
        # ============================================================

        # Edit the movie with information from the form
        if request.form['title']: 
            movie.title = request.form['title']
        if request.form['tmdbID']:
            movie.tmdb_id = int(request.form['tmdbID'])
        if request.form['imdbID']:
            movie.imdb_id = request.form['imdbID']
        if request.form['overview']:
            movie.overview = request.form['overview']
        if request.form['poster']:
            movie.poster = request.form['poster']
        if request.form['youtubeID']:
            movie.youtube_id = request.form['youtubeID']
        if request.form['releaseDate']:
            try: 
                movie.release_date = datetime.strptime(
                                         request.form['releaseDate'], 
                                         '%Y-%m-%d')
            except:
                movie.release_date = None
        if request.form.getlist('genres'):
            movie.genres = (session.query(Genre)
                                   .filter(Genre.id.in_(
                                       request.form.getlist('genres')))
                                   .all())
        session.add(movie)
        flash('"%s" Successfully Edited' % movie.title)
        session.commit()
        return redirect('/')
    # GET request, render the edit form with movie information from database
    else:
        return render_template('edit_movie.html', 
                               movie = movie, 
                               genres = genres, 
                               username = login_session['username'])


# Will delete a movie. Only POST method is allowed
@app.route('/movie/<int:movie_id>/delete', methods=['POST'])
# Only users logged in can delete movies
@login_required
def deleteMovie(movie_id):
    movie = session.query(Movie).filter(Movie.id==movie_id).one()
    # Only the user who created this movie can delete it
    if movie.user_id != login_session['user_id']:
        response = make_response(
            json.dumps('You can only delete your own movie'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Only POST method is allowed
    if request.method == 'POST':
        session.delete(movie)
        flash('"%s" Successfully Deleted' % movie.title)
        session.commit()
        return 'Movie Deleted'


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    return newUser.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Connect with google account. Only POST method is allowed
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.to_json()
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = 'Login successful! Redirecting...'
    flash("Now logged in as %s" % login_session['username'])
    return output

# Disconnect with google account
@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    credentials = OAuth2Credentials.from_json(credentials)
    access_token = credentials.access_token
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] != '200':
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# Disconnect based on provider
@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['credentials']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showMovies'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showMovies'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
