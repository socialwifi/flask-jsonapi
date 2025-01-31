import pytest
import sqlalchemy

from flask_jsonapi.resource_repositories import sqlalchemy_repositories

Base = sqlalchemy.orm.declarative_base()


class User(Base):
    __tablename__ = 'user'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    type = sqlalchemy.Column(sqlalchemy.Text, nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': type,
    }


class SpecialUser(User):
    __tablename__ = 'special_user'
    id = sqlalchemy.Column(sqlalchemy.ForeignKey('user.id'), primary_key=True)
    special_value = sqlalchemy.Column(sqlalchemy.Integer)

    __mapper_args__ = {
        'polymorphic_identity': 'special_user',
    }


@pytest.fixture
def special_user_repository(db_session):
    class SpecialUserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = SpecialUser
        instance_name = 'special_user'
        session = db_session

    return SpecialUserRepository()


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestInheritance:
    def test_filtering_using_parent_attributes(self, special_user_repository):
        special_user_repository.create({
            'name': 'Mr. Bean',
            'special_value': 5,
        })
        filters = {'name': 'Mr. Bean'}
        users = special_user_repository.get_list(filters=filters)
        assert len(users) == 1
        assert users[0].name == 'Mr. Bean'

    def test_filtering_using_child_attributes(self, special_user_repository):
        special_user_repository.create({
            'name': 'Mr. Bean',
            'special_value': 5,
        })
        filters = {'special_value': 5}
        users = special_user_repository.get_list(filters=filters)
        assert len(users) == 1
        assert users[0].name == 'Mr. Bean'
