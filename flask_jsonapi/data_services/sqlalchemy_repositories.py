import logging

from sqlalchemy import exc
from sqlalchemy import func
from sqlalchemy.orm import exc as orm_exc

from flask_jsonapi.utils import sqlalchemy_django_query

from . import base
from . import exceptions

logger = logging.getLogger(__name__)


class SqlAlchemyModelRepository(base.DataService):
    model = None
    session = None
    filter_methods_map = {}

    def create(self, data, strategy='commit'):
        obj = self.build(data)
        self.session.add(obj)
        try:
            self._run_session_strategy(strategy)
            return obj
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise exceptions.DataServiceException(detail="Resource could not be created.")

    def get_list(self, filters=None, sorting=None, pagination=None):
        try:
            query = self.get_query()
            query = self.apply_filters(query, filters)
            query = self.apply_sorts(query, sorting)
            query = self.apply_pagination(query, pagination)
            return query.all()
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise exceptions.DataServiceException(detail="Error while getting resource list.")

    def get_detail(self, id):
        try:
            return self.get_query().filter(self.model.id == id).one()
        except orm_exc.NoResultFound:
            raise exceptions.ResourceNotFound("Resource {} not found.".format(id))
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise exceptions.DataServiceException("Error while getting resource details.")

    def delete(self, id, strategy='commit'):
        obj = self.get_detail(id)
        try:
            self.session.delete(obj)
            self._run_session_strategy(strategy)
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise exceptions.DataServiceException(detail="Error while deleting resource.")

    def update(self, data, strategy='commit', id=None, resource=None):
        if resource is not None:
            obj = resource
        else:
            if id is None:
                id = data['id']
            obj = self.get_detail(id)
        for key, value in data.items():
            self.update_attribute(obj, key, value)
        try:
            self._run_session_strategy(strategy)
            return obj
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise exceptions.DataServiceException(detail="Error while updating resource.")

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
            raise exceptions.InvalidSortParameter("Invalid sort fields.")
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

    def get_or_create(self, *, create_data=None, for_update=False, strategy='commit', **kwargs):
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
        update_data = update_data or {}
        updated_rows = self.session.query(self.model).filter_by(**kwargs).update(
            update_data, synchronize_session=False)
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
                    self.session.query(self.model).filter_by(**kwargs).update(
                        update_data, synchronize_session=False)
                    self._run_session_strategy(strategy)
                else:
                    raise
        else:
            self._run_session_strategy(strategy)
