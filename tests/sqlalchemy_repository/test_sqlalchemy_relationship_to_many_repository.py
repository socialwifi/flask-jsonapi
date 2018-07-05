import pytest
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy.ext.declarative import declarative_base

import flask_jsonapi
from flask_jsonapi import exceptions
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


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestSqlAlchemyRelationshipToManyRepository:
    def test_relationship_repository_to_one_view_get_existing(self, user_repository, address_repository,
                                                              user_addresses_relationship_repository):
        bean_addresses = [
            address_repository.create({'email': 'bean@email.com'}),
        ]
        vader_addresses = [
            address_repository.create({'email': 'vader@email.com'}),
            address_repository.create({'email': 'vader@sith.com'}),
        ]
        user_repository.create({'name': 'Mr. Bean', 'addresses': bean_addresses})
        vader = user_repository.create({'name': 'Darth Vader', 'addresses': vader_addresses})
        related_addresses = user_addresses_relationship_repository.get_list(vader.id)
        assert related_addresses == vader_addresses

    def test_relationship_repository_to_one_view_get_empty_list(self, user_repository,
                                                                user_addresses_relationship_repository):
        user = user_repository.create({'name': 'Mr. Bean'})
        related_profile = user_addresses_relationship_repository.get_list(user.id)
        assert related_profile == []

    def test_relationship_repository_to_one_view_get_not_existing_parent(self, user_addresses_relationship_repository):
        with pytest.raises(flask_jsonapi.exceptions.ObjectNotFound):
            user_addresses_relationship_repository.get_list(1)

    def test_relationship_repository_to_one_view_create(self, user_repository, address_repository,
                                                        user_addresses_relationship_repository):
        vader_address = address_repository.create({'email': 'vader@email.com'})
        other_vader_address = address_repository.create({'email': 'vader@sith.com'})
        vader = user_repository.create({'name': 'Darth Vader', 'addresses': [vader_address]})
        user_addresses_relationship_repository.create(
            vader.id, [{'id': other_vader_address.id}])
        assert len(vader.addresses) == 2
        assert vader_address in vader.addresses
        assert other_vader_address in vader.addresses

    def test_relationship_repository_to_one_view_create_only_not_existing(self, user_repository, address_repository,
                                                                          user_addresses_relationship_repository):
        vader_address = address_repository.create({'email': 'vader@email.com'})
        other_vader_address = address_repository.create({'email': 'vader@sith.com'})
        another_vader_address = address_repository.create({'email': 'darth@icloud.com'})
        vader = user_repository.create({'name': 'Darth Vader', 'addresses': [vader_address, other_vader_address]})
        user_addresses_relationship_repository.create(
            vader.id, [{'id': other_vader_address.id}, {'id': another_vader_address.id}])
        assert len(vader.addresses) == 3
        assert vader_address in vader.addresses
        assert other_vader_address in vader.addresses
        assert another_vader_address in vader.addresses

    def test_relationship_repository_to_one_view_update(self, user_repository, address_repository,
                                                        user_addresses_relationship_repository):
        vader_address = address_repository.create({'email': 'vader@email.com'})
        other_vader_address = address_repository.create({'email': 'vader@sith.com'})
        vader = user_repository.create({'name': 'Darth Vader', 'addresses': []})
        user_addresses_relationship_repository.update(
            vader.id, [{'id': vader_address.id}, {'id': other_vader_address.id}])
        assert len(vader.addresses) == 2
        assert vader_address in vader.addresses
        assert other_vader_address in vader.addresses

    def test_relationship_repository_to_one_view_update_full_swap(self, user_repository, address_repository,
                                                                  user_addresses_relationship_repository):
        vader_address = address_repository.create({'email': 'vader@email.com'})
        other_vader_address = address_repository.create({'email': 'vader@sith.com'})
        another_vader_address = address_repository.create({'email': 'darth@icloud.com'})
        vader = user_repository.create({'name': 'Darth Vader', 'addresses': [vader_address, other_vader_address]})
        user_addresses_relationship_repository.update(
            vader.id, [{'id': other_vader_address.id}, {'id': another_vader_address.id}])
        assert len(vader.addresses) == 2
        assert other_vader_address in vader.addresses
        assert another_vader_address in vader.addresses

    def test_relationship_repository_to_one_view_delete(self, user_repository, address_repository,
                                                        user_addresses_relationship_repository):
        vader_address = address_repository.create({'email': 'vader@email.com'})
        other_vader_address = address_repository.create({'email': 'vader@sith.com'})
        vader = user_repository.create({'name': 'Darth Vader', 'addresses': [vader_address, other_vader_address]})
        user_addresses_relationship_repository.delete(
            vader.id, [{'id': other_vader_address.id}])
        assert vader.addresses == [vader_address]

    def test_relationship_repository_to_one_view_delete_not_related_object(self, user_repository, address_repository,
                                                                           user_addresses_relationship_repository):
        vader_address = address_repository.create({'email': 'vader@email.com'})
        other_vader_address = address_repository.create({'email': 'vader@sith.com'})
        vader = user_repository.create({'name': 'Darth Vader', 'addresses': [vader_address]})
        with pytest.raises(exceptions.ForbiddenError):
            user_addresses_relationship_repository.delete(
                vader.id, [{'id': other_vader_address.id}])
