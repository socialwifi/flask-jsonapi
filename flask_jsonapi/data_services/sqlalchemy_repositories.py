import contextlib
import logging

from sqlalchemy import exc
from sqlalchemy import func
from sqlalchemy.orm import exc as orm_exc

from flask_jsonapi import exceptions as http_exceptions
from flask_jsonapi.utils import sqlalchemy_django_query

from . import base
from . import exceptions

logger = logging.getLogger(__name__)


class SqlAlchemyModelRepository(base.DataService):
    model = None
    session = None
    filter_methods_map = {}

    def create(self, *, data, strategy='commit'):
        with self._translated_errors('Resource could not be created.', data_error=exceptions.InvalidData):
            obj = self.build(data)
            self.session.add(obj)
            self._run_session_strategy(strategy)
            return obj

    def list(self, *, filters=None, sorting=None, pagination=None):
        with self._translated_errors(
                'Error while getting resource list.', data_error=exceptions.InvalidFilterParameter):
            query = self.apply_filters(self.get_query(), filters)
            total = self._count(query) if pagination else None
            query = self.apply_sorts(query, sorting)
            items = self.apply_pagination(query, pagination).all()
            return base.ListResult(items, total)

    def read(self, *, id):
        with self._translated_errors(
                'Error while getting resource details.', data_error=exceptions.ResourceNotFound):
            try:
                return self.get_query().filter(self.model.id == id).one()
            except orm_exc.NoResultFound:
                raise exceptions.ResourceNotFound('Resource {} not found.'.format(id))

    def update(self, *, resource, data, strategy='commit'):
        with self._translated_errors('Error while updating resource.', data_error=exceptions.InvalidData):
            for key, value in data.items():
                self.update_attribute(resource, key, value)
            self._run_session_strategy(strategy)
            return resource

    def destroy(self, *, resource, strategy='commit'):
        with self._translated_errors('Error while deleting resource.', data_error=exceptions.InvalidData):
            self.session.delete(resource)
            self._run_session_strategy(strategy)

    def get_or_create(self, *, create_data=None, for_update=False, strategy='commit', **kwargs):
        with self._translated_errors(
                'Error while getting or creating resource.', data_error=exceptions.InvalidData):
            query = self.session.query(self.model)
            if for_update:
                query = query.with_for_update()
            try:
                return query.filter_by(**kwargs).one()
            except orm_exc.NoResultFound:
                create_data = create_data or {}
                build_data = kwargs.copy()
                build_data.update(create_data)
                try:
                    created = self.build(build_data)
                    with self.session.begin_nested():
                        self.session.add(created)
                    self._run_session_strategy(strategy)
                    return created
                except exc.IntegrityError as e:
                    if 'duplicate key value violates unique constraint' in str(e.orig):
                        return query.filter_by(**kwargs).one()
                    else:
                        raise

    def update_or_create(self, *, update_data=None, strategy='commit', **kwargs):
        with self._translated_errors(
                'Error while updating or creating resource.', data_error=exceptions.InvalidData):
            update_data = update_data or {}
            updated_rows = self.session.query(self.model).filter_by(**kwargs).update(update_data)
            if updated_rows == 0:
                create_data = {}
                create_data.update(kwargs)
                create_data.update(update_data)
                try:
                    created = self.build(create_data)
                    with self.session.begin_nested():
                        self.session.add(created)
                    self._run_session_strategy(strategy)
                    return created
                except exc.IntegrityError as e:
                    if 'duplicate key value violates unique constraint' in str(e.orig):
                        self.session.query(self.model).filter_by(**kwargs).update(update_data)
                        self._run_session_strategy(strategy)
                    else:
                        raise
            else:
                self._run_session_strategy(strategy)

    @contextlib.contextmanager
    def _translated_errors(self, detail, data_error):
        try:
            yield
        except exc.SQLAlchemyError as error:
            self.session.rollback()
            if isinstance(error, exc.IntegrityError):
                logger.info('Integrity error translated to Conflict.')
                raise exceptions.Conflict('Resource conflicts with existing data.') from error
            if isinstance(error, exc.OperationalError):
                logger.warning('Operational error translated to Unavailable.', exc_info=error)
                raise exceptions.Unavailable('Database is temporarily unavailable.') from error
            if isinstance(error, exc.DataError):
                logger.info('Data error translated to a client error.')
                raise data_error('Value has an invalid format.') from error
            raise exceptions.DataServiceException(detail) from error

    def _count(self, query):
        return self.session.execute(query.statement.with_only_columns(func.count(self.model.id))).scalar()

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
        try:
            return query.filter_by(**filters)
        except ValueError:
            raise exceptions.InvalidFilterParameter('Invalid filter fields.')

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
            return query.order_by(*sorting)
        except (http_exceptions.InvalidSort, exc.InvalidRequestError):
            raise exceptions.InvalidSortParameter('Invalid sort fields.')

    def build(self, kwargs):
        return self.model(**kwargs)

    def update_attribute(self, obj, key, new_value):
        setattr(obj, key, new_value)
