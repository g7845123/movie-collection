# Overview

This is a project for [Full Stack Web Developer Nanodegree](https://www.udacity.com/course/nd004) provided by [Udacity](https://www.udacity.com). 

In this project, I developed a website named "Movie Collection" essentially from scratch, with no templates provided. This site provides a list of movies as well as a variety of movie genres and integrate third party user registration and authentication. Authenticated users will have the ability to post, edit, and delete their own movies.

In addition to the basic requirements, I implememted several extra features:

* Form autofill functionality using Ajax request to themoviedb.org facilitates the adding of a new movie
* XML and Atom API endpoints are implemented apart from JSON
* CSRF token are included for all POST requests
* Most of the pages are responsive and compatible to devices of different screen size

# Live demo

Live demo is available [here](http://cheng-lab.tk:50002/)

# Package Dependency

The following script may help you configure your environment

```sh
$ apt-get -qqy install python-sqlalchemy
$ apt-get -qqy install python-pip
$ pip install werkzeug==0.8.3
$ pip install flask==0.9
$ pip install oauth2client
$ pip install requests
$ pip install httplib2
$ pip install dict2xml
$ pip install flask-seasurf
```

Please note: Other package version, e.g. higher flask version, should also work, though not tested

# Usage

1. Install [Vagrant](http://vagrantup.com) and [VirtualBox](https://www.virtualbox.org)
1. Download the source code and unzip it
1. Launch the Vagrant VM and log in

    ```sh
    $ vagrant up
    $ vagrant ssh
    $ cd path/to/project/folder
    ```
1. Configure Vagrant. See 'Dependency' part for detail
1. Initialize database

    ```sh
    $ python database_setup.py
    ```
1. Fill database with popular movies in themoviedb.org

    ```sh
    $ python init_databases.py
    ```
1. Setup the server

    ```sh
    $ python moviecollection.py
    ```
1. Open http://localhost:5000/ in browser

# API Endpoints

* JSON: /movies/JSON
* XML:  /movies/XML
* Atom: /movies/ATOM

# References

All Web sites, books, forums, blog posts, github repositories etc. that I referred to or used are listed in "references.txt". 
