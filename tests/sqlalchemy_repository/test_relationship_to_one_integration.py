import http
import json

import marshmallow_jsonapi
import pytest
import sqlalchemy
from marshmallow_jsonapi import fields
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

from flask_jsonapi import resource_repository_views
from flask_jsonapi.resource_repositories import sqlalchemy_repositories
from tests.sqlalchemy_repository import conftest

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


class UserSchema(marshmallow_jsonapi.Schema):
    id = fields.Int(required=True)
    name = fields.Str()
    profile = fields.Relationship(type_='profile', schema='ProfileSchema')

    class Meta:
        type_ = 'user'
        strict = True


class ProfileSchema(marshmallow_jsonapi.Schema):
    id = fields.Int(required=True)
    premium_membership = fields.Bool(attribute='premium-membership')

    class Meta:
        type_ = 'profile'
        strict = True


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


@pytest.fixture
def user_profile_relationship_view(user_profile_relationship_repository):
    class UserProfileRelationshipView(resource_repository_views.ToOneRelationshipRepositoryView):
        schema = ProfileSchema
        repository = user_profile_relationship_repository

    return UserProfileRelationshipView


@pytest.fixture
def app_with_user_profile_relationship_view(app, user_profile_relationship_view):
    app.add_url_rule('/user/<int:id>/relationships/profile/',
                     view_func=user_profile_relationship_view.as_view('user_profile_relationship'))
    return app


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestRelationshipToOneIntegration:
    def test_relationship_repository_to_one_view_get_existing_integration(self, app_with_user_profile_relationship_view,
                                                                          user_repository, profile_repository):
        premium_member_profile = profile_repository.create({'premium_membership': True})
        user = user_repository.create({'name': 'Darth Vader', 'profile': premium_member_profile})
        response = app_with_user_profile_relationship_view.test_client().get(
            '/user/{}/relationships/profile/'.format(user.id),
            headers=conftest.JSONAPI_HEADERS
        )
        result = json.loads(response.data.decode('utf-8'))
        assert result == {
            'data': {
                'id': premium_member_profile.id,
                'type': 'profile'
            },
            'jsonapi': {
                'version': '1.0'
            }
        }

    def test_relationship_to_one_view_get_not_existing_integration(self, user_repository,
                                                                   app_with_user_profile_relationship_view):
        user = user_repository.create({'name': 'Mr. Bean'})
        response = app_with_user_profile_relationship_view.test_client().get(
            '/user/{}/relationships/profile/'.format(user.id),
            headers=conftest.JSONAPI_HEADERS
        )
        result = json.loads(response.data.decode('utf-8'))
        assert result == {
            'data': None,
            'jsonapi': {
                'version': '1.0'
            }
        }

    def test_relationship_to_one_view_get_missing_parent_integration(self, app_with_user_profile_relationship_view):
        response = app_with_user_profile_relationship_view.test_client().get(
            '/user/1/relationships/profile/',
            headers=conftest.JSONAPI_HEADERS
        )
        assert response.status_code == http.HTTPStatus.NOT_FOUND
