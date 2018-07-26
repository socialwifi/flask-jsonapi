from contextlib import contextmanager

from flask_jsonapi import exceptions


class ResourceRepository:
    def create(self, data, **kwargs):
        raise exceptions.NotImplementedMethod('Creating is not implemented.')

    def get_list(self, filters=None, pagination=None):
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


class ToOneRelationshipRepository:
    def get_detail(self, parent_id):
        raise exceptions.NotImplementedMethod('Getting relationship is not implemented.')

    def update(self, parent_id, data):
        raise exceptions.NotImplementedMethod('Updating relationship is not implemented.')

    def delete(self, parent_id):
        raise exceptions.NotImplementedMethod('Deleting relationship is not implemented.')


class ToManyRelationshipRepository:
    def get_list(self, parent_id):
        raise exceptions.NotImplementedMethod('Getting relationship is not implemented.')

    def create(self, parent_id, data):
        raise exceptions.NotImplementedMethod('Creating relationship is not implemented.')

    def update(self, parent_id, data):
        raise exceptions.NotImplementedMethod('Updating relationship is not implemented.')

    def delete(self, parent_id, data):
        raise exceptions.NotImplementedMethod('Deleting relationship is not implemented.')
