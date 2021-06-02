Flask-jsonapi
=============

.. module:: overview

JSONAPI 1.0 server implementation for Flask.

Flask-jsonapi is a server implementation of `JSON API 1.0 <http://jsonapi.org>`__ specification
for `Flask <http://flask.pocoo.org/>`_.
It allows for rapid creation of CRUD JSON API endpoints. Those endpoints can be used by JSON API clients, eg.
JavaScript frontend applications written in Ember.js, React, Angular.js etc.

A compatible Python client can be found in the following package:
`jsonapi-request <https://github.com/socialwifi/jsonapi-requests>`__.

Flask-jsonapi depends on the following external libraries:

* `Flask <http://flask.pocoo.org/docs/>`__ (micro web framework)
* `marshmallow-jsonapi <https://marshmallow-jsonapi.readthedocs.io>`__ (serialization, deserialization, validation with JSON API format)
* `SQLAlchemy <https://docs.sqlalchemy.org/>`__ (SQL ORM)

Features
--------

Flask-jsonapi implements the following parts of the JSON API specification:

* **fetching resources** [`specification <http://jsonapi.org/format/#fetching-resources>`__]
* **creating, updating and deleting resources** [`specification <http://jsonapi.org/format/#crud>`__]
* **inclusion of related resources** [`specification <http://jsonapi.org/format/#fetching-includes>`__]
* **filtering** - helps with adding filters to views (helpers for SQLAlchemy - in development), the format is compatible with `recommendations <http://jsonapi.org/recommendations/#filtering>`__
* **pagination** [`specification <http://jsonapi.org/format/#fetching-pagination>`__]
* **links** [`specification <http://jsonapi.org/format/#document-links>`__] - resolved by marshmallow-jsonapi (`docs <https://marshmallow-jsonapi.readthedocs.io/en/latest/quickstart.html#flask-integration>`__)
* **error objects** [`specification <http://jsonapi.org/format/#errors>`__]
* **resource-level permissions** - view-level decorators support in ViewSets

Flask-jsonapi implements two extensions of the JSON API specification:

* **creating resources with relationships in one request** - server implementation compatible with `ember-data-save-relationships <https://emberigniter.com/saving-models-relationships-json-api/>`__
* **polymorphic relationships** - as defined in `ember-data <https://guides.emberjs.com/v2.18.0/models/relationships/#toc_polymorphism>`__

Not implemented yet:

* **fetching relationships** [`specification <http://jsonapi.org/format/#fetching-relationships>`__] and **updating relationships** [`specification <http://jsonapi.org/format/#crud-updating-relationships>`__] - in development
* **object-level permissions** - in development
* **sparse fieldsets** [`specification <http://jsonapi.org/format/#fetching-sparse-fieldsets>`__]
* **sorting** [`specification <http://jsonapi.org/format/#fetching-sorting>`__]


Architecture
------------

Flow through layers beginning with an HTTP Request and ending with an HTTP Response::

                                                   Schema
                                                     🡙
    [HTTP Request] -> [Flask Routing] -> ViewSet -> View -> Repository -> (         )
                                                                          ( Storage )
                                 [HTTP Response] <- View <- Repository <- (         )
                                                     🡙
                                                   Schema

Installation
------------

To install (with SQLAlchemy support) run:

.. code-block:: bash

    pip install Flask-jsonapi[sqlalchemy]

Simple example
--------------

Let's create a working example of a minimal Flask application. It will expose a single resource ``Article`` as
a REST endpoint with fetch/create/update/delete operations. For persistence layer, it will use an in-memory SQLite
database with SQLAlchemy for storage.

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

    db_engine = sqlalchemy.create_engine('sqlite:///')
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

    curl -H 'Content-Type: application/vnd.api+json' \
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

    curl -H 'Accept: application/vnd.api+json' \
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

Table of Contents
=================

.. toctree::
   :maxdepth: 3

   Overview<self>
   tutorial
   view_sets
   views
   repositories
   including_relationships
   sparse_fieldsets
   filtering
   sorting
   pagination
   extensions
