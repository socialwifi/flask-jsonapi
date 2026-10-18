from contextlib import contextmanager

from flask_jsonapi import exceptions


class ResourceRepository:
    """Deprecated since 1.5.0, use flask_jsonapi.data_services.DataService."""

    def create(self, data, **kwargs):
        raise exceptions.NotImplementedMethod('Creating is not implemented.')

    def get_list(self, filters=None, sorting=None, pagination=None):
        raise exceptions.NotImplementedMethod('Getting list is not implemented.')

    def get_detail(self, id):
        raise exceptions.NotImplementedMethod('Getting object is not implemented.')

    def delete(self, id):
        raise exceptions.NotImplementedMethod('Deleting is not implemented')

    def update(self, data, **kwargs):
        raise exceptions.NotImplementedMethod('Updating is not implemented')

    def get_count(self, filters=None):
        raise NotImplementedError

    @contextmanager
    def begin_transaction(self):
        yield
