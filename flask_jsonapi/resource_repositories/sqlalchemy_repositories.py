import logging

from sqlalchemy import exc
from sqlalchemy import func
from sqlalchemy.orm import exc as orm_exc

from flask_jsonapi import exceptions
from flask_jsonapi.resource_repositories import repositories

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
            raise exceptions.ForbiddenError(detail='{} could not be created.'.format(self.instance_name.capitalize()))

    def get_list(self, filters=None, pagination=None):
        try:
            query = self.get_query()
            filtered_query = self.apply_filters(query, filters)
            paginated_query = self.apply_pagination(filtered_query, pagination)
            return paginated_query.all()
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise exceptions.ForbiddenError(detail='Error while getting {} list.'.format(self.instance_name))

    def get_detail(self, id):
        try:
            return self.get_query().filter(self.model.id == id).one()
        except orm_exc.NoResultFound:
            raise exceptions.ObjectNotFound(source={'parameter': 'id'},
                                            detail='{} {} not found.'.format(self.instance_name.capitalize(), id))
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise exceptions.ForbiddenError(detail='Error while getting {} details.'.format(self.instance_name))

    def delete(self, id):
        obj = self.get_detail(id)
        try:
            self.session.delete(obj)
            self.session.flush()
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise exceptions.ForbiddenError(detail='Error while deleting {}.'.format(self.instance_name))

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
            raise exceptions.ForbiddenError(detail='Error while updating {}.'.format(self.instance_name))

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

    def apply_pagination(self, query, pagination):
        pagination = pagination or {}
        size = pagination.get('size')
        number = pagination.get('number')
        if size is not None and number is not None:
            return query.limit(size).offset(size * (number - 1))
        else:
            return query

    def build(self, kwargs):
        return self.model(**kwargs)

    def update_attribute(self, obj, key, new_value):
        setattr(obj, key, new_value)

    def get_count(self, filters=None):
        query = self.get_query()
        filtered_query = self.apply_filters(query, filters)
        count_query = filtered_query.statement.with_only_columns([func.count()])
        return self.session.execute(count_query).scalar()


class SqlAlchemyRelationshipRepositoryMixin:
    session = None
    parent_model_repository = None
    related_model_repository = None
    relationship_name = None
    id_attribute = 'id'

    @property
    def _error_message(self):
        return "Error while updating '{}' relationship.".format(self.relationship_name)

    def _get_parent(self, parent_id):
        parent = self.parent_model_repository.get_detail(parent_id)
        return parent

    def _get_current_related_objects(self, parent):
        return getattr(parent, self.relationship_name)

    def _flush(self):
        try:
            self.session.flush()
        except exc.SQLAlchemyError as error:
            logger.exception(error)
            raise exceptions.ForbiddenError(detail=self._error_message)


class SqlAlchemyToOneRelationshipRepository(SqlAlchemyRelationshipRepositoryMixin,
                                            repositories.ToOneRelationshipRepository):
    def get_detail(self, parent_id):
        parent = self._get_parent(parent_id)
        object_ = self._get_current_related_objects(parent)
        assert not isinstance(object_, list)
        return object_

    def update(self, parent_id, data):
        assert not isinstance(data, list)
        parent = self._get_parent(parent_id)
        object_ = self.related_model_repository.get_detail(data[self.id_attribute])
        self._update_relationship(parent, object_)
        self._flush()
        return object_

    def delete(self, parent_id):
        parent = self._get_parent(parent_id)
        self._update_relationship(parent, None)
        self._flush()
        return None

    def _update_relationship(self, parent, object_):
        setattr(parent, self.relationship_name, object_)


class SqlAlchemyToManyRelationshipRepository(SqlAlchemyRelationshipRepositoryMixin,
                                             repositories.ToManyRelationshipRepository):
    def get_list(self, parent_id):
        parent = self._get_parent(parent_id)
        objects = self._get_current_related_objects(parent)
        assert isinstance(objects, list)
        return objects

    def create(self, parent_id, data):
        assert isinstance(data, list)
        parent = self._get_parent(parent_id)
        objects_ids = self._get_objects_ids(data)
        self._add_to_relationship(parent, objects_ids)
        self._flush()
        return self._get_current_related_objects(parent)

    def update(self, parent_id, data):
        assert isinstance(data, list)
        parent = self._get_parent(parent_id)
        objects_ids = self._get_objects_ids(data)

        self._add_to_relationship(parent, objects_ids)

        objects_ids_to_delete = self._get_objects_ids_to_delete_in_update(parent, objects_ids)
        self._delete_from_relationship(parent, objects_ids_to_delete)

        self._flush()
        return self._get_current_related_objects(parent)

    def delete(self, parent_id, data):
        assert isinstance(data, list)
        parent = self._get_parent(parent_id)
        objects_ids = self._get_objects_ids(data)
        self._delete_from_relationship(parent, objects_ids)
        self._flush()
        return self._get_current_related_objects(parent)

    def _get_objects_ids(self, data):
        return [object_[self.id_attribute] for object_ in data]

    def _add_to_relationship(self, parent, objects_ids):
        objects_to_add = self._get_objects_to_add(parent, objects_ids)
        current_related_objects = self._get_current_related_objects(parent)
        current_related_objects.extend(objects_to_add)

    def _get_objects_to_add(self, parent, objects_ids):
        current_related_objects_ids = self._get_current_related_objects_ids(parent)
        objects_ids_to_add = list(set(objects_ids) - set(current_related_objects_ids))
        objects_to_add = self._get_objects(objects_ids_to_add)
        return objects_to_add

    def _get_current_related_objects_ids(self, parent):
        return [getattr(object_, self.id_attribute) for object_ in self._get_current_related_objects(parent)]

    def _get_objects(self, objects_ids):
        return [self.related_model_repository.get_detail(id) for id in objects_ids]

    def _get_objects_ids_to_delete_in_update(self, parent, objects_ids):
        current_related_objects_ids = self._get_current_related_objects_ids(parent)
        objects_ids_to_delete = list(set(current_related_objects_ids) - set(objects_ids))
        return objects_ids_to_delete

    def _delete_from_relationship(self, parent, objects_ids):
        objects_to_delete = self._get_objects_to_delete(parent, objects_ids)
        self._delete_objects_from_relationship(parent, objects_to_delete)

    def _get_objects_to_delete(self, parent, objects_ids):
        current_related_objects_ids = self._get_current_related_objects_ids(parent)
        objects_ids_to_delete = list(set(objects_ids) & set(current_related_objects_ids))
        if len(objects_ids) != len(objects_ids_to_delete):
            raise exceptions.ForbiddenError(detail=self._error_message)
        objects_to_delete = self._get_objects(objects_ids_to_delete)
        return objects_to_delete

    def _delete_objects_from_relationship(self, parent, objects_to_delete):
        current_related_objects = self._get_current_related_objects(parent)
        for object_ in objects_to_delete:
            current_related_objects.remove(object_)


class SqlAlchemyAssociationRepository(SqlAlchemyToManyRelationshipRepository):
    association_model = None
    parent_id_attribute = None

    def get_query(self):
        return self.association_model.query

    def _get_objects_to_add(self, parent, objects_ids):
        current_related_objects_ids = self._get_current_related_objects_ids(parent)
        objects_ids_to_add = list(set(objects_ids) - set(current_related_objects_ids))
        objects_to_add = self._create_objects(objects_ids_to_add)
        return objects_to_add

    def _create_objects(self, objects_ids_to_add):
        return [self._build_object({self.id_attribute: id}) for id in objects_ids_to_add]

    def _build_object(self, kwargs):
        return self.association_model(**kwargs)

    def _get_objects_to_delete(self, parent, objects_ids):
        current_related_objects_ids = self._get_current_related_objects_ids(parent)
        objects_ids_to_delete = list(set(objects_ids) & set(current_related_objects_ids))
        if len(objects_ids) != len(objects_ids_to_delete):
            raise exceptions.ForbiddenError(detail=self._error_message)
        objects_to_delete = self._get_objects(parent, objects_ids_to_delete)
        return objects_to_delete

    def _get_objects(self, parent, objects_ids):
        id_attribute_orm_field = getattr(self.association_model, self.id_attribute)
        parent_id_attribute_orm_field = getattr(self.association_model, self.parent_id_attribute)
        objects = (self.get_query()
                   .filter(id_attribute_orm_field.in_(objects_ids))
                   .filter(parent_id_attribute_orm_field == parent.id)
                   .all())
        if len(objects) != len(objects_ids):
            raise exceptions.ForbiddenError(detail=self._error_message)
        return objects
