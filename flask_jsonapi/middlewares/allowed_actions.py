from flask_jsonapi import exceptions
from flask_jsonapi import resources

from . import base


class CheckAllowedActions(base.Middleware):
    def __init__(self, allowed_actions: list[str]):
        self.allowed_actions = allowed_actions

    def create(self, *args, **kwargs):
        self._check_allowed_action(resources.Actions.create)
        return super().create(*args, **kwargs)

    def read(self, *args, **kwargs):
        self._check_allowed_action(resources.Actions.read)
        return super().read(*args, **kwargs)

    def read_many(self, *args, **kwargs):
        self._check_allowed_action(resources.Actions.read_many)
        return super().read_many(*args, **kwargs)

    def update(self, *args, **kwargs):
        self._check_allowed_action(resources.Actions.update)
        return super().update(*args, **kwargs)

    def destroy(self, *args, **kwargs):
        self._check_allowed_action(resources.Actions.destroy)
        return super().destroy(*args, **kwargs)

    def _check_allowed_action(self, action):
        if action not in self.allowed_actions:
            raise exceptions.MethodNotAllowed(detail="{} is not allowed for this resource".format(action.capitalize()))
