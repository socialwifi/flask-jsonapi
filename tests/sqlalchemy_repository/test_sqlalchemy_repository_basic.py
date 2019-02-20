import pytest
import sqlalchemy

from sqlalchemy.ext.declarative import declarative_base

from flask_jsonapi.resource_repositories import sqlalchemy_repositories

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String)


@pytest.fixture
def user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

    return UserRepository()


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestBasic:
    def test_create(self, user_repository):
        user = user_repository.create({'id': 123, 'name': 'Mr. Bean'})
        assert user.id == 123
        assert user.name == 'Mr. Bean'

    def test_get_detail(self, user_repository):
        user_repository.create({'id': 123, 'name': 'Mr. Bean'})
        user = user_repository.get_detail(123)
        assert user.name == 'Mr. Bean'

    def test_get_list(self, user_repository):
        user_repository.create({'name': 'Mr. Bean'})
        user_repository.create({'name': 'Darth Vader'})
        users = user_repository.get_list()
        assert len(users) == 2

    def test_delete(self, user_repository):
        user_repository.create({'id': 123, 'name': 'Mr. Bean'})
        users = user_repository.get_list()
        assert len(users) == 1
        user_repository.delete(123)
        users = user_repository.get_list()
        assert len(users) == 0

    def test_update(self, user_repository):
        user = user_repository.create({'id': 123, 'name': 'Mr. Bean'})
        assert user.name == 'Mr. Bean'
        user = user_repository.update({'id': 123, 'name': 'Darth Vader'})
        assert user.name == 'Darth Vader'
