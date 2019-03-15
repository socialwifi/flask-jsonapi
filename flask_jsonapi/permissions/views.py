import abc
import logging

from flask_jsonapi import ResourceRepositoryDetailView
from flask_jsonapi import ResourceRepositoryListView
from flask_jsonapi import ResourceRepositoryViewSet
from flask_jsonapi import descriptors
from flask_jsonapi import exceptions

from . import checkers

logger = logging.getLogger(__name__)


class ProtectedDetailView(ResourceRepositoryDetailView):
    def __init__(self, permission_checker: checkers.PermissionChecker, **kwargs):
        super().__init__(**kwargs)
        self.permission_checker = permission_checker

    def read(self, id):
        resource = super().read(id)
        resource = self.permission_checker.check_read_permission(resource=resource)
        return resource

    def destroy(self, id):
        resource = super().read(id)
        resource = self.permission_checker.check_destroy_permission(resource=resource)
        return super().destroy(resource.id)

    def update(self, id, data, **kwargs):
        resource = super().read(id)
        resource, data = self.permission_checker.check_update_permission(resource=resource, data=data)
        return super().update(id, data, **kwargs)


class ProtectedListView(ResourceRepositoryListView, abc.ABC):
    def __init__(self, permission_checker: checkers.PermissionChecker, **kwargs):
        super().__init__(**kwargs)
        self.permission_checker = permission_checker

    def get(self, *args, **kwargs):
        try:
            return super().get(*args, **kwargs)
        except checkers.PermissionException:
            raise exceptions.ForbiddenError("You don't have permissions")

    def post(self, *args, **kwargs):
        try:
            return super().post(*args, **kwargs)
        except checkers.PermissionException:
            raise exceptions.ForbiddenError("You don't have permissions")

    def read_many(self, filters: dict, **kwargs):
        filters = self._apply_permission_filter(filters)
        resources = super().read_many(filters, **kwargs)
        length_before_permission = len(resources)
        resources = self.permission_checker.check_list_permission(resources=resources)
        if length_before_permission != len(resources):
            logger.warning('No permission for some items!', extra=kwargs)
        return resources

    @abc.abstractmethod
    def _apply_permission_filter(self, filters: dict) -> dict:
        pass

    def create(self, data: dict, **kwargs):
        data = self.permission_checker.check_create_permission(data=data)
        return super().create(data, **kwargs)


class ProtectedViewSet(ResourceRepositoryViewSet):
    detail_view_cls = ProtectedDetailView
    list_view_cls: ProtectedListView
    permission_checker: checkers.PermissionChecker = descriptors.NotImplementedProperty('permission_checker')

    def get_views_kwargs(self):
        kwargs = super().get_views_kwargs()
        kwargs['permission_checker'] = self.permission_checker
        return kwargs
