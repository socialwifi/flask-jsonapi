import logging

from sqlalchemy import exc
from sqlalchemy import func
from sqlalchemy.orm import exc as orm_exc

from flask_jsonapi import exceptions
from flask_jsonapi.exceptions import ForbiddenError
from flask_jsonapi.resource_repositories import repositories
from flask_jsonapi.utils import sqlalchemy_django_query

logger = logging.getLogger(__name__)


class SqlAlchemyModelRepository(repositories.ResourceRepository):
    model = None
    session = None
    instance_name = 'model instance'
    filter_methods_map = {}

    def create(self, data, strategy='commit', **kwargs):
        obj = self.build(data)
        self.session.add(obj)
        try:
            self._run_session_strategy(strategy)
            return obj
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise ForbiddenError(detail='{} could not be created.'.format(self.instance_name.capitalize()))

    def get_list(self, filters=None, sorting=None, pagination=None):
        try:
            query = self.get_query()
            query = self.apply_filters(query, filters)
            query = self.apply_sorts(query, sorting)
            query = self.apply_pagination(query, pagination)
            return query.all()
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

    def delete(self, id, strategy='commit'):
        obj = self.get_detail(id)
        try:
            self.session.delete(obj)
            self._run_session_strategy(strategy)
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise ForbiddenError(detail='Error while deleting {}.'.format(self.instance_name))

    def update(self, data, strategy='commit', **kwargs):
        id = data['id']
        obj = self.get_detail(id)
        for key, value in data.items():
            self.update_attribute(obj, key, value)
        try:
            self._run_session_strategy(strategy)
            return obj
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise ForbiddenError(detail='Error while updating {}.'.format(self.instance_name))

    def _run_session_strategy(self, strategy):
        if strategy == 'commit':
            self.session.commit()
        if strategy == 'flush':
            self.session.flush()

    def get_query(self):
        return sqlalchemy_django_query.DjangoQuery(self.model, session=self.session())

    def apply_filters(self, query, filters):
        filters = filters or {}
        filters = filters.copy()
        for filter, filter_method in self.filter_methods_map.items():
            if filter in filters:
                value = filters.pop(filter)
                query = query.filter(filter_method(value))
        query = query.filter_by(**filters)
        return query

    def apply_pagination(self, query, pagination):
        pagination = pagination or {}
        size = pagination.get('size')
        number = pagination.get('number')
        if size is not None and number is not None:
            return query.limit(size).offset(size * (number - 1))
        else:
            return query

    def apply_sorts(self, query, sorting):
        sorting = sorting or []
        try:
            query = query.order_by(*sorting)
        except exc.InvalidRequestError:
            raise exceptions.InvalidSort("Invalid sort fields for {}".format(self.instance_name))
        return query

    def build(self, kwargs):
        return self.model(**kwargs)

    def update_attribute(self, obj, key, new_value):
        setattr(obj, key, new_value)

    def get_count(self, filters=None):
        query = self.get_query()
        filtered_query = self.apply_filters(query, filters)
        count_query = filtered_query.statement.with_only_columns(func.count(self.model.id))
        return self.session.execute(count_query).scalar()
