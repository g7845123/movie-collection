from flask import Flask, render_template, request, redirect, jsonify, url_for, flash
from werkzeug.contrib.atom import AtomFeed
from flask import session as login_session
from flask import make_response
import json

from sqlalchemy import create_engine, desc, func
from sqlalchemy.orm import sessionmaker
from database_setup import Base, User, Movie, Genre, MovieGenre

import requests
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2

from datetime import datetime

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

# Connect to Database and create database session
engine = create_engine('sqlite:///moviecollection.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

# genres will be used to create left-side nav bar
genres = session.query(Genre)

# Generate nonce to prevent CSRF
def stateGenerator():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return state

# Show all movies ordered by their created time
@app.route('/')
@app.route('/movies/')
def showMovies():
    movies = session.query(Movie).order_by(desc(Movie.create_time)).all()
    # Login button will be available if user is not logged in
    if 'username' not in login_session:
        # Generate nonce for login functionality
        state = stateGenerator()
        return render_template('public_movies.html', 
                               movies = movies, 
                               genres = genres, 
                               current_genre = 'Recently Added', 
                               CLIENT_ID = CLIENT_ID, 
                               state = state)
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
    results = []
    movies = session.query(Movie).order_by(desc(Movie.create_time)).all()
    for movie in movies:
        # genre information is not part of Movie class, but stored in MovieGenre
        # Thus join is necessary to get genres of a movie
        current_genres = (session.query(Genre)
                                 .join(MovieGenre, MovieGenre.genre_id==Genre.id)
                                 .filter(MovieGenre.movie_id==movie.id)
                                 .all())
        current_genres = [e.genre for e in current_genres]
        result = {
            'id': movie.id, 
            'tmdb_id': movie.tmdb_id, 
            'imdb_id': movie.imdb_id, 
            'title': movie.title, 
            'poster': movie.poster, 
            'youtube_id': movie.youtube_id, 
            'overview': movie.overview, 
            'release_date': str(movie.release_date), 
            'genres': current_genres
        }
        results.append(result)
    return jsonify(movies = results)


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
        # genre information is not part of Movie class, but stored in MovieGenre
        # Thus join is necessary to get genres of a movie
        current_genres = (session.query(Genre)
                                 .join(MovieGenre, MovieGenre.genre_id==Genre.id)
                                 .filter(MovieGenre.movie_id==movie.id)
                                 .all())
        current_genres = [e.genre for e in current_genres]
        content = render_template('movie_entry.atom', movie=movie, current_genres=current_genres)
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
    # genre information is not part of Movie class, but stored in MovieGenre
    # Thus join is necessary to get movies of a specific genre
    movies = (session.query(Movie)
                     .join(MovieGenre, Movie.id==MovieGenre.movie_id)
                     .filter(MovieGenre.genre_id==genre_id)
                     .order_by(desc(Movie.create_time))
                     .all())
    current_genre = session.query(Genre).filter(Genre.id==genre_id).one().genre
    # Login button will be available if user is not logged in
    if 'username' not in login_session:
        # Generate nonce for login functionality
        state = stateGenerator()
        return render_template('public_movies.html', 
                               movies = movies, 
                               genres = genres, 
                               current_genre = current_genre, 
                               CLIENT_ID = CLIENT_ID, 
                               state = state)
    # User logged in will be able to add new movies
    else:
        return render_template('movies.html', 
                               movies = movies, 
                               genres = genres, 
                               current_genre = current_genre, 
                               username = login_session['username'])


# Show details of a specific movie
@app.route('/movie/<int:movie_id>/')
def showMovieDetail(movie_id):
    movie = session.query(Movie).filter(Movie.id==movie_id).one()
    creator = getUserInfo(movie.user_id)
    # genre information is not part of Movie class, but stored in MovieGenre
    # Thus join is necessary to get genres of a specific movie
    current_genres = (session.query(Genre)
                             .join(MovieGenre, Genre.id==MovieGenre.genre_id)
                             .filter(MovieGenre.movie_id==movie.id)
                             .all())
    # Login button will be available if user is not logged in
    if 'username' not in login_session:
        # Generate nonce for login functionality
        state = stateGenerator()
        return render_template('public_movie_detail.html', 
                               movie = movie, 
                               genres = genres, 
                               creator = creator, 
                               current_genres = current_genres, 
                               CLIENT_ID = CLIENT_ID, 
                               state = state)
    # If the user is also the creator, he can edit and delete this movie
    elif creator.id == login_session['user_id']:
        # Generate nonce for deletion functionality
        state = stateGenerator()
        return render_template('movie_detail.html', 
                               movie = movie, 
                               genres = genres, 
                               creator = creator, 
                               current_genres = current_genres, 
                               username = login_session['username'], 
                               show_edit_btn = True, 
                               state = state)
    # If the user is not the creator, he can not edit or delete this movie
    else:
        return render_template('movie_detail.html', 
                               movie = movie, 
                               genres = genres, 
                               creator = creator, 
                               current_genres = current_genres, 
                               username = login_session['username'], 
                               show_edit_btn = False)


# Users logged in can create a new movie
@app.route('/movie/new/', methods=['GET', 'POST'])
def addMovie():
    # Only users logged in can add new movie
    if 'username' not in login_session:
        flash('To add a new movie, please login')
        return redirect('/')
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
        # Server-side form validation should go here
        # Will be added in the future

        # New movie entry with information from the form
        newMovie = Movie(
            tmdb_id = tmdb_id, 
            imdb_id = imdb_id, 
            title = title, 
            overview = overview, 
            poster = poster, 
            youtube_id = youtube_id, 
            release_date = release_date, 
            user_id = login_session['user_id'])
        # Insert into database
        session.add(newMovie)
        session.commit()
        # genre information is not part of Movie class, but stored in MovieGenre
        # Thus entries describing genres of the movie should also be added
        for genre_id in genre_ids:
            genre_id = int(genre_id)
            newMovieGenre = MovieGenre(movie_id=newMovie.id, genre_id=genre_id)
            session.add(newMovieGenre)
        session.commit()
        return redirect('/')
    # GET request, render the page with form
    else:
        return render_template('new_movie.html', 
                               genres = genres, 
                               username = login_session['username'])


# Users can edit movies that are created by them
@app.route('/movie/<int:movie_id>/edit/', methods=['GET', 'POST'])
def editMovie(movie_id):
    movie = session.query(Movie).filter(Movie.id==movie_id).one()
    # genre information is not part of Movie class, but stored in MovieGenre
    # Thus join is necessary to get genres of a movie
    current_genres = (session.query(Genre)
                             .join(MovieGenre, Genre.id==MovieGenre.genre_id)
                             .filter(MovieGenre.movie_id==movie.id)
                             .all())
    current_genre_ids = [e.id for e in current_genres]
    # Only users logged in can edit movies
    if 'username' not in login_session:
        flash('To edit an existing movie, please login')
        return redirect('/')
    # Only the user who created this movie can edit it
    if movie.user_id != login_session['user_id']:
        flash('You can only edit your own movie')
        return redirect('/')
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
        release_date = datetime.strptime(release_date, '%Y-%m-%d') if release_date else None
        # Server-side form validation should go here
        # Will be added in the future

        # Edit the movie with information from the form
        if title: 
            movie.title = title
        if tmdb_id:
            movie.tmdb_id = tmdb_id
        if imdb_id:
            movie.imdb_id = imdb_id
        if overview:
            movie.overview = overview
        if poster:
            movie.poster = poster
        if youtube_id:
            movie.youtube_id = youtube_id
        if release_date:
            movie.release_date = release_date
        session.add(movie)
        # Edit genre entries of this movie is a bit tricky by first deleting 
        # genre info and then re-add new genre entries
        session.query(MovieGenre).filter(MovieGenre.movie_id==movie.id).delete()
        for genre_id in genre_ids:
            genre_id = int(genre_id)
            genre = MovieGenre(movie_id=movie.id, genre_id=genre_id)
            session.add(genre)
        flash('"%s" Successfully Edited' % movie.title)
        session.commit()
        return redirect('/')
    # GET request, render the edit form with movie information from database
    else:
        return render_template('edit_movie.html', 
                               movie = movie, 
                               genres = genres, 
                               current_genre_ids = current_genre_ids, 
                               username = login_session['username'])


# Will delete a movie. Only POST method is allowed
@app.route('/movie/<int:movie_id>/delete', methods=['POST'])
def deleteMovie(movie_id):
    movie = session.query(Movie).filter(Movie.id==movie_id).one()
    # Only users logged in can delete movies
    if 'username' not in login_session:
        response = make_response(
            json.dumps('To delete an existing movie, please login'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Only the user who created this movie can delete it
    if movie.user_id != login_session['user_id']:
        response = make_response(
            json.dumps('You can only delete your own movie'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Only POST method is allowed
    if request.method == 'POST':
        state = request.data
        # Validate nonce to prevent CSRF
        if state != login_session['state']:
            response = make_response(json.dumps('Nonces did not match'), 401)
            response.headers['Content-Type'] = 'application/json'
            return response
        session.delete(movie)
        # genre information is not part of Movie class, but stored in MovieGenre
        # Thus entries describing genres of the movie should also be deleted
        session.query(MovieGenre).filter(MovieGenre.movie_id==movie_id).delete()
        flash('"%s" Successfully Deleted' % movie.title)
        session.commit()
        return 'Movie Deleted'


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


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
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
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
    login_session['credentials'] = credentials
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
