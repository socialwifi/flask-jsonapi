import collections
import json

import marshmallow_jsonapi
import pytest
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi import resource


@pytest.fixture
def test_client_with_example_model(app):
    class ExmapleSchema(marshmallow_jsonapi.Schema):
        id = fields.Str(dump_only=True, required=True)
        body = fields.Str()

        class Meta:
            type_ = 'example'
            self_view_many = 'example_list'
            self_view = 'example_detail'
            self_view_kwargs = {'example_id': '<id>'}
            strict = True

    ExampleModel = collections.namedtuple('ExampleModel', 'id body')

    class ExampleListView(resource.ResourceList):
        schema = ExmapleSchema

        def get_list(self):
            return [ExampleModel(id='1234', body='heheh'), ExampleModel(id='5678', body='hihi')]

    application_api = api.Api(app)
    application_api.route(ExampleListView, 'example_list', '/examples/')
    return app.test_client()


def test_integration(test_client_with_example_model):
    response = test_client_with_example_model.get(
        '/examples/',
        headers={'content-type': 'application/vnd.api+json'}
    )
    result = json.loads(response.data.decode())
    assert result == {
        'data': [
            {
                'id': '1234',
                'type': 'example',
                'attributes': {
                    'body': 'heheh'
                }
            }, {
                'id': '5678',
                'type': 'example',
                'attributes': {
                    'body': 'hihi'
                },
            }
        ],
        'jsonapi': {
            'version': '1.0'
        },
        'meta': {
            'count': 2
        }
    }
