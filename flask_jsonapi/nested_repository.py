import collections

from flask_jsonapi import exceptions

ChildRepository = collections.namedtuple('ChildRepository', 'repository foreign_parent_name')


class NestedRepository:
    children_repositories = {}

    def __init__(self, repository):
        self.repository = repository
        try:
            self.children_repositories = repository.children_repositories
        except AttributeError:
            self.children_repositories = {}

    def create(self, data, **kwargs):
        if self.structure_has_nested_object(data) and self.children_repositories != {}:
            return self.create_model_with_children(data, **kwargs)
        else:
            return self.repository.create(data, **kwargs)

    def get_detail(self, id):
        return self.repository.get_detail(id)

    def get_list(self, filters=None):
        return self.repository.get_list(filters)

    def delete(self, id):
        return self.repository.delete(id)

    def update(self, id, **data):
        return self.repository.update(id, **data)

    def create_model_with_children(self, data, **kwargs):
        model_dict = self.get_model_dict(data)
        model = self.create(model_dict, **kwargs)
        self.create_children_models(model, data,  **kwargs)
        return model

    def structure_has_nested_object(self, data):
        return all(child_field in data.keys() for child_field in self.children_repositories.keys())

    def get_model_dict(self, dict_with_nested_object):
        model_dict = dict_with_nested_object.copy()
        for child_field in self.children_repositories.keys():
            model_dict.pop(child_field)
        return model_dict

    def create_children_models(self, model, data,  **kwargs):
        for child_field in self.children_repositories.keys():
            for child_tree in data.get(child_field):
                parent_foreign_key_name = self.children_repositories[child_field].foreign_parent_name
                child_tree[parent_foreign_key_name] = model.id
                __id__ = IdMapper.pop_id(child_tree)
                nested_child_repo = NestedRepository(self.children_repositories[child_field].repository)
                children_model = nested_child_repo.create(child_tree, **kwargs)
                IdMapper.map_ids(kwargs['id_map'], __id__, children_model)

    @staticmethod
    def underscorize(text):
        return text.replace(' ', '_')


class IdMapper:
    temp_id_name = '__id__'

    @staticmethod
    def map_ids(id_map,  __id__, model):
        id_map[model.id] = __id__

    @staticmethod
    def pop_id(data):
        try:
            return data.pop(IdMapper.temp_id_name)
        except KeyError:
            raise exceptions.BadRequest(
                source="Lack of {}".format(IdMapper.temp_id_name),
                detail="Nested objects mush have temporary id in attribute."
            )
