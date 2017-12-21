import logging

from sqlalchemy import exc
from sqlalchemy.orm import exc as orm_exc

from flask_jsonapi import exceptions
from flask_jsonapi.resource_repositories import repositories
from flask_jsonapi.exceptions import ForbiddenError

logger = logging.getLogger(__name__)


class SqlAlchemyModelRepository(repositories.ResourceRepository):
    model = None
    session = None
    instance_name = 'model instance'
    filter_methods_map = {}

    def create(self, data, **kwargs):
        obj = self.build(data)
        self.session.add(obj)
        try:
            self.session.flush()
            return obj
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise ForbiddenError(detail='{} could not be created.'.format(self.instance_name.capitalize()))

    def get_list(self, filters=None):
        try:
            query = self.get_query()
            return self.apply_filters(query, filters).all()
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise ForbiddenError(detail='Error while getting {} list.'.format(self.instance_name))

    def get_detail(self, id):
        try:
            return self.get_query().filter(self.model.id == id).one()
        except orm_exc.NoResultFound:
            raise exceptions.ObjectNotFound(source={'parameter': 'id'},
                                            detail='{} {} not found.'.format(self.instance_name.capitalize(), id))
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise ForbiddenError(detail='Error while getting {} details.'.format(self.instance_name))

    def delete(self, id):
        obj = self.get_detail(id)
        try:
            self.session.delete(obj)
            self.session.flush()
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise ForbiddenError(detail='Error while deleting {}.'.format(self.instance_name))

    def update(self, data, **kwargs):
        id = data['id']
        obj = self.get_detail(id)
        for key, value in data.items():
            self.update_attribute(obj, key, value)
        try:
            self.session.flush()
            return obj
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise ForbiddenError(detail='Error while updating {}.'.format(self.instance_name))

    def get_query(self):
        return self.model.query

    def apply_filters(self, query, filters):
        filters = filters or {}
        for filter, value in filters.items():
            if filter in self.filter_methods_map:
                filter_method = self.filter_methods_map[filter]
                query = query.filter(filter_method(value))
            else:
                query.filter_by(**{filter: value})
        return query

    def build(self, kwargs):
        return self.model(**kwargs)

    def update_attribute(self, obj, key, new_value):
        setattr(obj, key, new_value)