from unittest import mock

from flask_jsonapi import nested_repository


class Repository:
    def create(self, data, **kwargs):
        pass


class TestUtils:
    def test_underscorize(self):
        orignal = "some name of class"
        underscorize_text = nested_repository.NestedRepository.underscorize(orignal)
        assert 'some_name_of_class' == underscorize_text


class TestRecognisingNestedObjects:
    def test_if_is_recognised_that_structure_has_nested_objects(self):
        nested_repo = nested_repository.NestedRepository(mock.Mock())
        nested_repo.children_repositories = {
            'children': mock.Mock(),
        }
        data = {
            'atr1': 1,
            'children': [{}]
        }
        has_nested_objects = nested_repo.structure_has_nested_object(data)
        assert has_nested_objects is True

    def test_if_is_recognised_that_structure_has_not_nested_objects(self):
        nested_repo = nested_repository.NestedRepository(mock.Mock())
        nested_repo.children_repositories = {
            'children': mock.Mock(),
        }
        data = {
            'atr1': 1,
        }
        has_nested_objects = nested_repo.structure_has_nested_object(data)
        assert has_nested_objects is False

    def test_if_model_recognised_that_request_has_not_all_nested_objects(self):
        nested_repo = nested_repository.NestedRepository(mock.Mock())
        nested_repo.children_repositories = {
            'children1': mock.Mock(),
            'children2': mock.Mock(),
        }
        data = {
            'atr1': 1,
            'children1': [{}]
        }
        has_nested_objects = nested_repo.structure_has_nested_object(data)
        assert has_nested_objects is False


class TestParsingModelDict:
    def test_if_model_dict_if_returned(self):
        nested_repo = nested_repository.NestedRepository(mock.Mock())
        nested_repo.children_repositories = {
            'children': mock.Mock(),
        }
        kwargs = {
            'atr1': 1,
            'children': [{}]
        }
        result = nested_repo.get_model_dict(kwargs)
        expected = {
            'atr1': 1,
        }
        assert result == expected


class TestCreatingChildredModels:
    def test_creating_children_models(self):
        model = mock.Mock()
        model.id = 4444444444
        nested_repo = nested_repository.NestedRepository(mock.Mock())
        child_repositorium_object = Repository()
        created_object = mock.Mock()
        created_object.id = 7777777
        child_repositorium_object.create = mock.Mock(return_value=created_object)
        nested_repo.children_repositories = {
            'children': nested_repository.ChildRepository(
                repository=child_repositorium_object,
                foreign_parent_name='parent_name_id'
            )
        }
        data = {
            'atr1': 1,
            'children': [
                {
                    '__id__': 120,
                    'art_child': 66,
                }
            ]
        }
        kwargs = {'id_map': {}}
        nested_repo.create_children_models(model, data, **kwargs)
        expected_parametes = {
            'art_child': 66,
            'parent_name_id': 4444444444
        }
        kwargs = {
            'id_map': {7777777: 120}
        }
        child_repositorium_object.create.assert_called_with(expected_parametes, **kwargs)


