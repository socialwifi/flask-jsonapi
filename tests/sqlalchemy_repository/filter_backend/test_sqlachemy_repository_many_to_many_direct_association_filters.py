import datetime

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
    post_likes = orm.relationship("UserPostLike", back_populates="user")


class Post(Base):
    __tablename__ = 'post'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String)
    user_likes = orm.relationship("UserPostLike", back_populates="post")


class UserPostLike(Base):
    __tablename__ = 'user_post_like'
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('user.id'), primary_key=True)
    post_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('post.id'), primary_key=True)
    date = sqlalchemy.Column(sqlalchemy.DateTime)
    user = orm.relationship("User", back_populates="post_likes")
    post = orm.relationship("Post", back_populates="user_likes")


@pytest.fixture
def user_repository(db_session):
    class UserRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
        model = User
        instance_name = 'user'
        session = db_session

    return UserRepository()


@pytest.mark.parametrize(argnames='setup_db_schema', argvalues=[Base], indirect=True)
@pytest.mark.usefixtures('setup_db_schema')
class TestManyToManyAssociation:
    def test_basic(self, user_repository):
        stroustrup = user_repository.create({'name': 'Bjarne Stroustrup'})
        gosling = user_repository.create({'name': 'James Gosling'})
        UserPostLike(user=stroustrup, post=Post(title='C++ rocks!'))
        UserPostLike(user=gosling, post=Post(title='Java is the best!'))
        filters = {'post_likes__post__title': 'C++ rocks!'}
        users = user_repository.get_list(filters=filters)
        assert len(users) == 1
        assert users[0].name == 'Bjarne Stroustrup'

    def test_filter_by_association_attribute(self, user_repository):
        stroustrup = user_repository.create({'name': 'Bjarne Stroustrup'})
        gosling = user_repository.create({'name': 'James Gosling'})
        cpp_date = datetime.datetime.now()
        java_date = datetime.datetime.now() + datetime.timedelta(days=1)
        UserPostLike(user=stroustrup, post=Post(title='C++ rocks!'), date=cpp_date)
        UserPostLike(user=gosling, post=Post(title='Java is the best!'), date=java_date)
        filters = {'post_likes__date': cpp_date}
        users = user_repository.get_list(filters=filters)
        assert len(users) == 1
        assert users[0].name == 'Bjarne Stroustrup'
