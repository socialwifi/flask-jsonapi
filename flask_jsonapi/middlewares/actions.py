from .. import exceptions
from . import base


CREATE = 'create'
READ = 'fetch'
READ_MANY = 'fetch list'
UPDATE = 'update'
DESTROY = 'delete'


class AllowedActions(base.Middleware):
    def __init__(self, allowed_actions: list[str]):
        self.allowed_actions = allowed_actions

    def create(self, *args, **kwargs):
        self._check_allowed_action(CREATE)
        return super().create(*args, **kwargs)

    def read(self, *args, **kwargs):
        self._check_allowed_action(READ)
        return super().read(*args, **kwargs)

    def read_many(self, *args, **kwargs):
        self._check_allowed_action(READ_MANY)
        return super().read_many(*args, **kwargs)

    def update(self, *args, **kwargs):
        self._check_allowed_action(UPDATE)
        return super().update(*args, **kwargs)

    def destroy(self, *args, **kwargs):
        self._check_allowed_action(DESTROY)
        return super().destroy(*args, **kwargs)

    def _check_allowed_action(self, action):
        if action not in self.allowed_actions:
            raise exceptions.MethodNotAllowed(detail="{} is not allowed for this resource".format(action.capitalize()))
