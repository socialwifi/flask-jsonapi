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
```

`allowed_actions` lists what the endpoint serves; a ViewSet that does not declare it serves nothing. A ViewSet can
also declare `guards` (request checks such as authentication), `object_permissions` (row-level permissions, for
example a `flask_jsonapi.permissions.CheckObjectPermission`) and `middlewares` around its `data_service`. The data
service has one method per action: `create`, `read`, `list`, `update` and `destroy`. `list` returns a
`flask_jsonapi.data_services.ListResult` with the items and, when the client asks for a page, their total.
The [documentation](https://flask-jsonapi.readthedocs.io/) describes every layer, and the
[guide](https://flask-jsonapi.readthedocs.io/en/latest/guide.html) shows how to add authentication, permissions and
business logic, and builds a complete application.

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
