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
* **filtering** - helps with adding filters to views (including helpers for SQLAlchemy), the format is compatible with `recommendations <http://jsonapi.org/recommendations/#filtering>`__
* **sorting** [`specification <http://jsonapi.org/format/#fetching-sorting>`__]
* **pagination** [`specification <http://jsonapi.org/format/#fetching-pagination>`__]
* **sparse fieldsets** [`specification <http://jsonapi.org/format/#fetching-sparse-fieldsets>`__]
* **links** [`specification <http://jsonapi.org/format/#document-links>`__] - resolved by marshmallow-jsonapi (`docs <https://marshmallow-jsonapi.readthedocs.io/en/latest/quickstart.html#flask-integration>`__)
* **error objects** [`specification <http://jsonapi.org/format/#errors>`__]
* **allowed actions** - a ViewSet declares which actions it serves, see :doc:`view_sets`
* **resource-level permissions** - guards run before the request body is parsed, see :doc:`layers`
* **business logic** - middlewares wrap the data service, see :doc:`layers`
* **object-level permissions** - the ``object_permissions`` of a ViewSet check every call to the data service,
  see :doc:`layers`

Not implemented yet:

* **fetching relationships** [`specification <http://jsonapi.org/format/#fetching-relationships>`__] and **updating relationships** [`specification <http://jsonapi.org/format/#crud-updating-relationships>`__] - `#27 <https://github.com/socialwifi/flask-jsonapi/pull/27>`__


Architecture
------------

Flow through layers beginning with an HTTP Request and ending with an HTTP Response::

    [HTTP Request] -> [Flask Routing] -> View -> Allowed actions -> Guards
        -> Object permissions -> Middlewares -> Data service -> Storage

    [HTTP Response] <- View <- Object permissions <- Middlewares <- Data service <- Storage

The View parses the request and dumps the response with the Schema.

Every layer is described in :doc:`layers`. ``ResourceRepositoryViewSet`` and ``ProtectedViewSet`` are deprecated
since 1.5.0, see :doc:`migration`.

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
    from flask_jsonapi.data_services import sqlalchemy_repositories

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
        session = session

    class ArticleSchema(Schema):
        id = fields.Int()
        title = fields.Str()

        class Meta:
            type_ = 'articles'

    class ArticleViewSet(flask_jsonapi.ViewSet):
        schema_class = ArticleSchema
        data_service = ArticleRepository()
        allowed_actions = {
            flask_jsonapi.Actions.create,
            flask_jsonapi.Actions.read,
            flask_jsonapi.Actions.list,
            flask_jsonapi.Actions.update,
            flask_jsonapi.Actions.destroy,
        }

    app = flask.Flask(__name__)
    api = flask_jsonapi.Api(app)
    api.repository(ArticleViewSet(), 'articles', '/articles/')
    app.run(host='127.0.0.1', port=5000)

``allowed_actions`` lists what the endpoint serves; a ViewSet that does not declare it serves nothing.
Guards, object permissions, middlewares and data services are described in :doc:`layers`.

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
   guide
   tutorial
   view_sets
   views
   layers
   migration
   repositories
   including_relationships
   sparse_fieldsets
   filtering
   sorting
   pagination
   extensions
