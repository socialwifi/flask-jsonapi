from marshmallow_jsonapi import fields


class IdMappingSchema:
    __id__ = fields.Str(required=False)

    def dump(self, obj, many=None, update_fields=True, **kwargs):
        self.id_map = kwargs.pop('id_map', None)
        if self.id_map is not None:
            if hasattr(obj, 'id') and obj.id in self.id_map.keys():
                obj.__id__ = self.id_map[obj.id]
        return super().dump(obj, many, update_fields, **kwargs)
