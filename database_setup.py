from datetime import datetime

from sqlalchemy import Column, Table, ForeignKey, Integer, String, Text, Date, DateTime
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

# Use association table to represent many-to-many relationship
# between Movie and Genre
movie_genre = Table(
    "movie_genre", 
    Base.metadata, 
    Column("movie_id", Integer, ForeignKey("movie.id")), 
    Column("genre_id", Integer, ForeignKey("genre.id")), 
)

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
    user = relationship("User")
    genres = relationship("Genre", backref="movies", secondary=movie_genre)
    create_time = Column(DateTime, default=datetime.utcnow)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id': self.id,
           'tmdb_id': self.tmdb_id, 
           'imdb_id': self.imdb_id, 
           'title': self.title, 
           'poster': self.poster, 
           'youtube_id': self.youtube_id, 
           'overview': self.overview, 
           'release_date': str(self.release_date), 
           'genres': [e.genre for e in self.genres]
       }

class Genre(Base):
    __tablename__ = 'genre'

    id = Column(Integer, primary_key=True)
    genre = Column(String(255), nullable=False)

engine = create_engine('sqlite:///moviecollection.db')
Base.metadata.create_all(engine)
