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
    profile = orm.relationship("Profile", uselist=False, backref="user")


class Profile(Base):
    __tablename__ = 'profile'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    premium_membership = sqlalchemy.Column(sqlalchemy.Boolean)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('user.id'), unique=True)


@pytest.fixture
def user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

    return UserRepository()


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestOneToOne:
    def test_basic(self, user_repository):
        regular_member_profile = Profile(premium_membership=False)
        premium_member_profile = Profile(premium_membership=True)
        user_repository.create({'name': 'Mr. Bean', 'profile': regular_member_profile})
        user_repository.create({'name': 'Darth Vader', 'profile': premium_member_profile})
        filters = {'profile__premium_membership': True}
        users = user_repository.get_list(filters=filters)
        assert len(users) == 1
        assert users[0].name == 'Darth Vader'
