import pytest
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

import flask_jsonapi
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


@pytest.fixture
def profile_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Profile
        instance_name = 'profile'
        session = db_session

    return UserRepository()


@pytest.fixture
def user_profile_relationship_repository(db_session, user_repository, profile_repository):
    class UserProfileRelationshipRepository(sqlalchemy_repositories.SqlAlchemyToOneRelationshipRepository):
        session = db_session
        parent_model_repository = user_repository
        related_model_repository = profile_repository
        relationship_name = 'profile'

    return UserProfileRelationshipRepository()


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestSqlAlchemyRelationshipToOneRepository:
    def test_relationship_repository_to_one_view_get_existing(self, user_repository, profile_repository,
                                                              user_profile_relationship_repository):
        regular_member_profile = profile_repository.create({'premium_membership': False})
        premium_member_profile = profile_repository.create({'premium_membership': True})
        user_repository.create({'name': 'Mr. Bean', 'profile': regular_member_profile})
        user = user_repository.create({'name': 'Darth Vader', 'profile': premium_member_profile})
        related_profile = user_profile_relationship_repository.get_detail(user.id)
        assert related_profile == premium_member_profile

    def test_relationship_repository_to_one_view_get_not_existing(self, user_repository,
                                                                  user_profile_relationship_repository):
        user = user_repository.create({'name': 'Mr. Bean'})
        related_profile = user_profile_relationship_repository.get_detail(user.id)
        assert related_profile is None

    def test_relationship_repository_to_one_view_get_not_existing_parent(self, user_profile_relationship_repository):
        with pytest.raises(flask_jsonapi.exceptions.ObjectNotFound):
            user_profile_relationship_repository.get_detail(1)

    def test_relationship_repository_to_one_view_update(self, user_repository, profile_repository,
                                                        user_profile_relationship_repository):
        regular_member_profile = profile_repository.create({'premium_membership': False})
        premium_member_profile = profile_repository.create({'premium_membership': True})
        user = user_repository.create({'name': 'Darth Vader', 'profile': regular_member_profile})
        related_profile = user_profile_relationship_repository.update(user.id, {'id': premium_member_profile.id})
        assert related_profile == premium_member_profile

    def test_relationship_repository_to_one_view_delete(self, user_repository, profile_repository,
                                                        user_profile_relationship_repository):
        premium_member_profile = profile_repository.create({'premium_membership': True})
        user = user_repository.create({'name': 'Darth Vader', 'profile': premium_member_profile})
        user_profile_relationship_repository.delete(user.id)
        assert user.profile is None
