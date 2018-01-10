Overview
========

flask-jsonapi is a server implementation of `JSON API 1.0 <http://jsonapi.org>`_ specification
for `Flask <http://flask.pocoo.org/>`_.
It allows for rapid creation of CRUD JSON API endpoints. Such endpoints can be used by other compatible clients
like JavaScript frontend applications written in Ember.js, React, Angular.js and alike.

A compatible Python client can be found in the following package:
`jsonapi-request <https://github.com/socialwifi/jsonapi-requests>`_.

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

To install run:

.. code-block:: bash

    pip install flask-jsonapi[sqlalchemy]

Short example
-------------

Let's create a minimal example exposing a single resource ``Article`` as a REST endpoint with CRUD operations.
We'll use an in-memory SQLite database with SQLAlchemy for storage.

Configuration
~~~~~~~~~~~~~

.. code-block:: python

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

    class Article(Base):
        __tablename__ = 'articles'
        id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
        title = sqlalchemy.Column(sqlalchemy.String)

    Base.metadata.create_all(db_engine)

    class ArticleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Article
        instance_name = 'articles'
        session = session

    class ArticleSchema(Schema):
        id = fields.Int()
        title = fields.Str()

        class Meta:
            type_ = 'articles'
            strict = True

    class ArticleRepositoryViewSet(flask_jsonapi.resource_repository_views.ResourceRepositoryViewSet):
        schema = ArticleSchema
        repository = ArticleRepository()

    app = flask.Flask(__name__)
    api = flask_jsonapi.Api(app)
    api.repository(ArticleRepositoryViewSet(), 'articles', '/articles/')
    app.run(host='127.0.0.1', port=5000)

Usage
~~~~~

Create a new ``Article`` with title "First article":

.. code-block:: bash

    $ curl -H 'Content-Type: application/vnd.api+json' \
        -H 'Accept: application/vnd.api+json' \
        http://localhost:5000/articles/ \
        --data '{"data": {"attributes": {"title": "First article"}, "type": "articles"}}' \
        2>/dev/null | python -m json.tool

Result:

.. code-block:: json

    {
        "data": {
            "type": "articles",
            "id": 1,
            "attributes": {
                "title": "First article"
            }
        },
        "jsonapi": {
            "version": "1.0"
        }
    }

Get the list of ``Articles``:

.. code-block:: bash

    $ curl -H 'Accept: application/vnd.api+json' \
        http://localhost:5000/articles/ \
        2>/dev/null | python -m json.tool

Result:

.. code-block:: json

    {
        "data": [
            {
                "type": "articles",
                "id": 1,
                "attributes": {
                    "title": "First article"
                }
            }
        ],
        "jsonapi": {
            "version": "1.0"
        },
        "meta": {
            "count": 1
        }
    }
