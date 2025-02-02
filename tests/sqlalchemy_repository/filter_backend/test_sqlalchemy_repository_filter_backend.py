import pytest
import sqlalchemy

from sqlalchemy import orm

from flask_jsonapi.resource_repositories import sqlalchemy_repositories

Base = sqlalchemy.orm.declarative_base()


class User(Base):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    date_joined = sqlalchemy.Column(sqlalchemy.DateTime)
    email = sqlalchemy.Column(sqlalchemy.String)
    experience_level = sqlalchemy.Column(sqlalchemy.Integer)
    address_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('address.id'))
    address = orm.relationship("Address", back_populates="user")


class Address(Base):
    __tablename__ = 'address'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    email = sqlalchemy.Column(sqlalchemy.String)
    user = orm.relationship("User", back_populates="address")


@pytest.fixture
def user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

    return UserRepository()


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestFilterMethods:
    def test_equal(self, user_repository):
        user_repository.create({'name': 'Mr. Bean'})
        user_repository.create({'name': 'Darth Vader'})
        users = user_repository.get_list(filters={
            'name': 'Darth Vader',
        })
        assert len(users) == 1
        assert users[0].name == 'Darth Vader'

    def test_not_equal(self, user_repository):
        user_repository.create({'name': 'Mr. Bean'})
        user_repository.create({'name': 'Darth Vader'})
        users = user_repository.get_list(filters={'name__ne': 'Darth Vader'})
        assert len(users) == 1
        assert users[0].name == 'Mr. Bean'

    def test_contains(self, user_repository):
        user_repository.create({'name': 'Mr. Bean', 'email': 'bean@email.com'})
        user_repository.create({'name': 'Darth Vader', 'email': 'vader@email.com'})
        users = user_repository.get_list({'email__contains': 'bean'})
        assert len(users) == 1
        assert users[0].name == 'Mr. Bean'

    def test_not_like(self, user_repository):
        user_repository.create({'name': 'Mr. Bean', 'email': 'bean@email.com'})
        user_repository.create({'name': 'Darth Vader', 'email': 'vader@email.com'})
        users = user_repository.get_list({'email__notcontains': '%bean%'})
        assert len(users) == 1
        assert users[0].name == 'Darth Vader'

    def test_less_than(self, user_repository):
        user_repository.create({'name': 'Mr. Bean', 'experience_level': 3})
        user_repository.create({'name': 'Darth Vader', 'experience_level': 9000})
        users = user_repository.get_list({'experience_level__lt': 100})
        assert len(users) == 1
        assert users[0].name == 'Mr. Bean'

    def test_less_than_equal(self, user_repository):
        user_repository.create({'name': 'Mr. Bean', 'experience_level': 3})
        user_repository.create({'name': 'Darth Vader', 'experience_level': 9000})
        users = user_repository.get_list({'experience_level__lte': 3})
        assert len(users) == 1
        assert users[0].name == 'Mr. Bean'

    def test_greater_than(self, user_repository):
        user_repository.create({'name': 'Mr. Bean', 'experience_level': 3})
        user_repository.create({'name': 'Darth Vader', 'experience_level': 9000})
        users = user_repository.get_list({'experience_level__gt': 100})
        assert len(users) == 1
        assert users[0].name == 'Darth Vader'

    def test_greater_than_equal(self, user_repository):
        user_repository.create({'name': 'Mr. Bean', 'experience_level': 3})
        user_repository.create({'name': 'Darth Vader', 'experience_level': 9000})
        users = user_repository.get_list({'experience_level__gte': 9000})
        assert len(users) == 1
        assert users[0].name == 'Darth Vader'

    def test_in(self, user_repository):
        user_repository.create({'name': 'Mr. Bean', 'experience_level': 3})
        user_repository.create({'name': 'Darth Vader', 'experience_level': 9000})
        user_repository.create({'name': 'Marcin Kopec', 'experience_level': 420})
        users = user_repository.get_list({'name__in': ['Mr. Bean', 'Marcin Kopec']})
        assert len(users) == 2

    def test_if_exception_is_raised_for_unknown_column_in_filter(self, user_repository):
        user_repository.create({'name': 'Mr. Bean'})
        with pytest.raises(ValueError) as e:
            user_repository.get_list(filters={'last_name': 'Doe'})
        assert 'Could not find column for filter "last_name"' in str(e.value)

    def test_if_exception_is_raised_for_unknown_related_column_in_filter(self, user_repository):
        user_repository.create({'name': 'Mr. Bean'})
        with pytest.raises(ValueError) as e:
            user_repository.get_list(filters={'address__street': 'x@x.com'})
        assert 'Could not find column for filter "address__street"' in str(e.value)

    def test_if_exception_is_raised_for_unknown_operator_in_filter(self, user_repository):
        user_repository.create({'name': 'Mr. Bean'})
        with pytest.raises(ValueError) as e:
            user_repository.get_list(filters={'name__exactly': 'Mr. Bean'})
        assert "No idea what to do with 'exactly'" in str(e.value)
