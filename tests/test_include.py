import collections
import http
import json
import uuid
from unittest import mock

import marshmallow_jsonapi
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi import resource_repositories

JSONAPI_HEADERS = {'content-type': 'application/vnd.api+json', 'accept': 'application/vnd.api+json'}


class ChildSchema(marshmallow_jsonapi.Schema):
    id = fields.UUID(required=True)
    name = fields.Str()

    class Meta:
        type_ = 'childs'
        strict = True


class ParentSchema(marshmallow_jsonapi.Schema):
    id = fields.UUID(required=True)
    name = fields.Str()
    children = fields.Relationship(schema=ChildSchema, type_='childs', many=True)

    class Meta:
        type_ = 'parents'
        include_resource_linkage = True
        strict = True


ParentModel = collections.namedtuple('ParentModel', 'id name children')
ChildModel = collections.namedtuple('ChildModel', 'id name')


class ParentDetailRepository:
    def get_detail(self, id):
        return ParentModel(
            id=id, name='Adam',
            children=[
                ChildModel(id=uuid.uuid4(), name='Cain'),
                ChildModel(id=uuid.uuid4(), name='Abel'),
            ]
        )


class ParentResourceRepositoryViewSet(resource_repositories.ResourceRepositoryViewSet):
    schema = ParentSchema
    repository = ParentDetailRepository()


def test_get_parent_detail_with_include_data(app):
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')
    response = app.test_client().get(
        '/parents/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/?include=children',
        headers=JSONAPI_HEADERS
    )
    result = json.loads(response.data.decode('utf-8'))
    result['included'].sort(key=lambda x: x['attributes']['name'])
    expected = {
       'data': {
          'attributes': {
             'name': 'Adam'
          },
          'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
          'relationships': {
             'children': {
                'data': [
                   {
                      'id': mock.ANY,
                      'type': 'childs'
                   },
                   {
                      'id': mock.ANY,
                      'type': 'childs'
                   }
                ]
             }
          },
          'type': 'parents'
       },
       'included': [
           {
               'attributes': {
                   'name': 'Abel'
               },
               'id': mock.ANY,
               'type': 'childs'
           },
           {
               'attributes': {
                   'name': 'Cain'
               },
               'id': mock.ANY,
               'type': 'childs'
           },
       ],
       'jsonapi': {
          'version': '1.0'
       }
    }
    assert expected == result


def test_get_parent_detail_without_include_data(app):
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')
    response = app.test_client().get(
        '/parents/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/',
        headers=JSONAPI_HEADERS
    )
    result = json.loads(response.data.decode())
    expected = {
        'data': {
            'type': 'parents',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'attributes': {
                'name': 'Adam'
            }
        },
        'jsonapi': {
            'version': '1.0'
        }
    }
    assert expected == result


def test_invalid_include_parameter_response(app):
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')
    response = app.test_client().get(
        '/parents/f60717a3-7dc2-4f1a-bdf4-f2804c3127a4/?include=children.children',
        headers=JSONAPI_HEADERS
    )
    assert response.status_code == http.HTTPStatus.BAD_REQUEST
