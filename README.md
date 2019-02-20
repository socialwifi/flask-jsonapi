# Flask-jsonapi
[![Build Status](https://travis-ci.org/socialwifi/flask-jsonapi.svg?branch=master)](https://travis-ci.org/socialwifi/flask-jsonapi)
[![Documentation Status](https://readthedocs.org/projects/flask-jsonapi/badge/?version=latest)](http://flask-jsonapi.readthedocs.io/en/latest/?badge=latest)
[![Coverage Status](https://coveralls.io/repos/github/socialwifi/flask-jsonapi/badge.svg)](https://coveralls.io/github/socialwifi/flask-jsonapi)
[![Latest Version](https://img.shields.io/pypi/v/flask-jsonapi.svg)](https://pypi.python.org/pypi/flask-jsonapi/)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/flask-jsonapi.svg)](https://pypi.python.org/pypi/flask-jsonapi/)
[![Wheel Status](https://img.shields.io/pypi/wheel/flask-jsonapi.svg)](https://pypi.python.org/pypi/flask-jsonapi/)
[![License](https://img.shields.io/pypi/l/flask-jsonapi.svg)](https://github.com/socialwifi/flask-jsonapi/blob/master/LICENSE)

JSONAPI 1.0 server implementation for Flask.

## Installation

This package requires at least python 3.7. To install run: `pip install flask-jsonapi`. You can install SQLAlchemy support
with: `pip install flask-jsonapi[sqlalchemy]`.

## Documentation

Full documentation is available at: https://flask-jsonapi.readthedocs.io/.

## Simple example

Let’s create a working example of a minimal Flask application. It will expose a single resource `Article` as a REST 
endpoint with fetch/create/update/delete operations. For persistence layer, it will use an in-memory SQLite database 
with SQLAlchemy for storage.

### Configuration

```python
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
```

### Usage

Create a new `Article` with title “First article”:
```bash
curl -H 'Content-Type: application/vnd.api+json' \
    -H 'Accept: application/vnd.api+json' \
    http://localhost:5000/articles/ \
    --data '{"data": {"attributes": {"title": "First article"}, "type": "articles"}}' \
    2>/dev/null | python -m json.tool
```

Result:
```json
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
```

Get the list of `Articles`:
```bash
curl -H 'Accept: application/vnd.api+json' \
    http://localhost:5000/articles/ \
    2>/dev/null | python -m json.tool
```

Result:
```json
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
```

## Running tests

```bash
virtualenv -p python3.7 ~/flask-jsonapi-virtualenv
. ~/flask-jsonapi-virtualenv/bin/activate
pip install -r base_requirements.txt
pip install -U pytest==3.0.5
pytest
```

## Credits

Some parts of this project were written based on [Flask-REST-JSONAPI](https://github.com/miLibris/flask-rest-jsonapi).
