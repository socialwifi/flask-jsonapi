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
    liked_posts = orm.relationship("Post", secondary="user_post_like", backref="users_liked")


class Post(Base):
    __tablename__ = 'post'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String)


class UserPostLike(Base):
    __tablename__ = 'user_post_like'
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('user.id'), primary_key=True)
    post_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('post.id'), primary_key=True)


@pytest.fixture
def user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

    return UserRepository()


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestManyToManySecondary:
    def test_basic(self, user_repository):
        user_repository.create({'name': 'Bjarne Stroustrup', 'liked_posts': [Post(title='C++ rocks!')]})
        user_repository.create({'name': 'James Gosling', 'liked_posts': [Post(title='Java is the best!')]})
        filters = {'liked_posts__title': 'C++ rocks!'}
        users = user_repository.get_list(filters=filters)
        assert len(users) == 1
        assert users[0].name == 'Bjarne Stroustrup'
