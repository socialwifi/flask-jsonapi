from marshmallow_jsonapi import fields
from marshmallow import ValidationError


class CompleteNestedRelationship(fields.Relationship):
    def extract_value(self, data):
        """Extract the object with data and validate the request structure."""
        errors = []
        if 'type' not in data:
            errors.append('Must have a `type` field')
        elif data['type'] != self.type_:
            errors.append('Invalid `type` specified')

        if errors:
            raise ValidationError(errors)
        data = {'data': data}
        schema = self.schema
        result = schema.load(data)
        return result.data

    def _serialize(self, value, attr, obj):
        dict_class = self.parent.dict_class if self.parent else dict

        ret = dict_class()
        self_url = self.get_self_url(obj)
        related_url = self.get_related_url(obj)
        if self_url or related_url:
            ret['links'] = dict_class()
            if self_url:
                ret['links']['self'] = self_url
            if related_url:
                ret['links']['related'] = related_url

        if self.include_resource_linkage or self.include_data:
            if value is None:
                ret['data'] = [] if self.many else None
            else:
                ret['data'] = self._serialize_included(value)
        return ret

    def _serialize_included(self, value):
        if self.many:
            included_resource = []
            for item in value:
                data = self._serialize_included_child(item)
                included_resource.append(data)
        else:
            included_resource = self._serialize_included_child(value)
        return included_resource

    def _serialize_included_child(self, value):
        result = self.schema.dump(value, **self._id_map_if_exist_in_parent_schema())
        if result.errors:
            raise ValidationError(result.errors)
        return result.data['data']

    def _id_map_if_exist_in_parent_schema(self):
        return {'id_map': self.parent.id_map} if hasattr(self.parent, 'id_map') else {}
