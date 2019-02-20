import pytest
import sqlalchemy

from sqlalchemy.ext.declarative import declarative_base

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
class TestIntegration:
    def test_getting_list_with_pagination_and_sorting(self, user_repository):
        user_repository.create({'id': 1, 'name': 'Betty'})
        kate = user_repository.create({'id': 2, 'name': 'Kate'})
        mary = user_repository.create({'id': 3, 'name': 'Mary'})
        users = user_repository.get_list(pagination={'size': 2, 'number': 1}, sorting=['-name'])
        assert users == [mary, kate]
