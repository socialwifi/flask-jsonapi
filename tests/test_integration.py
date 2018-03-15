import json

from marshmallow_jsonapi import Schema
from marshmallow_jsonapi import fields

from flask_jsonapi import api
from flask_jsonapi.resource_repositories import repositories
from flask_jsonapi.marshmallow_nested_extension.field import CompleteNestedRelationship
from flask_jsonapi.marshmallow_nested_extension.schema import IdMappingSchema
from flask_jsonapi.nested import nested_resource_repositories
from flask_jsonapi.nested.nested_repository import ChildRepository

JSONAPI_HEADERS = {'content-type': 'application/vnd.api+json', 'accept': 'application/vnd.api+json'}


class DescendantSchema(IdMappingSchema, Schema):
    id = fields.Str(required=False)
    name = fields.Str(required=False)

    class Meta:
        type_ = 'descendant'
        self_view_many = 'descendant_list'
        self_view = 'descendant_detail'
        self_view_kwargs = {'descendant_id': '<id>'}
        strict = True


class ParentSchema(Schema):
    id = fields.Str(required=True)

    class Meta:
        type_ = 'parent'
        self_view_many = 'parent_list'
        self_view = 'parent_detail'
        self_view_kwargs = {'parent_id': '<id>'}
        strict = True


class ParentSchemaAtomic(IdMappingSchema, ParentSchema):
    descendant = CompleteNestedRelationship(
        schema=DescendantSchema,
        attribute='descendant',
        many=True, include_resource_linkage=True,
        type_='descendant'
    )


class DescendantModel:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.name = kwargs['name']
        self.parent_id = kwargs['parent_id']


class ParentModel:
    def __init__(self, **kwargs):
        self.id = kwargs['id']
        self.descendant = kwargs.get('descendant', [])


database_simulation = {}


class DescendantRepository(repositories.ResourceRepository):
    def create(self, data, **kwargs):
        data['id'] = "n3w-ch1ld-3d"
        descendant = DescendantModel(**data)
        self._add_descendant_object_to_parent(data, descendant)
        return descendant

    def update(self, data, **kwargs):
        parent = database_simulation[data['parent_id']]
        current_descedants = getattr(parent, 'descendant')
        for descendant in current_descedants:
            if descendant.id == data['id']:
                current_descedants.remove(descendant)
        updated_descendant = DescendantModel(**data)
        current_descedants.append(updated_descendant)
        setattr(parent, 'descendant', current_descedants)
        return updated_descendant

    def delete(self, id):
        for parent in database_simulation.values():
            parent.descendant = [descendant for descendant in parent.descendant if descendant.id != id]

    def _add_descendant_object_to_parent(self, data, descendant):
        parent = database_simulation[data['parent_id']]
        current_descedants = getattr(parent, 'descendant')
        current_descedants.append(descendant)
        setattr(parent, 'descendant', current_descedants)


class ParentRepository(repositories.ResourceRepository):
    children_repositories = {
        'descendant': ChildRepository(
            repository=DescendantRepository(),
            foreign_parent_name='parent_id'
        )
    }

    def create(self, data, **kwargs):
        obj = ParentModel(**data)
        database_simulation[data['id']] = obj
        return obj

    def update(self, data, **kwargs):
        if data['id'] in database_simulation:
            return database_simulation[data['id']]
        else:
            return self.create(data, **kwargs)

    def get_list(self, filters=None):
        return database_simulation.values()


class ParentResourceRepositoryViewSet(nested_resource_repositories.NestedResourceRepositoryViewSet):
    schema = ParentSchema
    nested_schema = ParentSchemaAtomic

    def __init__(self):
        super().__init__(repository=ParentRepository())


def test_integration_create_nested_resource(app):
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')

    json_data = json.dumps({
        'data': {
            'type': 'parent',
            'id': 'f60717a3-7dc2-4f1a-bdf4-f2804c3127a4',
            'relationships': {
                'descendant': {
                    'data': [
                        {
                            'type': 'descendant',
                            'attributes': {
                                'name': 'Olga',
                                '__id__': '_tem_id_3344'
                            },
                        },
                    ]
                }
            }
        }
    })
    response = app.test_client().post(
        '/parents/',
        headers=JSONAPI_HEADERS,
        data=json_data,
    )
    result = json.loads(response.data.decode('utf-8'))
    expected = {
        "data": {
            "id": "f60717a3-7dc2-4f1a-bdf4-f2804c3127a4",
            "type": "parent",
            "relationships": {
                "descendant": {
                    "data":
                        [
                            {
                                "id": "n3w-ch1ld-3d",
                                "type": "descendant",
                                "attributes": {
                                    "__id__": "_tem_id_3344",
                                    "name": "Olga"
                                }
                            }
                        ]
                }
            }
        },
        "jsonapi": {"version": "1.0"}
    }
    assert expected == result


def test_integration_update_nested_resource(app):
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')
    parent_repo = ParentRepository()
    kwargs = {
        'parent_id': 'l337-p4r3n7-1d',
        'id': 'l337-ch1ld1-1d',
        'name': 'Riot'
    }
    descendant1 = DescendantModel(**kwargs)
    kwargs = {
        'parent_id': 'l337-p4r3n7-1d',
        'id': 'l337-ch1ld2-1d',
        'name': 'Blizzard'
    }
    descendant2 = DescendantModel(**kwargs)
    parent_repo.create({
        'id': 'l337-p4r3n7-1d',
        'descendant': [descendant1, descendant2]
    })
    json_data = json.dumps({
        'data': {
            'type': 'parent',
            'id': 'l337-p4r3n7-1d',
            'relationships': {
                'descendant': {
                    'data': [
                        {
                            'type': 'descendant',
                            'attributes': {
                                'name': 'Mrukus',
                                '__id__': '_tem_id_3344'
                            },
                        },
                        {
                            'id': 'l337-ch1ld1-1d',
                            'type': 'descendant',
                            'attributes': {
                                'name': 'Janek Pochodnia'
                            },
                        },
                    ]
                }
            }
        }
    })
    response = app.test_client().patch(
        '/parents/l337-p4r3n7-1d/',
        headers=JSONAPI_HEADERS,
        data=json_data,
    )
    result = json.loads(response.data.decode('utf-8'))
    expected = {
        'data': {
            'type': 'parent',
            'id': 'l337-p4r3n7-1d',
            'relationships': {
                'descendant': {
                    'data': [
                        {
                            'id': 'l337-ch1ld1-1d',
                            'type': 'descendant',
                            'attributes': {
                                'name': 'Janek Pochodnia'
                            }
                        },
                        {
                            'id': 'n3w-ch1ld-3d',
                            'type': 'descendant',
                            'attributes': {
                                '__id__': '_tem_id_3344',
                                'name': 'Mrukus'
                            }
                        }
                    ]
                }
            }
        },
        'jsonapi': {
            'version': '1.0'
        }
    }
    assert expected == result


def test_integration_get_list_use_schema_instead_of_atomic_schema(app):
    database_simulation.clear()
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')
    parent = ParentModel(**{'id': 111})
    database_simulation[parent.id] = parent
    response = app.test_client().get(
        '/parents/',
        headers=JSONAPI_HEADERS,
    )
    result = json.loads(response.data.decode('utf-8'))
    expected = {
        'meta': {'count': 1},
        'data': [
            {
                'id': '111',
                'type': 'parent'
            }
        ],
        'jsonapi': {'version': '1.0'}
    }
    assert expected == result


def test_integration_get_nested_resource(app):
    database_simulation.clear()
    application_api = api.Api(app)
    application_api.repository(ParentResourceRepositoryViewSet(), 'parent', '/parents/')

    response = app.test_client().get(
        '/parents/',
        headers=JSONAPI_HEADERS,
    )
    result = json.loads(response.data.decode('utf-8'))
    expected = {
        "data": [],
        "meta": {"count": 0},
        "jsonapi": {"version": "1.0"},
    }
    assert expected == result
