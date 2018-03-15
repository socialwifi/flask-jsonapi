from contextlib import contextmanager
from unittest import mock

import pytest

from flask_jsonapi.resource_repositories import repositories
from flask_jsonapi.nested import nested_repository


class Repository:
    def create(self, data, **kwargs):
        pass

    def update(self, data, **kwargs):
        pass

    def delete(self, id):
        pass


class RepositoryWithBeginTransaction(repositories.ResourceRepository):
    children_repositories = {}
    very_important_test_value = 0

    @contextmanager
    def begin_transaction(self):
        self.very_important_test_value = 999
        yield
        self.very_important_test_value = 0


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


class TestCreatingNestedRepo:
    def test_creating_nested_repository_raise_attr_error(self):
        repo = Repository()
        with pytest.raises(AttributeError):
            nested_repository.NestedRepository(repo)


class TestCreatingChildrenModels:
    def test_creating_children_models(self):
        model = mock.Mock()
        model.id = 4444444444
        model.children = []
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
        nested_repo.handle_children_objects(model, data,  **kwargs)
        expected_parametes = {
            'art_child': 66,
            'parent_name_id': 4444444444
        }
        kwargs = {
            'id_map': {7777777: 120}
        }
        child_repositorium_object.create.assert_called_with(expected_parametes, **kwargs)


class TestUpdatingChildrenModels:
    class ParentRepository(RepositoryWithBeginTransaction):
        def update(self, *args, **kwargs):
            parent = mock.Mock()
            parent.id = 4444444444
            child1 = mock.Mock()
            child1.id = 1
            child1.name = 'Tom'
            child2 = mock.Mock()
            child2.id = 2
            child2.name = 'Pat'
            parent.children = [child1, child2]
            return parent

    def setup_parent(self):
        parent = mock.Mock()
        parent.id = 4444444444
        parent_repository = self.ParentRepository()
        child_repository_object = Repository()
        parent_repository.children_repositories = {
            'children': nested_repository.ChildRepository(
                repository=child_repository_object,
                foreign_parent_name='parent_name_id'
            )
        }
        nested_repo = nested_repository.NestedRepository(repository=parent_repository)
        return nested_repo, child_repository_object, parent.id

    def test_updating_child_which_was_present_but_has_changed(self):
        nested_repo, child_repository_object, parent_id = self.setup_parent()
        updated_object = mock.Mock()
        updated_object.id = 1
        child_repository_object.update = mock.Mock(return_value=updated_object)
        data = {
            'atr1': 1,
            'children': [
                {
                    'id': 1,
                    'name': 'Janek Pochodnia',
                },
                {
                    'id': 2,
                    'name': 'Pat Petarda',
                },
            ]
        }
        expected_parametes = {
            'id': 1,
            'name': 'Janek Pochodnia',
            'parent_name_id': 4444444444
        }
        nested_repo.update(data)
        args, _ = child_repository_object.update.call_args_list[0]
        assert args == (expected_parametes,)
        expected_parametes = {
            'id': 2,
            'name': 'Pat Petarda',
            'parent_name_id': 4444444444
        }
        args, _ = child_repository_object.update.call_args_list[1]
        assert args == (expected_parametes,)

    def test_creating_child_which_was_not_present(self):
        nested_repo, child_repository_object, parent_id = self.setup_parent()
        created_object = mock.Mock()
        created_object.id = 7777777
        child_repository_object.create = mock.Mock(return_value=created_object)
        data = {
            'atr1': 1,
            'children': [
                {
                    'id': 1,
                    'name': 'Tom',
                },
                {
                    'id': 2,
                    'name': 'Pat',
                },
                {
                    '__id__': 120,
                    'name': 'JOHN CENA',
                }
            ]
        }
        kwargs = {
            'id_map': {7777777: 120}
        }
        expected_parametes = {
            'name': 'JOHN CENA',
            'parent_name_id': 4444444444
        }
        nested_repo.update(data, **kwargs)
        child_repository_object.create.assert_called_with(expected_parametes, **kwargs)

    def test_deleting_child_which_was_present_but_now_is_not(self):
        nested_repo, child_repository_object, parent_id = self.setup_parent()
        deleted_object = mock.Mock()
        deleted_object.id = 1
        child_repository_object.delete = mock.Mock()
        data = {
            'atr1': 1,
            'children': [
                {
                    'id': 2,
                    'name': 'Pat',
                },
            ]
        }
        nested_repo.update(data)
        child_repository_object.delete.assert_called_with(deleted_object.id)


class RepositoryWithOutBeginTransaction(repositories.ResourceRepository):
    children_repositories = {}
    very_important_test_value = 0


class TestTransaction:
    def test_if_function_works_in_repository_begin_transaction_if_it_exist(self):
        repo_with_begin_transaction = RepositoryWithBeginTransaction()
        nested_repo = nested_repository.NestedRepository(repo_with_begin_transaction)
        with nested_repo.repository.begin_transaction():
            assert repo_with_begin_transaction.very_important_test_value == 999
        assert repo_with_begin_transaction.very_important_test_value == 0

    def test_if_function_works_without_transaction_if_it_not_exist_in_repo(self):
        repo_with_out_begin_transaction = RepositoryWithOutBeginTransaction()
        nested_repo = nested_repository.NestedRepository(repo_with_out_begin_transaction)
        with nested_repo.repository.begin_transaction():
            assert repo_with_out_begin_transaction.very_important_test_value == 0
