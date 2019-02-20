import pytest
import sqlalchemy

from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

from flask_jsonapi.resource_repositories import sqlalchemy_repositories

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    addresses = orm.relationship("Address", backref="user")


class Address(Base):
    __tablename__ = 'address'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    email = sqlalchemy.Column(sqlalchemy.String)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('user.id'))


@pytest.fixture
def user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

    return UserRepository()


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestOneToMany:
    def test_basic(self, user_repository):
        bean_address = Address(email='bean@email.com')
        vader_address = Address(email='vader@email.com')
        other_vader_address = Address(email='vader@sith.com')
        user_repository.create({'name': 'Mr. Bean', 'addresses': [bean_address]})
        user_repository.create({'name': 'Darth Vader', 'addresses': [vader_address, other_vader_address]})
        filters = {'addresses__email': 'vader@sith.com'}
        users = user_repository.get_list(filters=filters)
        assert len(users) == 1
        assert users[0].name == 'Darth Vader'
