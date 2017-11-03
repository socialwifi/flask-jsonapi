from contextlib import contextmanager
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
            raise AttributeError("If nested is true, repository must have attr children_repositories")

    def create(self, data, **kwargs):
        if self.structure_has_nested_object(data):
            with self.repository.begin_transaction():
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
        for child_field, children_repository_value in self.children_repositories.items():
            for child_tree in data.get(child_field):
                parent_foreign_key_name = children_repository_value.foreign_parent_name
                child_tree[parent_foreign_key_name] = model.id
                mapper = IdMapper(kwargs['id_map'])
                child_tree = mapper.remove_id(child_tree)
                child_repo = self._get_child_repository(children_repository_value.repository)
                children_model = child_repo.create(child_tree, **kwargs)
                mapper.map_ids(children_model.id)

    def _get_child_repository(self, repository):
        return NestedRepository(repository) if hasattr(repository, 'children_repositories') else repository

    @staticmethod
    def underscorize(text):
        return text.replace(' ', '_')


class IdMapper:
    temp_id_name = '__id__'

    def __init__(self, id_map):
        self.id_map = id_map

    def map_ids(self, model_id):
        self.id_map[model_id] = self.temp_id

    def remove_id(self, child_tree):
        child_tree = child_tree.copy()
        try:
            self.temp_id = child_tree.pop(self.temp_id_name)
        except KeyError:
            raise exceptions.BadRequest(
                source="Lack of {}".format(IdMapper.temp_id_name),
                detail="Nested objects mush have temporary id in attribute."
            )
        return child_tree
