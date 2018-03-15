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
                return self.handle_model_with_children(data, self.create, **kwargs)
        else:
            return self.repository.create(data, **kwargs)

    def update(self, data, **kwargs):
        if self.structure_has_nested_object(data):
            with self.repository.begin_transaction():
                return self.handle_model_with_children(data, self.update, **kwargs)
        else:
            return self.repository.update(data, **kwargs)

    def get_detail(self, id):
        return self.repository.get_detail(id)

    def get_list(self, filters=None):
        return self.repository.get_list(filters)

    def delete(self, id):
        return self.repository.delete(id)

    def structure_has_nested_object(self, data):
        return all(child_field in data.keys() for child_field in self.children_repositories.keys())

    def handle_model_with_children(self, data, method, **kwargs):
        model_dict = self.get_model_dict(data)
        model = method(model_dict, **kwargs)
        self.handle_children_objects(model, data, **kwargs)
        return model

    def get_model_dict(self, dict_with_nested_object):
        model_dict = dict_with_nested_object.copy()
        for child_field in self.children_repositories.keys():
            model_dict.pop(child_field)
        return model_dict

    def handle_children_objects(self, model, data, **kwargs):
        for child_field, children_repository_value in self.children_repositories.items():
            child_repo = self._get_child_repository(children_repository_value.repository)
            foreign_parent_name = children_repository_value.foreign_parent_name
            objects_to_create = []
            objects_to_update = []
            for child_tree in data.get(child_field):
                if '__id__' in child_tree.keys():
                    objects_to_create.append(child_tree)
                if 'id' in child_tree.keys():
                    objects_to_update.append(child_tree)
            if objects_to_update:
                [self.update_child(obj, child_repo, model, foreign_parent_name, **kwargs) for obj in objects_to_update]
                current_children_ids = set([child.id for child in getattr(model, child_field)])
                objects_ids = [obj['id'] for obj in objects_to_update]
                object_ids_to_delete = list(current_children_ids - set(objects_ids))
                [self.delete_child(object_id, child_repo) for object_id in object_ids_to_delete]
            else:
                [self.delete_child(child.id, child_repo) for child in getattr(model, child_field)]
            if objects_to_create:
                [self.create_child(obj, child_repo, model, foreign_parent_name, **kwargs) for obj in objects_to_create]

    def _get_child_repository(self, repository):
        return NestedRepository(repository) if hasattr(repository, 'children_repositories') else repository

    @staticmethod
    def create_child(obj, child_repo, model, parent_fk_name, **kwargs):
        obj[parent_fk_name] = model.id
        mapper = IdMapper(kwargs['id_map'])
        obj = mapper.remove_id(obj)
        object_model = child_repo.create(obj, **kwargs)
        mapper.map_ids(object_model.id)

    @staticmethod
    def update_child(obj, child_repo, model, parent_fk_name, **kwargs):
        obj[parent_fk_name] = model.id
        child_repo.update(obj, **kwargs)

    @staticmethod
    def delete_child(object_id, child_repo):
        child_repo.delete(object_id)

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
