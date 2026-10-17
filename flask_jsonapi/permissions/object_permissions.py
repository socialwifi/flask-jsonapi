import abc
import logging
import typing

from flask_jsonapi import data_services
from flask_jsonapi import descriptors
from flask_jsonapi.permissions import checkers

logger = logging.getLogger(__name__)


class ObjectPermissions(abc.ABC):
    @abc.abstractmethod
    def create(self, *, data, inner):
        ...

    @abc.abstractmethod
    def read(self, *, id, inner):
        ...

    @abc.abstractmethod
    def list(self, *, filters, sorting, pagination, inner):
        ...

    @abc.abstractmethod
    def update(self, *, resource, data, inner):
        ...

    @abc.abstractmethod
    def destroy(self, *, resource, inner):
        ...


class CheckObjectPermission(ObjectPermissions):
    permission_checker = descriptors.NotImplementedProperty('permission_checker')

    def __init__(self, permission_checker: typing.Optional[checkers.PermissionChecker] = None):
        if permission_checker:
            self.permission_checker = permission_checker

    def create(self, *, data, inner):
        data = self.permission_checker.check_create_permission(data=data)
        return inner.create(data=data)

    def read(self, *, id, inner):
        resource = inner.read(id=id)
        return self.permission_checker.check_read_permission(resource=resource)

    def list(self, *, filters, sorting, pagination, inner):
        result = inner.list(filters=self.apply_permission_filter(filters), sorting=sorting, pagination=pagination)
        permitted = self.permission_checker.check_list_permission(resources=result.items)
        if len(permitted) == len(result.items):
            return data_services.ListResult(permitted, result.total)
        # The filter let through rows the check rejects, so the total counts objects the user may not see.
        logger.warning('Object permission check dropped listed objects; the total is hidden.')
        return data_services.ListResult(permitted, total=None)

    def update(self, *, resource, data, inner):
        resource, data = self.permission_checker.check_update_permission(resource=resource, data=data)
        return inner.update(resource=resource, data=data)

    def destroy(self, *, resource, inner):
        resource = self.permission_checker.check_destroy_permission(resource=resource)
        return inner.destroy(resource=resource)

    @abc.abstractmethod
    def apply_permission_filter(self, filters: dict) -> dict:
        """Return a new dict restricting the query to objects the user may list; never mutate ``filters``.

        Raise ``PermissionException`` (403) when the client's own filters ask for a scope the user may not list.
        """
