from marshmallow_jsonapi import fields


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
