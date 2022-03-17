import uuid

from unittest import mock

import marshmallow_jsonapi
import pytest

from marshmallow_jsonapi import fields

from flask_jsonapi import exceptions
from flask_jsonapi import permissions

ALLOWED_PARENT_ID = '11111111-1111-1111-1111-111111111111'
NOT_ALLOWED_PARENT_ID = '22222222-2222-2222-2222-222222222222'


def viewset_factory(repository_mock):
    class ExampleResourceSchema(marshmallow_jsonapi.Schema):
        id = fields.UUID(required=True)
        parent_id = fields.UUID(required=True)
        content = fields.String(required=False)

        class Meta:
            type_ = 'example'
            self_view_many = 'example_list'
            self_view = 'example_detail'
            self_view_kwargs = {'example_id': '<id>'}
            strict = True

    class ExampleProtectedListView(permissions.ProtectedListView):
        def _apply_permission_filter(self, filters: dict):
            filters['parent_id'] = self.permission_checker.get_allowed_parent_id()
            return filters

    class ExamplePermissionChecker(permissions.ObjectLevelPermissionChecker):
        object_id_attribute = 'parent_id'

        def has_permission(self, object_id, action) -> bool:
            return str(object_id) == self.get_allowed_parent_id()

        def get_allowed_parent_id(self):
            return ALLOWED_PARENT_ID

    class ExampleViewSet(permissions.ProtectedViewSet):
        list_view_cls = ExampleProtectedListView
        permission_checker = ExamplePermissionChecker()
        repository = repository_mock
        schema = ExampleResourceSchema

    return ExampleViewSet()


@pytest.fixture
def repository():
    return mock.Mock()


@pytest.fixture
def configured_api(api, repository):
    view_set = viewset_factory(repository)
    api.repository(view_set, 'example', '/examples')


def resource_factory(id=None, parent_id=None, content=None):
    object = mock.Mock()
    object.id = uuid.uuid4() if id is None else id
    object.parent_id = uuid.uuid4() if parent_id is None else parent_id
    object.content = 'Sample content' if content is None else content
    return object


@pytest.mark.usefixtures('configured_api')
class TestProtectedViewSet:
    def test_list(self, jsonapi_client, repository):
        repository.get_list.return_value = [
            resource_factory(parent_id=ALLOWED_PARENT_ID),
            resource_factory(parent_id=NOT_ALLOWED_PARENT_ID),
        ]

        response = jsonapi_client.get('/examples')

        assert response.status_code == 200
        response_body = response.get_json(force=True)
        assert len(response_body['data']) == 1
        assert response_body['data'][0]['attributes']['parent_id'] == ALLOWED_PARENT_ID
        repository.get_list.assert_called_with({'parent_id': '11111111-1111-1111-1111-111111111111'}, (), {})

    def test_list_if_no_permissions(self, jsonapi_client, repository):
        repository.get_list.return_value = [
            resource_factory(parent_id=NOT_ALLOWED_PARENT_ID),
            resource_factory(parent_id=NOT_ALLOWED_PARENT_ID),
        ]

        response = jsonapi_client.get('/examples')

        assert response.status_code == 200
        response_body = response.get_json(force=True)
        assert response_body['data'] == []
        repository.get_list.assert_called_with({'parent_id': '11111111-1111-1111-1111-111111111111'}, (), {})

    def test_details(self, jsonapi_client, repository):
        repository.get_detail.return_value = resource_factory(
            id='33333333-3333-3333-3333-333333333333',
            parent_id=ALLOWED_PARENT_ID,
        )

        response = jsonapi_client.get('/examples/33333333-3333-3333-3333-333333333333')

        assert response.status_code == 200
        response_body = response.get_json(force=True)
        assert response_body['data']['attributes']['parent_id'] == ALLOWED_PARENT_ID
        repository.get_detail.assert_called_with('33333333-3333-3333-3333-333333333333')

    def test_details_if_no_permissions(self, jsonapi_client, repository):
        repository.get_detail.return_value = resource_factory(
            id='33333333-3333-3333-3333-333333333333',
            parent_id=NOT_ALLOWED_PARENT_ID,
        )

        response = jsonapi_client.get('/examples/33333333-3333-3333-3333-333333333333')

        assert response.status_code == 403
        repository.get_detail.assert_called_with('33333333-3333-3333-3333-333333333333')

    def test_details_if_does_not_exist(self, jsonapi_client, repository):
        repository.get_detail.side_effect = exceptions.ObjectNotFound(source={}, detail='')

        response = jsonapi_client.get('/examples/33333333-3333-3333-3333-333333333333')

        assert response.status_code == 404
        repository.get_detail.assert_called_with('33333333-3333-3333-3333-333333333333')

    def test_update(self, jsonapi_client, repository):
        repository.get_detail.return_value = resource_factory(
            id='33333333-3333-3333-3333-333333333333',
            parent_id=ALLOWED_PARENT_ID,
            content='Initial content.',
        )

        response = jsonapi_client.patch(
            '/examples/33333333-3333-3333-3333-333333333333',
            json={
                'data': {
                    'type': 'example',
                    'id': '33333333-3333-3333-3333-333333333333',
                    'attributes': {
                        'content': 'Changed content.',
                    },
                },
            },
        )

        assert response.status_code == 204
        repository.get_detail.assert_called_with('33333333-3333-3333-3333-333333333333')
        repository.update.assert_called_with({
            'id': '33333333-3333-3333-3333-333333333333',
            'content': 'Changed content.'
        })

    def test_update_if_no_permissions(self, jsonapi_client, repository):
        repository.get_detail.return_value = resource_factory(
            id='33333333-3333-3333-3333-333333333333',
            parent_id=NOT_ALLOWED_PARENT_ID,
            content='Initial content.',
        )

        response = jsonapi_client.patch(
            '/examples/33333333-3333-3333-3333-333333333333',
            json={
                'data': {
                    'type': 'example',
                    'id': '33333333-3333-3333-3333-333333333333',
                    'attributes': {
                        'content': 'Changed content.',
                    },
                },
            },
        )

        assert response.status_code == 403
        repository.get_detail.assert_called_with('33333333-3333-3333-3333-333333333333')
        repository.update.assert_not_called()

    def test_delete(self, jsonapi_client, repository):
        repository.get_detail.return_value = resource_factory(
            id='33333333-3333-3333-3333-333333333333',
            parent_id=ALLOWED_PARENT_ID,
        )

        response = jsonapi_client.delete('/examples/33333333-3333-3333-3333-333333333333')

        assert response.status_code == 204
        repository.get_detail.assert_called_with('33333333-3333-3333-3333-333333333333')
        repository.delete.assert_called_with('33333333-3333-3333-3333-333333333333')

    def test_delete_if_no_permissions(self, jsonapi_client, repository):
        repository.get_detail.return_value = resource_factory(
            id='33333333-3333-3333-3333-333333333333',
            parent_id=NOT_ALLOWED_PARENT_ID,
        )

        response = jsonapi_client.delete('/examples/33333333-3333-3333-3333-333333333333')

        assert response.status_code == 403
        repository.get_detail.assert_called_with('33333333-3333-3333-3333-333333333333')
        repository.delete.assert_not_called()

    def test_create(self, jsonapi_client, repository):
        response = jsonapi_client.post(
            '/examples',
            json={
                'data': {
                    'type': 'example',
                    'id': '33333333-3333-3333-3333-333333333333',
                    'attributes': {
                        'parent_id': ALLOWED_PARENT_ID,
                        'content': 'Boring test content text.',
                    },
                },
            },
        )

        assert response.status_code == 201
        repository.create.assert_called_with({
            'id': uuid.UUID('33333333-3333-3333-3333-333333333333'),
            'parent_id': uuid.UUID('11111111-1111-1111-1111-111111111111'),
            'content': 'Boring test content text.',
        })

    def test_create_if_no_permissions(self, jsonapi_client, repository):
        response = jsonapi_client.post(
            '/examples',
            json={
                'data': {
                    'type': 'example',
                    'id': '33333333-3333-3333-3333-333333333333',
                    'attributes': {
                        'parent_id': NOT_ALLOWED_PARENT_ID,
                        'content': 'Boring test content text.',
                    },
                },
            },
        )

        assert response.status_code == 403
        repository.create.assert_not_called()
