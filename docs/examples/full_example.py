import flask
import sqlalchemy
import sqlalchemy.orm

from marshmallow_jsonapi import Schema
from marshmallow_jsonapi import fields

import flask_jsonapi

from flask_jsonapi import exceptions
from flask_jsonapi import guards
from flask_jsonapi import permissions
from flask_jsonapi.data_services import sqlalchemy_repositories

# One in-memory database shared by every thread of the development server.
engine = sqlalchemy.create_engine(
    'sqlite://', poolclass=sqlalchemy.pool.StaticPool, connect_args={'check_same_thread': False},
)
session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker(bind=engine))
Base = sqlalchemy.orm.declarative_base()


class Author(Base):
    __tablename__ = 'authors'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False)


class Article(Base):
    __tablename__ = 'articles'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    body = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='')
    author_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('authors.id'), nullable=False)
    author = sqlalchemy.orm.relationship(Author)


class AuthorSchema(Schema):
    id = fields.Int(as_string=True)
    name = fields.Str(required=True)

    class Meta:
        type_ = 'authors'


class ArticleSchema(Schema):
    id = fields.Int(as_string=True)
    title = fields.Str(required=True)
    body = fields.Str()
    author = fields.Relationship(
        type_='authors', include_resource_linkage=True, schema='AuthorSchema', dump_only=True,
    )

    class Meta:
        type_ = 'articles'


class AuthorRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
    model = Author
    session = session


class ArticleRepository(sqlalchemy_repositories.SqlAlchemyModelRepository):
    model = Article
    session = session


# Fixed tokens for the example only. A real application checks a token against its identity provider.
DEMO_TOKENS = {
    'alice-token': 1,
    'bob-token': 2,
}


def current_author_id():
    scheme, _, token = flask.request.headers.get('Authorization', '').partition(' ')
    if scheme != 'Bearer':
        return None
    return DEMO_TOKENS.get(token)


class RequireToken(guards.Guard):
    def check(self, action):
        if current_author_id() is None:
            raise exceptions.Unauthorized(detail='A valid bearer token is required.')


class AuthorCanChange(permissions.PermissionChecker):
    def check_create_permission(self, *, data):
        return {**data, 'author_id': current_author_id()}

    def check_read_permission(self, *, resource):
        return resource

    def check_update_permission(self, *, resource, data):
        return self._check_author(resource), data

    def check_destroy_permission(self, *, resource):
        return self._check_author(resource)

    @staticmethod
    def _check_author(article):
        if article.author_id != current_author_id():
            raise permissions.PermissionException(detail='Only the author can change an article.')
        return article


class AuthorPermissions(permissions.CheckObjectPermission):
    permission_checker = AuthorCanChange()

    def apply_permission_filter(self, filters):
        return dict(filters)


class AuthorViewSet(flask_jsonapi.ViewSet):
    schema_class = AuthorSchema
    data_service = AuthorRepository()
    allowed_actions = {
        flask_jsonapi.Actions.read,
        flask_jsonapi.Actions.list,
    }
    guards = [RequireToken()]


class ArticleViewSet(flask_jsonapi.ViewSet):
    schema_class = ArticleSchema
    data_service = ArticleRepository()
    allowed_actions = {
        flask_jsonapi.Actions.create,
        flask_jsonapi.Actions.read,
        flask_jsonapi.Actions.list,
        flask_jsonapi.Actions.update,
    }
    guards = [RequireToken()]
    object_permissions = AuthorPermissions()


app = flask.Flask(__name__)
api = flask_jsonapi.Api(app)
api.repository(AuthorViewSet(), 'authors', '/authors/')
api.repository(ArticleViewSet(), 'articles', '/articles/')


@app.teardown_appcontext
def remove_session(exception):
    session.remove()


def create_database():
    Base.metadata.create_all(engine)
    session.add_all([Author(id=1, name='Alice'), Author(id=2, name='Bob')])
    session.commit()


if __name__ == '__main__':
    create_database()
    app.run(host='127.0.0.1', port=5000)
