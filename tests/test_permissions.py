import uuid

from dataclasses import dataclass
from unittest import mock

import pytest

from flask_jsonapi import permissions


class PermissionCheckerForTests(permissions.ObjectLevelPermissionChecker):
    object_id_attribute = 'object_id'

    def has_permission(self, object_id, action) -> bool:
        return False


@dataclass
class ResourceForTests:
    object_id: uuid.UUID


class TestObjectLevelPermissionChecker:
    def test_check_read_permission(self):
        checker = PermissionCheckerForTests()
        checker.has_permission = mock.MagicMock()
        resource = ResourceForTests(uuid.uuid4())

        checker.check_read_permission(resource=resource)

        checker.has_permission.assert_called_with(action=permissions.READ_ACTION, object_id=resource.object_id)

    def test_check_list_permission(self):
        checker = PermissionCheckerForTests()
        checker.has_permission = mock.MagicMock()
        resource0 = ResourceForTests(uuid.uuid4())
        resource1 = ResourceForTests(uuid.uuid4())
        resource2 = ResourceForTests(uuid.uuid4())
        resource3 = ResourceForTests(uuid.uuid4())
        resource4 = ResourceForTests(uuid.uuid4())

        checker.check_list_permission(resources=[resource0, resource1, resource2, resource3, resource4])

        checker.has_permission.assert_has_calls(
            [
                mock.call(action=permissions.READ_ACTION, object_id=resource0.object_id),
                mock.call(action=permissions.READ_ACTION, object_id=resource1.object_id),
                mock.call(action=permissions.READ_ACTION, object_id=resource2.object_id),
                mock.call(action=permissions.READ_ACTION, object_id=resource3.object_id),
                mock.call(action=permissions.READ_ACTION, object_id=resource4.object_id),
            ],
            any_order=True,
        )

    def test_check_destroy_permission(self):
        checker = PermissionCheckerForTests()
        checker.has_permission = mock.MagicMock()
        resource = ResourceForTests(uuid.uuid4())

        checker.check_destroy_permission(resource=resource)

        checker.has_permission.assert_called_with(action=permissions.DESTROY_ACTION, object_id=resource.object_id)

    def test_check_create_permission(self):
        checker = PermissionCheckerForTests()
        checker.has_permission = mock.MagicMock()
        data = {'object_id': str(uuid.uuid4())}

        checker.check_create_permission(data=data)

        checker.has_permission.assert_called_with(action=permissions.CREATE_ACTION, object_id=data['object_id'])

    def test_check_update_permission(self):
        checker = PermissionCheckerForTests()
        checker.has_permission = mock.MagicMock()
        resource_id = uuid.uuid4()
        resource = ResourceForTests(resource_id)
        data = {'object_id': str(resource_id)}

        checker.check_update_permission(data=data, resource=resource)

        checker.has_permission.assert_has_calls(
            [
                mock.call(action=permissions.UPDATE_ACTION, object_id=resource_id),
                mock.call(action=permissions.UPDATE_ACTION, object_id=str(resource_id)),
            ],
            any_order=True,
        )

    def test_exception_raised_when_not_permission_to_read(self):
        checker = PermissionCheckerForTests()
        resource_id = uuid.uuid4()
        resource = ResourceForTests(resource_id)

        with pytest.raises(permissions.PermissionException):
            checker.check_read_permission(resource=resource)

    def test_exception_raised_when_not_permission_to_destroy(self):
        checker = PermissionCheckerForTests()
        resource_id = uuid.uuid4()
        resource = ResourceForTests(resource_id)

        with pytest.raises(permissions.PermissionException):
            checker.check_destroy_permission(resource=resource)

    def test_exception_raised_when_not_permission_to_update(self):
        checker = PermissionCheckerForTests()
        resource_id = uuid.uuid4()
        data = {'object_id': resource_id}
        resource = ResourceForTests(resource_id)

        with pytest.raises(permissions.PermissionException):
            checker.check_update_permission(resource=resource, data=data)

    def test_exception_raised_when_not_permission_to_create(self):
        checker = PermissionCheckerForTests()
        resource_id = uuid.uuid4()
        data = {'object_id': resource_id}

        with pytest.raises(permissions.PermissionException):
            checker.check_create_permission(data=data)

    def test_exception_not_raised_when_not_permission_to_list(self):
        checker = PermissionCheckerForTests()
        resource0 = ResourceForTests(uuid.uuid4())
        resource1 = ResourceForTests(uuid.uuid4())
        resource2 = ResourceForTests(uuid.uuid4())
        resource3 = ResourceForTests(uuid.uuid4())
        resource4 = ResourceForTests(uuid.uuid4())

        result = checker.check_list_permission(resources=[resource0, resource1, resource2, resource3, resource4])

        assert result == []

    def test_check_list_permissions_should_filter_resources(self):
        checker = PermissionCheckerForTests()
        checker.has_permission = mock.MagicMock()
        checker.has_permission.side_effect = [
            True,
            False,
            False,
            False,
            True,
        ]
        resource0 = ResourceForTests(uuid.uuid4())
        resource1 = ResourceForTests(uuid.uuid4())
        resource2 = ResourceForTests(uuid.uuid4())
        resource3 = ResourceForTests(uuid.uuid4())
        resource4 = ResourceForTests(uuid.uuid4())

        result = checker.check_list_permission(resources=[resource0, resource1, resource2, resource3, resource4])

        assert result == [resource0, resource4]
