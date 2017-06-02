# flask-jsonapi
[![Build Status](https://travis-ci.org/socialwifi/flask-jsonapi.svg?branch=master)](https://travis-ci.org/socialwifi/flask-jsonapi)
[![Latest Version](https://img.shields.io/pypi/v/flask-jsonapi.svg)](https://github.com/socialwifi/flask-jsonapi/blob/master/CHANGELOG.md)
[![Supported Python versions](https://img.shields.io/pypi/pyversions/flask-jsonapi.svg)](https://pypi.python.org/pypi/flask-jsonapi/)
[![Wheel Status](https://img.shields.io/pypi/wheel/flask-jsonapi.svg)](https://pypi.python.org/pypi/flask-jsonapi/)
[![License](https://img.shields.io/pypi/l/flask-jsonapi.svg)](https://github.com/socialwifi/flask-jsonapi/blob/master/LICENSE)

JSONAPI 1.0 server implementation for Flask.

## Installation

This package requires at least python 3.5. To install run `pip install flask-jsonapi`

## Application example

Run in python:

```
import collections

import flask
import marshmallow_jsonapi

import flask_jsonapi
from flask_jsonapi import exceptions

class ExampleSchema(marshmallow_jsonapi.Schema):
    id = marshmallow_jsonapi.fields.UUID()
    body = marshmallow_jsonapi.fields.Str()

    class Meta:
        type_ = 'example'
        strict = True

ExampleModel = collections.namedtuple('ExampleModel', 'id body')

repository = {
    'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4': ExampleModel(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a4', body='stop'),
    'f60717a3-7dc2-4f1a-bdf4-f2804c3127a5': ExampleModel(id='f60717a3-7dc2-4f1a-bdf4-f2804c3127a5', body='hammer'),
}

app = flask.Flask(__name__)

class ExampleListView(flask_jsonapi.ResourceList):
    schema = ExampleSchema

    def read_many(self, filters):
        return list(repository.values())

    def create(self, data):
        id = data.get('id') or str(uuid.uuid4())
        if id in repository:
            raise exceptions.JsonApiException
        obj = ExampleModel(id=id, body=data['body'])
        repository[id] = obj
        return obj

class ExampleDetailView(flask_jsonapi.ResourceDetail):
    schema = ExampleSchema

    def read(self, id):
        if id not in repository:
            raise exceptions.ObjectNotFound
        return repository[id]

    def update(self, id, data):
        if id != data.pop('id', id):
            raise exceptions.JsonApiException
        obj = repository[id]
        obj_dict = obj._asdict()
        obj_dict.update(data)
        repository[id] = ExampleModel(**obj_dict)

    def destroy(self, id):
        if id in repository:
            del repository[id]

application_api = flask_jsonapi.Api(app)
application_api.route(ExampleListView, 'example_list', '/examples/')
application_api.route(ExampleDetailView, 'example_detail', '/examples/<id>/')

app.run(host='127.0.0.1', port=5000)
```
And test it:
```
$ curl -H 'Content-Type: application/vnd.api+json' \
    http://localhost:5000/examples/ \
    --data '{"data": {"attributes": {"body": "time"}, "type": "example"}}' 2>/dev/null | python -m json.tool
{
    "data": {
        "attributes": {
            "body": "time"
        },
        "id": "77e23a62-7c49-4d0f-bb75-3ae5519226f5",
        "type": "example"
    },
    "jsonapi": {
        "version": "1.0"
    }
}
$ curl http://localhost:5000/examples/ 2>/dev/null|python -m json.tool
{
    "data": [
        {
            "attributes": {
                "body": "stop"
            },
            "id": "f60717a3-7dc2-4f1a-bdf4-f2804c3127a4",
            "type": "example"
        },
        {
            "attributes": {
                "body": "time"
            },
            "id": "77e23a62-7c49-4d0f-bb75-3ae5519226f5",
            "type": "example"
        },
        {
            "attributes": {
                "body": "hammer"
            },
            "id": "f60717a3-7dc2-4f1a-bdf4-f2804c3127a5",
            "type": "example"
        }
    ],
    "jsonapi": {
        "version": "1.0"
    },
    "meta": {
        "count": 3
    }
}
```
## Running tests

```
virtualenv -p python3.6 ~/flask-jsonapi-virtualenv
. ~/flask-jsonapi-virtualenv/bin/activate
pip install -r base_requirements.txt
pip install -U pytest==3.0.5
pytest
```

## Credits

Some parts of this project were written based on [Flask-REST-JSONAPI](https://github.com/miLibris/flask-rest-jsonapi).
