import logging

from flask_jsonapi import ResourceRepositoryDetailView
from flask_jsonapi import ResourceRepositoryListView
from flask_jsonapi import ResourceRepositoryViewSet
from flask_jsonapi.exceptions import ForbiddenError
from flask_jsonapi.resource_repositories import repositories

logger = logging.getLogger(__name__)


class ResourceRepositoryViewMixin:
    repository = repositories.ResourceRepository()

    def __init__(self, *, repository=None, **kwargs):
        super().__init__(**kwargs)
        if repository:
            self.repository = repository


OWNER_ROLE = 'owner'
MANAGER_ROLE = 'manager'
READER_ROLE = 'reader'
# Special role used to bypass role check
NO_ROLE = 'ALLOW_ANY'

ROLES = {
    OWNER_ROLE: {OWNER_ROLE, MANAGER_ROLE, READER_ROLE},
    MANAGER_ROLE: {MANAGER_ROLE, READER_ROLE},
    READER_ROLE: {READER_ROLE},
}

READ_ACTION = 'read'
DESTROY_ACTION = 'destroy'
UPDATE_ACTION = 'update'
LIST_ACTION = 'list'
CREATE_ACTION = 'read'

OWNER_ONLY_ROLE_MAP = {
    READ_ACTION: OWNER_ROLE,
    LIST_ACTION: OWNER_ROLE,
    CREATE_ACTION: OWNER_ROLE,
    UPDATE_ACTION: OWNER_ROLE,
    DESTROY_ACTION: OWNER_ROLE,
}

DEFAULT_ROLE_MAP = {
    READ_ACTION: READER_ROLE,
    LIST_ACTION: READER_ROLE,
    CREATE_ACTION: MANAGER_ROLE,
    UPDATE_ACTION: MANAGER_ROLE,
    DESTROY_ACTION: MANAGER_ROLE,
}


class PermissionManagerBase:
    def __init__(self, get_account_id_method, get_account_role_name_method, permission_map: dict = None):
        self.get_account_id_method = get_account_id_method
        self.get_account_role_name_method = get_account_role_name_method
        self.permission_map = permission_map or DEFAULT_ROLE_MAP

    def check_read_permission(self, *, view, id):
        parent = self.get_parent_by_id(view=view, id=id)
        self.check_permissions(parent, READ_ACTION)

    def check_destroy_permission(self, *, view, id):
        parent = self.get_parent_by_id(view=view, id=id)
        self.check_permissions(parent, DESTROY_ACTION)

    def check_update_permission(self, *, view, id):
        parent = self.get_parent_by_id(view=view, id=id)
        self.check_permissions(parent, UPDATE_ACTION)

    def check_list_permission(self, *, view, filters):
        parent = self.get_parent_by_filters(view=view, filters=filters)
        self.check_permissions(parent, LIST_ACTION)

    def check_create_permission(self, *, view, data):
        parent = self.get_parent_by_data(view=view, data=data)
        self.check_permissions(parent, CREATE_ACTION)

    def get_parent_by_id(self, *, view, id):
        method = self._get_parent_method(view=view, method_name='get_parent_by_id')
        return method(id=id)

    def get_parent_by_filters(self, *, view, filters):
        method = self._get_parent_method(view=view, method_name='get_parent_by_filters')
        return method(filters=filters)

    def get_parent_by_data(self, *, view, data):
        method = self._get_parent_method(view=view, method_name='get_parent_by_data')
        return method(data=data)

    def _get_parent_method(self, *, view, method_name: str):
        repository = getattr(view, 'repository')
        get_parent_method = getattr(repository, method_name)
        return get_parent_method

    def check_permissions(self, parent: repositories.Parent, action: str):
        if action in self.permission_map:
            required_role = self.permission_map[action]
            if required_role == NO_ROLE:
                return None
            account_id = self.get_account_id_method()
            account_role_name = self.get_account_role_name_method(parent, account_id)
            if account_role_name and required_role in ROLES[account_role_name]:
                return None
        raise ForbiddenError(detail='Insufficient permissions!')


class ProtectedViewMixin:
    permission_manager = None

    def __init__(self, *, permission_manager=None, **kwargs):
        super().__init__(**kwargs)
        if permission_manager:
            self.permission_manager = permission_manager


class ProtectedResourceRepositoryDetailView(ProtectedViewMixin, ResourceRepositoryDetailView):
    def read(self, id):
        self.permission_manager.check_read_permission(view=self, id=id)
        return self.repository.get_detail(id)

    def destroy(self, id):
        self.permission_manager.check_destroy_permission(view=self, id=id)
        return super().destroy(id)

    def update(self, id, data, **kwargs):
        self.permission_manager.check_update_permission(view=self, id=id)
        return super().update(id, data, **kwargs)


class ProtectedResourceRepositoryListView(ProtectedViewMixin, ResourceRepositoryListView):
    def read_many(self, filters, sorting, pagination):
        self.permission_manager.check_list_permission(view=self, filters=filters)
        return self.repository.get_list(filters, sorting, pagination)

    def create(self, data, **kwargs):
        self.permission_manager.check_create_permission(view=self, data=data)
        return self.repository.create(data, **kwargs)

    def get_count(self, filters):
        self.permission_manager.check_list_permission(view=self, filters=filters)
        return self.repository.get_count(filters)


class ProtectedResourceRepositoryViewSet(ResourceRepositoryViewSet):
    repository = repositories.ProtectedResourceRepository()
    detail_view_cls = ProtectedResourceRepositoryDetailView
    list_view_cls = ProtectedResourceRepositoryListView
    permission_manager = None

    def __init__(self, *, permission_manager=None, **kwargs):
        if permission_manager:
            self.permission_manager = permission_manager
        super().__init__(**kwargs)

    def get_views_kwargs(self):
        view_kwargs = super().get_views_kwargs()
        view_kwargs['permission_manager'] = self.permission_manager
        return view_kwargs
