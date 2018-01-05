Overview
++++++++

flask-jsonapi is a server implementation of JSON API 1.0 for Flask. It allows the rapid creation of API endpoints using this
format. Such endpoints can be then used by other services or single page applications based on Ember.js, React, Angular.js and alike.
In a need to write own backend client application e.g. microservices or just a client to external API please refer to
our client package `jsonapi-request <https://github.com/socialwifi/jsonapi-requests>`_

Features
--------

    - REST Server
    - Filters
    - Polymorphic
    - more .....

Architecture
------------

Picture to include

flask-jsonapi package is using:

    - Marshmallow Schema
    - Flask

Installation
------------

To install run::

    pip install flask-jsonapi

Short example
-------------

Example of simple server::

    import flask
    import sqlalchemy
    from sqlalchemy.orm import scoped_session
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.declarative import declarative_base
    from marshmallow_jsonapi import Schema, fields

    import flask_jsonapi
    from flask_jsonapi.resource_repositories import sqlalchemy_repositories

    db_engine = sqlalchemy.create_engine('sqlite:///:memory:')
    connection = db_engine.connect()
    session = scoped_session(sessionmaker(bind=db_engine))
    Base = declarative_base()
    Base.query = session.query_property()

    class Post(Base):
        __tablename__ = 'posts'
        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        title = sqlalchemy.Column(sqlalchemy.String)

    Base.metadata.create_all(db_engine)

    class PostRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Post
        instance_name = 'posts'
        session = session

    post_repository = PostRepository()
    post_repository.create({'id': 1, 'title': 'First post'})

    class PostSchema(Schema):
        id = fields.Int()
        title = fields.Str()

        class Meta:
            type_ = 'posts'
            strict = True

    class PostRepositoryViewSet(flask_jsonapi.resource_repository_views.ResourceRepositoryViewSet):
        schema = PostSchema
        repository = post_repository

    app = flask.Flask(__name__)
    api = flask_jsonapi.Api(app)
    api.repository(PostRepositoryViewSet(), 'posts', '/posts/')
    app.run(host='127.0.0.1', port=5000)

And test it::

    $ curl -H 'Content-Type: application/vnd.api+json' \
        -H 'Accept: application/vnd.api+json' \
        http://localhost:5000/posts/ \
        --data '{"data": {"attributes": {"title": "Second post"}, "type": "posts"}}' 2>/dev/null | python -m json.tool
    {
        "data": {
            "attributes": {
                "title": "Second post"
            },
            "id": 2,
            "type": "posts"
        },
        "jsonapi": {
            "version": "1.0"
        }
    }
    $ curl -H 'Accept: application/vnd.api+json' http://localhost:5000/posts/ 2>/dev/null | python -m json.tool
    {
        "data": [
            {
                "attributes": {
                    "title": "First post"
                },
                "id": 1,
                "type": "posts"
            },
            {
                "attributes": {
                    "title": "Second post"
                },
                "id": 2,
                "type": "posts"
            }
        ],
        "jsonapi": {
            "version": "1.0"
        },
        "meta": {
            "count": 2
        }
    }

