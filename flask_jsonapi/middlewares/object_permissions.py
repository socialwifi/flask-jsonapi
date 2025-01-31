import abc
import logging
import typing

from flask_jsonapi import descriptors
from flask_jsonapi.permissions import checkers

from . import base

logger = logging.getLogger(__name__)


class CheckObjectPermission(base.Middleware, abc.ABC):
    permission_checker = descriptors.NotImplementedProperty('permission_checker')

    def __init__(self, permission_checker: typing.Optional[checkers.PermissionChecker] = None):
        if permission_checker:
            self.permission_checker = permission_checker

    def create(self, data, **kwargs):
        self.permission_checker.check_create_permission(data=data)
        return super().create(data=data, **kwargs)

    def read(self, *, id, **kwargs):
        resource = super().read(id=id, **kwargs)
        self.permission_checker.check_read_permission(resource=resource)
        return resource

    def read_many(self, *, filters, **kwargs):
        filters = self._apply_permission_filter(filters)
        resources = super().read_many(filters=filters, **kwargs)
        length_before_permission = len(resources)
        resources = self.permission_checker.check_list_permission(resources=resources)
        if length_before_permission != len(resources):
            logger.warning('User has no permission for some items!', extra=kwargs)
        return resources

    def update(self, *, data_service, id, data, data_service_kwargs, **kwargs):
        resource = data_service.get_detail(id=id)
        self.permission_checker.check_update_permission(resource=resource, data=data)
        data_service_kwargs = data_service_kwargs or {}
        data_service_kwargs['resource'] = resource
        return super().update(
            data_service=data_service, id=id, data=data, data_service_kwargs=data_service_kwargs, **kwargs)

    # TODO: pass resource down like in "update". Do not fetch it again below.
    def destroy(self, *, data_service, id, **kwargs):
        resource = data_service.get_detail(id=id)
        self.permission_checker.check_destroy_permission(resource=resource)
        return super().destroy(data_service=data_service, id=id, **kwargs)

    @abc.abstractmethod
    def _apply_permission_filter(self, filters: dict) -> dict:
        ...
