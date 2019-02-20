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
class TestPagination:
    def test_basic(self, user_repository):
        bean = user_repository.create({'id': 1, 'name': 'Mr. Bean'})
        vader = user_repository.create({'id': 2, 'name': 'Darth Vader'})
        dexter = user_repository.create({'id': 3, 'name': 'Dexter'})
        sasha = user_repository.create({'id': 4, 'name': 'Sasha'})
        users_1 = user_repository.get_list(pagination={'size': 2, 'number': 1})
        assert users_1 == [
            bean,
            vader,
        ]
        users_2 = user_repository.get_list(pagination={'size': 2, 'number': 2})
        assert users_2 == [
            dexter,
            sasha,
        ]

    def test_empty_page_when_no_more_records(self, user_repository):
        bean = user_repository.create({'id': 1, 'name': 'Mr. Bean'})
        vader = user_repository.create({'id': 2, 'name': 'Darth Vader'})
        users_1 = user_repository.get_list(pagination={'size': 2, 'number': 1})
        assert users_1 == [
            bean,
            vader,
        ]
        users_2 = user_repository.get_list(pagination={'size': 2, 'number': 2})
        assert users_2 == []

    def test_get_count(self, user_repository):
        user_repository.create({'id': 1, 'name': 'Mr. Bean'})
        user_repository.create({'id': 2, 'name': 'Darth Vader'})
        count = user_repository.get_count()
        assert count == 2
