from marshmallow_jsonapi import fields


class EqualityMixin:
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            return self.__dict__ == other.__dict__
        else:
            return NotImplemented


def get_model_field(schema, field):
    if schema._declared_fields.get(field) is None:
        raise ValueError('{} has no attribute {}'.format(schema.__name__, field))
    if schema._declared_fields[field].attribute is not None:
        return schema._declared_fields[field].attribute
    if (isinstance(schema._declared_fields[field], fields.Relationship)
            and schema._declared_fields[field].id_field is not None):
        return '{}__{}'.format(field, schema._declared_fields[field].id_field)
    return field


def get_field_class(schema, field, default=fields.Str):
    if type(schema._declared_fields.get(field)) == fields.Relationship:
        return default
    if schema._declared_fields.get(field) is None:
        return default
    return type(schema._declared_fields[field])
