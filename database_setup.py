from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, Text, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
 
Base = declarative_base()

class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    picture = Column(String(255))

class Movie(Base):
    __tablename__ = 'movie'
   
    id = Column(Integer, primary_key=True)
    tmdb_id = Column(Integer)
    imdb_id = Column(String(255))
    title = Column(String(255), nullable=False)
    poster = Column(String(255))
    youtube_id = Column(String(255))
    overview = Column(Text)
    release_date = Column(Date)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    create_time = Column(DateTime, default=datetime.utcnow)

class Genre(Base):
    __tablename__ = 'genre'

    id = Column(Integer, primary_key=True)
    genre = Column(String(255), nullable=False)

# Movie and Genre are many to many relationship
# Thus genre information is not part of Movie class, but stored in MovieGenre
class MovieGenre(Base):
    __tablename__ = 'movie_genre'

    movie_id = Column(Integer, ForeignKey('movie.id'), primary_key=True)
    movie = relationship(Movie)
    genre_id = Column(Integer, ForeignKey('genre.id'), primary_key=True)
    genre = relationship(Genre)

engine = create_engine('sqlite:///moviecollection.db')
Base.metadata.create_all(engine)
