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
    addresses = orm.relationship("Address", backref="user")


class Address(Base):
    __tablename__ = 'address'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    email = sqlalchemy.Column(sqlalchemy.String)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('user.id'))


class UserSchema(marshmallow_jsonapi.Schema):
    id = fields.Int(required=True)
    name = fields.Str()
    profile = fields.Relationship(type_='profile', schema='ProfileSchema')

    class Meta:
        type_ = 'user'
        strict = True


class AddressSchema(marshmallow_jsonapi.Schema):
    id = fields.Int(required=True)
    email = fields.Str()

    class Meta:
        type_ = 'address'
        strict = True


@pytest.fixture
def user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

    return UserRepository()


@pytest.fixture
def address_repository(db_session):
    class AddressRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = Address
        instance_name = 'address'
        session = db_session

    return AddressRepository()


@pytest.fixture
def user_addresses_relationship_repository(db_session, user_repository, address_repository):
    class UserAddressesRelationshipRepository(sqlalchemy_repositories.SqlAlchemyToManyRelationshipRepository):
        session = db_session
        parent_model_repository = user_repository
        related_model_repository = address_repository
        relationship_name = 'addresses'

    return UserAddressesRelationshipRepository()


@pytest.fixture()
def user_addresses_relationship_view(user_addresses_relationship_repository):
    class UserProfileRelationshipView(resource_repository_views.ToManyRelationshipRepositoryView):
        schema = AddressSchema
        repository = user_addresses_relationship_repository

    return UserProfileRelationshipView()


@pytest.fixture
def app_with_user_addresses_relationship_view(app, user_addresses_relationship_view):
    app.add_url_rule('/user/<int:id>/relationships/addresses/',
                     view_func=user_addresses_relationship_view.as_view('user_addresses_relationship'))
    return app


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestRelationshipToManyIntegration:
    def test_relationship_to_many_view_get_existing_integration(self, user_repository, address_repository,
                                                                app_with_user_addresses_relationship_view):
        bean_address = address_repository.create({'email': 'bean@email.com'})
        bean = user_repository.create({'name': 'Mr. Bean', 'addresses': [bean_address]})
        response = app_with_user_addresses_relationship_view.test_client().get(
            '/user/{}/relationships/addresses/'.format(bean.id),
            headers=conftest.JSONAPI_HEADERS
        )
        result = json.loads(response.data.decode('utf-8'))
        assert result == {
           'data': [
              {
                 'id': bean_address.id,
                 'type': 'address'
              },
           ],
           'jsonapi': {
              'version': '1.0'
           }
        }

    def test_relationship_to_many_view_get_empty_integration(self, user_repository,
                                                             app_with_user_addresses_relationship_view):
        user = user_repository.create({'name': 'Mr. Bean'})
        response = app_with_user_addresses_relationship_view.test_client().get(
            '/user/{}/relationships/addresses/'.format(user.id),
            headers=conftest.JSONAPI_HEADERS
        )
        result = json.loads(response.data.decode('utf-8'))
        assert result == {
            'data': [],
            'jsonapi': {
                'version': '1.0'
            }
        }

    def test_relationship_to_many_view_get_missing_parent_integration(self, app_with_user_addresses_relationship_view):
        response = app_with_user_addresses_relationship_view.test_client().get(
            '/user/1/relationships/addresses/',
            headers=conftest.JSONAPI_HEADERS
        )
        assert response.status_code == http.HTTPStatus.NOT_FOUND
