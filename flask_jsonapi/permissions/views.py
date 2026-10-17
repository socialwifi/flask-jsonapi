import abc
import logging

from flask_jsonapi import descriptors
from flask_jsonapi import resource_repository_views
from flask_jsonapi.permissions import checkers

logger = logging.getLogger(__name__)


class ProtectedDetailViewMixin:
    """Deprecated since 1.5.0, use flask_jsonapi.permissions.CheckObjectPermission with flask_jsonapi.DetailView."""

    def __init__(self, permission_checker: checkers.PermissionChecker, **kwargs):
        super().__init__(**kwargs)
        self.permission_checker = permission_checker

    def read(self, id):
        resource = self.protected_read(id)
        resource = self.permission_checker.check_read_permission(resource=resource)
        return resource

    def protected_read(self, id):
        return super().read(id)

    def destroy(self, id):
        resource = self.protected_read(id)
        resource = self.permission_checker.check_destroy_permission(resource=resource)
        return self.protected_destroy(resource)

    def protected_destroy(self, resource):
        return super().destroy(resource.id)

    def update(self, id, data, **kwargs):
        resource = self.protected_read(id)
        resource, data = self.permission_checker.check_update_permission(resource=resource, data=data)
        return self.protected_update(resource, data, **kwargs)

    def protected_update(self, resource, data, **kwargs):
        return super().update(resource.id, data, **kwargs)


class ProtectedListViewMixin(abc.ABC):
    """Deprecated since 1.5.0, use flask_jsonapi.permissions.CheckObjectPermission with flask_jsonapi.ListView."""

    def __init__(self, permission_checker: checkers.PermissionChecker, **kwargs):
        super().__init__(**kwargs)
        self.permission_checker = permission_checker

    def read_many(self, filters: dict, **kwargs):
        filters = self._apply_permission_filter(filters)
        resources = self.protected_read_many(filters, **kwargs)
        length_before_permission = len(resources)
        resources = self.permission_checker.check_list_permission(resources=resources)
        if length_before_permission != len(resources):
            logger.warning('No permission for some items!', extra=kwargs)
        return resources

    @abc.abstractmethod
    def _apply_permission_filter(self, filters: dict) -> dict:
        pass

    def protected_read_many(self, filters, **kwargs):
        return super().read_many(filters, **kwargs)

    def create(self, data: dict, **kwargs):
        data = self.permission_checker.check_create_permission(data=data)
        return self.protected_create(data, **kwargs)

    def protected_create(self, data: dict, **kwargs):
        return super().create(data, **kwargs)


class ProtectedDetailView(ProtectedDetailViewMixin, resource_repository_views.ResourceRepositoryDetailView):
    """Deprecated since 1.5.0, use flask_jsonapi.DetailView with flask_jsonapi.permissions.CheckObjectPermission."""

    pass


class ProtectedListView(ProtectedListViewMixin, resource_repository_views.ResourceRepositoryListView):
    """Deprecated since 1.5.0, use flask_jsonapi.ListView with flask_jsonapi.permissions.CheckObjectPermission."""

    pass


class ProtectedViewSet(resource_repository_views.ResourceRepositoryViewSet):
    """Deprecated since 1.5.0, use flask_jsonapi.ViewSet with flask_jsonapi.permissions.CheckObjectPermission."""

    detail_view_cls = ProtectedDetailView
    list_view_cls: ProtectedListView
    permission_checker: checkers.PermissionChecker = descriptors.NotImplementedProperty('permission_checker')

    def get_views_kwargs(self):
        kwargs = super().get_views_kwargs()
        kwargs['permission_checker'] = self.permission_checker
        return kwargs
