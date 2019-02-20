import pytest
import sqlalchemy

from sqlalchemy.ext.declarative import declarative_base

from flask_jsonapi import exceptions
from flask_jsonapi.resource_repositories import sqlalchemy_repositories

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    age = sqlalchemy.Column(sqlalchemy.Integer)


@pytest.fixture
def user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

    return UserRepository()


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestSort:
    def test_sorting_by_one_field_ascending(self, user_repository):
        kate = user_repository.create({'id': 1, 'name': 'Kate'})
        betty = user_repository.create({'id': 2, 'name': 'Betty'})
        users = user_repository.get_list(sorting=['name'])
        assert users == [betty, kate]

    def test_sorting_by_one_field_descending(self, user_repository):
        kate = user_repository.create({'id': 1, 'name': 'Kate'})
        betty = user_repository.create({'id': 2, 'name': 'Betty'})
        users = user_repository.get_list(sorting=['-name'])
        assert users == [kate, betty]

    def test_sorting_by_many_fields(self, user_repository):
        kate_younger = user_repository.create({'id': 1, 'name': 'Kate', 'age': 10})
        kate_older = user_repository.create({'id': 2, 'name': 'Kate', 'age': 30})
        users = user_repository.get_list(sorting=['name', 'age'])
        assert users == [kate_younger, kate_older]

    def test_sorting_by_wrong_column_name_raise_exception(self, user_repository):
        with pytest.raises(exceptions.InvalidSort):
            user_repository.get_list(sorting=['WRONG_COL_NAME'])

    def test_sorting_by_order_neither_desc_nor_acs(self, user_repository):
        with pytest.raises(exceptions.InvalidSort):
            user_repository.get_list(sorting=['!name'])
