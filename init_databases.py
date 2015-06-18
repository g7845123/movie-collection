from datetime import datetime
import time
import requests

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Base, User, Movie, Genre, MovieGenre

engine = create_engine('sqlite:///moviecollection.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()

# Init Genre
print 'Feching genre list from tmdb.org'
params = {'api_key': '407133ea196ce7efa62e2619d865e21b'}
r = requests.get("http://api.themoviedb.org/3/genre/movie/list", 
        params=params)
if r.status_code != requests.codes.ok:
    raise ValueError('Error fetching genre list from tmdb.org')
genres = r.json()['genres']
for genre in genres:
    genre_new = Genre(id=genre['id'], genre=genre['name'])
    session.add(genre_new)
session.commit()

# Create dummy user
print 'Adding dummy user to database'
user1 = User(name="user1", email="user1@user1.com",
             picture='blank_user.gif')
session.add(user1)
session.commit()

# Fetch popular movie list from tmdb.org
print 'Adding popular movies from tmdb.org'
params = {'api_key': '407133ea196ce7efa62e2619d865e21b'}
r = requests.get("http://api.themoviedb.org/3/movie/popular", 
        params=params)
if r.status_code != requests.codes.ok:
    raise ValueError('Error fetching popular movies from tmdb.org')
movies = r.json()['results'][::-1]
# Iterate through all movies. And fetch movie detail from themoviedb.org
for idx, movie in enumerate(movies):
    # Wait due to request limit of themoviedb.org
    if idx%30 == 29:
        print 'Cooling down for tmdb api'
        time.sleep(30)
    tmdb_id = movie['id']
    title = movie['original_title']
    print 'Fetching movie "%s" from tmdb'%title
    params = {'api_key': '407133ea196ce7efa62e2619d865e21b', 
              'append_to_response': 'videos'}
    r = requests.get("http://api.themoviedb.org/3/movie/%s"%tmdb_id, 
            params=params)
    if r.status_code != requests.codes.ok:
        raise ValueError('Error fetching movie detail from tmdb.org')
    movie_detail = r.json()
    poster_path = movie_detail['poster_path']
    if poster_path:
        poster = 'https://image.tmdb.org/t/p/w185' + poster_path
    else:
        poster = 'http://placehold.it/185x278'
    trailers = movie_detail['videos']['results']
    youtube_id = None
    for trailer in trailers: 
        if trailer['site']=='YouTube':
            youtube_id = trailer['key']
            break
    release_date = movie_detail.get('release_date')
    if release_date:
        release_date = datetime.strptime(release_date, '%Y-%m-%d')
    movie_new = Movie(
        tmdb_id = movie_detail['id'], 
        imdb_id = movie_detail.get('imdb_id'), 
        title = movie_detail['original_title'], 
        poster = poster, 
        youtube_id = youtube_id, 
        overview = movie_detail.get('overview'), 
        release_date = release_date, 
        user = user1)
    session.add(movie_new)
    genres = movie_detail['genres']
    for genre in genres:
        moviegenre_new = MovieGenre(movie=movie_new, genre_id=genre['id'])
        session.add(moviegenre_new)
    session.commit()

print "Data added"
