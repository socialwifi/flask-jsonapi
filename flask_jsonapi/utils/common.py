import flask
import sqlalchemy.orm

from marshmallow_jsonapi import fields

from flask_jsonapi import exceptions


class EqualityMixin:
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__
        else:
            return NotImplemented


def field_exist(schema, field):
    return schema._declared_fields.get(field) is not None


def is_field_mapped(schema, field):
    if not field_exist(schema, field):
        raise ValueError('{} has no attribute {}'.format(schema.__name__, field))
    return schema._declared_fields[field].attribute is not None


def is_relationship(schema, field: str):
    if not field_exist(schema, field):
        raise ValueError('{} has no attribute {}'.format(schema.__name__, field))
    field = schema._declared_fields[field]
    return isinstance(field, fields.Relationship)


def get_model_field(schema, field):
    if is_field_mapped(schema, field):
        return schema._declared_fields[field].attribute
    return field


def get_field_class(schema, field, default=fields.Str):
    if type(schema._declared_fields.get(field)) == fields.Relationship:
        return default
    if schema._declared_fields.get(field) is None:
        return default
    return type(schema._declared_fields[field])


def get_account_id():
    try:
        return flask.request.oauth['account_id']
    except (AttributeError, KeyError):
        raise exceptions.BadRequest(source={}, detail='Unauthenticated user.')


def get_account_role_name(role_model, parent, account_id):
    """
    Use partial(get_account_role, [role_model]) to pass this function to Permission Manager
    """
    try:
        return role_model.query.filter_by(
            generic_foreign_key_table=parent.name,
            generic_foreign_key_id=parent.id,
            account_id=account_id,
        ).one().name
    except sqlalchemy.orm.exc.NoResultFound:
        return None
